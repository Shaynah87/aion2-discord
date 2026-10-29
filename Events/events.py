
"""
Nyerk24 · Events

Eine öffentliche Discord-Nachricht pro Event.
Bestehende Nachrichten werden aktualisiert.

Halloween:
- vorhandenes Banner behalten
- öffentliche kompakte Übersicht
- Button für private Eventdetails
- Details werden vom Cloudflare-Worker geliefert

Einmalige Umstellung:
Webhook-Nachricht -> Bot-Nachricht

Die bisherige Nachricht wird erst entfernt, nachdem die
neue Bot-Nachricht erfolgreich erstellt und gespeichert wurde.

Keine neuen Bots oder Secrets erforderlich.
"""

import importlib.util
import json
import os
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
STATE = ROOT / "events_message.json"
API = "https://discord.com/api/v10"

BUTTON_ID = "event:details:halloween_2026"


def load_event():
    path = ROOT / "Halloween" / "halloween.py"

    spec = importlib.util.spec_from_file_location(
        "nyerk24_event",
        path
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Eventmodul kann nicht geladen werden: {path}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def response_json(response, context):
    if not response.ok:
        raise RuntimeError(
            f"{context}: HTTP {response.status_code}: "
            f"{response.text[:700]}"
        )

    return response.json()


def read_state():
    if not STATE.exists():
        return {}

    data = json.loads(
        STATE.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise RuntimeError(
            "events_message.json muss ein JSON-Objekt enthalten"
        )

    return data


def save_state(state):
    temporary = STATE.with_suffix(".json.tmp")

    temporary.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    temporary.replace(STATE)


def bot_session():
    token = os.environ["DISCORD_BOT"].strip()

    if not token:
        raise RuntimeError("DISCORD_BOT ist leer.")

    session = requests.Session()

    session.headers.update({
        "Authorization": f"Bot {token}"
    })

    return session


def webhook_identity():
    webhook = (
        os.environ["EVENTS_WEBHOOK"]
        .strip()
        .split("?", 1)[0]
        .rstrip("/")
    )

    identity = response_json(
        requests.get(webhook, timeout=30),
        "Events-Webhook abrufen"
    )

    return webhook, identity


def message_url(channel_id, message_id=None):
    url = f"{API}/channels/{channel_id}/messages"

    if message_id:
        url += f"/{message_id}"

    return url


def fetch_message(bot, channel_id, message_id):
    response = bot.get(
        message_url(channel_id, message_id),
        timeout=30
    )

    if response.status_code == 404:
        return None

    return response_json(
        response,
        "Discord-Nachricht prüfen"
    )


def find_existing_event(bot, channel_id, webhook_id, event):
    """
    Verhindert einen unbeabsichtigten Erstpost,
    wenn die gespeicherte Nachrichten-ID fehlt.
    """

    event_id = event.EVENT["id"]
    before = None

    filenames = {
        f"{event_id}_banner.png",
        "halloween_banner.png"
    }

    titles = {
        section["title"]
        for section in event.EVENT["sections"]
    }

    for _ in range(30):
        params = {"limit": 100}

        if before:
            params["before"] = before

        messages = response_json(
            bot.get(
                message_url(channel_id),
                params=params,
                timeout=35
            ),
            "Vorhandene Events suchen"
        )

        for message in messages:
            if str(message.get("webhook_id", "")) != webhook_id:
                continue

            attachments = message.get("attachments", [])
            embeds = message.get("embeds", [])

            has_banner = any(
                attachment.get("filename") in filenames
                for attachment in attachments
            )

            has_section = any(
                embed.get("title") in titles
                for embed in embeds
            )

            has_image = any(
                filename in (
                    embed.get("image") or {}
                ).get("url", "")
                for embed in embeds
                for filename in filenames
            )

            if has_banner or has_section or has_image:
                raise RuntimeError(
                    "Halloween ist bereits im Kanal vorhanden, "
                    "aber die gespeicherte ID fehlt. "
                    "Kein neuer Post."
                )

        if len(messages) < 100:
            break

        before = messages[-1]["id"]


def public_payload(event, current):
    """
    Öffentliche Halloween-Nachricht.

    Die ausführlichen neun Eventabschnitte erscheinen
    ausschließlich im privaten Cloudflare-Dropdown.
    """

    event_data = event.EVENT
    event_id = event_data["id"]

    filename = f"{event_id}_banner.png"

    source = event_data["source_url"]

    if not source.startswith("https://"):
        raise RuntimeError(
            "Gültige HTTPS-Eventquelle fehlt."
        )

    status_labels = {
        "upcoming": "Bald verfügbar",
        "active": "Aktiv",
        "finished": "Beendet"
    }

    status_label = status_labels.get(
        current,
        "Unbekannt"
    )

    description = (
        f"**Zeitraum:** {event_data['date_label']}\n"
        f"**Status:** {status_label}\n\n"
        "Alle Informationen zu Missionen, Belohnungen, "
        "Eventshop und Süßigkeiten findest du über "
        "den Button **Eventdetails anzeigen**.\n\n"
        "Die Details werden dir persönlich angezeigt "
        "und sind für andere Mitglieder nicht sichtbar."
    )

    payload = {
        "embeds": [
            {
                "title": "🔗 Eventankündigung & Belohnungen",
                "url": source,
                "description": description,
                "color": 0xFF7100,
                "image": {
                    "url": f"attachment://{filename}"
                },
                "footer": {
                    "text": event_id
                }
            }
        ],
        "components": [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 1,
                        "label": "🎃 Eventdetails anzeigen",
                        "custom_id": BUTTON_ID
                    }
                ]
            }
        ],
        "allowed_mentions": {
            "parse": []
        },
        "attachments": [
            {
                "id": 0,
                "filename": filename
            }
        ]
    }

    return payload


