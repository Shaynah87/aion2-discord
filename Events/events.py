
"""Nyerk24 · Events – eine Discord-Nachricht pro Event.

Keine automatischen Inhaltsänderungen. GitHub Actions speichert die Message-ID
in Events/events_message.json. Ein erneuter Lauf bearbeitet dieselbe Nachricht.
"""
import importlib.util
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'events_message.json'
API = 'https://discord.com/api/v10'


def load_event():
    path = ROOT / 'Halloween' / 'halloween.py'
    spec = importlib.util.spec_from_file_location('nyerk24_event', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Eventdatei nicht ladbar: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(response, label):
    if not response.ok:
        raise RuntimeError(f'{label}: HTTP {response.status_code}: {response.text[:700]}')
    return response.json() if response.content else {}


def state_read():
    if not STATE.exists():
        return {}
    result = json.loads(STATE.read_text(encoding='utf-8'))
    if not isinstance(result, dict):
        raise RuntimeError('Events/events_message.json muss ein JSON-Objekt sein.')
    return result


def state_write(data):
    STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def is_our_event(message, webhook_id, event):
    if str(message.get('webhook_id', '')) != str(webhook_id):
        return False
    event_id = event.EVENT['id']
    filenames = {f'{event_id}_banner.png', 'halloween_banner.png'}
    if any(a.get('filename') in filenames for a in message.get('attachments', [])):
        return True
    if f'event-id:{event_id}' in (message.get('content') or ''):
        return True
    embeds = message.get('embeds') or []
    if any((e.get('footer') or {}).get('text') == f'event-id:{event_id}' for e in embeds):
        return True
    titles = {section['title'] for section in event.EVENT['sections']}
    if sum(e.get('title') in titles for e in embeds) >= 2:
        return True
    return any(any(name in ((e.get('image') or {}).get('url') or '') for name in filenames) for e in embeds)


def find_existing(bot, channel_id, webhook_id, event):
    matches = []
    before = None
    for _ in range(30):
        params = {'limit': 100}
        if before:
            params['before'] = before
        batch = check(bot.get(f'{API}/channels/{channel_id}/messages', params=params, timeout=35), 'Kanal durchsuchen')
        if not batch:
            break
        matches.extend(str(m['id']) for m in batch if is_our_event(m, webhook_id, event))
        before = batch[-1]['id']
        if len(batch) < 100:
            break
    return sorted(set(matches), key=int)


def publish(event):
    webhook = os.environ['EVENTS_WEBHOOK'].strip().split('?', 1)[0].rstrip('/')
    token = os.environ['DISCORD_BOT'].strip()
    info = check(requests.get(webhook, timeout=30), 'Events-Webhook prüfen')
    channel_id, webhook_id = str(info['channel_id']), str(info['id'])
    bot = requests.Session()
    bot.headers['Authorization'] = f'Bot {token}'
    state = state_read()
    event_id = event.EVENT['id']
    stored = str(state.get(event_id) or '')

    # Immer zuerst den Kanal durchsuchen. Das funktioniert auch, wenn der
    # vorherige Lauf nach dem Discord-Post, aber vor dem Git-Commit abbrach.
    matches = find_existing(bot, channel_id, webhook_id, event)
    if stored and stored not in matches:
        response = bot.get(f'{API}/channels/{channel_id}/messages/{stored}', timeout=30)
        if response.status_code == 200 and is_our_event(response.json(), webhook_id, event):
            matches.append(stored)
        elif response.status_code not in (200, 404):
            check(response, 'Gespeicherte Nachricht prüfen')
        else:
            print('Gespeicherte ID ist nicht mehr zuordenbar; vorhandene Nachrichten haben Vorrang.')

    matches = sorted(set(matches), key=int)
    message_id = matches[0] if matches else None
    current = event.status()
    payload = event.payload(current)
    filename = f'{event_id}_banner.png'
    payload['attachments'] = [{'id': 0, 'filename': filename}]
    # Sichtbarer Marker wird bewusst NICHT benötigt: die Dateibenennung
    # identifiziert das Event, ohne störende event-id-Zeile in Discord.
    multipart = {
        'payload_json': (None, json.dumps(payload, ensure_ascii=False)),
        'files[0]': (filename, event.banner(current), 'image/png'),
    }

    if message_id:
        url = f'{webhook}/messages/{message_id}'
        response = requests.patch(url, params={'wait': 'true'}, files=multipart, timeout=60)
        action = 'bearbeitet'
    else:
        # Ausschließlich dann POST, wenn die komplette Suche nichts fand.
        response = requests.post(webhook, params={'wait': 'true'}, files=multipart, timeout=60)
        action = 'erstellt'

    result = check(response, 'Discord-Nachricht veröffentlichen')
    result_id = str(result['id'])
    # Ein erfolgreicher PATCH/POST ist ausreichend. Keine nachträgliche
    # Validierung, die den Workflow nach einem erfolgreichen POST abbricht.
    state[event_id] = result_id
    state_write(state)
    print(f'{event_id}: {action}; ID {result_id}; Status {current}')

    # Nach erfolgreichem Speichern ausschließlich eindeutig erkannte
    # weitere Nachrichten desselben Events-Webhooks entfernen.
    for duplicate in matches:
        if duplicate == result_id:
            continue
        response = requests.delete(f'{webhook}/messages/{duplicate}', timeout=35)
        if response.status_code not in (204, 404):
            raise RuntimeError(f'Duplikat {duplicate} konnte nicht gelöscht werden: HTTP {response.status_code}: {response.text[:500]}')
        print(f'Duplikat entfernt: {duplicate}')
    print('Andere Events und Helper-Nachrichten bleiben unverändert.')


if __name__ == '__main__':
    publish(load_event())
