
import os
import json
import re
import html
import time
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime


# ============================================================
# AION 2 UPDATES – NYERK24
# ============================================================

DISCORD_WEBHOOK = os.environ.get("UPDATES_WEBHOOK_URL")

API_ROOT = (
    "https://api-global-community.plaync.com/"
    "aion2_global/board/update_de"
)

BOARD_API = API_ROOT

LIST_API = (
    API_ROOT
    + "/article/search/moreArticle"
    + "?isVote=true&moreSize=18"
    + "&moreDirection=BEFORE&previousArticleId=0"
)

BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / "updates_status.json"

DELETION_CONFIRMATIONS = 2


# ============================================================
# HTTP-ANFRAGEN MIT WIEDERHOLUNGSVERSUCHEN
# ============================================================

def request_json(url, method="GET", payload=None):
    data = (
        json.dumps(
            payload,
            ensure_ascii=False
        ).encode("utf-8")
        if payload is not None
        else None
    )

    headers = {
        "User-Agent": "AION2-Discord-Bot",
        "Accept": "application/json"
    }

    if data is not None:
        headers["Content-Type"] = "application/json"

    for attempt in range(5):
        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:
                body = response.read()

                if not body:
                    return {}

                return json.loads(
                    body.decode("utf-8")
                )

        except urllib.error.HTTPError as error:
            retryable = (
                error.code == 429
                or 500 <= error.code < 600
            )

            if retryable and attempt < 4:
                retry_after = error.headers.get(
                    "Retry-After"
                )

                try:
                    delay = (
                        float(retry_after)
                        if retry_after
                        else 2 ** attempt
                    )
                except (TypeError, ValueError):
                    delay = 2 ** attempt

                time.sleep(
                    max(1, min(delay, 60))
                )
                continue

            raise

        except (
            urllib.error.URLError,
            TimeoutError
        ):
            if attempt == 4:
                raise

            time.sleep(2 ** attempt)


# ============================================================
# DISCORD-WEBHOOK
# ============================================================

def discord_url(message_id=None, wait=False):
    base = DISCORD_WEBHOOK.rstrip("/")

    if message_id is not None:
        return (
            f"{base}/messages/{message_id}"
        )

    if wait:
        return base + "?wait=true"

    return base


def discord_create(embed):
    return request_json(
        discord_url(wait=True),
        method="POST",
        payload={
            "username": "Nyerk24 · News",
            "embeds": [embed],
            "allowed_mentions": {
                "parse": []
            }
        }
    )


def discord_edit(message_id, embed):
    return request_json(
        discord_url(message_id),
        method="PATCH",
        payload={
            "embeds": [embed],
            "allowed_mentions": {
                "parse": []
            }
        }
    )


def discord_delete(message_id):
    return request_json(
        discord_url(message_id),
        method="DELETE"
    )


# ============================================================
# BILDER AUS ARTIKELN AUSLESEN
# ============================================================

def find_images(value):
    if not isinstance(value, str):
        return []

    result = []

    matches = re.findall(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        value,
        re.IGNORECASE
    )

    for image in matches:
        image = html.unescape(image)

        if image.startswith("//"):
            image = "https:" + image

        if image not in result:
            result.append(image)

    return result


def image_dimensions(url):
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:
            data = response.read(200000)

        # PNG

        if (
            data.startswith(b"\x89PNG")
            and len(data) >= 24
        ):
            width = int.from_bytes(
                data[16:20],
                "big"
            )

            height = int.from_bytes(
                data[20:24],
                "big"
            )

            return width, height

        # JPEG

        if data.startswith(b"\xff\xd8"):
            index = 2

            while index < len(data) - 9:
                if data[index] != 0xff:
                    index += 1
                    continue

                marker = data[index + 1]

                if marker in (
                    0xc0, 0xc1, 0xc2, 0xc3,
                    0xc5, 0xc6, 0xc7, 0xc9,
                    0xca, 0xcb, 0xcd, 0xce, 0xcf
                ):
                    height = int.from_bytes(
                        data[index + 5:index + 7],
                        "big"
                    )

                    width = int.from_bytes(
                        data[index + 7:index + 9],
                        "big"
                    )

                    return width, height

                length = int.from_bytes(
                    data[index + 2:index + 4],
                    "big"
                )

                if length < 2:
                    break

                index += 2 + length

    except Exception as error:
        print(
            f"Bildgröße nicht lesbar: {error}"
        )

    return None


def choose_preview_image(images):
    for image in images:
        dimensions = image_dimensions(image)

        if not dimensions:
            continue

        width, height = dimensions

        if (
            height > 0
            and width >= 500
            and height >= 250
            and 1.4 <= width / height <= 4
        ):
            return image

    return None


