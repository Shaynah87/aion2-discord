"""Nyerk24 Events: Halloween aktualisieren, vier Kategorie-Banner einmalig posten.

Nur EVENTS_WEBHOOK veröffentlicht Bilder. Der Helper wird nicht verändert.
Die Original-PNGs bleiben unverändert; Pillow beschriftet nur Kopien im Speicher.
"""
import importlib.util
import io
import json
import os
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'events_message.json'
API = 'https://discord.com/api/v10'
TIMEOUT = 45

CATEGORIES = (
    ('twitch_drops', 'Twitch Drops', 'Twitch/twitch_drops.png'),
    ('ingame_events', 'Ingame-Events', 'In-Game/ingame_events.png'),
    ('community_events', 'Community-Events', 'Community/community_events.png'),
    ('anwesenheitslisten', 'Anwesenheitslisten', 'Anwesenheit/anwesenheitslisten.png'),
)


def checked(response, context):
    if not response.ok:
        raise RuntimeError(f'{context}: HTTP {response.status_code}: {response.text[:700]}')
    return response.json() if response.content else {}


def read_state():
    if not STATE.exists():
        raise RuntimeError('events_message.json fehlt. Kein automatischer Erstpost.')
    state = json.loads(STATE.read_text(encoding='utf-8'))
    if not isinstance(state, dict):
        raise ValueError('events_message.json muss ein JSON-Objekt sein')
    return state


def save_state(state):
    tmp = STATE.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(STATE)


