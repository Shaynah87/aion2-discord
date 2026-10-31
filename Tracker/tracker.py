
import hashlib
import importlib.util
import io
import json
import os
import time

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "events_message.json"
API = "https://discord.com/api/v10"
TIMEZONE = ZoneInfo("Europe/Berlin")

WIDTH = 1200
BANNER_HEIGHT = 65
HEADER_HEIGHT = 110
EMPTY_HEADER_HEIGHT = 94
ROW_HEIGHT = 72

TITLE_FONT_SIZE = 42
NAME_FONT_SIZE = 32
DATE_FONT_SIZE = 28
STATUS_FONT_SIZE = 28

STARTED_COLOR = "#83D9AC"
UPCOMING_COLOR = "#F29B72"

CATEGORIES = (
    ("anwesenheitslisten", "Anwesenheitslisten",
     "Anwesenheit/anwesenheitslisten.png", 0x25A9A6),
    ("ingame_events", "Ingame-Events",
     "In-Game/ingame_events.png", 0x2779BB),
    ("community_events", "Community-Events",
     "Community/community_events.png", 0xB83B91),
    ("twitch_drops", "Twitch Drops",
     "Twitch/twitch_drops.png", 0x8953CF),
)

HELPER_CATEGORIES = (
    ("Halloween", "halloween_2026", "🎃"),
    ("Anwesenheitslisten", "anwesenheitslisten", "📅"),
    ("Ingame-Events", "ingame_events", "⚔️"),
    ("Community-Events", "community_events", "🎉"),
    ("Twitch Drops", "twitch_drops", "🎁"),
)


# ============================================================
# ZUSÄTZLICHE EVENTS
# ============================================================

INGAME_EVENTS = (
    {
        "id": "odenergie_boost",
        "name": "Odenergie-Boost",
        "start": "2026-10-28",
        "end": "2026-11-11",
        "date_label": "28.10.–11.11.26",
    },
    {
        "id": "ludra_jagd",
        "name": "Ludra-Jagd",
        "start": "2026-11-04",
        "end": "2026-11-25",
        "date_label": "04.11.–25.11.26",
    },
)

COMMUNITY_EVENTS = (
    {
        "id": "guides_for_glory",
        "name": "Guides for Glory",
        "start": "2026-10-05",
        "end": "2026-11-02",
        "date_label": "05.10.–02.11.26",
    },
    {
        "id": "transcendence_leaderboard",
        "name": "Transcendence Dungeon Leaderboard",
        "start": "2026-10-05",
        "end": "2026-11-02",
        "date_label": "05.10.–02.11.26",
    },
    {
        "id": "beauty_of_atreia",
        "name": "Beauty of Atreia",
        "start": "2026-10-05",
        "end": "2026-11-09",
        "date_label": "05.10.–09.11.26",
    },
    {
        "id": "daeva_bootcamp",
        "name": "Daeva Bootcamp",
        "start": "2026-11-04",
        "end": "2026-11-18",
        "date_label": "04.11.–18.11.26",
    },
    {
        "id": "ludra_outfit",
        "name": "Ludra-Outfit-Wettbewerb",
        "start": "2026-11-04",
        "end": "2026-11-18",
        "date_label": "04.11.–18.11.26",
    },
)

TWITCH_EVENTS = (
    {
        "id": "halloween_twitch",
        "name": "Globale Halloween Twitch-Drops",
        "start": "2026-10-28T18:00:00+01:00",
        "end": "2026-11-04T08:59:00+01:00",
        "date_label": "28.10.–04.11.26",
    },
    {
        "id": "ludra_twitch",
        "name": "Ludra Twitch-Drops",
        "start": "2026-11-04T15:00:00+01:00",
        "end": "2026-11-18T08:59:00+01:00",
        "date_label": "04.11.–18.11.26",
    },
)

ADDITIONAL_ATTENDANCE = (
    {
        "id": "ludra_anwesenheit",
        "name": "Ludra-Eroberung",
        "start": "2026-11-04T15:00:00+01:00",
        "end": "2026-11-18T08:59:00+01:00",
        "date_label": "04.11.–18.11.26",
    },
)


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def api_request(method, url, session=None, **kwargs):
    client = session or requests
    kwargs.setdefault("timeout", 60)

    for attempt in range(10):
        response = client.request(method, url, **kwargs)

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

        if response.status_code in (500, 502, 503, 504):
            if method.upper() == "POST":
                raise RuntimeError(
                    "Discord-Fehler beim POST. "
                    "Bitte vor einem erneuten Lauf prüfen, "
                    "ob die Nachricht erstellt wurde."
                )
            if attempt == 9:
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


def load_state():
    if not STATE_FILE.exists():
        return {}

    state = json.loads(
        STATE_FILE.read_text(encoding="utf-8")
    )
    if not isinstance(state, dict):
        raise RuntimeError("Ungültige Statusdatei")
    return state