# ============================================================
# VERÖFFENTLICHUNGSDATUM
# ============================================================

def format_date(item):
    timestamps = item.get("timestamps") or {}

    raw = timestamps.get(
        "postDateTime",
        ""
    )

    if not raw:
        return ""

    try:
        return datetime.fromisoformat(
            raw.replace("Z", "+00:00")
        ).strftime("%d.%m.%Y")

    except (ValueError, TypeError):
        return str(raw)[:10]


# ============================================================
# STATUS LADEN UND SPEICHERN
# ============================================================

def load_state():
    if not STATE_FILE.exists():
        return {
            "posted_article_ids": [],
            "managed": {}
        }

    with STATE_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        state = json.load(file)

    if not isinstance(state, dict):
        raise ValueError(
            "Ungültige Statusdatei"
        )

    state.setdefault(
        "posted_article_ids",
        []
    )

    state.setdefault(
        "managed",
        {}
    )

    if not isinstance(
        state["posted_article_ids"],
        list
    ):
        raise ValueError(
            "Ungültige Artikel-ID-Liste"
        )

    if not isinstance(
        state["managed"],
        dict
    ):
        raise ValueError(
            "Ungültige Nachrichtenverwaltung"
        )

    return state


def save_state(state):
    temporary_file = STATE_FILE.with_suffix(
        ".json.tmp"
    )

    with temporary_file.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            state,
            file,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temporary_file,
        STATE_FILE
    )


# ============================================================
# ARTIKELDETAILS ABRUFEN
# ============================================================

def article_detail(article_id):
    url = (
        f"{API_ROOT}/article/{article_id}"
    )

    data = request_json(url)

    article = data.get("article")

    if not isinstance(article, dict):
        raise ValueError(
            f"Artikel {article_id}: "
            "Keine gültigen Artikeldaten erhalten"
        )

    content = article.get("content") or {}

    if not isinstance(content, dict):
        raise ValueError(
            f"Artikel {article_id}: "
            "Ungültiger Artikelinhalt"
        )

    raw_content = str(
        content.get("content") or ""
    )

    return article, raw_content


# ============================================================
# DISCORD-EMBED ERSTELLEN
# ============================================================

def make_embed(
    item,
    raw_content,
    preview_image
):
    article_id = item["id"]

    title = (
        item.get("title")
        or "Neues AION 2 Update"
    )

    date = format_date(item)

    description = (
        "🛠️ **Offizielles AION 2 Update**"
    )

    if date:
        description += (
            f"\nVeröffentlicht am **{date}**"
        )

    embed = {
        "title": title[:256],
        "url": (
            "https://aion2.plaync.com/"
            "de-de/board/update/view"
            f"?articleId={article_id}"
        ),
        "description": description,
        "color": 5763719
    }

    if preview_image:
        embed["image"] = {
            "url": preview_image
        }

    return embed


# ============================================================
# ÄNDERUNGEN AN ARTIKELN ERKENNEN
# ============================================================

