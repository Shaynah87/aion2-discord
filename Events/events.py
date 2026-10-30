"""Nyerk24 Events: Halloween via EVENTS_WEBHOOK; Helper owns detail button.

Safe one-time migration: first create/save the webhook post, then turn the
existing Helper post into a button-only control. Never delete it automatically.
"""
import importlib.util
import io
import json
import os
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'events_message.json'
API = 'https://discord.com/api/v10'
EVENT_ID = 'halloween_2026'
BUTTON_ID = 'event:details:halloween_2026'
TIMEOUT = 45


def load_event():
    path = ROOT / 'Halloween' / 'halloween.py'
    spec = importlib.util.spec_from_file_location('nyerk24_halloween', path)
    if not spec or not spec.loader:
        raise RuntimeError(f'Eventmodul nicht gefunden: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checked(response, context):
    if not response.ok:
        raise RuntimeError(f'{context}: HTTP {response.status_code}: {response.text[:800]}')
    return response.json() if response.content else {}


def read_state():
    if not STATE.exists():
        raise RuntimeError('events_message.json fehlt. Aus Sicherheitsgründen kein Erstpost.')
    value = json.loads(STATE.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise RuntimeError('events_message.json muss ein Objekt sein')
    return value


def save_state(value):
    tmp = STATE.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(STATE)


def bot_client():
    token = os.environ['DISCORD_BOT'].strip()
    client = requests.Session()
    client.headers.update({'Authorization': f'Bot {token}'})
    return client


def webhook_url():
    return os.environ['EVENTS_WEBHOOK'].strip().split('?', 1)[0].rstrip('/')


def message(bot, channel_id, message_id):
    response = bot.get(f'{API}/channels/{channel_id}/messages/{message_id}', timeout=TIMEOUT)
    if response.status_code == 404:
        return None
    return checked(response, 'Nachricht prüfen')


def webhook_payload(event):
    # No extra public title/description: all information is already on the banner.
    filename = f'{EVENT_ID}_banner.png'
    return {'embeds': [{'color': 0xFF7100, 'image': {'url': f'attachment://{filename}'}}],
            'allowed_mentions': {'parse': []}}, filename


def send_webhook(url, event, current, message_id=None):
    banner = event.banner(current)
    with Image.open(io.BytesIO(banner)) as img:
        if img.size != (1200, 180):
            raise ValueError(f'Halloween-Banner muss 1200×180 sein, ist {img.size}')
    payload, filename = webhook_payload(event)
    # For edits Discord requires the attachment entry to preserve/replace image.
    payload['attachments'] = [{'id': 0, 'filename': filename}]
    target = f'{url}/messages/{message_id}' if message_id else url
    params = None if message_id else {'wait': 'true'}
    files = {
        'payload_json': (None, json.dumps(payload, ensure_ascii=False)),
        'files[0]': (filename, banner, 'image/png'),
    }
    method = 'PATCH' if message_id else 'POST'
    result = checked(requests.request(method, target, params=params, files=files, timeout=70),
                     'Events-Webhook aktualisieren' if message_id else 'Events-Webhook veröffentlichen')
    if not result.get('id'):
        raise RuntimeError('Discord lieferte keine Nachrichten-ID')
    return str(result['id'])


def helper_button_only(bot, channel_id, message_id):
    old = message(bot, channel_id, message_id)
    if old is None:
        raise RuntimeError('Die alte Helper-Nachricht wurde nicht gefunden. Keine automatische Neuanlage.')
    if old.get('webhook_id'):
        raise RuntimeError('Die gespeicherte Helper-ID gehört zu einem Webhook; keine Bearbeitung.')
    me = checked(bot.get(f'{API}/users/@me', timeout=TIMEOUT), 'Helper-Identität')
    if str(old.get('author', {}).get('id')) != str(me['id']):
        raise RuntimeError('Helper-Nachricht gehört nicht zu DISCORD_BOT; keine Bearbeitung.')
    payload = {
        'content': '', 'embeds': [], 'attachments': [],
        'components': [{'type': 1, 'components': [{
            'type': 2, 'style': 1, 'label': '🎃 Eventdetails anzeigen', 'custom_id': BUTTON_ID
        }]}], 'allowed_mentions': {'parse': []},
    }
    checked(bot.patch(f'{API}/channels/{channel_id}/messages/{message_id}', json=payload, timeout=TIMEOUT),
            'Helper-Nachricht auf Button reduzieren')


def publish():
    event = load_event()
    if event.EVENT['id'] != EVENT_ID:
        raise RuntimeError('Unerwartete Event-ID')
    current = event.status()
    state = read_state()
    record = state.get(EVENT_ID)
    if not isinstance(record, dict) or not record.get('message_id'):
        raise RuntimeError('Bestehende Nachrichten-ID fehlt; kein Doppelpost.')
    webhook = webhook_url()
    identity = checked(requests.get(webhook, timeout=TIMEOUT), 'Events-Webhook prüfen')
    channel_id = str(identity['channel_id'])
    webhook_id = str(identity['id'])
    bot = bot_client()

    webhook_msg_id = str(record.get('webhook_message_id') or '')
    helper_msg_id = str(record.get('helper_message_id') or '')
    legacy_id = str(record['message_id'])

    if not webhook_msg_id:
        existing = message(bot, channel_id, legacy_id)
        if existing is None:
            raise RuntimeError('Alte Nachricht fehlt; kein neuer Post.')
        if str(existing.get('webhook_id') or '') == webhook_id:
            # Legacy state already points at an Events webhook message.
            webhook_msg_id = legacy_id
        elif existing.get('webhook_id'):
            raise RuntimeError('Alte Nachricht gehört zu einem fremden Webhook.')
        else:
            me = checked(bot.get(f'{API}/users/@me', timeout=TIMEOUT), 'Bot-Identität prüfen')
            if str(existing.get('author', {}).get('id')) != str(me['id']):
                raise RuntimeError('Alte Nachricht gehört nicht zum Helper.')
            helper_msg_id = legacy_id

    if webhook_msg_id:
        existing_webhook = message(bot, channel_id, webhook_msg_id)
        if existing_webhook is None:
            raise RuntimeError('Gespeicherter Webhook-Beitrag fehlt; kein automatischer Doppelpost.')
        if str(existing_webhook.get('webhook_id') or '') != webhook_id:
            raise RuntimeError('Gespeicherte Webhook-ID gehört nicht zu EVENTS_WEBHOOK.')
        result_id = send_webhook(webhook, event, current, webhook_msg_id)
        if result_id != webhook_msg_id:
            raise RuntimeError('Unerwartete Nachrichten-ID nach Webhook-Update')
        print(f'{EVENT_ID}: Events-Beitrag aktualisiert ({webhook_msg_id})')
    else:
        # The only new post during migration. Save ID before editing the Helper.
        webhook_msg_id = send_webhook(webhook, event, current)
        state[EVENT_ID] = {'message_id': webhook_msg_id,
                           'webhook_message_id': webhook_msg_id,
                           'helper_message_id': helper_msg_id,
                           'old_webhook_message_id': ''}
        save_state(state)
        print(f'{EVENT_ID}: Events-Beitrag erstellt ({webhook_msg_id})')

    if helper_msg_id:
        helper_button_only(bot, channel_id, helper_msg_id)
        print(f'{EVENT_ID}: Helper auf Detailbutton reduziert ({helper_msg_id})')

    state[EVENT_ID] = {'message_id': webhook_msg_id,
                       'webhook_message_id': webhook_msg_id,
                       'helper_message_id': helper_msg_id,
                       'old_webhook_message_id': ''}
    save_state(state)
    print(f'{EVENT_ID}: fertig, Status {current}')


if __name__ == '__main__':
    publish()
