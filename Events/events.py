
"""Nyerk24 Events: Banner aktualisieren und Anwesenheitsbuttons verwalten.

EVENTS_WEBHOOK veröffentlicht ausschließlich Bilder.
DISCORD_BOT veröffentlicht die Anwesenheitsbuttons.
Halloween-Helper und Kalender bleiben unverändert.
"""

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

CATEGORIES = (
    ("twitch_drops", "Twitch Drops", "Twitch/twitch_drops.png"),
    ("ingame_events", "Ingame-Events", "In-Game/ingame_events.png"),
    ("community_events", "Community-Events", "Community/community_events.png"),
    ("anwesenheitslisten", "Anwesenheitslisten", "Anwesenheit/anwesenheitslisten.png"),
)


def checked(response, context):
    if not response.ok:
        raise RuntimeError(
            f"{context}: HTTP {response.status_code}: {response.text[:700]}"
        )
    return response.json() if response.content else {}


def read_state():
    if not STATE.exists():
        raise RuntimeError(
            "events_message.json fehlt. Kein automatischer Erstpost."
        )
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError("events_message.json muss ein JSON-Objekt sein")
    return state


def save_state(state):
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(STATE)


def load_module(relative_path, module_name):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Modul fehlt: {path}")
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
    raise RuntimeError("DejaVuSans-Bold oder LiberationSans-Bold fehlt")


def category_banner(relative_path, title):
    path = ROOT / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"Banner fehlt: {path}")

    with Image.open(path) as source:
        if source.size != (1200, 65):
            raise ValueError(
                f"{relative_path}: erwartet 1200×65, "
                f"gefunden {source.size}"
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
        raise ValueError(f"Überschrift zu lang: {title}")

    bbox = draw.textbbox(
        (0, 0), title, font=face, stroke_width=1
    )

    x = 600 - (bbox[0] + bbox[2]) / 2
    y = 32.5 - (bbox[1] + bbox[3]) / 2

    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).text(
        (round(x), round(y)),
        title,
        font=face,
        fill=255,
    )

    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    alpha = mask.filter(
        ImageFilter.GaussianBlur(3)
    ).point(lambda a: min(255, int(a * 0.75)))

    shadow.putalpha(alpha)
    base = Image.alpha_composite(base, shadow)

    ImageDraw.Draw(base).text(
        (round(x), round(y)),
        title,
        font=face,
        fill=(248, 247, 250, 255),
        stroke_width=1,
        stroke_fill=(12, 10, 18, 255),
    )

    out = io.BytesIO()
    base.convert("RGB").save(
        out, format="PNG", optimize=True
    )
    return out.getvalue()


def get_message(bot, channel, message_id):
    response = bot.get(
        f"{API}/channels/{channel}/messages/{message_id}",
        timeout=TIMEOUT,
    )
    if response.status_code == 404:
        return None
    return checked(response, "Nachricht prüfen")


def verify_webhook_message(bot, channel, webhook_id, message_id):
    msg = get_message(bot, channel, message_id)

    if msg is None:
        raise RuntimeError(
            f"Gespeicherte Nachricht {message_id} fehlt. "
            "Kein Doppelpost."
        )

    if str(msg.get("webhook_id") or "") != webhook_id:
        raise RuntimeError(
            f"Nachricht {message_id} gehört nicht "
            "zum Events-Webhook"
        )

    return msg


def find_existing_filename(
    bot, channel, webhook_id, filename
):
    before = None

    for _ in range(30):
        params = {"limit": 100}

        if before:
            params["before"] = before

        messages = checked(
            bot.get(
                f"{API}/channels/{channel}/messages",
                params=params,
                timeout=TIMEOUT,
            ),
            "Vorhandene Events prüfen",
        )

        for msg in messages:
            if str(msg.get("webhook_id") or "") != webhook_id:
                continue

            if any(
                a.get("filename") == filename
                for a in msg.get("attachments", [])
            ):
                raise RuntimeError(
                    f"{filename} ist bereits in Discord, "
                    "aber ohne gespeicherte ID. "
                    "Kein Doppelpost; bitte ID nachtragen."
                )

        if len(messages) < 100:
            return

        before = messages[-1]["id"]

    raise RuntimeError(
        f"Kanalhistorie zu lang, Erstpost von "
        f"{filename} nicht sicher"
    )


def upload(webhook, message_id, filename, data):
    payload = {
        "content": "",
        "embeds": [],
        "components": [],
        "attachments": [
            {"id": 0, "filename": filename}
        ],
        "allowed_mentions": {"parse": []},
    }

    files = {
        "payload_json": (
            None,
            json.dumps(payload, ensure_ascii=False),
        ),
        "files[0]": (
            filename,
            data,
            "image/png",
        ),
    }

    if message_id:
        result = checked(
            requests.patch(
                f"{webhook}/messages/{message_id}",
                files=files,
                timeout=70,
            ),
            "Banner aktualisieren",
        )
    else:
        result = checked(
            requests.post(
                webhook,
                params={"wait": "true"},
                files=files,
                timeout=70,
            ),
            "Banner veröffentlichen",
        )

    if not result.get("id"):
        raise RuntimeError(
            "Discord lieferte keine Nachrichten-ID"
        )

    if message_id and str(result["id"]) != str(message_id):
        raise RuntimeError(
            "Discord lieferte unerwartete Nachrichten-ID"
        )

    return str(result["id"])


