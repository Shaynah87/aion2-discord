import os
import json
import re
import html
import urllib.request
import urllib.error
import time

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

BOARD_API = "https://api-global-community.plaync.com/aion2_global/board/notice_de"
STATE_FILE = "last_article.json"


def api_get(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def clean_html(value):
    if not value:
        return ""

    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"</p>|</div>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)

    lines = [line.strip() for line in value.splitlines()]

    return "\n".join(line for line in lines if line)


def find_images(value):
    if not value:
        return []

    return re.findall(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        value,
        flags=re.I,
    )


def discord_post(content):
    data = json.dumps(
        {
            "content": content,
            "allowed_mentions": {
                "parse": []
            },
        }
    ).encode("utf-8")

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

            # Kleine Pause, damit Discord nicht zugespammt wird
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
                    f"Discord Rate Limit – warte {retry_after} Sekunden..."
                )

                time.sleep(retry_after + 0.5)
                continue

            raise


def split_message(text, limit=1900):
    parts = []

    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)

        if cut == -1:
            cut = limit

        parts.append(text[:cut])
        text = text[cut:].lstrip()

    if text:
        parts.append(text)

    return parts


def load_posted_ids():
    if not os.path.exists(STATE_FILE):
        return []

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)

        return state.get("posted_article_ids", [])

    except Exception:
        return []


def save_posted_ids(posted_ids):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "posted_article_ids": posted_ids
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


def main():
    if not DISCORD_WEBHOOK:
        raise RuntimeError("DISCORD_WEBHOOK fehlt.")

    # Board-Informationen laden
    board = api_get(BOARD_API)

    board_ref = board["board"]["id"]

    # Liste der aktuellen Ankündigungen abrufen
    list_url = (
        "https://api-global-community.plaync.com/"
        "aion2_global/board/notice_de/article/search/moreArticle"
        "?isVote=true"
        "&moreSize=18"
        "&moreDirection=BEFORE"
        "&previousArticleId=0"
    )

    listing = api_get(list_url)

    articles = listing.get("contentList", [])

    if not articles:
        print("Keine Ankündigungen gefunden.")
        return

    posted_ids = load_posted_ids()

    # Nur Ankündigungen nehmen, die noch nicht gepostet wurden
    new_articles = [
        article
        for article in articles
        if article["id"] not in posted_ids
    ]

    if not new_articles:
        print("Keine neue Ankündigung.")
        return

    # AION liefert neu -> alt.
    # Discord soll alt -> neu bekommen.
    new_articles.reverse()

    print(
        f"{len(new_articles)} neue Ankündigung(en) gefunden."
    )

    for item in new_articles:
        article_id = item["id"]

        # Einzelnen Artikel laden
        article_url = (
            "https://api-global-community.plaync.com/"
            f"aion2_global/board/notice_de/article/{article_id}"
        )

        data = api_get(article_url)

        # WICHTIG:
        # article -> content -> content
        article = data["article"]["content"]

        title = (
            item.get("title")
            or "Neue AION 2 Ankündigung"
        )

        raw_content = article.get("content", "")

        text = clean_html(raw_content)

        images = find_images(raw_content)

        # Überschrift
        discord_post(
            f"## 📢 {title}"
        )

        # Text posten
        for part in split_message(text):
            discord_post(part)

        # Bilder posten
        for image in images:
            discord_post(image)

        # Erst nach erfolgreichem Posten als erledigt markieren
        posted_ids.append(article_id)

        save_posted_ids(posted_ids)

        print(
            f"Gepostet: {title}"
        )

    print("Fertig.")


if __name__ == "__main__":
    main()
