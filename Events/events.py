"""Nyerk24 · Events: pro Event eine Discord-Nachricht, danach nur PATCH.

Erstveröffentlichung automatisch, wenn noch keine Event-ID gespeichert ist.
Nachrichten-IDs bleiben in Events/events_message.json und werden von Actions committet.
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


def response_json(response, context):
    if not response.ok:
        raise RuntimeError(f'{context}: HTTP {response.status_code}: {response.text[:700]}')
    return response.json()


def read_state():
    if not STATE.exists():
        return {}
    data = json.loads(STATE.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise RuntimeError('events_message.json muss ein JSON-Objekt enthalten')
    return data


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def publish(event):
    webhook = os.environ['EVENTS_WEBHOOK'].strip().split('?', 1)[0].rstrip('/')
    identity = response_json(requests.get(webhook, timeout=30), 'Webhook abrufen')
    event_id = event.EVENT['id']
    state = read_state()
    stored_id = str(state.get(event_id) or '')
    channel_id = str(identity['channel_id'])
    webhook_id = str(identity['id'])
    bot = requests.Session()
    bot.headers['Authorization'] = 'Bot ' + os.environ['DISCORD_BOT'].strip()

    if stored_id:
        check = bot.get(f'{API}/channels/{channel_id}/messages/{stored_id}', timeout=30)
        if check.status_code == 404:
            raise RuntimeError('Gespeicherte Eventnachricht wurde gelöscht. Kein neuer Post.')
        msg = response_json(check, 'Gespeicherte Nachricht prüfen')
        if str(msg.get('webhook_id', '')) != webhook_id:
            raise RuntimeError('Gespeicherte Message-ID gehört nicht zum Events-Webhook. Kein Post.')
    else:
        # Nur beim allerersten Veröffentlichen nach einer bestehenden Nachricht suchen.
        # Wenn eine passende Nachricht existiert, lieber abbrechen als doppelt posten.
        before = None
        for _ in range(30):
            params = {'limit': 100}
            if before:
                params['before'] = before
            messages = response_json(bot.get(f'{API}/channels/{channel_id}/messages', params=params, timeout=35), 'Sicherheitsprüfung auf vorhandene Events')
            for message in messages:
                if str(message.get('webhook_id', '')) != webhook_id:
                    continue
                names = {f'{event_id}_banner.png', 'halloween_banner.png'}
                sections = {section['title'] for section in event.EVENT['sections']}
                embeds = message.get('embeds', [])
                if (any(a.get('filename') in names for a in message.get('attachments', []))
                        or any(e.get('title') in sections for e in embeds)
                        or any(n in (e.get('image') or {}).get('url', '') for e in embeds for n in names)
                        or any(event_id in (e.get('footer') or {}).get('text', '') for e in embeds)):
                    raise RuntimeError('Event ist bereits im Kanal vorhanden, aber die gespeicherte ID fehlt. Kein Doppelpost.')
            if len(messages) < 100:
                break
            before = messages[-1]['id']

    current = event.status()
    payload = event.payload(current)
    filename = f'{event_id}_banner.png'
    payload['attachments'] = [{'id': 0, 'filename': filename}]
    files = {
        'payload_json': (None, json.dumps(payload, ensure_ascii=False)),
        'files[0]': (filename, event.banner(current), 'image/png'),
    }
    url = webhook + (f'/messages/{stored_id}' if stored_id else '')
    result = response_json(requests.request('PATCH' if stored_id else 'POST', url,
                                           params={'wait': 'true'}, files=files, timeout=65),
                           'Discord-Nachricht bearbeiten' if stored_id else 'Erstveröffentlichung')
    message_id = str(result['id'])
    if stored_id and message_id != stored_id:
        raise RuntimeError('Discord hat eine unerwartete Nachrichten-ID geliefert.')
    state[event_id] = message_id
    save_state(state)
    print(f'{event_id}: {"BEARBEITET" if stored_id else "ERSTMALIG ERSTELLT"}; ID {message_id}; Status {current}')
    print('Weitere Updates bearbeiten die gespeicherte Nachricht. Kein Häkchen erforderlich.')


if __name__ == '__main__':
    publish(load_event())
