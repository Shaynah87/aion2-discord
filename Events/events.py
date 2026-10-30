
"""Nyerk24 Events – ein gemeinsamer Events-Beitrag mit fünf Bannern.

Beim ersten Lauf wird ein neuer Gesamtbeitrag als Test veröffentlicht.
Alte Nachrichten werden NICHT gelöscht.
Unveränderte Beiträge werden NICHT bearbeitet.
"""

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "events_message.json"
API = "https://discord.com/api/v10"
TIMEOUT = 45
KEY = "events_gesamt"

CATEGORIES = (
    ("anwesenheitslisten", "Anwesenheitslisten",
     "Anwesenheit/anwesenheitslisten.png"),
    ("ingame_events", "Ingame-Events",
     "In-Game/ingame_events.png"),
    ("community_events", "Community-Events",
     "Community/community_events.png"),
    ("twitch_drops", "Twitch Drops",
     "Twitch/twitch_drops.png"),
)


def checked(response, context):
    if not response.ok:
        raise RuntimeError(
            f"{context}: HTTP {response.status_code}: "
            f"{response.text[:900]}"
        )
    return response.json() if response.content else {}


def read_state():
    if not STATE.exists():
        raise RuntimeError(
            "events_message.json fehlt. Kein Erstpost."
        )
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError(
            "events_message.json muss ein Objekt sein"
        )
    return state


def save_state(state):
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(STATE)


