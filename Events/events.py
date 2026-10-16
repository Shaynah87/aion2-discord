
"""Nyerk24 · Events: eine dauerhaft gespeicherte Discord-Nachricht je Event.

Die Message-ID wird in Events/events_message.json gespeichert. Der Workflow
committet diese Datei, damit die ID auch beim nächsten Lauf erhalten bleibt.
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
        raise RuntimeError(f'Eventmodul kann nicht geladen werden: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_state():
    if not STATE.exists():
        return {}
    data = json.loads(STATE.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise RuntimeError('events_message.json muss ein JSON-Objekt sein')
    return data


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def api_json(response, context):
    if not response.ok:
        raise RuntimeError(f'{context}: HTTP {response.status_code}: {response.text[:800]}')
    return response.json()


def belongs_to_event(message, webhook_id, event):
    if str(message.get('webhook_id', '')) != str(webhook_id):
        return False
    event_id = event.EVENT['id']
    marker = f'event-id:{event_id}'
    names = {f'{event_id}_banner.png', 'halloween_banner.png'}
    if any(a.get('filename') in names for a in message.get('attachments', [])):
        return True
    embeds = message.get('embeds', [])
    if any(e.get('footer', {}).get('text') == marker for e in embeds):
        return True
    titles = {s['title'] for s in event.EVENT['sections']}
    if sum(e.get('title') in titles for e in embeds) >= 2:
        return True
    return any(any(n in (e.get('image') or {}).get('url', '') for n in names) for e in embeds)


def find_messages(bot, channel_id, webhook_id, event):
    found, before = [], None
    for _ in range(30):
        params = {'limit': 100}
        if before:
            params['before'] = before
        messages = api_json(bot.get(f'{API}/channels/{channel_id}/messages', params=params, timeout=35), 'Nachrichtensuche')
        if not messages:
            break
        found.extend(m['id'] for m in messages if belongs_to_event(m, webhook_id, event))
        before = messages[-1]['id']
        if len(messages) < 100:
            break
    return sorted(set(found), key=int)


def publish(event):
    webhook = os.environ['EVENTS_WEBHOOK'].strip().split('?', 1)[0].rstrip('/')
    token = os.environ['DISCORD_BOT'].strip()
    identity = api_json(requests.get(webhook, timeout=30), 'Webhook-Informationen')
    channel_id, webhook_id = identity['channel_id'], identity['id']
    bot = requests.Session()
    bot.headers['Authorization'] = f'Bot {token}'
    state = read_state()
    event_id = event.EVENT['id']
    stored = str(state.get(event_id, ''))

    # Gespeicherte ID zunächst direkt prüfen. Bei gelöschter Nachricht neu suchen.
    if stored:
        response = bot.get(f'{API}/channels/{channel_id}/messages/{stored}', timeout=30)
        if response.status_code == 404:
            stored = ''
        else:
            message = api_json(response, 'Gespeicherte Nachricht prüfen')
            if not belongs_to_event(message, webhook_id, event):
                raise RuntimeError('Gespeicherte Message-ID gehört nicht zu diesem Events-Webhook/Event; Abbruch ohne neuen Post.')

    # Immer nach weiteren Kopien suchen, auch wenn eine ID gespeichert ist.
    found = find_messages(bot, channel_id, webhook_id, event)
    if stored and stored not in found:
        found.append(stored)
    found = sorted(set(found), key=int)
    message_id = found[0] if found else None

    current = event.status()
    payload = event.payload(current)
    filename = f'{event_id}_banner.png'
    payload['attachments'] = [{'id': 0, 'filename': filename}]
    files = {
        'payload_json': (None, json.dumps(payload, ensure_ascii=False)),
        'files[0]': (filename, event.banner(current), 'image/png'),
    }
    url = webhook + (f'/messages/{message_id}' if message_id else '')
    response = requests.request('PATCH' if message_id else 'POST', url,
                                params={'wait': 'true'}, files=files, timeout=60)
    published = api_json(response, 'Event veröffentlichen/bearbeiten')
    new_id = str(published['id'])
    state[event_id] = new_id
    save_state(state)
    print(f'{event_id}: {"bearbeitet" if message_id else "erstellt"}; ID {new_id}; Status {current}')

    # Ausschließlich eindeutig zugeordnete Doppelposts desselben Webhooks entfernen.
    for duplicate in found:
        if duplicate == new_id:
            continue
        deletion = requests.delete(f'{webhook}/messages/{duplicate}', timeout=35)
        if deletion.status_code not in (204, 404):
            raise RuntimeError(f'Duplikat {duplicate} konnte nicht gelöscht werden: HTTP {deletion.status_code}: {deletion.text[:500]}')
        print(f'Duplikat gelöscht: {duplicate}')
    print('Helper-Nachrichten und andere Events bleiben unberührt.')


if __name__ == '__main__':
    publish(load_event())