def send_bot_message(
    bot,
    channel_id,
    payload,
    filename,
    banner,
    message_id=None
):
    """
    Erstellt eine Bot-Nachricht oder aktualisiert
    eine bereits vorhandene Bot-Nachricht.
    """

    url = message_url(channel_id, message_id)

    method = "PATCH" if message_id else "POST"

    files = {
        "payload_json": (
            None,
            json.dumps(
                payload,
                ensure_ascii=False
            )
        ),
        "files[0]": (
            filename,
            banner,
            "image/png"
        )
    }

    response = bot.request(
        method,
        url,
        files=files,
        timeout=65
    )

    return response_json(
        response,
        "Bot-Nachricht aktualisieren"
        if message_id
        else "Bot-Nachricht erstellen"
    )


def delete_old_webhook_message(
    webhook,
    old_message_id
):
    """
    Entfernt ausschließlich die alte Webhook-Nachricht.

    Ein bereits gelöschter Beitrag gilt als erledigt.
    """

    response = requests.delete(
        f"{webhook}/messages/{old_message_id}",
        timeout=30
    )

    if response.status_code in (204, 404):
        return

    raise RuntimeError(
        "Neue Bot-Nachricht ist gespeichert, "
        "aber alte Webhook-Nachricht konnte "
        "nicht entfernt werden: "
        f"HTTP {response.status_code}: "
        f"{response.text[:500]}"
    )


def normalize_event_state(value):
    """
    Unterstützt sowohl das bisherige Format:

        "halloween_2026": "MESSAGE_ID"

    als auch das neue Format:

        "halloween_2026": {
            "message_id": "...",
            "old_webhook_message_id": "..."
        }
    """

    if isinstance(value, dict):
        return {
            "message_id": str(
                value.get("message_id") or ""
            ),
            "old_webhook_message_id": str(
                value.get("old_webhook_message_id") or ""
            )
        }

    return {
        "message_id": str(value or ""),
        "old_webhook_message_id": ""
    }