def save_state(state):
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(STATE_FILE)


def load_module(path, name):
    filename = ROOT / path
    spec = importlib.util.spec_from_file_location(
        name, filename
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Modul fehlt: {filename}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def font(size, bold=True):
    filename = (
        "DejaVuSans-Bold.ttf"
        if bold else "DejaVuSans.ttf"
    )
    return ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/" + filename,
        size,
    )


def fit_font(draw, value, maximum_width, size,
             minimum=18, bold=True):
    for candidate_size in range(size, minimum - 1, -1):
        candidate = font(candidate_size, bold)
        box = draw.textbbox(
            (0, 0), value, font=candidate
        )
        if box[2] - box[0] <= maximum_width:
            return candidate
    return font(minimum, bold)


def png(image):
    output = io.BytesIO()
    image.convert("RGB").save(
        output, format="PNG", optimize=True
    )
    return output.getvalue()


# ============================================================
# DATEN UND SORTIERUNG
# ============================================================

def parse_datetime(value, end_of_day=False):
    parsed = datetime.fromisoformat(str(value))

    if parsed.tzinfo is None:
        if end_of_day:
            parsed = parsed.replace(
                hour=23, minute=59, second=59
            )
        parsed = parsed.replace(tzinfo=TIMEZONE)

    return parsed.astimezone(TIMEZONE)


def start_time(event):
    return parse_datetime(event["start"])


def end_time(event):
    value = str(event["end"])
    return parse_datetime(
        value,
        end_of_day=("T" not in value),
    )


def event_status(event, now=None):
    now = now or datetime.now(TIMEZONE)

    if now > end_time(event):
        return None

    if now < start_time(event):
        return "KOMMEND"

    return "GESTARTET"


def sorted_events(events):
    now = datetime.now(TIMEZONE)
    active = []
    upcoming = []

    for event in events:
        status = event_status(event, now)

        if status == "GESTARTET":
            active.append(event)
        elif status == "KOMMEND":
            upcoming.append(event)

    # Zuerst das früheste Enddatum.
    # Bei gleichem Enddatum steht der
    # spätere Start weiter oben.
    active.sort(
        key=lambda event: (
            end_time(event).timestamp(),
            -start_time(event).timestamp(),
        )
    )

    # Kommende Events nach Startdatum.
    upcoming.sort(key=start_time)

    return active + upcoming


# ============================================================
# HALLOWEEN
# ============================================================

def halloween_banner():
    halloween = load_module(
        "Halloween/halloween.py",
        "nyerk24_halloween",
    )
    data = halloween.banner(halloween.status())

    with Image.open(io.BytesIO(data)) as image:
        if image.size != (1200, 180):
            raise RuntimeError(
                "Halloween-Banner muss 1200x180 sein"
            )

    return data


# ============================================================
# KATEGORIEGRAFIKEN
# ============================================================

def category_background(relative_path):
    path = ROOT / relative_path

    with Image.open(path) as original:
        if original.size != (WIDTH, BANNER_HEIGHT):
            raise RuntimeError(
                f"Falsches Bannerformat: {path}"
            )
        return original.convert("RGB")


def draw_event_area(image, events, top):
    draw = ImageDraw.Draw(image)

    for index, event in enumerate(events):
        y0 = top + index * ROW_HEIGHT
        y1 = y0 + ROW_HEIGHT - 1
        center = y0 + ROW_HEIGHT // 2

        background = (
            (35, 39, 47)
            if index % 2 == 0
            else (33, 37, 45)
        )

        draw.rectangle(
            (0, y0, WIDTH - 1, y1),
            fill=background,
        )

        if index:
            draw.line(
                (28, y0, WIDTH - 28, y0),
                fill=(62, 69, 80),
                width=1,
            )

        name = str(event["name"])
        period = str(event.get("date_label", ""))

        if event.get("time_label"):
            period += " · " + str(event["time_label"])

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
            fill="#F5F7FB",
        )

        draw.text(
            (785, center),
            period,
            font=fit_font(
                draw, period, 355,
                DATE_FONT_SIZE, bold=False
            ),
            anchor="mm",
            fill="#CDD6E3",
        )

        color = (
            STARTED_COLOR
            if status == "GESTARTET"
            else UPCOMING_COLOR
        )

        draw.text(
            (1170, center),
            status,
            font=font(STATUS_FONT_SIZE),
            anchor="rm",
            fill=color,
        )


