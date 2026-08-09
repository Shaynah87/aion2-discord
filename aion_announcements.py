import os
import json
import re
import html
import time
import uuid
import io
import urllib.request
import urllib.error

from datetime import datetime
from PIL import Image


DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

BOARD_API = (
    "https://api-global-community.plaync.com/"
    "aion2_global/board/notice_de"
)

STATE_FILE = "last_article.json"


# ============================================================
# AION API
# ============================================================

def api_get(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


# ============================================================
# AION HTML -> DISCORD TEXT
# ============================================================

def clean_html(value):
    if not value:
        return ""

    if not isinstance(value, str):
        value = str(value)

    # Listen besser lesbar machen
    value = re.sub(
        r"<li[^>]*>",
        "• ",
        value,
        flags=re.I,
    )

    value = re.sub(
        r"</li>",
        "\n",
        value,
        flags=re.I,
    )

    # Absätze
    value = re.sub(
        r"<br\s*/?>",
        "\n",
        value,
        flags=re.I,
    )

    value = re.sub(
        r"</p>",
        "\n\n",
        value,
        flags=re.I,
    )

    value = re.sub(
        r"</div>",
        "\n",
        value,
        flags=re.I,
    )

    value = re.sub(
        r"</tr>",
        "\n",
        value,
        flags=re.I,
    )

    value = re.sub(
        r"</td>",
        "  ",
        value,
        flags=re.I,
    )

    # Alle restlichen HTML-Tags entfernen
    value = re.sub(
        r"<[^>]+>",
        "",
        value,
    )

    value = html.unescape(value)

    # Leerzeilen aufräumen
    lines = [
        line.strip()
        for line in value.splitlines()
    ]

    result = []
    empty_before = False

    for line in lines:
        if line:
            result.append(line)
            empty_before = False

        elif not empty_before:
            result.append("")
            empty_before = True

    return "\n".join(result).strip()


# ============================================================
# BILDER AUS HTML
# ============================================================

def find_images(value):
    if not value or not isinstance(value, str):
        return []

    images = re.findall(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        value,
        flags=re.I,
    )

    result = []

    for image in images:
        image = html.unescape(image)

        if image.startswith("//"):
            image = "https:" + image

        if image not in result:
            result.append(image)

    return result


def download_image(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


# ============================================================
# DISCORD RATE LIMIT
# ============================================================

def wait_after_discord_post():
    time.sleep(0.8)


# ============================================================
# NORMALE DISCORD NACHRICHT
# ============================================================

def discord_post(content=None, embeds=None):
    payload = {
        "allowed_mentions": {
            "parse": []
        }
    }

    if content:
        payload["content"] = content

    if embeds:
        payload["embeds"] = embeds

    data = json.dumps(payload).encode("utf-8")

    while True:
        req = urllib.request.Request(
            DISCORD_WEBHOOK,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AION2-Discord-Bot",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                req,
                timeout=30,
            ):
                pass

            wait_after_discord_post()
            return

        except urllib.error.HTTPError as error:
            if error.code == 429:
                try:
                    response = json.loads(
                        error.read().decode("utf-8")
                    )

                    retry_after = float(
                        response.get(
                            "retry_after",
                            2,
                        )
                    )

                except Exception:
                    retry_after = 2

                print(
                    f"Discord Rate Limit – "
                    f"warte {retry_after} Sekunden..."
                )

                time.sleep(
                    retry_after + 0.5
                )

                continue

            raise


# ============================================================
# BILD ALS DATEI AN DISCORD
# ============================================================

def discord_upload_image(
    image_data,
    filename,
):
    boundary = uuid.uuid4().hex

    payload_json = json.dumps(
        {
            "allowed_mentions": {
                "parse": []
            }
        }
    )

    body = bytearray()

    body.extend(
        f"--{boundary}\r\n".encode()
    )

    body.extend(
        b'Content-Disposition: form-data; '
        b'name="payload_json"\r\n\r\n'
    )

    body.extend(
        payload_json.encode("utf-8")
    )

    body.extend(b"\r\n")

    body.extend(
        f"--{boundary}\r\n".encode()
    )

    body.extend(
        (
            'Content-Disposition: form-data; '
            f'name="files[0]"; '
            f'filename="{filename}"\r\n'
        ).encode()
    )

    body.extend(
        b"Content-Type: image/jpeg\r\n\r\n"
    )

    body.extend(image_data)

    body.extend(b"\r\n")

    body.extend(
        f"--{boundary}--\r\n".encode()
    )

    while True:
        req = urllib.request.Request(
            DISCORD_WEBHOOK,
            data=bytes(body),
            headers={
                "Content-Type":
                    f"multipart/form-data; boundary={boundary}",
                "User-Agent":
                    "AION2-Discord-Bot",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                req,
                timeout=45,
            ):
                pass

            wait_after_discord_post()
            return

        except urllib.error.HTTPError as error:
            if error.code == 429:
                try:
                    response = json.loads(
                        error.read().decode("utf-8")
                    )

                    retry_after = float(
                        response.get(
                            "retry_after",
                            2,
                        )
                    )

                except Exception:
                    retry_after = 2

                print(
                    f"Discord Rate Limit – "
                    f"warte {retry_after} Sekunden..."
                )

                time.sleep(
                    retry_after + 0.5
                )

                continue

            raise


# ============================================================
# LANGE INFOGRAFIKEN AUFTEILEN
# ============================================================

def process_image(image_url, article_id):
    try:
        raw = download_image(image_url)

        image = Image.open(
            io.BytesIO(raw)
        ).convert("RGB")

        width, height = image.size

        # --------------------------------------------
        # AION-Trenner / schmale Banner ignorieren
        # --------------------------------------------

        if height > 0:
            ratio = width / height
        else:
            return

        if ratio >= 4.5:
            print(
                "Schmales Banner übersprungen."
            )
            return

        # --------------------------------------------
        # Normales Bild
        # --------------------------------------------

        if height <= width * 2.5:
            discord_post(image_url)
            return

        # --------------------------------------------
        # Sehr langes Hochformatbild
        # -> in mehrere gut lesbare Stücke teilen
        # --------------------------------------------

        print(
            "Lange Infografik erkannt – "
            "wird für Discord geteilt."
        )

        # Sehr große Bilder etwas verkleinern
        if width > 1400:
            new_width = 1400

            new_height = int(
                height
                * new_width
                / width
            )

            image = image.resize(
                (
                    new_width,
                    new_height,
                ),
                Image.LANCZOS,
            )

            width, height = image.size

        chunk_height = int(
            width * 1.45
        )

        top = 0
        number = 1

        while top < height:
            bottom = min(
                top + chunk_height,
                height,
            )

            chunk = image.crop(
                (
                    0,
                    top,
                    width,
                    bottom,
                )
            )

            buffer = io.BytesIO()

            chunk.save(
                buffer,
                format="JPEG",
                quality=90,
                optimize=True,
            )

            discord_upload_image(
                buffer.getvalue(),
                (
                    f"aion2_{article_id}_"
                    f"{number}.jpg"
                ),
            )

            number += 1
            top = bottom

    except Exception as error:
        print(
            f"Bild konnte nicht verarbeitet werden: "
            f"{error}"
        )

        # Falls Bildbearbeitung scheitert,
        # wenigstens Originalbild posten.
        discord_post(image_url)


# ============================================================
# DISCORD TEXT AUFTEILEN
# ============================================================

def split_message(
    text,
    limit=1900,
):
    parts = []

    while len(text) > limit:
        cut = text.rfind(
            "\n",
            0,
            limit,
        )

        if cut == -1:
            cut = text.rfind(
                " ",
                0,
                limit,
            )

        if cut == -1:
            cut = limit

        part = text[:cut].strip()

        if part:
            parts.append(part)

        text = text[cut:].lstrip()

    if text.strip():
        parts.append(
            text.strip()
        )

    return parts


# ============================================================
# DATUM
# ============================================================

def format_date(item):
    timestamps = (
        item.get("timestamps")
        or {}
    )

    raw_date = timestamps.get(
        "postDateTime",
        "",
    )

    if not raw_date:
        return ""

    try:
        date = datetime.fromisoformat(
            raw_date.replace(
                "Z",
                "+00:00",
            )
        )

        return date.strftime(
            "%d.%m.%Y"
        )

    except Exception:
        return raw_date[:10]


# ============================================================
# STATE
# ============================================================

def load_posted_ids():
    if not os.path.exists(
        STATE_FILE
    ):
        return []

    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8",
        ) as f:
            state = json.load(f)

        return state.get(
            "posted_article_ids",
            [],
        )

    except Exception:
        return []


def save_posted_ids(
    posted_ids,
):
    with open(
        STATE_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "posted_article_ids":
                    posted_ids
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# HAUPTPROGRAMM
# ============================================================

def main():
    if not DISCORD_WEBHOOK:
        raise RuntimeError(
            "DISCORD_WEBHOOK fehlt."
        )

    # Board laden
    api_get(BOARD_API)

    # Liste der Ankündigungen
    list_url = (
        "https://api-global-community.plaync.com/"
        "aion2_global/board/notice_de/"
        "article/search/moreArticle"
        "?isVote=true"
        "&moreSize=18"
        "&moreDirection=BEFORE"
        "&previousArticleId=0"
    )

    listing = api_get(
        list_url
    )

    articles = listing.get(
        "contentList",
        [],
    )

    if not articles:
        print(
            "Keine Ankündigungen gefunden."
        )
        return

    posted_ids = (
        load_posted_ids()
    )

    new_articles = [
        article
        for article in articles
        if article.get("id")
        not in posted_ids
    ]

    if not new_articles:
        print(
            "Keine neue Ankündigung."
        )
        return

    # AION liefert neu -> alt.
    # Discord bekommt alt -> neu.
    new_articles.reverse()

    print(
        f"{len(new_articles)} "
        f"neue Ankündigung(en) gefunden."
    )

    for item in new_articles:
        article_id = item["id"]

        title = (
            item.get("title")
            or
            "Neue AION 2 Ankündigung"
        )

        date = format_date(
            item
        )

        public_url = (
            "https://aion2.plaync.com/"
            "de-de/board/notice/view"
            f"?articleId={article_id}"
        )

        article_url = (
            "https://api-global-community.plaync.com/"
            "aion2_global/board/notice_de/"
            f"article/{article_id}"
        )

        data = api_get(
            article_url
        )

        article = (
            data["article"]["content"]
        )

        raw_content = article.get(
            "content",
            "",
        )

        text = clean_html(
            raw_content
        )

        images = find_images(
            raw_content
        )

        # --------------------------------------------
        # KOPF DES BEITRAGS
        # --------------------------------------------

        description = (
            "**Offizielle AION 2 Ankündigung**"
        )

        if date:
            description += (
                f"\nVeröffentlicht am {date}"
            )

        discord_post(
            embeds=[
                {
                    "title":
                        f"📢 {title}",
                    "url":
                        public_url,
                    "description":
                        description,
                    "color":
                        4886754,
                }
            ]
        )

        # --------------------------------------------
        # TEXT
        # --------------------------------------------

        for part in split_message(
            text
        ):
            discord_post(
                part
            )

        # --------------------------------------------
        # BILDER
        # --------------------------------------------

        for image_url in images:
            process_image(
                image_url,
                article_id,
            )

        # --------------------------------------------
        # TRENNUNG ZUM NÄCHSTEN BEITRAG
        # --------------------------------------------

        discord_post(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        posted_ids.append(
            article_id
        )

        save_posted_ids(
            posted_ids
        )

        print(
            f"Gepostet: {title}"
        )

    print("Fertig.")


if __name__ == "__main__":
    main()