def load_halloween():
    path = ROOT / 'Halloween' / 'halloween.py'
    spec = importlib.util.spec_from_file_location('nyerk24_halloween', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Halloween-Modul fehlt: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def font(size):
    for path in (
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
    ):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    raise RuntimeError('DejaVuSans-Bold oder LiberationSans-Bold fehlt')


def category_banner(relative_path, title):
    path = ROOT / relative_path
    if not path.is_file():
        raise FileNotFoundError(f'Banner fehlt: {path}')
    with Image.open(path) as source:
        if source.size != (1200, 65):
            raise ValueError(f'{relative_path}: erwartet 1200×65, gefunden {source.size}')
        base = source.convert('RGBA')

    # Titel bleibt innerhalb der ruhigen mittleren 60 %.
    draw = ImageDraw.Draw(base)
    for size in range(42, 19, -1):
        face = font(size)
        bbox = draw.textbbox((0, 0), title, font=face, stroke_width=1)
        if bbox[2] - bbox[0] <= 660 and bbox[3] - bbox[1] <= 51:
            break
    else:
        raise ValueError(f'Überschrift zu lang: {title}')

    center_x, center_y = 600, 32.5
    bbox = draw.textbbox((0, 0), title, font=face, stroke_width=1)
    x = center_x - (bbox[0] + bbox[2]) / 2
    y = center_y - (bbox[1] + bbox[3]) / 2

    # Sehr dezenter Schatten für gute Lesbarkeit auf allen vier Farben.
    mask = Image.new('L', base.size, 0)
    md = ImageDraw.Draw(mask)
    md.text((round(x), round(y)), title, font=face, fill=255)
    shadow = Image.new('RGBA', base.size, (0, 0, 0, 0))
    alpha = mask.filter(ImageFilter.GaussianBlur(3)).point(lambda a: min(255, int(a * 0.75)))
    shadow.putalpha(alpha)
    base = Image.alpha_composite(base, shadow)
    draw = ImageDraw.Draw(base)
    draw.text((round(x), round(y)), title, font=face, fill=(248, 247, 250, 255),
              stroke_width=1, stroke_fill=(12, 10, 18, 255))

    out = io.BytesIO()
    base.convert('RGB').save(out, format='PNG', optimize=True)
    return out.getvalue()


def get_message(bot, channel, message_id):
    response = bot.get(f'{API}/channels/{channel}/messages/{message_id}', timeout=TIMEOUT)
    if response.status_code == 404:
        return None
    return checked(response, 'Nachricht prüfen')


def verify_webhook_message(bot, channel, webhook_id, message_id):
    msg = get_message(bot, channel, message_id)
    if msg is None:
        raise RuntimeError(f'Gespeicherte Nachricht {message_id} fehlt. Kein Doppelpost.')
    if str(msg.get('webhook_id') or '') != webhook_id:
        raise RuntimeError(f'Nachricht {message_id} gehört nicht zum Events-Webhook')
    return msg


def find_existing_filename(bot, channel, webhook_id, filename):
    """Vor Erstpost nach bestehendem Bild suchen, falls JSON-ID fehlt."""
    before = None
    for _ in range(30):
        params = {'limit': 100}
        if before:
            params['before'] = before
        messages = checked(bot.get(f'{API}/channels/{channel}/messages', params=params,
                                   timeout=TIMEOUT), 'Vorhandene Events prüfen')
        for msg in messages:
            if str(msg.get('webhook_id') or '') != webhook_id:
                continue
            if any(a.get('filename') == filename for a in msg.get('attachments', [])):
                raise RuntimeError(f'{filename} ist bereits in Discord, aber ohne gespeicherte ID. '
                                   'Kein Doppelpost; bitte ID nachtragen.')
        if len(messages) < 100:
            return
        before = messages[-1]['id']
    # We cannot prove there is no older copy: fail closed.
    raise RuntimeError(f'Kanalhistorie zu lang, Erstpost von {filename} nicht sicher')


def upload(webhook, message_id, filename, data):
    payload = {
        'content': '', 'embeds': [], 'components': [],
        'attachments': [{'id': 0, 'filename': filename}],
        'allowed_mentions': {'parse': []},
    }
    files = {
        'payload_json': (None, json.dumps(payload, ensure_ascii=False)),
        'files[0]': (filename, data, 'image/png'),
    }
    if message_id:
        url = f'{webhook}/messages/{message_id}'
        result = checked(requests.patch(url, files=files, timeout=70), 'Banner aktualisieren')
    else:
        result = checked(requests.post(webhook, params={'wait': 'true'}, files=files,
                                       timeout=70), 'Banner veröffentlichen')
    if not result.get('id'):
        raise RuntimeError('Discord lieferte keine Nachrichten-ID')
    if message_id and str(result['id']) != str(message_id):
        raise RuntimeError('Discord lieferte unerwartete Nachrichten-ID')
    return str(result['id'])


def main():
    state = read_state()
    webhook = os.environ['EVENTS_WEBHOOK'].strip().split('?', 1)[0].rstrip('/')
    identity = checked(requests.get(webhook, timeout=TIMEOUT), 'Events-Webhook prüfen')
    channel, webhook_id = str(identity['channel_id']), str(identity['id'])
    bot = requests.Session()
    bot.headers.update({'Authorization': 'Bot ' + os.environ['DISCORD_BOT'].strip()})

    # Halloween bleibt 1200x180 mit Schrift/Datum/Status im Bild.
    halloween = load_halloween()
    halloween_record = state.get('halloween_2026')
    if not isinstance(halloween_record, dict):
        raise RuntimeError('Halloween-State fehlt. Keine neue Halloween-Nachricht erstellen.')
    halloween_id = str(halloween_record.get('webhook_message_id') or '')
    if not halloween_id:
        raise RuntimeError('webhook_message_id für Halloween fehlt. Kein Doppelpost.')
    verify_webhook_message(bot, channel, webhook_id, halloween_id)
    halloween_data = halloween.banner(halloween.status())
    with Image.open(io.BytesIO(halloween_data)) as im:
        if im.size != (1200, 180):
            raise ValueError(f'Halloween muss 1200×180 bleiben, ist {im.size}')
    upload(webhook, halloween_id, 'halloween_2026_banner.png', halloween_data)
    print(f'Halloween unverändert aktualisiert: {halloween_id}')

    # Vier Kategorie-Überschriften, keine Helper-Buttons und keine Eventdetails.
    for key, title, relative_path in CATEGORIES:
        filename = f'{key}_banner.png'
        data = category_banner(relative_path, title)
        record = state.get(key)
        if record is not None and not isinstance(record, dict):
            raise ValueError(f'State für {key} muss ein Objekt sein')
        record = record or {}
        message_id = str(record.get('webhook_message_id') or '')
        if message_id:
            verify_webhook_message(bot, channel, webhook_id, message_id)
            print(f'{title}: bestehende Nachricht aktualisieren')
        else:
            find_existing_filename(bot, channel, webhook_id, filename)
            print(f'{title}: erste Veröffentlichung')
        new_id = upload(webhook, message_id, filename, data)
        state[key] = {'webhook_message_id': new_id}
        save_state(state)  # Jede ID sofort sichern, auch wenn später ein Fehler auftritt.
        print(f'{title}: {new_id}')

    print('Fertig. Helper-Nachricht und Halloween-Detailbutton unverändert.')


if __name__ == '__main__':
    main()
