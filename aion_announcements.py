import os
import json
import re
import html
import time
import urllib.request
import urllib.error

from datetime import datetime


DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

BOARD_API = (
    "https://api-global-community.plaync.com/"
    "aion2_global/board/notice_de"
)

STATE_FILE = "last_article.json"


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


def image_dimensions(url):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
            },
        )

        with urllib.request.urlopen(req, timeout=20) as response:
            data = response.read(100000)

        # PNG
        if data.startswith(b"\x89PNG") and len(data) >= 24:
            width = int.from_bytes(data[16:20], "big")
            height = int.from_bytes(data[20:24], "big")
            return width, height

        # JPEG
        if data.startswith(b"\xff\xd8"):
            index = 2

            while index < len(data) - 9:
                if data[index] != 0xFF:
                    index += 1
                    continue

                marker = data[index + 1]

                if marker in (
                    0xC0, 0xC1, 0xC2, 0xC3,
                    0xC5, 0xC6, 0xC7,
                    0xC9, 0xCA, 0xCB,
                    0xCD, 0xCE, 0xCF,
                ):
                    height = int.from_bytes(
                        data[index + 5:index + 7],
                        "big",
                    )
                    width = int.from_bytes(
                        data[index + 7:index + 9],
                        "big",
                    )
                    return width, height

                length = int.from_bytes(
                    data[index + 2:index + 4],
                    "big",
                )

                if length < 2:
                    break

                index += 2 + length

    except Exception:
        pass

    return None


def choose_preview_image(images):
    for image in images:
        dimensions = image_dimensions(image)

        if not dimensions:
            continue

        width, height = dimensions

        if width <= 0 or height <= 0:
            continue

        ratio = width / height

        # Sehr schmale AION-Trenner / Banner überspringen
        if ratio >= 4.0:
            continue

        # Extrem lange Infografiken nicht als Thumbnail nehmen
        if height > width * 3.0:
            continue

        # Zu kleine Bilder ignorieren
        if width < 300 or height < 150:
            continue

        return image

    return None


def discord_post_embed(embed):
    payload = {
        "embeds": [embed],
        "allowed_mentions": {
            "parse": []
        },
    }

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

            time.sleep(0.8)
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


def save_posted_ids(posted_ids):
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


def main():
    if not DISCORD_WEBHOOK:
        raise RuntimeError(
            "DISCORD_WEBHOOK fehlt."
        )

    api_get(BOARD_API)

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

    posted_ids = load_posted_ids()

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
    # Discord soll alt -> neu bekommen.
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

        date = format_date(item)

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

        images = find_images(
            raw_content
        )

        preview_image = (
            choose_preview_image(images)
        )

        embed = {
            "title": title,
            "url": public_url,
            "description": (
                "📢 **Offizielle AION 2 Ankündigung**"
                + (
                    f"\nVeröffentlicht am **{date}**"
                    if date
                    else ""
                )
                + "\n\n"
                + "🔗 **Zum vollständigen Beitrag**"
            ),
            "color": 4886754,
        }

        if preview_image:
            embed["image"] = {
                "url": preview_image
            }

        discord_post_embed(
            embed
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
