"""Discord Events: one persistent message per event, no message-ID JSON.
Requires EVENTS_BOT_TOKEN and EVENTS_CHANNEL_ID (GitHub Actions secrets).
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
TOKEN = os.environ['EVENTS_BOT_TOKEN']
CHANNEL = os.environ['EVENTS_CHANNEL_ID']
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

