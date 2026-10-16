
    """Gibt 'upcoming', 'active' oder 'finished' zurück."""
"""Halloween 2026: feste Daten, Bannerdesign und Discord-Darstellung.

Änderungen am Event erfolgen hier; keine automatische Inhaltsbeschaffung.
Die zentrale events.py kümmert sich ausschließlich um das Veröffentlichen.
"""
"""Nyerk24 · Events – manuelle Veröffentlichung ohne Doppelposts.

Nur Nachrichten des EVENTS_WEBHOOK für das konfigurierte Event werden
bearbeitet. Alte doppelte Events-Webhook-Nachrichten werden bereinigt.
Keine Änderungen an Kalender, Content oder Halloween-Gestaltung.
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


def discord_get(session, url, **kwargs):
    response = session.get(url, timeout=35, **kwargs)
    response.raise_for_status()  # Bei fehlendem Zugriff NIEMALS blind neu posten.
    return response.json()


def is_our_event(message, webhook_id, event):
    # Keine fremden Bots oder Webhooks anfassen.
    if str(message.get("webhook_id", "")) != str(webhook_id):
        return False

    event_id = event.EVENT["id"]
    marker = f"event-id:{event_id}"
    known_files = {f"{event_id}_banner.png", "halloween_banner.png"}
    attachments = message.get("attachments") or []
    embeds = message.get("embeds") or []

    if any(a.get("filename") in known_files for a in attachments):
        return True
    if any(e.get("footer", {}).get("text") == marker for e in embeds):
        return True

    # Ältere Discord-Nachrichten können ein Embed-Bild statt eines
    # normalen Anhangs haben. Auch solche Varianten wiedererkennen.
    for embed in embeds:
        image_url = (embed.get("image") or {}).get("url", "")
        if any(name in image_url for name in known_files):
            return True

    # Die aktuellen neun Inhaltsabschnitte sind ein zusätzlicher Marker.
    # Ein einzelner Titel genügt nicht: mindestens zwei Titel abgleichen.
    section_titles = {s["title"] for s in event.EVENT["sections"]}
    matches = sum(1 for e in embeds if e.get("title") in section_titles)
    return matches >= 2


def find_existing_messages(session, channel_id, webhook_id, event):
    found = []
    before = None
    for _ in range(30):  # Bis zu 3.000 neueste Nachrichten, seitenweise.
        params = {"limit": 100}
        if before:
            params["before"] = before
        messages = discord_get(
            session, f"{API}/channels/{channel_id}/messages", params=params
        )
        if not messages:
            break
        for message in messages:
            if is_our_event(message, webhook_id, event):
                found.append(message["id"])
        before = messages[-1]["id"]
        if len(messages) < 100:
            break
    # Älteste Nachricht behalten, neuere Duplikate nach Erfolg entfernen.
    return sorted(set(found), key=int)


def publish(event):
    webhook = os.environ["EVENTS_WEBHOOK"].strip().split("?", 1)[0].rstrip("/")
    token = os.environ["DISCORD_BOT"].strip()
    identity = discord_get(requests.Session(), webhook)
    channel_id, webhook_id = identity.get("channel_id"), identity.get("id")
    if not channel_id or not webhook_id:
        raise RuntimeError("EVENTS_WEBHOOK liefert keine Kanal- oder Webhook-ID")

    session = requests.Session()
    session.headers.update({"Authorization": f"Bot {token}"})
    existing = find_existing_messages(session, channel_id, webhook_id, event)
    message_id = existing[0] if existing else None

    current = event.status()
    payload = event.payload(current)
    filename = f'{event.EVENT["id"]}_banner.png'
    payload["attachments"] = [{"id": 0, "filename": filename}]
    files = {
        "payload_json": (None, json.dumps(payload, ensure_ascii=False)),
        "files[0]": (filename, event.banner(current), "image/png"),
    }
    url = webhook + (f"/messages/{message_id}" if message_id else "")
    response = requests.request(
        "PATCH" if message_id else "POST", url,
        params={"wait": "true"}, files=files, timeout=50,
    )
    if not response.ok:
        raise RuntimeError(
            f"Webhook-Veröffentlichung fehlgeschlagen: HTTP {response.status_code}: "
            f"{response.text[:1200]}"
        )
    published = response.json()
    print(
        f'{event.EVENT["name"]}: '
        f'{"aktualisiert" if message_id else "erstellt"}, '
        f'Nachricht {published["id"]}, Status {current}'
    )

    # Erst nach erfolgreichem PATCH weitere, eindeutig erkannte
    # Duplikate desselben Events UND desselben Webhooks entfernen.
    for duplicate_id in existing[1:]:
        delete = requests.delete(
            f"{webhook}/messages/{duplicate_id}", timeout=35
        )
        if delete.status_code not in (204, 404):
            raise RuntimeError(
                f"Duplikat {duplicate_id} konnte nicht gelöscht werden: "
                f"HTTP {delete.status_code}: {delete.text[:600]}"
            )
        print(f"Doppelten Events-Beitrag entfernt: {duplicate_id}")

    print("Alte Helper-Nachrichten werden nicht angerührt.")


if __name__ == "__main__":
    publish(load_event())
