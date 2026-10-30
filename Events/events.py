"""Nyerk24 Events: Halloween image by EVENTS_WEBHOOK, detail button by Helper.

Preserves existing message IDs. Migrates the existing Events embed to a plain
image attachment; places the Helper button below the image exactly once.
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


def checked(response, context):
    if not response.ok:
        raise RuntimeError(f'{context}: HTTP {response.status_code}: {response.text[:800]}')
    return response.json() if response.content else {}


def load_event():
    path = ROOT / 'Halloween' / 'halloween.py'
    spec = importlib.util.spec_from_file_location('nyerk24_halloween', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Eventmodul fehlt: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_state():
    if not STATE.is_file():
        raise RuntimeError('events_message.json fehlt: keine automatische Neuanlage')
    state = json.loads(STATE.read_text(encoding='utf-8'))
    if not isinstance(state, dict):
        raise RuntimeError('events_message.json ist kein Objekt')
    return state


def save_state(state):
    tmp = STATE.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    tmp.replace(STATE)


def get_message(bot, channel, message_id):
    response = bot.get(f'{API}/channels/{channel}/messages/{message_id}', timeout=TIMEOUT)
    if response.status_code == 404:
        return None
    return checked(response, 'Discord-Nachricht abrufen')


def verify_owner(message, owner, bot_user_id=None, webhook_id=None):
    if message is None:
        raise RuntimeError(f'{owner}-Nachricht fehlt. Kein neuer Beitrag.')
    if owner == 'webhook':
        if str(message.get('webhook_id') or '') != str(webhook_id):
            raise RuntimeError('Events-Beitrag gehört nicht zu EVENTS_WEBHOOK')
    else:
        if message.get('webhook_id') or str(message.get('author', {}).get('id')) != str(bot_user_id):
            raise RuntimeError('Helper-Nachricht gehört nicht zum Helper-Bot')


def upload_plain_banner(webhook, event, current, message_id):
    data = event.banner(current)
    with Image.open(io.BytesIO(data)) as im:
        if im.size != (1200, 180):
            raise ValueError(f'Halloween muss 1200×180 sein; ist {im.size}')
    filename = f'{EVENT_ID}_banner.png'
    # A normal image attachment, NOT an embed (no orange side stripe).
    payload = {
        'content': '', 'embeds': [], 'components': [],
        'attachments': [{'id': 0, 'filename': filename}],
        'allowed_mentions': {'parse': []},
    }
    files = {
        'payload_json': (None, json.dumps(payload, ensure_ascii=False)),
        'files[0]': (filename, data, 'image/png'),
    }
    result = checked(requests.patch(f'{webhook}/messages/{message_id}', files=files, timeout=70),
                     'Events-Banner aktualisieren')
    if str(result.get('id')) != message_id:
        raise RuntimeError('Discord lieferte eine unerwartete Nachrichten-ID')


def button_payload():
    return {
        'content': '', 'embeds': [], 'attachments': [],
        'components': [{'type': 1, 'components': [{
            'type': 2, 'style': 1, 'label': '🎃 Eventdetails anzeigen',
            'custom_id': BUTTON_ID,
        }]}],
        'allowed_mentions': {'parse': []},
    }


def main():
    event = load_event()
    if event.EVENT['id'] != EVENT_ID:
        raise RuntimeError('Falsche Event-ID')
    state = read_state()
    record = state.get(EVENT_ID)
    if not isinstance(record, dict):
        raise RuntimeError('Eventzustand muss ein Objekt sein')
    webhook_id_msg = str(record.get('webhook_message_id') or record.get('message_id') or '')
    helper_id_msg = str(record.get('helper_message_id') or '')
    if not webhook_id_msg:
        raise RuntimeError('Events-Nachrichten-ID fehlt; kein automatischer Doppelpost')

    webhook = os.environ['EVENTS_WEBHOOK'].strip().split('?', 1)[0].rstrip('/')
    identity = checked(requests.get(webhook, timeout=TIMEOUT), 'Webhook prüfen')
    channel, webhook_id = str(identity['channel_id']), str(identity['id'])
    bot = requests.Session()
    bot.headers.update({'Authorization': 'Bot ' + os.environ['DISCORD_BOT'].strip()})
    bot_user_id = str(checked(bot.get(f'{API}/users/@me', timeout=TIMEOUT), 'Helper prüfen')['id'])

    event_message = get_message(bot, channel, webhook_id_msg)
    verify_owner(event_message, 'webhook', webhook_id=webhook_id)
    if not helper_id_msg:
        raise RuntimeError('Helper-Nachrichten-ID fehlt. Bitte aktuellen events_message.json-Inhalt prüfen.')
    old_helper = get_message(bot, channel, helper_id_msg)
    verify_owner(old_helper, 'bot', bot_user_id=bot_user_id)

    # Keep same Events message ID and remove the colored embed border.
    upload_plain_banner(webhook, event, event.status(), webhook_id_msg)
    print(f'Events-Bild aktualisiert: {webhook_id_msg}')

    # Discord messages are chronological. Move button ONLY when above banner.
    if int(helper_id_msg) < int(webhook_id_msg):
        new_helper = checked(bot.post(f'{API}/channels/{channel}/messages', json=button_payload(), timeout=TIMEOUT),
                             'Helper-Button unter Banner veröffentlichen')
        new_id = str(new_helper['id'])
        record['helper_message_id'] = new_id
        record['webhook_message_id'] = webhook_id_msg
        record['message_id'] = webhook_id_msg
        state[EVENT_ID] = record
        save_state(state)
        print(f'Neuer Helper-Button unter dem Banner: {new_id}')
        # Delete old button after new button has been posted and ID saved.
        response = bot.delete(f'{API}/channels/{channel}/messages/{helper_id_msg}', timeout=TIMEOUT)
        if response.status_code not in (204, 404):
            raise RuntimeError(f'Alter Helper-Button konnte nicht gelöscht werden (HTTP {response.status_code}). '
                               'Bitte alte Nachricht manuell entfernen; neue ID ist bereits gespeichert.')
        print('Alter Helper-Button entfernt')
    else:
        # Existing button already follows the banner; don't create duplicates.
        checked(bot.patch(f'{API}/channels/{channel}/messages/{helper_id_msg}', json=button_payload(), timeout=TIMEOUT),
                'Helper-Button aktualisieren')
        print('Helper-Button bleibt unter dem Banner')

    record['message_id'] = webhook_id_msg
    record['webhook_message_id'] = webhook_id_msg
    state[EVENT_ID] = record
    save_state(state)
    print('Fertig: Events-Bild ohne Embed-Rahmen, Helper-Button darunter')


if __name__ == '__main__':
    main()
