
"""
Nyerk24 · Events

Eine gemeinsame Discord-Nachricht mit:
- Halloween-Banner aus Halloween/halloween.py (1200x180)
- vier Kategorie-Bannern (je 1200x65)
- einem gemeinsamen Eventblock für Anwesenheitslisten

Die vorhandenen Discord-Nachrichten werden nicht gelöscht.
Der Helper und die Halloween-Details bleiben unverändert.
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
STATE_FILE = ROOT / "events_message.json"

API = "https://discord.com/api/v10"

WIDTH = 1200
BANNER_HEIGHT = 65
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


# --------------------------------------------------
# DISCORD
# --------------------------------------------------

def discord_request(method, url, session=None, **kwargs):
    client = session or requests
    kwargs.setdefault("timeout", 45)

    for attempt in range(12):
        try:
            response = client.request(
                method,
                url,
                **kwargs,
            )
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as error:
            if method.upper() == "POST":
                raise RuntimeError(
                    "Verbindung während POST unterbrochen. "
                    "Bitte vor erneutem Start den "
                    "Discord-Kanal kontrollieren."
                ) from error

            if attempt == 11:
                raise

            time.sleep(min(2 ** attempt, 15))
            continue

        if response.status_code == 429:
            try:
                retry_after = float(
                    response.json().get("retry_after", 1)
                )
            except (ValueError, TypeError):
                retry_after = 1.0

            if attempt == 11:
                raise RuntimeError(
                    "Discord Rate Limit nach 12 Versuchen"
                )

            time.sleep(max(0.5, retry_after + 0.3))
            continue

        if response.status_code in (500, 502, 503, 504):
            if method.upper() == "POST":
                raise RuntimeError(
                    "Discord-Serverfehler beim POST. "
                    "Vor einem erneuten Lauf prüfen, "
                    "ob die Nachricht erstellt wurde."
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


# --------------------------------------------------
# STATUSDATEI
# --------------------------------------------------

def load_state():
    if not STATE_FILE.exists():
        raise RuntimeError(
            "Events/events_message.json fehlt"
        )

    state = json.loads(
        STATE_FILE.read_text(encoding="utf-8")
    )

    if not isinstance(state, dict):
        raise RuntimeError(
            "events_message.json ist ungültig"
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


# --------------------------------------------------
# PYTHON-MODULE LADEN
# --------------------------------------------------

def load_module(relative_path, module_name):
    path = ROOT / relative_path

    if not path.is_file():
        raise RuntimeError(
            f"Python-Datei fehlt: {path}"
        )

    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Python-Modul kann nicht geladen werden: {path}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


# --------------------------------------------------
# SCHRIFTEN / BILDER
# --------------------------------------------------

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
        raise RuntimeError(
            f"Schriftart fehlt: {path}"
        )

    return ImageFont.truetype(
        str(path),
        size,
    )


def image_bytes(image):
    buffer = io.BytesIO()

    image.convert("RGB").save(
        buffer,
        format="PNG",
        optimize=True,
    )

    return buffer.getvalue()


def fit_font(draw, text, max_width, initial_size):
    for size in range(initial_size, 15, -1):
        current = font(size)

        bounds = draw.textbbox(
            (0, 0),
            text,
            font=current,
        )

        if bounds[2] - bounds[0] <= max_width:
            return current

    return font(16)


# --------------------------------------------------
# HALLOWEEN – BESTEHENDE FUNKTION VERWENDEN
# --------------------------------------------------

def halloween_banner():
    halloween = load_module(
        "Halloween/halloween.py",
        "nyerk24_halloween",
    )

    # Die Originaldatei stellt diese Funktionen
    # bereits zur Verfügung.
    current = halloween.status()
    data = halloween.banner(current)

    with Image.open(io.BytesIO(data)) as image:
        if image.size != (1200, 180):
            raise RuntimeError(
                "Halloween-Banner muss 1200x180 sein. "
                f"Erhalten: {image.size}"
            )

    print(
        "Halloween erfolgreich erzeugt:",
        current,
        "1200x180",
    )

    return data


# --------------------------------------------------
# KATEGORIE-BANNER
# --------------------------------------------------

def category_banner(relative_path, title):
    path = ROOT / relative_path

    if not path.is_file():
        raise RuntimeError(
            f"Kategorie-Banner fehlt: {path}"
        )

    with Image.open(path) as source:
        if source.size != (WIDTH, BANNER_HEIGHT):
            raise RuntimeError(
                f"Falsche Bannergröße: {path}. "
                f"Erwartet 1200x65, "
                f"erhalten {source.size}"
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

    return image_bytes(image)


# --------------------------------------------------
# GEMEINSAMER GRAUER EVENTBLOCK
# --------------------------------------------------

def event_background():
    path = REPO / "Tracker" / "event_overview.png"

    if not path.is_file():
        raise RuntimeError(
            f"Eventvorlage fehlt: {path}"
        )

    with Image.open(path) as source:
        original = source.convert("RGB")

    return ImageOps.fit(
        original,
        (WIDTH, ROW_HEIGHT),
        method=Image.Resampling.LANCZOS,
    )


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


def create_event_block(events):
    events = list(events)

    if not events:
        return None

    background = event_background()

    block = Image.new(
        "RGB",
        (
            WIDTH,
            len(events) * ROW_HEIGHT,
        ),
        "#24272E",
    )

    for index, event in enumerate(events):
        row = background.copy()
        draw = ImageDraw.Draw(row)

        name = str(event["name"])
        period = str(
            event.get("date_label") or ""
        )

        if event.get("time_label"):
            period += (
                " · " + str(event["time_label"])
            )

        status = event_status(event)

        # Links: Eventname
        draw.text(
            (25, ROW_HEIGHT // 2),
            name,
            font=fit_font(
                draw,
                name,
                530,
                26,
            ),
            anchor="lm",
            fill="white",
            stroke_width=1,
            stroke_fill="#10151E",
        )

        # Mitte: Zeitraum
        draw.text(
            (790, ROW_HEIGHT // 2),
            period,
            font=fit_font(
                draw,
                period,
                350,
                22,
            ),
            anchor="mm",
            fill="#E5EAF2",
            stroke_width=1,
            stroke_fill="#10151E",
        )

        # Rechts: Status
        draw.text(
            (1175, ROW_HEIGHT // 2),
            status,
            font=font(23),
            anchor="rm",
            fill="white",
            stroke_width=1,
            stroke_fill="#10151E",
        )

        block.paste(
            row,
            (0, index * ROW_HEIGHT),
        )

    return image_bytes(block)


# --------------------------------------------------
# BILDER ZUSAMMENSTELLEN
# --------------------------------------------------

def prepare_images():
    images = []

    # Halloween als separates Bild in Originalgröße.
    images.append((
        "00_halloween.png",
        halloween_banner(),
    ))

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

    for index, (key, title, path) in enumerate(
        CATEGORIES,
        start=1,
    ):
        # Kategorie-Banner separat.
        images.append((
            f"{index:02d}_{key}.png",
            category_banner(path, title),
        ))

        # Alle Events der Kategorie in EIN Bild.
        block = create_event_block(
            event_map[key]
        )

        if block is not None:
            images.append((
                f"{index:02d}_{key}_events.png",
                block,
            ))

    if len(images) > 10:
        raise RuntimeError(
            "Discord erlaubt maximal zehn "
            "Anhänge pro Nachricht."
        )

    print(
        f"{len(images)} Einzelbilder vorbereitet"
    )

    return images


def images_hash(images):
    digest = hashlib.sha256()

    for filename, data in images:
        digest.update(
            filename.encode("utf-8")
        )
        digest.update(data)

    return digest.hexdigest()


# --------------------------------------------------
# HAUPTPROGRAMM
# --------------------------------------------------

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
        discord_request(
            "GET",
            webhook,
        ),
        "Webhook prüfen",
    )

    channel_id = str(
        webhook_info["channel_id"]
    )

    webhook_id = str(
        webhook_info["id"]
    )

    # Alle Bilder lokal vorbereiten.
    # Kein Download aus einer Discord-Nachricht.
    images = prepare_images()

    current_hash = images_hash(images)

    # Eigenständiger Testbeitrag.
    # Alte State-Einträge bleiben unangetastet.
    record = state.setdefault(
        "overview_v4",
        {},
    )

    message_id = str(
        record.get("message_id") or ""
    )

    if message_id:
        response = discord_request(
            "GET",
            (
                f"{API}/channels/{channel_id}"
                f"/messages/{message_id}"
            ),
            session=bot,
        )

        if response.status_code == 404:
            raise RuntimeError(
                "Gespeicherte Testnachricht fehlt. "
                "Bitte den Eintrag overview_v4 "
                "in events_message.json prüfen. "
                "Kein automatischer Doppelpost."
            )

        message = checked(
            response,
            "Testnachricht prüfen",
        )

        if (
            str(message.get("webhook_id") or "")
            != webhook_id
        ):
            raise RuntimeError(
                "Die Testnachricht gehört nicht "
                "zum erwarteten Webhook."
            )

        if record.get("hash") == current_hash:
            print(
                "Keine Änderungen: "
                "Discord-Nachricht bleibt unverändert."
            )
            return

    payload = {
        "content": "",
        "embeds": [],
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
        ),
    }

    for index, (filename, data) in enumerate(images):
        multipart[f"files[{index}]"] = (
            filename,
            data,
            "image/png",
        )

    if message_id:
        print(
            "Aktualisiere bestehenden Testbeitrag."
        )

        response = discord_request(
            "PATCH",
            (
                f"{webhook}/messages/"
                f"{message_id}"
            ),
            files=multipart,
            timeout=120,
        )

    else:
        print(
            "Erstelle einen gemeinsamen "
            "Discord-Testbeitrag."
        )

        response = discord_request(
            "POST",
            webhook,
            params={"wait": "true"},
            files=multipart,
            timeout=120,
        )

    message = checked(
        response,
        "Eventübersicht veröffentlichen",
    )

    record["message_id"] = str(
        message["id"]
    )

    record["hash"] = current_hash

    save_state(state)

    print(
        "Eventübersicht erfolgreich:",
        message["id"],
    )

    print(
        "Halloween-Banner: 1200x180"
    )

    print(
        "Kategorie-Banner: 1200x65"
    )

    print(
        "Eventblöcke: zusammengefasst"
    )

    print(
        "Bestehende Beiträge: unverändert"
    )

    print(
        "Helper: unverändert"
    )


if __name__ == "__main__":
    main()
