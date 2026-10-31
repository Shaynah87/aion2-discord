
import hashlib
import importlib.util
import io
import json
import os
import time

from datetime import datetime, time as clock_time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# ALLGEMEINE EINSTELLUNGEN
# ============================================================

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "events_message.json"

API = "https://discord.com/api/v10"
TIMEZONE = ZoneInfo("Europe/Berlin")
DEFAULT_EVENT_TIME = clock_time(8, 30)

WIDTH = 1200
ROW_HEIGHT = 72

TITLE_FONT_SIZE = 42
NAME_FONT_SIZE = 32
DATE_FONT_SIZE = 28
STATUS_FONT_SIZE = 28

BACKGROUND = (35, 39, 47)
NAME_COLOR = "#F5F7FB"
DATE_COLOR = "#F0F2F6"
STARTED_COLOR = "#83D9AC"
UPCOMING_COLOR = "#F29B72"


# ============================================================
# BEREICHSMODULE
#
# Neue Events werden NICHT hier eingetragen.
#
# Jedes Modul verwaltet seine eigenen Events.
# ============================================================

CATEGORIES = (
    {
        "key": "anwesenheitslisten",
        "title": "Anwesenheitslisten",
        "module": "Anwesenheit/anwesenheit.py",
        "banner": "Anwesenheit/anwesenheitslisten.png",
        "color": 0x25A9A6,
    },
    {
        "key": "community_events",
        "title": "Community-Events",
        "module": "Community/community.py",
        "banner": "Community/community_events.png",
        "color": 0xB83B91,
    },
    {
        "key": "ingame_events",
        "title": "Ingame-Events",
        "module": "In-Game/ingame.py",
        "banner": "In-Game/ingame_events.png",
        "color": 0x2779BB,
    },
    {
        "key": "twitch_drops",
        "title": "Twitch Drops",
        "module": "Twitch/twitch.py",
        "banner": "Twitch/twitch_drops.png",
        "color": 0x8953CF,
    },
)

HALLOWEEN_MODULE = "Halloween/halloween.py"

HELPER_CATEGORIES = (
    ("Halloween", "halloween_2026", "🎃"),
    ("Anwesenheitslisten", "anwesenheitslisten", "📅"),
    ("Ingame-Events", "ingame_events", "⚔️"),
    ("Community-Events", "community_events", "🎉"),
    ("Twitch Drops", "twitch_drops", "🎁"),
)


# ============================================================
# MODULE LADEN
# ============================================================

def load_module(relative_path, name):
    path = ROOT / relative_path

    if not path.is_file():
        raise FileNotFoundError(
            f"Bereichsmodul fehlt: {relative_path}"
        )

    spec = importlib.util.spec_from_file_location(
        name, path
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Modul kann nicht geladen werden: {path}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_events(category):
    module = load_module(
        category["module"],
        "nyerk24_" + category["key"],
    )

    events = getattr(module, "EVENTS", None)

    if events is None:
        raise RuntimeError(
            f"{category['module']} enthält keine EVENTS"
        )

    if not isinstance(events, (list, tuple)):
        raise TypeError(
            f"EVENTS muss eine Liste oder ein Tupel sein: "
            f"{category['module']}"
        )

    return list(events)


# ============================================================
# ZEITBERECHNUNG
# ============================================================

def parse_datetime(value):
    raw = str(value)
    parsed = datetime.fromisoformat(raw)

    if parsed.tzinfo is None:
        if "T" not in raw and " " not in raw:
            parsed = datetime.combine(
                parsed.date(),
                DEFAULT_EVENT_TIME,
            )

        parsed = parsed.replace(tzinfo=TIMEZONE)

    return parsed.astimezone(TIMEZONE)


def start_time(event):
    return parse_datetime(event["start"])


def end_time(event):
    return parse_datetime(event["end"])


def event_status(event, now=None):
    now = now or datetime.now(TIMEZONE)

    if now >= end_time(event):
        return None

    if now < start_time(event):
        return "KOMMEND"

    return "GESTARTET"


def sorted_events(events):
    now = datetime.now(TIMEZONE)

    started = []
    upcoming = []

    for event in events:
        status = event_status(event, now)

        if status == "GESTARTET":
            started.append(event)
        elif status == "KOMMEND":
            upcoming.append(event)

    started.sort(
        key=lambda event: (
            end_time(event).timestamp(),
            -start_time(event).timestamp(),
        )
    )

    upcoming.sort(key=start_time)

    return started + upcoming


# ============================================================
# SCHRIFTEN UND BILDER
# ============================================================

def font(size, bold=True):
    filename = (
        "DejaVuSans-Bold.ttf"
        if bold else "DejaVuSans.ttf"
    )

    return ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/" + filename,
        size,
    )


