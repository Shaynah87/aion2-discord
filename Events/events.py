
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
from PIL import Image, ImageDraw, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "events_message.json"
API = "https://discord.com/api/v10"

WIDTH = 1200
HEADER_HEIGHT = 110
ROW_HEIGHT = 64

CATEGORIES = (
    (
        "anwesenheitslisten",
        "Anwesenheitslisten",
        "Anwesenheit/anwesenheitslisten.png",
        0x25A9A6,
    ),
    (
        "ingame_events",
        "Ingame-Events",
        "In-Game/ingame_events.png",
        0x2779BB,
    ),
    (
        "community_events",
        "Community-Events",
        "Community/community_events.png",
        0xB83B91,
    ),
    (
        "twitch_drops",
        "Twitch Drops",
        "Twitch/twitch_drops.png",
        0x8953CF,
    ),
)

HELPER_CATEGORIES = (
    ("Halloween", "halloween_2026", "🎃"),
    ("Anwesenheitslisten", "anwesenheitslisten", "📅"),
    ("Ingame-Events", "ingame_events", "⚔️"),
    ("Community-Events", "community_events", "🎉"),
    ("Twitch Drops", "twitch_drops", "🎁"),
)


# ==================================================
# HTTP
# ==================================================

def api_request(method, url, session=None, **kwargs):
    client = session or requests
    kwargs.setdefault("timeout", 60)

    for attempt in range(12):
        try:
            response = client.request(method, url, **kwargs)
        except (
            requests.ConnectionError,
            requests.Timeout,
        ) as error:
            if method.upper() == "POST":
                raise RuntimeError(
                    "POST-Verbindung unterbrochen. "
                    "Bitte Discord vor erneutem Start prüfen."
                ) from error

            if attempt == 11:
                raise

            time.sleep(min(2 ** attempt, 15))
            continue

        if response.status_code == 429:
            try:
                delay = float(
                    response.json().get("retry_after", 1)
                )
            except (ValueError, TypeError):
                delay = 1.0

            if attempt == 11:
                raise RuntimeError("Discord Rate Limit")

            time.sleep(max(0.5, delay + 0.3))
            continue

        if response.status_code in (500, 502, 503, 504):
            if method.upper() == "POST":
                raise RuntimeError(
                    "Discord-Serverfehler beim POST. "
                    "Vor erneutem Start Discord prüfen."
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


# ==================================================
# STATUSDATEI
# ==================================================

def load_state():
    if not STATE_FILE.is_file():
        raise RuntimeError(
            "Events/events_message.json fehlt"
        )

    state = json.loads(
        STATE_FILE.read_text(encoding="utf-8")
    )

    if not isinstance(state, dict):
        raise RuntimeError("Ungültige Statusdatei")

    return state


def save_state(state):
    temporary = STATE_FILE.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    temporary.replace(STATE_FILE)


# ==================================================
# MODULE UND SCHRIFTEN
# ==================================================

def load_module(relative_path, name):
    path = ROOT / relative_path

    if not path.is_file():
        raise RuntimeError(f"Datei fehlt: {path}")

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if not spec or not spec.loader:
        raise RuntimeError(
            f"Modul kann nicht geladen werden: {path}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def font(size, bold=True):
    filename = (
        "DejaVuSans-Bold.ttf"
        if bold
        else "DejaVuSans.ttf"
    )

    path = (
        Path("/usr/share/fonts/truetype/dejavu")
        / filename
    )

    if not path.is_file():
        raise RuntimeError(f"Schrift fehlt: {path}")

    return ImageFont.truetype(str(path), size)


def to_png(image):
    output = io.BytesIO()

    image.convert("RGB").save(
        output,
        format="PNG",
        optimize=True,
    )

    return output.getvalue()


def fit_font(draw, text, maximum, initial):
    for size in range(initial, 15, -1):
        candidate = font(size)

        bounds = draw.textbbox(
            (0, 0),
            text,
            font=candidate,
        )

        if bounds[2] - bounds[0] <= maximum:
            return candidate

    return font(16)


# ==================================================
# HALLOWEEN – ORIGINALFUNKTION
# ==================================================

def halloween_banner():
    halloween = load_module(
        "Halloween/halloween.py",
        "nyerk24_halloween",
    )

    result = halloween.banner(
        halloween.status()
    )

    with Image.open(io.BytesIO(result)) as image:
        if image.size != (1200, 180):
            raise RuntimeError(
                "Halloween muss 1200x180 sein."
            )

    return result


# ==================================================
# BANNER
# ==================================================

def category_background(relative_path):
    path = ROOT / relative_path

    if not path.is_file():
        raise RuntimeError(
            f"Banner fehlt: {path}"
        )

    with Image.open(path) as source:
        if source.size != (1200, 65):
            raise RuntimeError(
                f"Falsches Bannerformat: {path}"
            )

        return source.convert("RGB")


def draw_category_header(image, title):
    draw = ImageDraw.Draw(image)

    draw.text(
        (WIDTH // 2, image.height // 2),
        title,
        font=font(39),
        anchor="mm",
        fill="white",
        stroke_width=2,
        stroke_fill="#121923",
    )


def standalone_banner(relative_path, title):
    image = category_background(relative_path)

    draw_category_header(image, title)

    return to_png(image)


# ==================================================
# NEUER ANTHRAZIT-EVENTBLOCK
# ==================================================

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


def draw_event_area(image, events, top):
    draw = ImageDraw.Draw(image)

    # Ruhiger, gleichmäßiger Hintergrund.
    # Kein Zuschnitt aus Tracker/event_overview.png.
    for y in range(top, image.height):
        distance = y - top
        shade = max(27, 37 - distance // 75)

        draw.line(
            (0, y, WIDTH, y),
            fill=(shade, shade + 3, shade + 9),
        )

    for index, event in enumerate(events):
        y0 = top + index * ROW_HEIGHT
        center = y0 + ROW_HEIGHT // 2

        if index % 2 == 1:
            draw.rectangle(
                (
                    0,
                    y0,
                    WIDTH - 1,
                    y0 + ROW_HEIGHT - 1,
                ),
                fill=(34, 38, 46),
            )

        if index:
            draw.line(
                (28, y0, WIDTH - 28, y0),
                fill=(63, 70, 81),
                width=1,
            )

        name = str(event["name"])
        period = str(event.get("date_label") or "")

        if event.get("time_label"):
            period += (
                " · " + str(event["time_label"])
            )

        status = event_status(event)

        draw.text(
            (30, center),
            name,
            font=fit_font(
                draw, name, 525, 27
            ),
            anchor="lm",
            fill="#F5F7FB",
        )

        draw.text(
            (785, center),
            period,
            font=fit_font(
                draw, period, 355, 23
            ),
            anchor="mm",
            fill="#CDD6E3",
        )

        status_color = {
            "Gestartet": "#A9E6CF",
            "Kommend": "#F2D59C",
            "Beendet": "#AEB7C5",
        }[status]

        draw.text(
            (1170, center),
            status,
            font=font(24),
            anchor="rm",
            fill=status_color,
        )


def combined_category(relative_path, title, events):
    events = list(events)

    if not events:
        return standalone_banner(relative_path, title)

    original = category_background(relative_path)

    # Die vorhandene Banner-Grafik wird nicht
    # zugeschnitten. Sie erhält einen sanften
    # Übergang in den größeren Kopfbereich.
    total_height = (
        HEADER_HEIGHT + len(events) * ROW_HEIGHT
    )

    image = Image.new(
        "RGB",
        (WIDTH, total_height),
        "#22262E",
    )

    # Originalbanner vollständig erhalten.
    image.paste(original, (0, 0))

    # Die zusätzlichen 45 Pixel bilden einen
    # farblich passenden Übergang.
    bottom_colors = [
        original.getpixel((x, original.height - 1))
        for x in range(WIDTH)
    ]

    draw = ImageDraw.Draw(image)

    for y in range(65, HEADER_HEIGHT):
        progress = (y - 65) / (HEADER_HEIGHT - 65)
        progress = progress ** 0.75

        for x in range(WIDTH):
            r, g, b = bottom_colors[x]

            target = (37, 40, 48)

            color = (
                round(r * (1 - progress) + target[0] * progress),
                round(g * (1 - progress) + target[1] * progress),
                round(b * (1 - progress) + target[2] * progress),
            )

            draw.point((x, y), fill=color)

    # Titel mittig im ursprünglichen Bannerbereich.
    title_draw = ImageDraw.Draw(image)

    title_draw.text(
        (600, 37),
        title,
        font=font(39),
        anchor="mm",
        fill="white",
        stroke_width=2,
        stroke_fill="#121923",
    )

    draw_event_area(
        image,
        events,
        HEADER_HEIGHT,
    )

    return to_png(image)


# ==================================================
# EMBEDS
# ==================================================

def prepare_overview():
    attendance = load_module(
        "Anwesenheit/anwesenheit.py",
        "nyerk24_attendance",
    )

    event_map = {
        "anwesenheitslisten": attendance.EVENTS,
        "ingame_events": (),
        "community_events": (),
        "twitch_drops": (),
    }

    images = [
        (
            "00_halloween.png",
            halloween_banner(),
        )
    ]

    embeds = [
        {
            "color": 0xFF7100,
            "image": {
                "url": "attachment://00_halloween.png"
            },
        }
    ]

    for index, (key, title, path, color) in enumerate(
        CATEGORIES,
        start=1,
    ):
        filename = f"{index:02d}_{key}.png"

        data = combined_category(
            path,
            title,
            event_map[key],
        )

        images.append((filename, data))

        embeds.append({
            "color": color,
            "image": {
                "url": f"attachment://{filename}"
            },
        })

    return images, embeds


def overview_hash(images, embeds):
    digest = hashlib.sha256()

    for filename, data in images:
        digest.update(filename.encode("utf-8"))
        digest.update(data)

    digest.update(
        json.dumps(
            embeds,
            sort_keys=True,
        ).encode("utf-8")
    )

    return digest.hexdigest()


# ==================================================
# HELPER
# ==================================================

def helper_payload():
    options = [
        {
            "label": label,
            "value": value,
            "emoji": {"name": emoji},
        }
        for label, value, emoji in HELPER_CATEGORIES
    ]

    return {
        "content": "",
        "embeds": [
            {
                "title": "Nyerk24 · Event Helper",
                "description": (
                    "Wähle eine Eventkategorie aus, "
                    "um die verfügbaren Events und "
                    "ihre Details aufzurufen.\n\n"
                    "Die Auswahl ist nur für dich sichtbar."
                ),
                "color": 0x596DDB,
            }
        ],
        "components": [
            {
                "type": 1,
                "components": [
                    {
                        "type": 3,
                        "custom_id": "event:menu:category",
                        "placeholder": "Eventkategorie auswählen",
                        "min_values": 1,
                        "max_values": 1,
                        "options": options,
                    }
                ],
            }
        ],
        "allowed_mentions": {
            "parse": [],
        },
    }


def ensure_helper(bot, channel_id, state):
    version = state.setdefault("overview_v6", {})

    helper_id = str(
        version.get("helper_message_id") or ""
    )

    payload = helper_payload()

    if helper_id:
        response = api_request(
            "GET",
            (
                f"{API}/channels/{channel_id}"
                f"/messages/{helper_id}"
            ),
            session=bot,
        )

        if response.status_code == 200:
            message = response.json()

            if not message.get("webhook_id"):
                api_request(
                    "PATCH",
                    (
                        f"{API}/channels/{channel_id}"
                        f"/messages/{helper_id}"
                    ),
                    session=bot,
                    json=payload,
                )

                print(
                    "Vorhandener Helper aktualisiert."
                )
                return

        elif response.status_code != 404:
            checked(response, "Helper prüfen")

    # Ein neuer Helper wird unter dem
    # Gesamtbeitrag veröffentlicht.
    response = api_request(
        "POST",
        f"{API}/channels/{channel_id}/messages",
        session=bot,
        json=payload,
    )

    message = checked(
        response,
        "Helper veröffentlichen",
    )

    version["helper_message_id"] = str(
        message["id"]
    )

    save_state(state)

    print(
        "Helper unter Übersicht erstellt:",
        message["id"],
    )


# ==================================================
# MAIN
# ==================================================

def main():
    state = load_state()

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
        api_request("GET", webhook),
        "Webhook",
    )

    channel_id = str(
        webhook_info["channel_id"]
    )

    webhook_id = str(
        webhook_info["id"]
    )

    images, embeds = prepare_overview()

    digest = overview_hash(images, embeds)

    record = state.setdefault(
        "overview_v6",
        {},
    )

    message_id = str(
        record.get("message_id") or ""
    )

    needs_update = True

    if message_id:
        response = api_request(
            "GET",
            (
                f"{API}/channels/{channel_id}"
                f"/messages/{message_id}"
            ),
            session=bot,
        )

        if response.status_code == 404:
            raise RuntimeError(
                "Gespeicherte Übersicht fehlt. "
                "Kein automatischer Doppelpost."
            )

        message = checked(
            response,
            "Übersicht prüfen",
        )

        if (
            str(message.get("webhook_id") or "")
            != webhook_id
        ):
            raise RuntimeError(
                "Übersicht gehört nicht zu diesem Webhook."
            )

        needs_update = (
            record.get("hash") != digest
        )

    if needs_update:
        payload = {
            "content": "",
            "embeds": embeds,
            "allowed_mentions": {
                "parse": [],
            },
            "attachments": [
                {
                    "id": index,
                    "filename": filename,
                }
                for index, (filename, _) in enumerate(images)
            ],
        }

        multipart = {
            "payload_json": (
                None,
                json.dumps(payload),
            )
        }

        for index, (filename, data) in enumerate(images):
            multipart[f"files[{index}]"] = (
                filename,
                data,
                "image/png",
            )

        if message_id:
            response = api_request(
                "PATCH",
                (
                    f"{webhook}/messages/"
                    f"{message_id}"
                ),
                files=multipart,
                timeout=120,
            )

        else:
            response = api_request(
                "POST",
                webhook,
                params={"wait": "true"},
                files=multipart,
                timeout=120,
            )

        message = checked(
            response,
            "Übersicht veröffentlichen",
        )

        record["message_id"] = str(
            message["id"]
        )

        record["hash"] = digest

        save_state(state)

        print(
            "Übersicht veröffentlicht:",
            message["id"],
        )

    else:
        print(
            "Übersicht unverändert."
        )

    # Helper kommt NACH der Übersicht.
    ensure_helper(
        bot,
        channel_id,
        state,
    )

    print("Fertig.")
    print("Halloween unverändert.")
    print("Anwesenheitslisten zusammengefasst.")
    print("Neuer Anthrazit-Hintergrund.")
    print("Keine alten Beiträge gelöscht.")


if __name__ == "__main__":
    main()
