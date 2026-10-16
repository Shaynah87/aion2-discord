
"""Halloween 2026: feste Daten, Bannerdesign und Discord-Darstellung.

Änderungen am Event erfolgen hier; keine automatische Inhaltsbeschaffung.
Die zentrale events.py kümmert sich ausschließlich um das Veröffentlichen.
"""
import io
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
"""Nyerk24 · Events: manuell gestartete, duplikatfreie Veröffentlichung.

Einmal pro GitHub-Actions-Lauf wird das Event veröffentlicht oder die
bestehende Nachricht desselben Events bearbeitet. Keine Endlosschleife,
kein Scheduler und keine Änderungen am Kalender oder Content-System.
"""
import importlib.util
import json
import os
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
API = "https://discord.com/api/v10"


def load_event(folder="Halloween", filename="halloween.py"):
    path = ROOT / folder / filename
    if not path.is_file():
        raise FileNotFoundError(f"Event-Datei fehlt: {path}")
    spec = importlib.util.spec_from_file_location("nyerk24_event", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Event kann nicht geladen werden: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def api_get_messages(session, channel, before=None):
    params = {"limit": 100}
    if before:
        params["before"] = before
    response = session.get(f"{API}/channels/{channel}/messages", params=params, timeout=35)
    response.raise_for_status()
    return response.json()


def find_existing(session, channel, webhook_id, marker, filename):
    # Niemals fremde Webhook- oder Helper-Nachrichten überschreiben.
    before = None
    for _ in range(10):
        messages = api_get_messages(session, channel, before)
        if not messages:
            break
        for msg in messages:
            if str(msg.get("webhook_id", "")) != str(webhook_id):
                continue
            # Neue Nachrichten: Event-ID steckt im eindeutigen Bild-Dateinamen.
            if any(a.get("filename") == filename for a in msg.get("attachments", [])):
                return msg["id"]
            # Bereits veröffentlichte Nachrichten mit altem Embed wiederfinden.
            if any(e.get("footer", {}).get("text") == marker for e in msg.get("embeds", [])):
                return msg["id"]
        before = messages[-1]["id"]
    return None


def publish(event):
    webhook = os.environ["EVENTS_WEBHOOK"].strip().rstrip("/")
    token = os.environ["DISCORD_BOT"].strip()
    identity_response = requests.get(webhook, timeout=25)
    identity_response.raise_for_status()
    identity = identity_response.json()
    channel = identity.get("channel_id")
    webhook_id = identity.get("id")
    if not channel or not webhook_id:
        raise RuntimeError("EVENTS_WEBHOOK hat keine Kanal- oder Webhook-ID")

    session = requests.Session()
    session.headers.update({"Authorization": f"Bot {token}"})
    marker = f'event-id:{event.EVENT["id"]}'
    filename = f'{event.EVENT["id"]}_banner.png'
    message_id = find_existing(session, channel, webhook_id, marker, filename)

    current = event.status()
    payload = event.payload(current)
    # Direktes Bild im Nachrichtenanhang: Discord zeigt es in voller Breite.
    # Der Dateiname dient gleichzeitig als dauerhafte Event-Kennung.
    payload["attachments"] = [{"id": 0, "filename": filename}]
    files = {
        "payload_json": (None, json.dumps(payload, ensure_ascii=False)),
        "files[0]": (filename, event.banner(current), "image/png"),
    }
    url = webhook + (f"/messages/{message_id}" if message_id else "")
    response = requests.request(
        "PATCH" if message_id else "POST", url,
        params={"wait": "true"}, files=files, timeout=45,
    )
    if not response.ok:
        raise RuntimeError(f"Discord Webhook HTTP {response.status_code}: {response.text[:1200]}")
    result = response.json()
    print(f'{event.EVENT["name"]}: {"bestehende Nachricht aktualisiert" if message_id else "einmalig veröffentlicht"}; '
          f'ID {result["id"]}; Status {current}; Absender Nyerk24 · Events')
    if not message_id:
        print("Alte Helper-Testnachrichten bei Bedarf einmalig manuell entfernen.")


if __name__ == "__main__":
    publish(load_event())
