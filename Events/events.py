
"""
Nyerk24 · Events

- Halloween bleibt vollständig unverändert
- Bestehende Kategorie-Banner bleiben erhalten
- Eventkarten sind exakt 1200 x 65 Pixel
- Ein Helper-Beitrag mit Kategorieauswahl
- Unveränderte Nachrichten werden nicht bearbeitet
- Discord Rate Limits (HTTP 429) werden automatisch behandelt
- Nachrichten-IDs werden nach jeder Änderung gespeichert
"""

import hashlib
import importlib.util
import io
import json
import os
import random
import time

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

MAX_RETRIES = 12
MAX_RATE_LIMIT_WAIT = 120

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
# DISCORD HTTP / RATE LIMITS
# --------------------------------------------------

def discord_request(method, url, **kwargs):
    """
    Führt eine Discord-Anfrage aus.

    Bei HTTP 429 wird retry_after ausgewertet.
    Die Anfrage wird anschließend automatisch wiederholt.

    Auch vorübergehende Serverfehler werden behandelt.
    """

    session = kwargs.pop("session", None)

    if session is None:
        session = requests

    kwargs.setdefault("timeout", TIMEOUT)

    for attempt in range(1, MAX_RETRIES + 1):

        try:
            response = session.request(
                method,
                url,
                **kwargs,
            )

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as error:

            # Bei POST könnte Discord die Nachricht bereits
            # erstellt haben. Deshalb keinen automatischen
            # zweiten POST ausführen.
            if method.upper() == "POST":
                raise RuntimeError(
                    "POST-Verbindung unterbrochen. "
                    "Discord könnte die Nachricht bereits "
                    "erstellt haben. Bitte den Kanal prüfen, "
                    "bevor der Workflow erneut gestartet wird."
                ) from error

            if attempt == MAX_RETRIES:
                raise

            delay = min(
                2 ** (attempt - 1),
                15,
            )

            print(
                f"Verbindungsproblem: "
                f"Versuch {attempt}/{MAX_RETRIES}, "
                f"warte {delay}s"
            )

            time.sleep(delay)
            continue

        if response.status_code == 429:

            try:
                body = response.json()
            except ValueError:
                body = {}

            retry_after = body.get("retry_after")

            if retry_after is None:
                retry_after = response.headers.get(
                    "Retry-After",
                    1,
                )

            try:
                delay = float(retry_after)
            except (TypeError, ValueError):
                delay = 1.0

            delay = max(0.5, delay + 0.25)

            if delay > MAX_RATE_LIMIT_WAIT:
                raise RuntimeError(
                    "Discord verlangt eine Wartezeit von "
                    f"{delay:.1f}s. Abbruch ohne "
                    "automatische Neuanlage."
                )

            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    "Discord Rate Limit nach "
                    f"{MAX_RETRIES} Versuchen: "
                    f"{response.text[:500]}"
                )

            print(
                f"Discord Rate Limit (429): "
                f"warte {delay:.2f}s, "
                f"Versuch {attempt}/{MAX_RETRIES}"
            )

            time.sleep(delay)
            continue

        if response.status_code in (
            500,
            502,
            503,
            504,
        ):

            # Auch hier kann ein POST bereits angekommen
            # sein. Keine automatische Doppelveröffentlichung.
            if method.upper() == "POST":
                raise RuntimeError(
                    "Discord-Serverfehler beim Erstellen "
                    "einer Nachricht. Bitte zuerst "
                    "den Discord-Kanal prüfen: "
                    f"HTTP {response.status_code}"
                )

            if attempt == MAX_RETRIES:
                return response

            delay = min(
                2 ** (attempt - 1),
                15,
            ) + random.uniform(0, 0.5)

            print(
                f"Discord HTTP {response.status_code}: "
                f"warte {delay:.2f}s"
            )

            time.sleep(delay)
            continue

        return response

    raise RuntimeError(
        "Discord-Anfrage konnte nicht "
        "abgeschlossen werden."
    )


def check(response, name):
    if not response.ok:
        raise RuntimeError(
            f"{name}: HTTP {response.status_code}: "
            f"{response.text[:1000]}"
        )

    return (
        response.json()
        if response.content
        else {}
    )


# --------------------------------------------------
# DATEIEN / MODULE
# --------------------------------------------------