def fit_font(draw, text, max_width, size,
             minimum=18, bold=True):
    for candidate_size in range(
        size, minimum - 1, -1
    ):
        candidate = font(candidate_size, bold)
        bounds = draw.textbbox(
            (0, 0), text, font=candidate
        )

        if bounds[2] - bounds[0] <= max_width:
            return candidate

    return font(minimum, bold)


def image_to_png(image):
    output = io.BytesIO()

    image.convert("RGB").save(
        output,
        format="PNG",
        optimize=True,
    )

    return output.getvalue()


# ============================================================
# EVENTNAMEN
# ============================================================

def display_name(event):
    name = str(event["name"])

    replacements = {
        "Transcendence Dungeon Leaderboard":
            "Transcendence Leaderboard",
        "Süßes oder Saures!":
            "Süßes oder Saures",
    }

    return replacements.get(name, name)


# ============================================================
# EVENTZEILEN ZEICHNEN
# ============================================================

def draw_events(image, events, top):
    draw = ImageDraw.Draw(image)

    for index, event in enumerate(events):
        y0 = top + index * ROW_HEIGHT
        y1 = y0 + ROW_HEIGHT - 1
        center = y0 + ROW_HEIGHT // 2

        color = (
            (35, 39, 47)
            if index % 2 == 0
            else (33, 37, 45)
        )

        draw.rectangle(
            (0, y0, WIDTH - 1, y1),
            fill=color,
        )

        if index:
            draw.line(
                (28, y0, WIDTH - 28, y0),
                fill=(62, 69, 80),
                width=1,
            )

        name = display_name(event)
        period = str(event.get("date_label", ""))
        status = event_status(event)

        if status is None:
            continue

        draw.text(
            (30, center),
            name,
            font=fit_font(
                draw, name, 525, NAME_FONT_SIZE
            ),
            anchor="lm",
            fill=NAME_COLOR,
        )

        draw.text(
            (785, center),
            period,
            font=fit_font(
                draw,
                period,
                355,
                DATE_FONT_SIZE,
                bold=False,
            ),
            anchor="mm",
            fill=DATE_COLOR,
        )

        status_color = (
            STARTED_COLOR
            if status == "GESTARTET"
            else UPCOMING_COLOR
        )

        draw.text(
            (1170, center),
            status,
            font=font(STATUS_FONT_SIZE),
            anchor="rm",
            fill=status_color,
        )


# ============================================================
# KATEGORIEBANNER
# ============================================================