def load_module(path, name):
    file = ROOT / path
    spec = importlib.util.spec_from_file_location(name, file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Modul fehlt: {file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def font(size):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    raise RuntimeError("Schriftart fehlt")


def category_banner(relative_path, title):
    path = ROOT / relative_path

    with Image.open(path) as source:
        if source.size != (1200, 65):
            raise ValueError(
                f"{relative_path}: erwartet 1200×65, "
                f"ist {source.size}"
            )
        base = source.convert("RGBA")

    draw = ImageDraw.Draw(base)

    for size in range(42, 19, -1):
        face = font(size)
        bbox = draw.textbbox(
            (0, 0), title, font=face, stroke_width=1
        )
        if (
            bbox[2] - bbox[0] <= 660
            and bbox[3] - bbox[1] <= 51
        ):
            break
    else:
        raise ValueError(f"Titel zu lang: {title}")

    bbox = draw.textbbox(
        (0, 0), title, font=face, stroke_width=1
    )

    x = round(600 - (bbox[0] + bbox[2]) / 2)
    y = round(32.5 - (bbox[1] + bbox[3]) / 2)

    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).text(
        (x, y), title, font=face, fill=255
    )

    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    alpha = mask.filter(
        ImageFilter.GaussianBlur(3)
    ).point(
        lambda a: min(255, int(a * 0.75))
    )
    shadow.putalpha(alpha)

    base = Image.alpha_composite(base, shadow)

    ImageDraw.Draw(base).text(
        (x, y),
        title,
        font=face,
        fill=(248, 247, 250, 255),
        stroke_width=1,
        stroke_fill=(12, 10, 18, 255),
    )

    output = io.BytesIO()
    base.convert("RGB").save(
        output, format="PNG", optimize=True
    )
    return output.getvalue()


def buttons(attendance):
    rows = attendance.buttons()

    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError(
            "Anwesenheit muss genau eine Action-Row liefern"
        )

    attendance_buttons = rows[0].get("components", [])

    if len(attendance_buttons) != 4:
        raise ValueError(
            "Genau vier Anwesenheitsbuttons erwartet"
        )

    halloween = {
        "type": 2,
        "style": 1,
        "label": "🎃 Halloween · Eventdetails",
        "custom_id": "event:details:halloween_2026",
    }

    all_buttons = [halloween, *attendance_buttons]
    ids = [b.get("custom_id") for b in all_buttons]

    if len(set(ids)) != 5 or any(not x for x in ids):
        raise ValueError(
            "Button-IDs fehlen oder sind doppelt"
        )

    if any(
        len(b.get("label", "")) > 80
        or len(b["custom_id"]) > 100
        for b in all_buttons
    ):
        raise ValueError(
            "Discord-Buttonlimit überschritten"
        )

    return [
        {
            "type": 1,
            "components": all_buttons,
        }
    ]


def fetch_message(bot, channel, message_id):
    response = bot.get(
        f"{API}/channels/{channel}/messages/{message_id}",
        timeout=TIMEOUT,
    )

    if response.status_code == 404:
        raise RuntimeError(
            f"Nachricht {message_id} fehlt. "
            "Keine Neuanlage ohne Prüfung."
        )

    return checked(
        response, "Bestehenden Beitrag prüfen"
    )


def fingerprint(images, components):
    digest = hashlib.sha256()

    for filename, data in images:
        digest.update(filename.encode())
        digest.update(hashlib.sha256(data).digest())

    digest.update(
        json.dumps(
            components,
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
    )

    return digest.hexdigest()


def send(webhook, message_id, images, components):
    payload = {
        "content": "",
        "embeds": [],
        "components": components,
        "allowed_mentions": {"parse": []},
        "attachments": [
            {"id": i, "filename": name}
            for i, (name, _) in enumerate(images)
        ],
    }

    files = {
        "payload_json": (
            None,
            json.dumps(payload, ensure_ascii=False),
        )
    }

    for i, (filename, data) in enumerate(images):
        files[f"files[{i}]"] = (
            filename,
            data,
            "image/png",
        )

    if message_id:
        response = requests.patch(
            f"{webhook}/messages/{message_id}",
            params={"with_components": "true"},
            files=files,
            timeout=90,
        )
    else:
        response = requests.post(
            webhook,
            params={
                "wait": "true",
                "with_components": "true",
            },
            files=files,
            timeout=90,
        )

    result = checked(
        response,
        "Gemeinsamen Eventbeitrag veröffentlichen",
    )

    if not result.get("id"):
        raise RuntimeError(
            "Discord hat keine Nachrichten-ID zurückgegeben"
        )

    if (
        message_id
        and str(result["id"]) != str(message_id)
    ):
        raise RuntimeError(
            "Unerwartete Nachrichten-ID"
        )

    if len(result.get("attachments", [])) != 5:
        raise RuntimeError(
            "Discord hat nicht alle fünf Banner bestätigt"
        )

    if not result.get("components"):
        raise RuntimeError(
            "Discord hat die Buttons nicht bestätigt"
        )

    return str(result["id"])


def main():
    state = read_state()

    webhook = (
        os.environ["EVENTS_WEBHOOK"]
        .strip()
        .split("?", 1)[0]
        .rstrip("/")
    )

    identity = checked(
        requests.get(webhook, timeout=TIMEOUT),
        "Webhook prüfen",
    )

    channel = str(identity["channel_id"])
    webhook_id = str(identity["id"])

    bot = requests.Session()
    bot.headers.update({
        "Authorization":
            "Bot " + os.environ["DISCORD_BOT"].strip()
    })

    # Prüfen, ob der bisherige Halloween-Beitrag
    # tatsächlich zum Events-Webhook gehört.
    halloween_record = state.get(
        "halloween_2026", {}
    )

    halloween_id = str(
        halloween_record.get("webhook_message_id") or ""
    )

    if not halloween_id:
        raise RuntimeError(
            "Halloween-Webhook-ID fehlt"
        )

    old = fetch_message(
        bot, channel, halloween_id
    )

    if str(old.get("webhook_id") or "") != webhook_id:
        raise RuntimeError(
            "Halloween gehört nicht zum angegebenen Webhook"
        )

    halloween = load_module(
        "Halloween/halloween.py",
        "nyerk24_halloween",
    )

    attendance = load_module(
        "Anwesenheit/anwesenheit.py",
        "nyerk24_anwesenheit",
    )

    halloween_data = halloween.banner(
        halloween.status()
    )

    with Image.open(
        io.BytesIO(halloween_data)
    ) as image:
        if image.size != (1200, 180):
            raise ValueError(
                "Halloween muss 1200×180 sein: "
                f"{image.size}"
            )

    # Reihenfolge bleibt fest:
    # Halloween, Anwesenheit, Ingame,
    # Community, Twitch.
    images = [
        (
            "halloween_2026_banner.png",
            halloween_data,
        )
    ]

    for key, title, path in CATEGORIES:
        images.append(
            (
                f"{key}_banner.png",
                category_banner(path, title),
            )
        )

    components = buttons(attendance)
    current_hash = fingerprint(
        images, components
    )

    record = state.get(KEY, {})

    if not isinstance(record, dict):
        raise ValueError(
            f"{KEY} muss ein Objekt sein"
        )

    message_id = str(
        record.get("webhook_message_id") or ""
    )

    if message_id:
        existing = fetch_message(
            bot, channel, message_id
        )

        if (
            str(existing.get("webhook_id") or "")
            != webhook_id
        ):
            raise RuntimeError(
                "Gesamtbeitrag gehört nicht "
                "zum Events-Webhook"
            )

        if record.get("content_hash") == current_hash:
            print(
                f"Unverändert – kein Edit: {message_id}"
            )
            return

        print(
            f"Gesamtbeitrag aktualisieren: {message_id}"
        )

    else:
        print(
            "Neuen Gesamtbeitrag als Test "
            "veröffentlichen. Alte Posts bleiben erhalten."
        )

    new_id = send(
        webhook,
        message_id,
        images,
        components,
    )

    state[KEY] = {
        "webhook_message_id": new_id,
        "content_hash": current_hash,
    }

    save_state(state)

    print(f"Gesamtbeitrag: {new_id}")
    print(
        "Bestehende vier Nachrichten bleiben erhalten, "
        "bis die Ansicht geprüft ist."
    )


if __name__ == "__main__":
    main()