def load(path, name):
    spec = importlib.util.spec_from_file_location(
        name,
        ROOT / path,
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
            return ImageFont.truetype(
                path,
                size,
            )

    raise RuntimeError(
        "DejaVuSans-Schriftart fehlt"
    )


def png(image):
    output = io.BytesIO()

    image.convert("RGB").save(
        output,
        format="PNG",
        optimize=True,
    )

    return output.getvalue()


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


# --------------------------------------------------
# KATEGORIE-BANNER
# --------------------------------------------------

def category_banner(path, title):

    with Image.open(ROOT / path) as source:

        if source.size != (1200, 65):
            raise ValueError(
                f"{path}: erwartet 1200x65, "
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


# --------------------------------------------------
# EVENTKARTEN
# --------------------------------------------------

def event_template():

    path = (
        REPO
        / "Tracker"
        / "event_overview.png"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Vorlage fehlt: {path}"
        )

    with Image.open(path) as source:
        original = source.convert("RGB")

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

    start = date.fromisoformat(
        event["start"]
    )

    end = date.fromisoformat(
        event["end"]
    )

    today = datetime.now(
        ZoneInfo("Europe/Berlin")
    ).date()

    if today < start:
        status = "Kommend"

    elif today <= end:
        status = "Gestartet"

    else:
        status = "Beendet"

    title_font = face(23)

    while (
        draw.textbbox(
            (0, 0),
            name,
            font=title_font,
        )[2] > 870
        and title_font.size > 15
    ):
        title_font = face(
            title_font.size - 1
        )

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
            "Eventkarte hat falsche Größe"
        )

    return png(image)


# --------------------------------------------------
# HAUPTPROGRAMM
# --------------------------------------------------

def main():

    if not STATE.exists():
        raise RuntimeError(
            "events_message.json fehlt"
        )

    state = json.loads(
        STATE.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(state, dict):
        raise ValueError(
            "events_message.json muss "
            "ein JSON-Objekt sein"
        )

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

    info = check(
        discord_request(
            "GET",
            webhook,
        ),
        "Webhook",
    )

    channel = str(
        info["channel_id"]
    )

    webhook_id = str(
        info["id"]
    )

    # Halloween nur überprüfen.
    # Nicht bearbeiten und nicht neu posten.

    halloween_id = str(
        state.get(
            "halloween_2026", {}
        ).get(
            "webhook_message_id"
        ) or ""
    )

    if not halloween_id:
        raise RuntimeError(
            "Halloween-ID fehlt. "
            "Abbruch ohne Änderungen."
        )

    existing_halloween = check(
        discord_request(
            "GET",
            (
                f"{API}/channels/"
                f"{channel}/messages/"
                f"{halloween_id}"
            ),
            session=bot,
        ),
        "Halloween prüfen",
    )

    if (
        str(
            existing_halloween.get(
                "webhook_id"
            ) or ""
        ) != webhook_id
    ):
        raise RuntimeError(
            "Halloween gehört nicht "
            "zu diesem Webhook"
        )

    print(
        "Halloween unverändert:",
        halloween_id,
    )

    # ----------------------------------------------
    # VORHANDENE NACHRICHTEN PRÜFEN
    # ----------------------------------------------

    def verify(message_id, expected):

        response = discord_request(
            "GET",
            (
                f"{API}/channels/"
                f"{channel}/messages/"
                f"{message_id}"
            ),
            session=bot,
        )

        if response.status_code == 404:
            raise RuntimeError(
                f"Gespeicherter Beitrag "
                f"{message_id} fehlt. "
                "Kein automatischer Doppelpost."
            )

        message = check(
            response,
            "Nachricht prüfen",
        )

        if expected == "webhook":

            if (
                str(
                    message.get(
                        "webhook_id"
                    ) or ""
                ) != webhook_id
            ):
                raise RuntimeError(
                    "Falscher Webhook für "
                    f"{message_id}"
                )

        elif expected == "bot":

            if message.get("webhook_id"):
                raise RuntimeError(
                    f"Helper {message_id} "
                    "ist eine Webhook-Nachricht"
                )

        return message

    # ----------------------------------------------
    # WEBHOOK-NACHRICHT VERÖFFENTLICHEN
    # ----------------------------------------------

    def webhook_post(key, filename, data):

        record = (
            state.setdefault(
                "overview_v2", {}
            ).setdefault(key, {})
        )

        message_id = str(
            record.get("message_id") or ""
        )

        digest = hash_payload(data)

        if message_id:

            verify(
                message_id,
                "webhook",
            )

            if record.get("hash") == digest:
                print(
                    "Unverändert:",
                    key,
                )
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

            response = discord_request(
                "PATCH",
                (
                    f"{webhook}/messages/"
                    f"{message_id}"
                ),
                files=files,
                timeout=90,
            )

        else:

            response = discord_request(
                "POST",
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
            message_id=str(
                message["id"]
            ),
            hash=digest,
        )

        save(state)

        print(
            "OK:",
            key,
        )

    # ----------------------------------------------
    # EVENTS LADEN
    # ----------------------------------------------

    attendance = load(
        "Anwesenheit/anwesenheit.py",
        "attendance",
    )

    template = event_template()

    event_map = {
        "anwesenheitslisten":
            attendance.EVENTS,

        "ingame_events": (),

        "community_events": (),

        "twitch_drops": (),
    }

    # ----------------------------------------------
    # KATEGORIEN UND EVENTS
    # ----------------------------------------------

    for key, title, path in CATEGORIES:

        webhook_post(
            "category:" + key,
            key + ".png",
            category_banner(
                path,
                title,
            ),
        )

        for event in event_map[key]:

            webhook_post(
                "event:" + event["id"],
                event["id"] + ".png",
                event_card(
                    template,
                    event,
                ),
            )

    # ----------------------------------------------
    # EIN HELPER-BEITRAG
    # ----------------------------------------------

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
                    "custom_id":
                        "event:menu:category",

                    "placeholder":
                        "Überschrift wählen",

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
            "Event wählen → "
            "Details erscheinen sofort"
        ),
        "components": components,
        "allowed_mentions": {
            "parse": []
        },
    }

    record = (
        state.setdefault(
            "overview_v2", {}
        ).setdefault(
            "helper", {}
        )
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

        verify(
            message_id,
            "bot",
        )

        if record.get("hash") == digest:
            print(
                "Helper unverändert"
            )
            return

        response = discord_request(
            "PATCH",
            (
                f"{API}/channels/"
                f"{channel}/messages/"
                f"{message_id}"
            ),
            session=bot,
            json=payload,
        )

    else:

        response = discord_request(
            "POST",
            (
                f"{API}/channels/"
                f"{channel}/messages"
            ),
            session=bot,
            json=payload,
        )

    message = check(
        response,
        "Helper",
    )

    record.update(
        message_id=str(
            message["id"]
        ),
        hash=digest,
    )

    save(state)

    print(
        "Helper OK"
    )


if __name__ == "__main__":
    main()
