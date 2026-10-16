
"""Discord Events: one persistent message per event, no message-ID JSON.
Uses existing DISCORD_BOT and EVENTS_WEBHOOK GitHub Actions secrets.
The existing Cloudflare Helper must handle custom_id 'event:details:halloween_2026'.
"""
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'Halloween'))
from halloween import EVENT, status

API = 'https://discord.com/api/v10'
TOKEN = os.environ['DISCORD_BOT']
WEBHOOK = os.environ['EVENTS_WEBHOOK'].rstrip('/')
webhook_info = requests.get(WEBHOOK, timeout=20)
if not webhook_info.ok:
    raise RuntimeError(f'Events webhook validation failed: HTTP {webhook_info.status_code}')
CHANNEL = webhook_info.json().get('channel_id')
if not CHANNEL:
    raise RuntimeError('Events webhook does not contain channel_id')
HEADERS = {'Authorization': f'Bot {TOKEN}'}
MARKER = f'event-id:{EVENT["id"]}'


def font(size, bold=False):
    candidates = ([
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
    ] if bold else [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
    ])
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def banner(current):
    width, height = 1200, 535 if current == 'upcoming' else 220
    source = Image.open(ROOT / 'Halloween' / 'halloween.png').convert('RGB')
    scale = max(width / source.width, height / source.height)
    resized = source.resize((round(source.width * scale), round(source.height * scale)), Image.Resampling.LANCZOS)
    x = (resized.width - width) // 2
    y = (resized.height - height) // 2
    base = resized.crop((x, y, x + width, y + height)).convert('RGBA')
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 115))
    base = Image.alpha_composite(base, overlay).convert('RGB')
    draw = ImageDraw.Draw(base)
    labels = {'upcoming': 'BALD VERFÜGBAR', 'active': 'GESTARTET', 'finished': 'BEENDET'}
    lines = [
        (EVENT['name'].upper(), 64 if height == 535 else 48, True),
        (EVENT['date_label'], 34 if height == 535 else 27, False),
        (f'• {labels[current]}', 39 if height == 535 else 30, True),
    ]
    fonts = [font(size, bold) for _, size, bold in lines]
    boxes = [draw.textbbox((0, 0), text, font=f) for (text, _, _), f in zip(lines, fonts)]
    spacing = 18 if height == 535 else 9
    total = sum(b[3] - b[1] for b in boxes) + spacing * 2
    yy = (height - total) // 2
    for (text, _, _), f, b in zip(lines, fonts, boxes):
        tw = draw.textlength(text, font=f)
        draw.text(((width - tw) / 2, yy - b[1]), text, font=f, fill='white', stroke_width=2, stroke_fill='#1c1021')
        yy += b[3] - b[1] + spacing
    out = io.BytesIO()
    base.save(out, format='PNG', optimize=True)
    return out.getvalue()


def format_entry(entry):
    if 'days' in entry:
        return f'**Tag {entry["days"]}:** {entry["coins_per_day"]} Münzen pro Tag'
    name = entry.get('name', '')
    if 'task' in entry:
        return f'**{name}:** {entry["task"]} — **{entry["coins"]}** Münzen'
    if 'price' in entry:
        return f'**{name}:** {entry["price"]} Münzen · {entry["limit"]}'
    if 'fragments' in entry:
        return f'**{name} ×{entry["quantity"]}:** {entry["fragments"]} Fragmente'
    if 'effects' in entry:
        return f'**{name}** ({entry["duration"]}): ' + ', '.join(entry['effects'])
    return f'**{name}** ×{entry.get("quantity", 1):,}'.replace(',', '.')


def section_embeds():
    result = []
    for section in EVENT['sections']:
        parts = []
        if section.get('description'):
            parts.append(section['description'])
        parts.extend(format_entry(entry) for entry in section['entries'])
        description = '\n'.join(parts)
        if len(description) > 4096:
            raise ValueError(f'Abschnitt zu lang: {section["title"]}')
        result.append({'title': section['title'], 'description': description, 'color': 0x7154AA})
    return result


def message_payload(current):
    heading = {'upcoming': 'Beginnt demnächst', 'active': 'Jetzt aktiv', 'finished': 'Event beendet'}[current]
    embeds = [{'title': f'🎃 {EVENT["name"]} · {heading}',
               'description': f'**{EVENT["date_label"]}**' + ('\nAlle Eventinformationen findest du unten.' if current == 'active' else '\nKlicke auf **Details anzeigen**, um die Informationen privat zu öffnen.'),
               'color': 0x7154AA,
               'image': {'url': 'attachment://halloween_banner.png'},
               'footer': {'text': MARKER}}]
    if current == 'active':
        embeds.extend(section_embeds())
    if len(embeds) > 10:
        raise ValueError('Discord erlaubt maximal 10 Embeds pro Nachricht')
    payload = {'embeds': embeds, 'allowed_mentions': {'parse': []}}
    if current != 'active':
        payload['components'] = [{'type': 1, 'components': [{
            'type': 2, 'style': 2, 'label': 'Details anzeigen',
            'custom_id': f'event:details:{EVENT["id"]}'
        }]}]
    else:
        payload['components'] = []
    return payload


def request(method, path, **kwargs):
    response = requests.request(method, API + path, headers=HEADERS, timeout=35, **kwargs)
    if not response.ok:
        raise RuntimeError(f'Discord API {response.status_code}: {response.text[:1000]}')
    return response.json() if response.content else None


def find_existing():
    before = None
    for _ in range(10):  # Search up to 1000 recent messages
        params = {'limit': 100}
        if before:
            params['before'] = before
        messages = request('GET', f'/channels/{CHANNEL}/messages', params=params)
        if not messages:
            break
        for msg in messages:
            if any(embed.get('footer', {}).get('text') == MARKER for embed in msg.get('embeds', [])):
                return msg['id']
        before = messages[-1]['id']
    return None


def publish():
    current = status()
    payload = message_payload(current)
    existing = find_existing()
    # On editing, retain only the newly uploaded banner attachment.
    payload['attachments'] = [{'id': 0, 'filename': 'halloween_banner.png'}]
    multipart = {'payload_json': (None, json.dumps(payload, ensure_ascii=False)),
                 'files[0]': ('halloween_banner.png', banner(current), 'image/png')}
    if existing:
        result = request('PATCH', f'/channels/{CHANNEL}/messages/{existing}', files=multipart)
        print(f'Updated Halloween message {result["id"]}: {current}')
    else:
        result = request('POST', f'/channels/{CHANNEL}/messages', files=multipart)
        print(f'Created Halloween message {result["id"]}: {current}')


if __name__ == '__main__':
    publish()
