
"""Nyerk24 Events – Kategorie-Banner und kompakte Eventkarten.

Halloween bleibt unverändert.
Kategorie-Banner bleiben erhalten.
Eventkarten: exakt 1200 × 65 Pixel.
Unveränderte Nachrichten werden nicht bearbeitet.
Vorhandene Nachrichten-IDs werden wiederverwendet.
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
from PIL import Image, ImageDraw, ImageFont, ImageOps

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
        raise RuntimeError(
            f"Modul nicht gefunden: {path}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def face(size, bold=True):
    candidates = (
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
        if bold
        else [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]
    )

    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)

    raise RuntimeError("DejaVuSans fehlt")


def png(image):
    output = io.BytesIO()
    image.convert("RGB").save(
        output,
        format="PNG",
        optimize=True,
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
            f"Vorlage fehlt: {path}"
        )

    with Image.open(path) as source:
        original = source.convert("RGB")

    # Feste Bannergröße, ohne das Motiv zu verzerren.
    return ImageOps.fit(
        original,
        (1200, 65),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def event_card(template, event):
    image = template.copy()
    draw = ImageDraw.Draw(image)

    name = str(event["name"])
    date_label = str(
        event.get("date_label") or ""
    )

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

    # Links: Name und Zeitraum
    # Rechts: Status
    # Die Mitte bleibt ruhig und übersichtlich.

    title_font = face(23)

    while (
        draw.textbbox(
            (0, 0), name, font=title_font
        )[2] > 870
        and title_font.size > 15
    ):
        title_font = face(title_font.size - 1)

    draw.text(
        (28, 22),
        name,
        font=title_font,
        fill="#FFFFFF",
        anchor="lm",
        stroke_width=1,
        stroke_fill="#10151e",
    )

    draw.text(
        (28, 49),
        date_label,
        font=face(15, bold=False),
        fill="#DCE5F0",
        anchor="lm",
        stroke_width=1,
        stroke_fill="#10151e",
    )

    draw.text(
        (1172, 32),
        status,
        font=face(20),
        fill="#FFFFFF",
        anchor="rm",
        stroke_width=1,
        stroke_fill="#10151e",
    )

    if image.size != (1200, 65):
        raise RuntimeError(
            "Eventkarte hat eine falsche Größe"
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
    if not STATE.exists():
        raise RuntimeError(
            "events_message.json fehlt"
        )

    state = json.loads(
        STATE.read_text(encoding="utf-8")
    )

    if not isinstance(state, dict):
        raise ValueError(
            "events_message.json muss ein Objekt sein"
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
        requests.get(
            webhook,
            timeout=TIMEOUT,
        ),
        "Webhook",
    )

    channel = str(info["channel_id"])
    webhook_id = str(info["id"])

    halloween_id = str(
        state.get(
            "halloween_2026", {}
        ).get("webhook_message_id") or ""
    )

    if not halloween_id:
        raise RuntimeError(
            "Halloween-ID fehlt. "
            "Abbruch ohne Änderungen."
        )

    existing_halloween = check(
        bot.get(
            f"{API}/channels/{channel}/messages/{halloween_id}",
            timeout=TIMEOUT,
        ),
        "Halloween prüfen",
    )

    if (
        str(
            existing_halloween.get("webhook_id") or ""
        ) != webhook_id
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
                f"Gespeicherter Beitrag {message_id} fehlt. "
                "Kein automatischer Doppelpost."
            )

        message = check(
            response,
            "Nachricht prüfen",
        )

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
                    f"Helper {message_id} "
                    "ist eine Webhook-Nachricht"
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
            "allowed_mentions": {
                "parse": []
            },
            "attachments": [
                {
                    "id": 0,
                    "filename": filename,
                }
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
                params={
                    "wait": "true"
                },
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

    # Halloween bleibt vollständig unverändert.

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

    # Ein einziger Helper am Ende der Übersicht.
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
            "Event wählen → Details erscheinen sofort"
        ),
        "components": components,
        "allowed_mentions": {
            "parse": []
        },
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

    message = check(
        response,
        "Helper",
    )

    record.update(
        message_id=str(message["id"]),
        hash=digest,
    )

    save(state)

    print("Helper OK")


if __name__ == "__main__":
    main()
