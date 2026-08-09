import os
import json
import re
import html
import urllib.request

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

    return re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', value, flags=re.I)


def discord_post(content):
    data = json.dumps({"content": content}).encode("utf-8")

    req = urllib.request.Request(
        DISCORD_WEBHOOK,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "AION2-Discord-Bot",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=20):
        pass


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


def main():
    if not DISCORD_WEBHOOK:
        raise RuntimeError("DISCORD_WEBHOOK fehlt.")

    board = api_get(BOARD_API)

    board_ref = board["board"]["id"]

    list_url = (
        f"https://api-global-community.plaync.com/aion2_global/board/"
        f"{board_ref}/moreArticle"
        f"?isVote=true&moreSize=18&moreDirection=BEFORE&previousArticleId=0"
    )

    listing = api_get(list_url)
    articles = listing.get("contentList", [])

    if not articles:
        print("Keine Ankündigungen gefunden.")
        return

    newest = articles[0]
    article_id = newest["id"]

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)

        if state.get("last_article_id") == article_id:
            print("Keine neue Ankündigung.")
            return

    # Beim allerersten Lauf nur den aktuellen Stand merken.
    # Dadurch werden nicht alle alten AION-Meldungen in Discord gepostet.
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_article_id": article_id}, f)

        print("Erster Lauf: aktuelle Ankündigung gespeichert.")
        return

    article_url = (
        f"https://api-global-community.plaync.com/aion2_global/board/"
        f"{board_ref}/article/{article_id}"
    )

    data = api_get(article_url)

    article = data["article"]["content"]
    title = article.get("title") or newest.get("title") or "Neue Ankündigung"
    raw_content = article.get("content", "")

    text = clean_html(raw_content)
    images = find_images(raw_content)

    discord_post(f"## 📢 {title}")

    for part in split_message(text):
        discord_post(part)

    for image in images:
        discord_post(image)

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_article_id": article_id}, f)

    print(f"Gepostet: {title}")


if __name__ == "__main__":
    main()