def publish(event):
    event_id = event.EVENT["id"]

    if event_id != "halloween_2026":
        raise RuntimeError(
            f"Event noch nicht eingerichtet: {event_id}"
        )

    webhook, identity = webhook_identity()

    channel_id = str(identity["channel_id"])
    webhook_id = str(identity["id"])

    bot = bot_session()

    state = read_state()

    record = normalize_event_state(
        state.get(event_id)
    )

    stored_id = record["message_id"]
    old_webhook_id = record["old_webhook_message_id"]

    current = event.status()

    payload = public_payload(
        event,
        current
    )

    filename = f"{event_id}_banner.png"

    banner = event.banner(current)

    # -----------------------------------------------------
    # 1. Bestehende Nachricht identifizieren
    # -----------------------------------------------------

    existing = None

    if stored_id:
        existing = fetch_message(
            bot,
            channel_id,
            stored_id
        )

        if existing is None:
            raise RuntimeError(
                "Die gespeicherte Eventnachricht wurde "
                "gelöscht. Kein automatischer Doppelpost."
            )

    else:
        find_existing_event(
            bot,
            channel_id,
            webhook_id,
            event
        )

    # -----------------------------------------------------
    # 2. Prüfen, ob die gespeicherte Nachricht
    #    noch vom alten Webhook stammt
    # -----------------------------------------------------

    migration_required = False

    if existing:
        message_webhook_id = str(
            existing.get("webhook_id") or ""
        )

        if message_webhook_id == webhook_id:
            migration_required = True
            old_webhook_id = stored_id

        elif message_webhook_id:
            raise RuntimeError(
                "Die gespeicherte Nachricht gehört "
                "zu einem anderen Webhook. "
                "Keine Änderung."
            )

        else:
            author = existing.get("author") or {}

            bot_user = response_json(
                bot.get(
                    f"{API}/users/@me",
                    timeout=30
                ),
                "Bot-Identität prüfen"
            )

            if str(author.get("id")) != str(
                bot_user.get("id")
            ):
                raise RuntimeError(
                    "Die gespeicherte Nachricht "
                    "gehört nicht zum Nyerk24-Bot. "
                    "Keine Änderung."
                )

    # -----------------------------------------------------
    # 3. Bereits vorhandene Bot-Nachricht bearbeiten
    # -----------------------------------------------------

    if existing and not migration_required:
        result = send_bot_message(
            bot,
            channel_id,
            payload,
            filename,
            banner,
            message_id=stored_id
        )

        if str(result["id"]) != stored_id:
            raise RuntimeError(
                "Discord hat eine unerwartete "
                "Nachrichten-ID geliefert."
            )

        print(
            f"{event_id}: BOT-NACHRICHT AKTUALISIERT; "
            f"ID {stored_id}; Status {current}"
        )

    # -----------------------------------------------------
    # 4. Webhook -> Bot umstellen
    # -----------------------------------------------------

    else:
        result = send_bot_message(
            bot,
            channel_id,
            payload,
            filename,
            banner
        )

        new_id = str(result["id"])

        # Die neue ID wird sofort gespeichert.
        # Falls das anschließende Löschen scheitert,
        # kann die nächste Ausführung es nachholen.

        state[event_id] = {
            "message_id": new_id,
            "old_webhook_message_id": old_webhook_id
        }

        save_state(state)

        stored_id = new_id

        print(
            f"{event_id}: BOT-NACHRICHT ERSTELLT; "
            f"ID {new_id}; Status {current}"
        )

    # -----------------------------------------------------
    # 5. Alte Webhook-Nachricht entfernen
    # -----------------------------------------------------

    if old_webhook_id:
        delete_old_webhook_message(
            webhook,
            old_webhook_id
        )

        print(
            f"{event_id}: ALTE WEBHOOK-NACHRICHT "
            f"{old_webhook_id} ENTFERNT"
        )

    # -----------------------------------------------------
    # 6. Endgültigen Zustand speichern
    # -----------------------------------------------------

    state[event_id] = {
        "message_id": stored_id,
        "old_webhook_message_id": ""
    }

    save_state(state)

    print(
        f"{event_id}: FERTIG; "
        f"ID {stored_id}; Status {current}"
    )

    print(
        "Weitere Ausführungen bearbeiten "
        "die gespeicherte Bot-Nachricht."
    )


if __name__ == "__main__":
    publish(load_event())
