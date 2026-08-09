import os
import json
import re
import html
import time
import urllib.request
import urllib.error
from datetime import datetime


# ------------------------------------------------------------
# EINSTELLUNGEN
# ------------------------------------------------------------

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

BOARD_API = (
    "https://api-global-community.plaync.com/"
    "aion2_global/board/notice_de"
)

ARTICLE_API = (
    "https://api-global-community.plaync.com/"
    "aion2_global/board/notice_de/article/{}"
)

ARTICLE_WEB = (
    "https://aion2.plaync.com/de-de/board/notice/view?articleId={}"
)

STATE_FILE = "last_article.json"

# Beim allerersten Lauf werden maximal so viele alte Beiträge gepostet.
MAX_INITIAL_POSTS = 5


# ------------------------------------------------------------
# API ABFRAGEN
# ------------------------------------------------------------

def api_get(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


# ------------------------------------------------------------
# DISCORD
# ------------------------------------------------------------

def discord_post(payload):
    if not DISCORD_WEBHOOK:
        raise RuntimeError("DISCORD_WEBHOOK wurde nicht gefunden.")

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
            with urllib.request.urlopen(req, timeout=20):
                pass

            # Kleine Pause zwischen mehreren Beiträgen
            time.sleep(0.8)
            return

        except urllib.error.HTTPError as error:
            if error.code == 429:
                try:
                    response = json.loads(
                        error.read().decode("utf-8")
                    )

                    retry_after = float(
                        response.get("retry_after", 2)
                    )

                except Exception:
                    retry_after = 2

                print(
                    f"Discord Rate Limit – "
                    f"warte {retry_after} Sekunden..."
                )

                time.sleep(retry_after + 0.5)
                continue

            raise


# ------------------------------------------------------------
# DATUM
# ------------------------------------------------------------

def format_date(value):
    if not value:
        return None

    # Millisekunden-Zeitstempel
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(
                value / 1000
            ).strftime("%d.%m.%Y")
        except Exception:
            return None

    value = str(value)

    # ISO-Datum
    try:
        clean = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        return dt.strftime("%d.%m.%Y")
    except Exception:
        pass

    # YYYY-MM-DD irgendwo im String
    match = re.search(
        r"(\d{4})-(\d{2})-(\d{2})",
        value
    )

    if match:
        year, month, day = match.groups()
        return f"{day}.{month}.{year}"

    return None


# ------------------------------------------------------------
# BILD AUS DEM ARTIKEL HOLEN
# ------------------------------------------------------------

def find_images(value):
    images = []

    def walk(obj):
        if isinstance(obj, dict):
            for key, val in obj.items():
                key_lower = str(key).lower()

                if (
                    isinstance(val, str)
                    and val.startswith(("http://", "https://"))
                    and (
                        key_lower in {
                            "src",
                            "url",
                            "image",
                            "imageurl",
                            "image_url",
                        }
                        or re.search(
                            r"\.(png|jpg|jpeg|webp)(?:\?|$)",
                            val,
                            re.IGNORECASE,
                        )
                    )
                ):
                    images.append(html.unescape(val))

                walk(val)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

        elif isinstance(obj, str):
            # HTML <img src="...">
            for match in re.findall(
                r'<img[^>]+src=["\']([^"\']+)["\']',
                obj,
                flags=re.IGNORECASE,
            ):
                images.append(html.unescape(match))

            # Direkte Bild-URLs im Text
            for match in re.findall(
                r'https?://[^\s"\'<>]+'
                r'\.(?:png|jpg|jpeg|webp)'
                r'(?:\?[^\s"\'<>]*)?',
                obj,
                flags=re.IGNORECASE,
            ):
                images.append(html.unescape(match))

    walk(value)

    # Doppelte Bilder entfernen
    unique = []

    for image in images:
        if image not in unique:
            unique.append(image)

    return unique


def choose_thumbnail(images):
    if not images:
        return None

    # Kleine Logos / Icons möglichst nicht verwenden
    bad_words = (
        "logo",
        "icon",
        "favicon",
        "symbol",
        "button",
        "banner_top",
        "board",
    )

    for image in images:
        lower = image.lower()

        if not any(word in lower for word in bad_words):
            return image

    # Wenn nichts Besseres vorhanden ist,
    # lieber gar kein Bild.
    return None


# ------------------------------------------------------------
# GESPEICHERTE ARTIKEL
# ------------------------------------------------------------

def load_state():
    if not os.path.exists(STATE_FILE):
        return []

    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        return data.get("posted_article_ids", [])

    except Exception:
        return []


def save_state(posted_ids):
    with open(
        STATE_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            {
                "posted_article_ids": posted_ids
            },
            file,
            ensure_ascii=False,
            indent=2,
        )


# ------------------------------------------------------------
# ARTIKELLISTE FINDEN
# ------------------------------------------------------------

def find_article_list(data):
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        # Häufige Namen zuerst
        for key in (
            "articles",
            "articleList",
            "list",
            "items",
            "contents",
            "content",
        ):
            value = data.get(key)

            if isinstance(value, list):
                return value

        # Falls die Liste tiefer verschachtelt ist
        for value in data.values():
            result = find_article_list(value)

            if result:
                return result

    return []


# ------------------------------------------------------------
# ARTIKEL-ID
# ------------------------------------------------------------

def get_article_id(item):
    if not isinstance(item, dict):
        return None

    for key in (
        "id",
        "articleId",
        "article_id",
        "articleNo",
        "article_no",
    ):
        if item.get(key):
            return str(item[key])

    return None


# ------------------------------------------------------------
# TITEL
# ------------------------------------------------------------

def get_title(item, article):
    for source in (item, article):
        if not isinstance(source, dict):
            continue

        for key in (
            "title",
            "subject",
            "articleTitle",
            "article_title",
        ):
            value = source.get(key)

            if value:
                return html.unescape(str(value)).strip()

    return "Neue AION 2 Ankündigung"


# ------------------------------------------------------------
# VERÖFFENTLICHUNGSDATUM
# ------------------------------------------------------------

def get_date(item, article):
    possible_keys = (
        "createdAt",
        "created_at",
        "createDate",
        "createdDate",
        "regDate",
        "registerDate",
        "publishedAt",
        "publishDate",
        "date",
    )

    for source in (item, article):
        if not isinstance(source, dict):
            continue

        for key in possible_keys:
            if source.get(key):
                result = format_date(source[key])

                if result:
                    return result

    return None


# ------------------------------------------------------------
# DISCORD EMBED ERSTELLEN
# ------------------------------------------------------------

def create_embed(article_id, item, article):
    title = get_title(item, article)

    date = get_date(item, article)

    article_url = ARTICLE_WEB.format(article_id)

    images = find_images(article)

    thumbnail = choose_thumbnail(images)

    description = "📢 **Offizielle AION 2 Ankündigung**"

    if date:
        description += (
            f"\nVeröffentlicht am **{date}**"
        )

    embed = {
        "title": title,
        "url": article_url,
        "description": description,
        "color": 3447003,
    }

    # Nur wenn der Artikel tatsächlich ein geeignetes Bild hat
    if thumbnail:
        embed["thumbnail"] = {
            "url": thumbnail
        }

    return embed


# ------------------------------------------------------------
# HAUPTPROGRAMM
# ------------------------------------------------------------

def main():
    print("AION 2 Ankündigungen werden geprüft...")

    board_data = api_get(BOARD_API)

    articles = find_article_list(board_data)

    if not articles:
        print("Keine Ankündigungen gefunden.")
        return

    posted_ids = load_state()

    new_articles = []

    for item in articles:
        article_id = get_article_id(item)

        if not article_id:
            continue

        if article_id not in posted_ids:
            new_articles.append(
                (article_id, item)
            )

    if not new_articles:
        print("Keine neuen Ankündigungen.")
        return

    # Wenn die Datei komplett leer ist,
    # nicht die gesamte Historie posten.
    if not posted_ids:
        new_articles = new_articles[:MAX_INITIAL_POSTS]

    # Älteste der neuen Meldungen zuerst posten,
    # damit Discord chronologisch aussieht.
    new_articles.reverse()

    print(
        f"{len(new_articles)} neue "
        f"Ankündigung(en) gefunden."
    )

    for article_id, item in new_articles:
        print(
            f"Verarbeite Artikel: {article_id}"
        )

        article_data = api_get(
            ARTICLE_API.format(article_id)
        )

        # Die API hatte bei uns den eigentlichen
        # Artikel unter "article".
        if (
            isinstance(article_data, dict)
            and isinstance(
                article_data.get("article"),
                dict,
            )
        ):
            article = article_data["article"]

        else:
            article = article_data

        embed = create_embed(
            article_id,
            item,
            article,
        )

        discord_post(
            {
                "embeds": [embed],
                "allowed_mentions": {
                    "parse": []
                },
            }
        )

        print(
            f"Gepostet: {embed['title']}"
        )

        # Erst nach erfolgreichem Discord-Post
        # als erledigt markieren.
        posted_ids.append(article_id)

        save_state(posted_ids)

    print("Fertig.")


if __name__ == "__main__":
    main()
