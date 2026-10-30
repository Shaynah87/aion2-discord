
"""
Nyerk24 · Events – gemeinsame Discord-Nachricht

- Halloween-Banner aus bestehender Nachricht übernehmen
- Vier Kategorie-Banner in Originalgröße
- Ein gemeinsamer Eventblock pro Kategorie
- Ein Discord-Beitrag für die gesamte Übersicht
- Keine Änderungen am Helper
- Keine Löschung alter Beiträge
- Rate-Limit-Behandlung
"""

import hashlib
import importlib.util
import io
import json
import os
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
STATE_PATH = ROOT / "events_message.json"

API = "https://discord.com/api/v10"
WIDTH = 1200
CATEGORY_HEIGHT = 65
ROW_HEIGHT = 58

CATEGORIES = (
    (
        "anwesenheitslisten",
        "Anwesenheitslisten",
        "Anwesenheit/anwesenheitslisten.png",
    ),
    (
        "ingame_events",
        "Ingame-Events",
        "In-Game/ingame_events.png",
    ),
    (
        "community_events",
        "Community-Events",
        "Community/community_events.png",
    ),
    (
        "twitch_drops",
        "Twitch Drops",
        "Twitch/twitch_drops.png",
    ),
)


def discord_request(method, url, session=None, **kwargs):
    client = session or requests
    kwargs.setdefault("timeout", 45)

    for attempt in range(12):
        try:
            response = client.request(
                method, url, **kwargs
            )
        except (requests.ConnectionError, requests.Timeout):
            if method.upper() == "POST":
                raise RuntimeError(
                    "POST-Verbindung unterbrochen. "
                    "Vor erneutem Start Discord prüfen."
                )
            if attempt == 11:
                raise
            time.sleep(min(2 ** attempt, 15))
            continue

        if response.status_code == 429:
            try:
                wait = float(
                    response.json().get("retry_after", 1)
                )
            except (ValueError, TypeError):
                wait = 1.0

            if attempt == 11:
                raise RuntimeError(
                    "Discord Rate Limit: zu viele Versuche"
                )

            time.sleep(max(0.5, wait + 0.3))
            continue

        if response.status_code in (500, 502, 503, 504):
            if method.upper() == "POST":
                raise RuntimeError(
                    "Discord-Serverfehler beim Veröffentlichen. "
                    "Vor erneutem Start Kanal prüfen."
                )
            if attempt == 11:
                return response
            time.sleep(min(2 ** attempt, 15))
            continue

        return response

    raise RuntimeError("Discord-Anfrage fehlgeschlagen")


def checked(response, label):
    if not response.ok:
        raise RuntimeError(
            f"{label}: HTTP {response.status_code}: "
            f"{response.text[:800]}"
        )
    return response.json() if response.content else {}


def read_state():
    if not STATE_PATH.exists():
        raise RuntimeError("events_message.json fehlt")

    state = json.loads(
        STATE_PATH.read_text(encoding="utf-8")
    )
    if not isinstance(state, dict):
        raise RuntimeError("Ungültige State-Datei")
    return state


def save_state(state):
    temp = STATE_PATH.with_suffix(".tmp")
    temp.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temp.replace(STATE_PATH)


def font(size, bold=True):
    filename = (
        "DejaVuSans-Bold.ttf"
        if bold else "DejaVuSans.ttf"
    )
    path = Path(
        "/usr/share/fonts/truetype/dejavu"
    ) / filename

    if not path.exists():
        raise RuntimeError(f"Schrift fehlt: {path}")

    return ImageFont.truetype(str(path), size)


def png(image):
    buffer = io.BytesIO()
    image.convert("RGB").save(
        buffer, format="PNG", optimize=True
    )
    return buffer.getvalue()


