
"""Nyerk24 – Kategorie-Banner, Eventkarten und EIN Helper-Menü.

Halloween-Nachricht bleibt unverändert.
Alte Posts werden nicht gelöscht.
Neue Posts werden anhand der State-IDs wiederverwendet.
"""

import hashlib
import importlib.util
import io
import json
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
STATE = ROOT / "events_message.json"
API = "https://discord.com/api/v10"
TIMEOUT = 45

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


def check(response, name):
    if not response.ok:
        raise RuntimeError(
            f"{name}: HTTP {response.status_code}: "
            f"{response.text[:1000]}"
        )
    return response.json() if response.content else {}


def load(path, name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / path
    )
    if not spec or not spec.loader:
        raise RuntimeError(f"Modul nicht gefunden: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def face(size):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    raise RuntimeError("DejaVuSans fehlt")


def png(image):
    output = io.BytesIO()
    image.convert("RGB").save(
        output, format="PNG", optimize=True
    )
    return output.getvalue()


def category_banner(path, title):
    with Image.open(ROOT / path) as source:
        if source.size != (1200, 65):
            raise ValueError(
                f"{path}: erwartet 1200×65, "
                f"erhalten {source.size}"
            )
        image = source.convert("RGB")

    draw = ImageDraw.Draw(image)
    draw.text(
        (600, 32),
        title,
        font=face(37),
        anchor="mm",
        fill="white",
        stroke_width=2,
        stroke_fill="#171c29",
    )
    return png(image)


def event_template():
    path = REPO / "Tracker" / "event_overview.png"

    if not path.exists():
        raise FileNotFoundError(
            f"Vorlage fehlt: {path} – bitte Pfad prüfen"
        )

    with Image.open(path) as source:
        image = source.convert("RGB")

    height = round(image.height * 1200 / image.width)

    return image.resize(
        (1200, height),
        Image.Resampling.LANCZOS,
    )


def event_card(template, event):
    image = template.copy()
    name = event["name"]
    date_label = event.get("date_label") or ""

    start = date.fromisoformat(event["start"])
    end = date.fromisoformat(event["end"])
    today = datetime.now(
        ZoneInfo("Europe/Berlin")
    ).date()

    if today < start:
        status = "Kommend"
    elif today <= end:
        status = "Gestartet"
    else:
        status = "Beendet"

    height = image.height

    if height < 115:
        expanded = Image.new(
            "RGB", (1200, 115), "#202936"
        )
        expanded.paste(image, (0, 0))
        image = expanded
        height = 115

    draw = ImageDraw.Draw(image)
    title_size = 36 if len(name) < 28 else 29

    draw.text(
        (45, height * 0.35),
        name,
        font=face(title_size),
        fill="white",
        anchor="lm",
        stroke_width=2,
        stroke_fill="#101621",
    )

    draw.text(
        (45, height * 0.77),
        date_label,
        font=face(23),
        fill="#e3e9f0",
        anchor="lm",
        stroke_width=1,
        stroke_fill="#101621",
    )

    draw.text(
        (1155, height * 0.5),
        status,
        font=face(25),
        fill="#eaf3ff",
        anchor="rm",
        stroke_width=2,
        stroke_fill="#101621",
    )

    return png(image)


def hash_payload(data):
    return hashlib.sha256(data).hexdigest()


def save(state):
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    temporary.replace(STATE)


def main():
    state = json.loads(
        STATE.read_text(encoding="utf-8")
    )

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

    info = check(
        requests.get(webhook, timeout=TIMEOUT),
        "Webhook",
    )

    channel = str(info["channel_id"])
    webhook_id = str(info["id"])

    halloween_id = str(
        state.get("halloween_2026", {}).get(
            "webhook_message_id"
        ) or ""
    )

    if not halloween_id:
        raise RuntimeError(
            "Halloween-ID fehlt. Abbruch ohne Änderungen."
        )

    existing_halloween = check(
        bot.get(
            f"{API}/channels/{channel}/messages/{halloween_id}",
            timeout=TIMEOUT,
        ),
        "Halloween prüfen",
    )

    if (
        str(existing_halloween.get("webhook_id") or "")
        != webhook_id
    ):
        raise RuntimeError(
            "Halloween gehört nicht zu diesem Webhook"
        )

    def verify(message_id, expected):
        response = bot.get(
            f"{API}/channels/{channel}/messages/{message_id}",
            timeout=TIMEOUT,
        )

        if response.status_code == 404:
            raise RuntimeError(
                f"Gespeicherter Post {message_id} fehlt; "
                "kein automatischer Doppelpost"
            )

        message = check(response, "Nachricht prüfen")

        if expected == "webhook":
            if (
                str(message.get("webhook_id") or "")
                != webhook_id
            ):
                raise RuntimeError(
                    f"Falscher Webhook für {message_id}"
                )

        if expected == "bot":
            if message.get("webhook_id"):
                raise RuntimeError(
                    f"Helper {message_id} ist eine Webhook-Nachricht"
                )

        return message

    def webhook_post(key, filename, data):
        record = (
            state.setdefault("overview_v2", {})
            .setdefault(key, {})
        )

        message_id = str(
            record.get("message_id") or ""
        )
        digest = hash_payload(data)

        if message_id:
            verify(message_id, "webhook")

            if record.get("hash") == digest:
                print("Unverändert:", key)
                return

        payload = {
            "content": "",
            "embeds": [],
            "allowed_mentions": {"parse": []},
            "attachments": [
                {"id": 0, "filename": filename}
            ],
        }

        files = {
            "payload_json": (
                None,
                json.dumps(payload),
            ),
            "files[0]": (
                filename,
                data,
                "image/png",
            ),
        }

        if message_id:
            response = requests.patch(
                f"{webhook}/messages/{message_id}",
                files=files,
                timeout=90,
            )
        else:
            response = requests.post(
                webhook,
                params={"wait": "true"},
                files=files,
                timeout=90,
            )

        message = check(
            response,
            f"Banner {key}",
        )

        record.update(
            message_id=str(message["id"]),
            hash=digest,
        )
        save(state)

        print("OK:", key)

    # Halloween wird NICHT aktualisiert
    # und NICHT neu veröffentlicht.

    attendance = load(
        "Anwesenheit/anwesenheit.py",
        "attendance",
    )

    template = event_template()

    event_map = {
        "anwesenheitslisten": attendance.EVENTS,
        "ingame_events": (),
        "community_events": (),
        "twitch_drops": (),
    }

    # Zuerst alle Kategorie-Banner
    # mit den jeweiligen Eventkarten.
    for key, title, path in CATEGORIES:
        webhook_post(
            "category:" + key,
            key + ".png",
            category_banner(path, title),
        )

        for event in event_map[key]:
            webhook_post(
                "event:" + event["id"],
                event["id"] + ".png",
                event_card(template, event),
            )

    # Ganz unten EIN Helper-Beitrag.
    # Öffentlich wird nur die Kategorie gewählt.
    # Eventauswahl und Details folgen privat.

    options = [
        {
            "label": "Halloween",
            "value": "halloween",
        }
    ]

    for key, title, _ in CATEGORIES:
        options.append({
            "label": title,
            "value": key,
        })

    components = [
        {
            "type": 1,
            "components": [
                {
                    "type": 3,
                    "custom_id": "event:menu:category",
                    "placeholder": "Überschrift wählen",
                    "min_values": 1,
                    "max_values": 1,
                    "options": options,
                }
            ],
        }
    ]

    payload = {
        "content": (
            "🔎 **Eventdetails**\n"
            "Überschrift wählen → "
            "Event wählen → Details sehen"
        ),
        "components": components,
        "allowed_mentions": {"parse": []},
    }

    record = (
        state.setdefault("overview_v2", {})
        .setdefault("helper", {})
    )

    message_id = str(
        record.get("message_id") or ""
    )

    digest = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
        ).encode()
    ).hexdigest()

    if message_id:
        verify(message_id, "bot")

        if record.get("hash") == digest:
            print("Helper unverändert")
            return

        response = bot.patch(
            f"{API}/channels/{channel}/messages/{message_id}",
            json=payload,
            timeout=TIMEOUT,
        )
    else:
        response = bot.post(
            f"{API}/channels/{channel}/messages",
            json=payload,
            timeout=TIMEOUT,
        )

    message = check(response, "Helper")

    record.update(
        message_id=str(message["id"]),
        hash=digest,
    )

    save(state)
    print("Helper OK")


if __name__ == "__main__":
    main()