def validate_attendance_buttons(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError(
            "Anwesenheit.buttons() muss eine "
            "nichtleere Liste zurückgeben"
        )

    ids = []

    for row in rows:
        components = row.get("components", [])

        if (
            row.get("type") != 1
            or not 1 <= len(components) <= 5
        ):
            raise ValueError(
                "Ungültige Discord-Action-Row "
                "für Anwesenheit"
            )

        for button in components:
            label = button.get("label", "")
            custom_id = button.get("custom_id", "")

            if (
                button.get("type") != 2
                or button.get("style") not in (1, 2, 3, 4)
            ):
                raise ValueError(
                    f"Ungültiger Button: {label}"
                )

            if (
                not label
                or len(label) > 80
                or not custom_id
                or len(custom_id) > 100
            ):
                raise ValueError(
                    f"Button-Länge ungültig: {label}"
                )

            ids.append(custom_id)

    if (
        len(rows) > 5
        or len(ids) != 4
        or len(set(ids)) != 4
    ):
        raise ValueError(
            "Erwartet genau vier eindeutige "
            "Anwesenheitsbuttons"
        )


def update_attendance_helper(
    bot, channel, state, rows, bot_id
):
    record = state["anwesenheitslisten"]
    helper_id = str(
        record.get("helper_message_id") or ""
    )

    payload = {
        "content": (
            "📅 **Anwesenheitslisten – "
            "Eventdetails anzeigen**"
        ),
        "components": rows,
        "allowed_mentions": {"parse": []},
    }

    if helper_id:
        msg = get_message(bot, channel, helper_id)

        if msg is None:
            raise RuntimeError(
                f"Anwesenheits-Helper {helper_id} fehlt. "
                "Kein Doppelpost."
            )

        if str(
            msg.get("author", {}).get("id") or ""
        ) != bot_id:
            raise RuntimeError(
                f"Anwesenheits-Helper {helper_id} "
                "gehört nicht zum Bot."
            )

        result = checked(
            bot.patch(
                f"{API}/channels/{channel}/messages/{helper_id}",
                json=payload,
                timeout=TIMEOUT,
            ),
            "Anwesenheitsbuttons aktualisieren",
        )

        print(
            "Anwesenheitsbuttons aktualisiert: "
            f'{result["id"]}'
        )

    else:
        result = checked(
            bot.post(
                f"{API}/channels/{channel}/messages",
                json=payload,
                timeout=TIMEOUT,
            ),
            "Anwesenheitsbuttons veröffentlichen",
        )

        record["helper_message_id"] = str(result["id"])
        save_state(state)

        print(
            "Anwesenheitsbuttons veröffentlicht: "
            f'{result["id"]}'
        )


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
        "Events-Webhook prüfen",
    )

    channel = str(identity["channel_id"])
    webhook_id = str(identity["id"])

    bot = requests.Session()
    bot.headers.update({
        "Authorization": (
            "Bot " + os.environ["DISCORD_BOT"].strip()
        )
    })

    bot_identity = checked(
        bot.get(
            f"{API}/users/@me",
            timeout=TIMEOUT,
        ),
        "Helper-Bot prüfen",
    )

    bot_id = str(bot_identity["id"])

    halloween = load_module(
        "Halloween/halloween.py",
        "nyerk24_halloween",
    )

    attendance = load_module(
        "Anwesenheit/anwesenheit.py",
        "nyerk24_anwesenheit",
    )

    rows = attendance.buttons()
    validate_attendance_buttons(rows)

    # Halloween bleibt unverändert.
    halloween_record = state.get("halloween_2026")

    if not isinstance(halloween_record, dict):
        raise RuntimeError(
            "Halloween-State fehlt. "
            "Keine neue Halloween-Nachricht erstellen."
        )

    halloween_id = str(
        halloween_record.get("webhook_message_id") or ""
    )

    if not halloween_id:
        raise RuntimeError(
            "webhook_message_id für Halloween fehlt. "
            "Kein Doppelpost."
        )

    verify_webhook_message(
        bot, channel, webhook_id, halloween_id
    )

    halloween_data = halloween.banner(
        halloween.status()
    )

    with Image.open(
        io.BytesIO(halloween_data)
    ) as im:
        if im.size != (1200, 180):
            raise ValueError(
                "Halloween muss 1200×180 bleiben, "
                f"ist {im.size}"
            )

    upload(
        webhook,
        halloween_id,
        "halloween_2026_banner.png",
        halloween_data,
    )

    print(
        f"Halloween aktualisiert: {halloween_id}"
    )

    # Bestehende Kategorie-Banner aktualisieren.
    for key, title, relative_path in CATEGORIES:
        filename = f"{key}_banner.png"
        data = category_banner(
            relative_path, title
        )

        record = state.get(key)

        if record is not None and not isinstance(
            record, dict
        ):
            raise ValueError(
                f"State für {key} muss ein Objekt sein"
            )

        record = record or {}

        message_id = str(
            record.get("webhook_message_id") or ""
        )

        if message_id:
            verify_webhook_message(
                bot,
                channel,
                webhook_id,
                message_id,
            )
        else:
            find_existing_filename(
                bot,
                channel,
                webhook_id,
                filename,
            )

        new_id = upload(
            webhook,
            message_id,
            filename,
            data,
        )

        record["webhook_message_id"] = new_id
        state[key] = record
        save_state(state)

        print(f"{title}: {new_id}")

    # Einmalige Helper-Nachricht mit vier Buttons.
    update_attendance_helper(
        bot,
        channel,
        state,
        rows,
        bot_id,
    )

    print(
        "Fertig. Halloween-Helper und "
        "Kalender unverändert."
    )


if __name__ == "__main__":
    main()