def load_module(relative_path, name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / relative_path
    )
    if not spec or not spec.loader:
        raise RuntimeError(
            f"Modul fehlt: {relative_path}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def category_banner(relative_path, title):
    with Image.open(ROOT / relative_path) as source:
        if source.size != (1200, 65):
            raise RuntimeError(
                f"Falsche Bannergröße: {relative_path}"
            )
        image = source.convert("RGB")

    draw = ImageDraw.Draw(image)
    draw.text(
        (600, 32),
        title,
        font=font(37),
        anchor="mm",
        fill="white",
        stroke_width=2,
        stroke_fill="#171c29",
    )
    return png(image)


def event_background():
    path = REPO / "Tracker" / "event_overview.png"
    if not path.exists():
        raise RuntimeError(f"Vorlage fehlt: {path}")

    with Image.open(path) as source:
        original = source.convert("RGB")

    return ImageOps.fit(
        original,
        (WIDTH, ROW_HEIGHT),
        method=Image.Resampling.LANCZOS,
    )


def fit_font(draw, text, maximum, initial):
    for size in range(initial, 15, -1):
        candidate = font(size)
        box = draw.textbbox(
            (0, 0), text, font=candidate
        )
        if box[2] - box[0] <= maximum:
            return candidate
    return font(16)


def event_status(event):
    today = datetime.now(
        ZoneInfo("Europe/Berlin")
    ).date()

    start = date.fromisoformat(event["start"])
    end = date.fromisoformat(event["end"])

    if today < start:
        return "Kommend"
    if today <= end:
        return "Gestartet"
    return "Beendet"


def event_block(events):
    background = event_background()
    events = list(events)

    if not events:
        return None

    block = Image.new(
        "RGB",
        (WIDTH, len(events) * ROW_HEIGHT),
        "#24272e",
    )

    for index, event in enumerate(events):
        row = background.copy()
        draw = ImageDraw.Draw(row)

        name = str(event["name"])
        period = str(event.get("date_label") or "")

        if event.get("time_label"):
            period += " · " + str(event["time_label"])

        status = event_status(event)

        draw.text(
            (25, ROW_HEIGHT // 2),
            name,
            font=fit_font(draw, name, 540, 26),
            anchor="lm",
            fill="white",
            stroke_width=1,
            stroke_fill="#10151e",
        )

        draw.text(
            (790, ROW_HEIGHT // 2),
            period,
            font=fit_font(draw, period, 360, 22),
            anchor="mm",
            fill="#e5eaf2",
            stroke_width=1,
            stroke_fill="#10151e",
        )

        draw.text(
            (1175, ROW_HEIGHT // 2),
            status,
            font=font(23),
            anchor="rm",
            fill="white",
            stroke_width=1,
            stroke_fill="#10151e",
        )

        block.paste(row, (0, index * ROW_HEIGHT))

    return png(block)


def halloween_original(bot, channel, webhook_id, state):
    record = state.get("halloween_2026", {})
    message_id = str(
        record.get("webhook_message_id")
        or record.get("message_id")
        or ""
    )

    if not message_id:
        raise RuntimeError("Halloween-ID fehlt")

    message = checked(
        discord_request(
            "GET",
            f"{API}/channels/{channel}/messages/{message_id}",
            session=bot,
        ),
        "Halloween prüfen",
    )

    if str(message.get("webhook_id") or "") != webhook_id:
        raise RuntimeError(
            "Halloween gehört nicht zu diesem Webhook"
        )

    attachments = message.get("attachments", [])
    attachment = next(
        (
            item for item in attachments
            if str(item.get("filename", "")).lower()
            .endswith((".png", ".jpg", ".jpeg", ".webp"))
        ),
        None,
    )

    if not attachment:
        raise RuntimeError(
            "Halloween-Bild nicht gefunden"
        )

    response = checked_image(
        discord_request(
            "GET",
            attachment["url"],
            timeout=90,
        )
    )

    with Image.open(io.BytesIO(response)) as source:
        image = source.convert("RGB")

    if image.width != WIDTH:
        raise RuntimeError(
            "Halloween-Banner hat nicht 1200 Pixel Breite"
        )

    return png(image)


def checked_image(response):
    if not response.ok:
        raise RuntimeError(
            f"Bilddownload fehlgeschlagen: "
            f"HTTP {response.status_code}"
        )
    return response.content


def main():
    state = read_state()

    webhook = (
        os.environ["EVENTS_WEBHOOK"]
        .strip()
        .split("?", 1)[0]
        .rstrip("/")
    )

    bot = requests.Session()
    bot.headers["Authorization"] = (
        "Bot " + os.environ["DISCORD_BOT"].strip()
    )

    webhook_info = checked(
        discord_request("GET", webhook),
        "Webhook",
    )

    channel = str(webhook_info["channel_id"])
    webhook_id = str(webhook_info["id"])

    # Bilder in gewünschter Reihenfolge vorbereiten.
    images = []

    images.append((
        "00_halloween.png",
        halloween_original(
            bot, channel, webhook_id, state
        ),
    ))

    attendance = load_module(
        "Anwesenheit/anwesenheit.py",
        "attendance",
    )

    event_map = {
        "anwesenheitslisten": attendance.EVENTS,
        "ingame_events": (),
        "community_events": (),
        "twitch_drops": (),
    }

    for index, (key, title, path) in enumerate(
        CATEGORIES, start=1
    ):
        images.append((
            f"{index:02d}_{key}.png",
            category_banner(path, title),
        ))

        block = event_block(event_map[key])

        if block is not None:
            images.append((
                f"{index:02d}_{key}_events.png",
                block,
            ))

    if len(images) > 10:
        raise RuntimeError(
            "Mehr als zehn Bilder. "
            "Discord erlaubt höchstens zehn Anhänge."
        )

    digest = hashlib.sha256()
    for filename, data in images:
        digest.update(filename.encode("utf-8"))
        digest.update(data)
    image_hash = digest.hexdigest()

    record = state.setdefault("overview_v4", {})
    message_id = str(record.get("message_id") or "")

    if message_id:
        message = checked(
            discord_request(
                "GET",
                f"{API}/channels/{channel}/messages/{message_id}",
                session=bot,
            ),
            "Gesamtbeitrag prüfen",
        )

        if str(message.get("webhook_id") or "") != webhook_id:
            raise RuntimeError(
                "Gesamtbeitrag gehört nicht zu diesem Webhook"
            )

        if record.get("hash") == image_hash:
            print("Übersicht unverändert")
            return

    payload = {
        "content": "",
        "embeds": [],
        "allowed_mentions": {"parse": []},
        "attachments": [
            {"id": index, "filename": filename}
            for index, (filename, _) in enumerate(images)
        ],
    }

    files = {
        "payload_json": (
            None,
            json.dumps(payload),
        )
    }

    for index, (filename, data) in enumerate(images):
        files[f"files[{index}]"] = (
            filename,
            data,
            "image/png",
        )

    if message_id:
        response = discord_request(
            "PATCH",
            f"{webhook}/messages/{message_id}",
            files=files,
            timeout=120,
        )
    else:
        response = discord_request(
            "POST",
            webhook,
            params={"wait": "true"},
            files=files,
            timeout=120,
        )

    message = checked(
        response,
        "Gesamtübersicht veröffentlichen",
    )

    record["message_id"] = str(message["id"])
    record["hash"] = image_hash
    save_state(state)

    print("Übersicht veröffentlicht:", message["id"])
    print("Bilder:", len(images))
    print("Halloween-Nachricht unverändert")
    print("Helper unverändert")
    print("Keine alten Beiträge gelöscht")


if __name__ == "__main__":
    main()