def create_category_image(category, events):
    events = sorted_events(events)

    banner_path = ROOT / category["banner"]

    with Image.open(banner_path) as source:
        banner = source.convert("RGB")

    if banner.width != WIDTH:
        raise RuntimeError(
            f"Banner muss {WIDTH} Pixel breit sein: "
            f"{banner_path}"
        )

    banner_height = banner.height

    if banner_height < 65:
        raise RuntimeError(
            f"Banner zu niedrig: {banner_path}"
        )

    header_height = banner_height + 45
    height = header_height + len(events) * ROW_HEIGHT

    image = Image.new(
        "RGB",
        (WIDTH, height),
        BACKGROUND,
    )

    image.paste(banner, (0, 0))
    draw = ImageDraw.Draw(image)

    # Übergang vom Banner zur Eventliste
    edge_colors = [
        banner.getpixel((x, banner_height - 1))
        for x in range(WIDTH)
    ]

    for y in range(banner_height, header_height):
        progress = (
            (y - banner_height + 1) / 45
        ) ** 0.72

        for x in range(WIDTH):
            source = edge_colors[x]

            color = tuple(
                round(
                    source[channel] * (1 - progress)
                    + BACKGROUND[channel] * progress
                )
                for channel in range(3)
            )

            draw.point((x, y), fill=color)

    draw.text(
        (WIDTH // 2, banner_height // 2),
        category["title"],
        font=font(TITLE_FONT_SIZE),
        anchor="mm",
        fill="white",
        stroke_width=2,
        stroke_fill="#111722",
    )

    if events:
        draw_events(image, events, header_height)

    return image_to_png(image)


# ============================================================
# HALLOWEEN
#
# Halloween behält seine eigene Darstellung.
# ============================================================

def halloween_banner():
    halloween = load_module(
        HALLOWEEN_MODULE,
        "nyerk24_halloween",
    )

    data = halloween.banner(
        halloween.status()
    )

    with Image.open(io.BytesIO(data)) as image:
        if image.size != (1200, 180):
            raise RuntimeError(
                "Halloween-Banner muss 1200x180 sein"
            )

    return data


# ============================================================
# GESAMTÜBERSICHT ZUSAMMENSTELLEN
# ============================================================

def prepare_overview():
    images = [
        ("00_halloween.png", halloween_banner())
    ]

    embeds = [{
        "color": 0xFF7100,
        "image": {
            "url": "attachment://00_halloween.png"
        },
    }]

    for index, category in enumerate(
        CATEGORIES, start=1
    ):
        events = load_events(category)

        filename = (
            f"{index:02d}_{category['key']}.png"
        )

        data = create_category_image(
            category, events
        )

        images.append((filename, data))

        embeds.append({
            "color": category["color"],
            "image": {
                "url": f"attachment://{filename}"
            },
        })

        print(
            f"{category['title']}: "
            f"{len(sorted_events(events))} "
            "sichtbare Events"
        )

    return images, embeds


# ============================================================
# ÄNDERUNGEN ERKENNEN
# ============================================================

def overview_hash(images, embeds):
    digest = hashlib.sha256()

    for filename, data in images:
        digest.update(filename.encode("utf-8"))
        digest.update(data)

    digest.update(
        json.dumps(
            embeds, sort_keys=True
        ).encode("utf-8")
    )

    return digest.hexdigest()


# ============================================================
# STATUSDATEI
# ============================================================

def load_state():
    if not STATE_FILE.exists():
        return {}

    state = json.loads(
        STATE_FILE.read_text(encoding="utf-8")
    )

    if not isinstance(state, dict):
        raise RuntimeError(
            "Ungültige events_message.json"
        )

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


# ============================================================
# DISCORD API
# ============================================================

def api_request(method, url, session=None, **kwargs):
    client = session or requests
    kwargs.setdefault("timeout", 60)

    for attempt in range(10):
        response = client.request(
            method, url, **kwargs
        )

        if response.status_code == 429:
            if attempt == 9:
                return response

            try:
                delay = float(
                    response.json().get("retry_after", 1)
                )
            except (ValueError, TypeError):
                delay = 1

            time.sleep(max(0.5, delay + 0.3))
            continue

        if response.status_code in (
            500, 502, 503, 504
        ):
            if method.upper() == "POST":
                raise RuntimeError(
                    "Discord-Fehler beim POST. "
                    "Vor erneutem Start prüfen, "
                    "ob eine Nachricht erstellt wurde."
                )

            if attempt == 9:
                return response

            time.sleep(min(2 ** attempt, 15))
            continue

        return response

    raise RuntimeError(
        "Discord-Anfrage fehlgeschlagen"
    )


def checked(response, label):
    if not response.ok:
        raise RuntimeError(
            f"{label}: HTTP {response.status_code}: "
            f"{response.text[:800]}"
        )

    return (
        response.json()
        if response.content
        else {}
    )


# ============================================================
# EVENT-HELPER
# ============================================================

def helper_payload():
    return {
        "content": "",
        "embeds": [{
            "title": "Nyerk24 · Event Helper",
            "description": (
                "Wähle eine Eventkategorie aus, "
                "um die verfügbaren Events und "
                "ihre Details aufzurufen.\n\n"
                "Deine Auswahl ist nur für "
                "dich sichtbar."
            ),
            "color": 0x596DDB,
        }],
        "components": [{
            "type": 1,
            "components": [{
                "type": 3,
                "custom_id": "event:menu:category",
                "placeholder": "Eventkategorie auswählen",
                "min_values": 1,
                "max_values": 1,
                "options": [
                    {
                        "label": label,
                        "value": value,
                        "emoji": {"name": emoji},
                    }
                    for label, value, emoji
                    in HELPER_CATEGORIES
                ],
            }],
        }],
        "allowed_mentions": {"parse": []},
    }


def helper_candidates(state):
    candidates = []

    records = [
        state.get("overview_v6", {}).get(
            "helper_message_id"
        ),
        state.get("overview_v2", {}).get(
            "helper", {}
        ).get("message_id"),
        state.get("halloween_2026", {}).get(
            "helper_message_id"
        ),
    ]

    for value in records:
        if value and str(value) not in candidates:
            candidates.append(str(value))

    return candidates


def ensure_helper(bot, channel_id, state):
    try:
        me = checked(
            api_request(
                "GET",
                f"{API}/users/@me",
                session=bot,
            ),
            "Bot prüfen",
        )

        bot_id = str(me["id"])

        for message_id in helper_candidates(state):
            response = api_request(
                "GET",
                (
                    f"{API}/channels/{channel_id}"
                    f"/messages/{message_id}"
                ),
                session=bot,
            )

            if response.status_code in (403, 404):
                continue

            message = checked(
                response, "Helper prüfen"
            )

            if str(
                message.get("author", {}).get("id", "")
            ) != bot_id:
                continue

            component_ids = [
                component.get("custom_id")
                for row in message.get("components", [])
                for component in row.get(
                    "components", []
                )
            ]

            if (
                "event:menu:category"
                not in component_ids
            ):
                response = api_request(
                    "PATCH",
                    (
                        f"{API}/channels/{channel_id}"
                        f"/messages/{message_id}"
                    ),
                    session=bot,
                    json=helper_payload(),
                )

                if not response.ok:
                    print(
                        "WARNUNG: Helper-Update:",
                        response.status_code,
                        response.text[:300],
                    )
                    continue

            state.setdefault(
                "overview_v6", {}
            )["helper_message_id"] = message_id

            save_state(state)

            print(
                "Bestehender Helper:",
                message_id,
            )
            return

        response = api_request(
            "POST",
            (
                f"{API}/channels/{channel_id}"
                "/messages"
            ),
            session=bot,
            json=helper_payload(),
        )

        if response.status_code == 403:
            print(
                "WARNUNG: Keine Berechtigung "
                "zum Erstellen des Helpers."
            )
            return

        message = checked(
            response,
            "Helper veröffentlichen",
        )

        state.setdefault(
            "overview_v6", {}
        )["helper_message_id"] = str(
            message["id"]
        )

        save_state(state)

        print(
            "Neuer Helper:",
            message["id"],
        )

    except Exception as error:
        print(
            "WARNUNG: Helper:",
            error,
        )


# ============================================================
# DISCORD-SYNCHRONISIERUNG
# ============================================================

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
        "Webhook prüfen",
    )

    channel_id = str(
        webhook_info["channel_id"]
    )
    webhook_id = str(
        webhook_info["id"]
    )

    # Erst alle Module laden und Bilder erstellen.
    # Bei einem Fehler wird nichts veröffentlicht.
    images, embeds = prepare_overview()
    digest = overview_hash(images, embeds)

    # Bestehende Nachrichten-ID weiterverwenden.
    record = state.setdefault(
        "overview_v6", {}
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
                "Gespeicherte Eventübersicht "
                "nicht gefunden. "
                "Kein automatischer Doppelpost."
            )

        message = checked(
            response,
            "Übersicht prüfen",
        )

        if str(
            message.get("webhook_id") or ""
        ) != webhook_id:
            raise RuntimeError(
                "Nachricht gehört nicht "
                "zum erwarteten Webhook."
            )

        needs_update = (
            record.get("hash") != digest
        )

    if needs_update:
        payload = {
            "content": "",
            "embeds": embeds,
            "allowed_mentions": {"parse": []},
            "attachments": [
                {
                    "id": index,
                    "filename": filename,
                }
                for index, (filename, _)
                in enumerate(images)
            ],
        }

        multipart = {
            "payload_json": (
                None,
                json.dumps(
                    payload,
                    ensure_ascii=False,
                ),
            )
        }

        for index, (filename, data) in enumerate(
            images
        ):
            multipart[f"files[{index}]"] = (
                filename,
                data,
                "image/png",
            )

        if message_id:
            response = api_request(
                "PATCH",
                f"{webhook}/messages/{message_id}",
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
            "Übersicht aktualisiert:",
            message["id"],
        )

    else:
        print("Übersicht unverändert.")

    ensure_helper(
        bot,
        channel_id,
        state,
    )

    print("Events-Synchronisierung abgeschlossen.")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
