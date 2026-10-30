
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
ROW_HEIGHT = 58

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


def request(method, url, session=None, **kwargs):
    client = session or requests
    kwargs.setdefault("timeout", 60)

    for attempt in range(12):
        try:
            response = client.request(method, url, **kwargs)
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
                    "Vor erneutem Lauf Discord prüfen."
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
            f"{response.text[:1000]}"
        )
    return response.json() if response.content else {}


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
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    temporary.replace(STATE_FILE)


def load_module(relative_path, name):
    path = ROOT / relative_path

    if not path.is_file():
        raise RuntimeError(f"Datei fehlt: {path}")

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
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

    return ImageFont.truetype(str(path), size)


def to_png(image):
    buffer = io.BytesIO()

    image.convert("RGB").save(
        buffer,
        format="PNG",
        optimize=True,
    )

    return buffer.getvalue()


def validate_png(data, expected_size, label):
    with Image.open(io.BytesIO(data)) as image:
        if image.size != expected_size:
            raise RuntimeError(
                f"{label}: erwartet {expected_size}, "
                f"erhalten {image.size}"
            )


def halloween_banner():
    halloween = load_module(
        "Halloween/halloween.py",
        "nyerk24_halloween",
    )

    data = halloween.banner(
        halloween.status()
    )

    validate_png(
        data,
        (1200, 180),
        "Halloween",
    )

    return data


def category_banner(relative_path, title):
    path = ROOT / relative_path

    if not path.is_file():
        raise RuntimeError(
            f"Kategorie-Banner fehlt: {path}"
        )

    with Image.open(path) as original:
        if original.size != (1200, 65):
            raise RuntimeError(
                f"{path}: erwartet 1200x65, "
                f"erhalten {original.size}"
            )

        image = original.convert("RGB")

    draw = ImageDraw.Draw(image)

    draw.text(
        (600, 32),
        title,
        font=font(37),
        anchor="mm",
        fill="white",
        stroke_width=2,
        stroke_fill="#171C29",
    )

    return to_png(image)


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
    events = list(events)

    if not events:
        return None

    background = event_background()

    block = Image.new(
        "RGB",
        (WIDTH, len(events) * ROW_HEIGHT),
        "#24272E",
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
            font=fit_font(draw, name, 530, 26),
            anchor="lm",
            fill="white",
            stroke_width=1,
            stroke_fill="#10151E",
        )

        draw.text(
            (790, ROW_HEIGHT // 2),
            period,
            font=fit_font(draw, period, 350, 22),
            anchor="mm",
            fill="#E5EAF2",
            stroke_width=1,
            stroke_fill="#10151E",
        )

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

    return to_png(block)


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

    # Jedes Bild erhält einen eigenen Embed.
    # Dadurch soll Discord keine Galerie erzeugen.
    images = [
        ("00_halloween.png", halloween_banner())
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
        banner_name = f"{index:02d}_{key}.png"

        images.append((
            banner_name,
            category_banner(path, title),
        ))

        embeds.append({
            "color": color,
            "image": {
                "url": f"attachment://{banner_name}"
            },
        })

        block = event_block(event_map[key])

        if block is not None:
            block_name = f"{index:02d}_{key}_events.png"

            images.append((
                block_name,
                block,
            ))

            embeds.append({
                "color": color,
                "image": {
                    "url": f"attachment://{block_name}"
                },
            })

    if len(images) > 10:
        raise RuntimeError(
            "Discord erlaubt maximal zehn Anhänge."
        )

    if len(embeds) > 10:
        raise RuntimeError(
            "Discord erlaubt maximal zehn Embeds."
        )

    return images, embeds


def calculate_hash(images, embeds):
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

    info = checked(
        request("GET", webhook),
        "Webhook",
    )

    channel_id = str(info["channel_id"])
    webhook_id = str(info["id"])

    images, embeds = prepare_overview()
    digest = calculate_hash(images, embeds)

    # Neuer State-Bereich für Embed-Version.
    # Alle bisherigen State-Bereiche bleiben erhalten.
    record = state.setdefault(
        "overview_v5",
        {},
    )

    message_id = str(
        record.get("message_id") or ""
    )

    if message_id:
        response = request(
            "GET",
            (
                f"{API}/channels/{channel_id}"
                f"/messages/{message_id}"
            ),
            session=bot,
        )

        if response.status_code == 404:
            raise RuntimeError(
                "Gespeicherter Embed-Beitrag fehlt. "
                "Kein automatischer Doppelpost."
            )

        message = checked(
            response,
            "Embed-Beitrag prüfen",
        )

        if (
            str(message.get("webhook_id") or "")
            != webhook_id
        ):
            raise RuntimeError(
                "Beitrag gehört nicht zu diesem Webhook."
            )

        if record.get("hash") == digest:
            print("Übersicht unverändert.")
            return

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
            json.dumps(
                payload,
                ensure_ascii=False,
            ),
        ),
    }

    for index, (filename, data) in enumerate(images):
        multipart[f"files[{index}]"] = (
            filename,
            data,
            "image/png",
        )

    if message_id:
        print("Aktualisiere Embed-Testbeitrag.")

        response = request(
            "PATCH",
            f"{webhook}/messages/{message_id}",
            files=multipart,
            timeout=120,
        )

    else:
        print("Erstelle Embed-Testbeitrag.")

        response = request(
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

    record["message_id"] = str(message["id"])
    record["hash"] = digest

    save_state(state)

    print("Erfolgreich:", message["id"])
    print("Embeds:", len(embeds))
    print("Anhänge:", len(images))
    print("Halloween: 1200x180")
    print("Kategorie-Banner: 1200x65")
    print("Alte Beiträge nicht gelöscht")
    print("Helper unverändert")


if __name__ == "__main__":
    main()