def fingerprint(item, raw_content):
    relevant = {
        "title": item.get("title"),
        "timestamps": item.get("timestamps"),
        "content": raw_content
    }

    serialized = json.dumps(
        relevant,
        sort_keys=True,
        ensure_ascii=False,
        default=str
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


# ============================================================
# HAUPTPROGRAMM
# ============================================================

def main():
    if not DISCORD_WEBHOOK:
        raise RuntimeError(
            "UPDATES_WEBHOOK_URL fehlt."
        )

    print(
        "AION 2 Updates werden geprüft ..."
    )

    # API-Verfügbarkeit prüfen.
    # Bei Fehlern werden keine Discord-
    # Nachrichten gelöscht oder verändert.

    request_json(BOARD_API)

    listing = request_json(LIST_API)

    articles = listing.get(
        "contentList"
    )

    if (
        not isinstance(articles, list)
        or not articles
    ):
        print(
            "Keine gültige Update-Liste "
            "erhalten – keine Änderungen."
        )
        return

    if any(
        not isinstance(article, dict)
        or article.get("id") is None
        for article in articles
    ):
        print(
            "Unvollständige Update-Liste "
            "– keine Änderungen."
        )
        return

    state = load_state()

    legacy_ids = {
        str(value)
        for value in state[
            "posted_article_ids"
        ]
    }

    managed = state["managed"]

    listed = {
        str(article["id"]): article
        for article in articles
    }

    print(
        f"{len(articles)} offizielle "
        "AION 2 Updates gefunden."
    )

    # ========================================================
    # SICHTBARES ARTIKELFENSTER BESTIMMEN
    # ========================================================

    numeric_ids = []

    for article in articles:
        try:
            numeric_ids.append(
                int(article["id"])
            )

        except (TypeError, ValueError):
            numeric_ids = []
            break

    oldest_visible = (
        min(numeric_ids)
        if numeric_ids
        else None
    )

    # ========================================================
    # NEUE UND BEARBEITETE UPDATES
    # ========================================================

    # Älteste zuerst, damit die Reihenfolge
    # in Discord stimmt.

    for item in reversed(articles):
        article_id = str(
            item["id"]
        )

        record = managed.get(
            article_id
        )

        # Alte Einträge ohne gespeicherte
        # Discord-Nachrichten-ID überspringen.

        if (
            not record
            and article_id in legacy_ids
        ):
            continue

        try:
            detail, raw_content = article_detail(
                article_id
            )

            digest = fingerprint(
                item,
                raw_content
            )

            # Keine Änderung vorhanden.

            if (
                record
                and record.get("hash") == digest
            ):
                if record.get(
                    "missing_checks"
                ):
                    record["missing_checks"] = 0
                    save_state(state)

                continue

            preview_image = choose_preview_image(
                find_images(raw_content)
            )

            embed = make_embed(
                item,
                raw_content,
                preview_image
            )

            # Bestehende Discord-Nachricht
            # bearbeiten.

            if record:
                discord_edit(
                    record[
                        "discord_message_id"
                    ],
                    embed
                )

                record["hash"] = digest
                record["missing_checks"] = 0
                record["title"] = item.get(
                    "title",
                    ""
                )

                print(
                    "Update bearbeitet: "
                    f'{embed["title"]}'
                )

            # Neues Update in Discord posten.

            else:
                response = discord_create(
                    embed
                )

                message_id = response.get(
                    "id"
                )

                if not message_id:
                    raise RuntimeError(
                        "Discord hat keine "
                        "Nachrichten-ID zurückgegeben."
                    )

                managed[article_id] = {
                    "discord_message_id": str(
                        message_id
                    ),
                    "hash": digest,
                    "missing_checks": 0,
                    "title": item.get(
                        "title",
                        ""
                    )
                }

                if article_id not in legacy_ids:
                    state[
                        "posted_article_ids"
                    ].append(
                        item["id"]
                    )

                    legacy_ids.add(
                        article_id
                    )

                print(
                    "Neues Update veröffentlicht: "
                    f'{embed["title"]}'
                )

            # Status nach jedem Artikel speichern.

            save_state(state)

        except Exception as error:
            print(
                f"Artikel {article_id} "
                f"konnte nicht verarbeitet "
                f"werden: {error}"
            )

    # ========================================================
    # GELÖSCHTE UPDATES ERKENNEN
    # ========================================================

    # Nur Beiträge berücksichtigen, die
    # innerhalb des sichtbaren Listenfensters
    # fehlen.
    #
    # Zwei getrennte Prüfungen müssen das
    # Fehlen bestätigen.

    for article_id, record in list(
        managed.items()
    ):
        if article_id in listed:
            if record.get(
                "missing_checks"
            ):
                record["missing_checks"] = 0
                save_state(state)

            continue

        if oldest_visible is None:
            continue

        try:
            if (
                int(article_id)
                < oldest_visible
            ):
                continue

        except ValueError:
            continue

        record["missing_checks"] = (
            record.get(
                "missing_checks",
                0
            ) + 1
        )

        if (
            record["missing_checks"]
            < DELETION_CONFIRMATIONS
        ):
            print(
                f"Update {article_id} fehlt. "
                "Erste Bestätigung – "
                "noch nicht löschen."
            )

            save_state(state)
            continue

        try:
            discord_delete(
                record[
                    "discord_message_id"
                ]
            )

            print(
                "Update aus Discord entfernt: "
                f'{record.get("title", article_id)}'
            )

            del managed[article_id]

            state[
                "posted_article_ids"
            ] = [
                value
                for value in state[
                    "posted_article_ids"
                ]
                if str(value) != article_id
            ]

            save_state(state)

        except urllib.error.HTTPError as error:
            if error.code == 404:
                # Nachricht wurde bereits
                # manuell in Discord gelöscht.

                del managed[article_id]

                state[
                    "posted_article_ids"
                ] = [
                    value
                    for value in state[
                        "posted_article_ids"
                    ]
                    if str(value) != article_id
                ]

                save_state(state)

            else:
                print(
                    "Discord-Löschung "
                    f"fehlgeschlagen "
                    f"({article_id}): {error}"
                )

        except Exception as error:
            print(
                "Löschen fehlgeschlagen "
                f"({article_id}): {error}"
            )

    print(
        "AION 2 Update-Abgleich abgeschlossen."
    )


if __name__ == "__main__":
    main()
