
"""
Nyerk24 · Events
Gemeinsame Eventübersicht mit Discord-Embeds.

- Halloween bleibt unverändert (1200 x 180)
- Alle Kategorie-Banner erhalten denselben Verlauf
- Kategorien ohne Events erhalten einen kurzen Verlauf
- Kategorien mit Events erhalten einen Anthrazit-Block
- Bestehende Übersicht wird aktualisiert
- Bestehender Helper wird nach Möglichkeit wiederverwendet
- Keine automatische Löschung alter Nachrichten
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
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "events_message.json"

API = "https://discord.com/api/v10"

WIDTH = 1200
BANNER_HEIGHT = 65
HEADER_HEIGHT = 110
EMPTY_HEADER_HEIGHT = 94
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
            response = client.request(
                method,
                url,
                **kwargs,
            )

        except (
            requests.ConnectionError,
            requests.Timeout,
        ) as error:

            if method.upper() == "POST":
                raise RuntimeError(
                    "Verbindung beim POST unterbrochen. "
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
                raise RuntimeError(
                    "Discord Rate Limit"
                )

            time.sleep(max(0.5, delay + 0.3))
            continue

        if response.status_code in (
            500, 502, 503, 504
        ):
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

    raise RuntimeError(
        "Discord-Anfrage fehlgeschlagen"
    )


def checked(response, label):
    if not response.ok:
        raise RuntimeError(
            f"{label}: HTTP {response.status_code}: "
            f"{response.text[:1000]}"
        )

    return (
        response.json()
        if response.content
        else {}
    )


# ==================================================
# STATUS
# ==================================================

def load_state():
    if not STATE_FILE.is_file():
        raise RuntimeError(
            "events_message.json fehlt"
        )

    state = json.loads(
        STATE_FILE.read_text(encoding="utf-8")
    )

    if not isinstance(state, dict):
        raise RuntimeError(
            "Ungültige Statusdatei"
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


# ==================================================
# MODULE
# ==================================================

def load_module(relative_path, name):
    path = ROOT / relative_path

    if not path.is_file():
        raise RuntimeError(
            f"Datei fehlt: {path}"
        )

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


# ==================================================
# SCHRIFTEN
# ==================================================

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


def fit_font(draw, text, max_width, initial):
    for size in range(initial, 15, -1):
        candidate = font(size)

        bounds = draw.textbbox(
            (0, 0),
            text,
            font=candidate,
        )

        if bounds[2] - bounds[0] <= max_width:
            return candidate

    return font(16)


def png(image):
    output = io.BytesIO()

    image.convert("RGB").save(
        output,
        format="PNG",
        optimize=True,
    )

    return output.getvalue()


# ==================================================
# HALLOWEEN
# ==================================================

def halloween_banner():
    halloween = load_module(
        "Halloween/halloween.py",
        "nyerk24_halloween",
    )

    data = halloween.banner(
        halloween.status()
    )

    with Image.open(io.BytesIO(data)) as image:
        if image.size != (1200, 180):
            raise RuntimeError(
                "Halloween muss 1200x180 sein."
            )

    return data


# ==================================================
# KATEGORIE-BANNER
# ==================================================

def load_category_background(relative_path):
    path = ROOT / relative_path

    if not path.is_file():
        raise RuntimeError(
            f"Banner fehlt: {path}"
        )

    with Image.open(path) as source:
        if source.size != (
            WIDTH, BANNER_HEIGHT
        ):
            raise RuntimeError(
                f"Falsches Bannerformat: {path}"
            )

        return source.convert("RGB")


def event_status(event):
    today = datetime.now(
        ZoneInfo("Europe/Berlin")
    ).date()

    start = date.fromisoformat(
        event["start"]
    )

    end = date.fromisoformat(
        event["end"]
    )

    if today < start:
        return "Kommend"

    if today <= end:
        return "Gestartet"

    return "Beendet"


# ==================================================
# VERLAUF
# ==================================================

def create_category_image(
    relative_path,
    title,
    events,
):
    events = list(events)

    has_events = bool(events)

    header_height = (
        HEADER_HEIGHT
        if has_events
        else EMPTY_HEADER_HEIGHT
    )

    total_height = (
        header_height
        + len(events) * ROW_HEIGHT
    )

    original = load_category_background(
        relative_path
    )

    image = Image.new(
        "RGB",
        (WIDTH, total_height),
        (35, 39, 47),
    )

    # Originalbanner unverändert einsetzen.
    image.paste(
        original,
        (0, 0),
    )

    draw = ImageDraw.Draw(image)

    # Weicher Übergang aus den tatsächlichen
    # Farben der unteren Originalbanner-Kante.
    #
    # Jede Kategorie erhält dadurch ihren
    # eigenen farblich passenden Verlauf.
    #
    # Auch ohne Events bleibt der Verlauf sichtbar.

    edge = [
        original.getpixel(
            (x, BANNER_HEIGHT - 1)
        )
        for x in range(WIDTH)
    ]

    target = (35, 39, 47)

    transition_height = (
        header_height - BANNER_HEIGHT
    )

    for y in range(
        BANNER_HEIGHT,
        header_height,
    ):
        progress = (
            (y - BANNER_HEIGHT + 1)
            / max(1, transition_height)
        )

        progress = progress ** 0.72

        for x in range(WIDTH):
            r, g, b = edge[x]

            color = (
                round(
                    r * (1 - progress)
                    + target[0] * progress
                ),
                round(
                    g * (1 - progress)
                    + target[1] * progress
                ),
                round(
                    b * (1 - progress)
                    + target[2] * progress
                ),
            )

            draw.point(
                (x, y),
                fill=color,
            )

    # Überschrift auf dem ursprünglichen
    # 65-Pixel-Banner platzieren.
    draw.text(
        (WIDTH // 2, 37),
        title,
        font=font(39),
        anchor="mm",
        fill="#FFFFFF",
        stroke_width=2,
        stroke_fill="#111722",
    )

    # Keine Events:
    # Fertiger Banner mit Verlauf,
    # ohne leere Zeilen oder Platzhalter.
    if not has_events:
        return png(image)

    # Eventbereich unter dem Verlauf.
    draw_event_area(
        image,
        events,
        header_height,
    )

    return png(image)


# ==================================================
# EVENTZEILEN
# ==================================================

def draw_event_area(image, events, top):
    draw = ImageDraw.Draw(image)

    for index, event in enumerate(events):
        y0 = top + index * ROW_HEIGHT
        y1 = y0 + ROW_HEIGHT - 1

        # Dezente wechselnde Anthrazit-Töne.
        background = (
            (35, 39, 47)
            if index % 2 == 0
            else (33, 37, 45)
        )

        draw.rectangle(
            (0, y0, WIDTH - 1, y1),
            fill=background,
        )

        # Feine Trennlinie, ohne schwarze Ränder.
        if index:
            draw.line(
                (
                    28,
                    y0,
                    WIDTH - 28,
                    y0,
                ),
                fill=(62, 69, 80),
                width=1,
            )

        center = y0 + ROW_HEIGHT // 2

        name = str(event["name"])

        period = str(
            event.get("date_label") or ""
        )

        if event.get("time_label"):
            period += (
                " · "
                + str(event["time_label"])
            )

        status = event_status(event)

        # Eventname links.
        draw.text(
            (30, center),
            name,
            font=fit_font(
                draw,
                name,
                530,
                27,
            ),
            anchor="lm",
            fill="#F5F7FB",
        )

        # Datum mittig.
        draw.text(
            (785, center),
            period,
            font=fit_font(
                draw,
                period,
                355,
                23,
            ),
            anchor="mm",
            fill="#CDD6E3",
        )

        status_color = {
            "Gestartet": "#A9E6CF",
            "Kommend": "#F2D59C",
            "Beendet": "#AEB7C5",
        }[status]

        # Status rechts.
        draw.text(
            (1170, center),
            status,
            font=font(24),
            anchor="rm",
            fill=status_color,
        )


# ==================================================
# ÜBERSICHT
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
                "url": (
                    "attachment://00_halloween.png"
                )
            },
        }
    ]

    for index, (
        key,
        title,
        path,
        color,
    ) in enumerate(CATEGORIES, start=1):

        filename = (
            f"{index:02d}_{key}.png"
        )

        data = create_category_image(
            path,
            title,
            event_map[key],
        )

        images.append(
            (filename, data)
        )

        embeds.append({
            "color": color,
            "image": {
                "url": (
                    f"attachment://{filename}"
                )
            },
        })

    return images, embeds


def calculate_hash(images, embeds):
    digest = hashlib.sha256()

    for filename, data in images:
        digest.update(
            filename.encode("utf-8")
        )

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
            "emoji": {
                "name": emoji,
            },
        }
        for label, value, emoji
        in HELPER_CATEGORIES
    ]

    return {
        "content": "",
        "embeds": [
            {
                "title": (
                    "Nyerk24 · Event Helper"
                ),
                "description": (
                    "Wähle eine Eventkategorie aus, "
                    "um die verfügbaren Events "
                    "und ihre Details aufzurufen.\n\n"
                    "Deine Auswahl ist nur "
                    "für dich sichtbar."
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
                        "custom_id": (
                            "event:menu:category"
                        ),
                        "placeholder": (
                            "Eventkategorie auswählen"
                        ),
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


def helper_candidates(state):
    candidates = []

    for value in (
        state.get(
            "overview_v6", {}
        ).get("helper_message_id"),

        state.get(
            "overview_v2", {}
        ).get("helper", {}).get("message_id"),

        state.get(
            "halloween_2026", {}
        ).get("helper_message_id"),
    ):
        if value:
            identifier = str(value)

            if identifier not in candidates:
                candidates.append(identifier)

    return candidates


def ensure_helper(bot, channel_id, state):
    payload = helper_payload()

    me_response = api_request(
        "GET",
        f"{API}/users/@me",
        session=bot,
    )

    me = checked(
        me_response,
        "Bot-Identität prüfen",
    )

    bot_id = str(me["id"])

    # Vorhandene Helper-Nachrichten prüfen.
    # Keine zweite Nachricht erstellen,
    # wenn bereits ein nutzbarer Helper existiert.
    for message_id in helper_candidates(state):
        response = api_request(
            "GET",
            (
                f"{API}/channels/{channel_id}"
                f"/messages/{message_id}"
            ),
            session=bot,
        )

        if response.status_code == 404:
            continue

        if response.status_code == 403:
            print(
                "WARNUNG: Helper-Nachricht kann "
                "nicht geprüft werden (403)."
            )
            continue

        message = checked(
            response,
            "Helper prüfen",
        )

        author_id = str(
            message.get(
                "author", {}
            ).get("id", "")
        )

        if author_id != bot_id:
            print(
                "Vorhandener Helper gehört "
                "nicht zum aktuellen Bot:",
                message_id,
            )
            continue

        # Bestehende Nachricht weiterverwenden.
        # Keine unnötige Bearbeitung, wenn
        # die Auswahl bereits vorhanden ist.
        existing_components = (
            message.get("components") or []
        )

        existing_ids = []

        for row in existing_components:
            for component in row.get(
                "components", []
            ):
                existing_ids.append(
                    component.get("custom_id")
                )

        if (
            "event:menu:category"
            in existing_ids
        ):
            print(
                "Bestehender Event Helper gefunden:",
                message_id,
            )

            state.setdefault(
                "overview_v6", {}
            )["helper_message_id"] = message_id

            save_state(state)
            return

        # Vorhandenen eigenen Helper aktualisieren.
        response = api_request(
            "PATCH",
            (
                f"{API}/channels/{channel_id}"
                f"/messages/{message_id}"
            ),
            session=bot,
            json=payload,
        )

        if response.ok:
            state.setdefault(
                "overview_v6", {}
            )["helper_message_id"] = message_id

            save_state(state)

            print(
                "Bestehender Helper aktualisiert:",
                message_id,
            )
            return

        print(
            "WARNUNG: Bestehender Helper "
            "konnte nicht aktualisiert werden:",
            response.status_code,
            response.text[:300],
        )

    # Kein nutzbarer Helper gefunden.
    # Ein neuer Beitrag wird nur versucht,
    # wenn noch keiner wiederverwendet wurde.
    response = api_request(
        "POST",
        (
            f"{API}/channels/{channel_id}"
            "/messages"
        ),
        session=bot,
        json=payload,
    )

    if response.status_code == 403:
        print(
            "WARNUNG: Helper konnte nicht "
            "veröffentlicht werden: "
            "403 Missing Permissions."
        )

        print(
            "Die Eventübersicht bleibt erfolgreich. "
            "Bitte Bot-Token und Kanalberechtigungen "
            "für genau diesen Bot prüfen."
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
        "Neuer Helper veröffentlicht:",
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
        "Bot "
        + os.environ["DISCORD_BOT"].strip()
    )

    webhook_info = checked(
        api_request(
            "GET",
            webhook,
        ),
        "Webhook",
    )

    channel_id = str(
        webhook_info["channel_id"]
    )

    webhook_id = str(
        webhook_info["id"]
    )

    images, embeds = prepare_overview()

    digest = calculate_hash(
        images,
        embeds,
    )

    # Gleiche Nachricht wie bei der letzten
    # funktionierenden Version verwenden.
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
            str(
                message.get("webhook_id") or ""
            )
            != webhook_id
        ):
            raise RuntimeError(
                "Übersicht gehört nicht "
                "zum erwarteten Webhook."
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
                for index, (
                    filename, _
                ) in enumerate(images)
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

        for index, (
            filename,
            data,
        ) in enumerate(images):

            multipart[
                f"files[{index}]"
            ] = (
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
                params={
                    "wait": "true",
                },
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

    # Helper nach der Übersicht prüfen.
    ensure_helper(
        bot,
        channel_id,
        state,
    )

    print("Fertig.")
    print("Alle Kategorien mit Verlauf.")
    print("Keine leeren Eventzeilen.")
    print("Halloween unverändert.")
    print("Keine alten Beiträge gelöscht.")


if __name__ == "__main__":
    main()