def create_category_image(relative_path, title, events):
    events = sorted_events(events)

    header_height = (
        HEADER_HEIGHT if events
        else EMPTY_HEADER_HEIGHT
    )

    height = header_height + len(events) * ROW_HEIGHT

    original = category_background(relative_path)

    image = Image.new(
        "RGB",
        (WIDTH, height),
        (35, 39, 47),
    )
    image.paste(original, (0, 0))

    draw = ImageDraw.Draw(image)

    edge_colors = [
        original.getpixel((x, BANNER_HEIGHT - 1))
        for x in range(WIDTH)
    ]

    target = (35, 39, 47)
    fade_height = header_height - BANNER_HEIGHT

    for y in range(BANNER_HEIGHT, header_height):
        progress = (
            (y - BANNER_HEIGHT + 1)
            / max(1, fade_height)
        ) ** 0.72

        for x in range(WIDTH):
            source = edge_colors[x]
            color = tuple(
                round(
                    source[channel] * (1 - progress)
                    + target[channel] * progress
                )
                for channel in range(3)
            )
            draw.point((x, y), fill=color)

    draw.text(
        (WIDTH // 2, 37),
        title,
        font=font(TITLE_FONT_SIZE),
        anchor="mm",
        fill="white",
        stroke_width=2,
        stroke_fill="#111722",
    )

    if events:
        draw_event_area(image, events, header_height)

    return png(image)


# ============================================================
# ÜBERSICHT
# ============================================================

def prepare_overview():
    attendance = load_module(
        "Anwesenheit/anwesenheit.py",
        "nyerk24_attendance",
    )

    attendance_events = list(attendance.EVENTS)

    existing_ids = {
        event["id"] for event in attendance_events
    }

    for event in ADDITIONAL_ATTENDANCE:
        if event["id"] not in existing_ids:
            attendance_events.append(event)

    event_map = {
        "anwesenheitslisten": attendance_events,
        "ingame_events": INGAME_EVENTS,
        "community_events": COMMUNITY_EVENTS,
        "twitch_drops": TWITCH_EVENTS,
    }

    images = [
        ("00_halloween.png", halloween_banner())
    ]

    embeds = [{
        "color": 0xFF7100,
        "image": {
            "url": "attachment://00_halloween.png"
        },
    }]

    for index, (
        key, title, path, color
    ) in enumerate(CATEGORIES, start=1):

        filename = f"{index:02d}_{key}.png"

        images.append((
            filename,
            create_category_image(
                path, title, event_map[key]
            ),
        ))

        embeds.append({
            "color": color,
            "image": {
                "url": f"attachment://{filename}"
            },
        })

        print(
            f"{title}: "
            f"{len(sorted_events(event_map[key]))} "
            "sichtbare Events"
        )

    return images, embeds


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
# HELPER
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

    for value in (
        state.get("overview_v6", {}).get(
            "helper_message_id"
        ),
        state.get("overview_v2", {}).get(
            "helper", {}
        ).get("message_id"),
        state.get("halloween_2026", {}).get(
            "helper_message_id"
        ),
    ):
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
                for component in row.get("components", [])
            ]

            if "event:menu:category" not in component_ids:
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
                "Bestehender Helper gefunden:",
                message_id,
            )
            return

        # Nur wenn kein vorhandener Helper
        # gefunden wurde.
        response = api_request(
            "POST",
            f"{API}/channels/{channel_id}/messages",
            session=bot,
            json=helper_payload(),
        )

        if response.status_code == 403:
            print(
                "WARNUNG: Helper konnte nicht "
                "erstellt werden (403)."
            )
            print(
                "Die Eventübersicht wurde "
                "trotzdem erfolgreich verarbeitet."
            )
            return

        message = checked(
            response, "Helper veröffentlichen"
        )

        state.setdefault(
            "overview_v6", {}
        )["helper_message_id"] = str(message["id"])

        save_state(state)

        print(
            "Neuer Helper:",
            message["id"],
        )

    except Exception as error:
        print(
            "WARNUNG: Helper konnte nicht "
            "verarbeitet werden:",
            error,
        )
        print(
            "Die Eventübersicht bleibt erhalten."
        )


# ============================================================
# DISCORD
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

    channel_id = str(webhook_info["channel_id"])
    webhook_id = str(webhook_info["id"])

    images, embeds = prepare_overview()
    digest = overview_hash(images, embeds)

    record = state.setdefault("overview_v6", {})
    message_id = str(record.get("message_id") or "")

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
                "nicht gefunden. Kein Doppelpost."
            )

        message = checked(
            response, "Übersicht prüfen"
        )

        if str(
            message.get("webhook_id") or ""
        ) != webhook_id:
            raise RuntimeError(
                "Die Übersicht gehört nicht "
                "zum erwarteten Webhook."
            )

        needs_update = record.get("hash") != digest

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
                    payload, ensure_ascii=False
                ),
            )
        }

        for index, (filename, data) in enumerate(images):
            multipart[f"files[{index}]"] = (
                filename, data, "image/png"
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
            response, "Übersicht veröffentlichen"
        )

        record["message_id"] = str(message["id"])
        record["hash"] = digest
        save_state(state)

        print(
            "Übersicht aktualisiert:",
            message["id"],
        )

    else:
        print("Übersicht unverändert.")

    ensure_helper(bot, channel_id, state)

    print("Fertig.")


if __name__ == "__main__":
    main()
