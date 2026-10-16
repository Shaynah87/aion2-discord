
"""Nyerk24 Events – Halloween-Veröffentlichung.
Bestehender Discord-Bot DISCORD_BOT und EVENTS_WEBHOOK; keine neuen Secrets.
Aktiv: alle Eventinformationen öffentlich. Davor/danach: privater Detailbutton.
Eine bestehende Eventnachricht wird anhand des Markers aktualisiert.
"""
import io
import json
import os
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Halloween"))
from halloween import EVENT, status

API = "https://discord.com/api/v10"
TOKEN = os.environ["DISCORD_BOT"].strip()
WEBHOOK = os.environ["EVENTS_WEBHOOK"].strip().rstrip("/")
SESSION = requests.Session()
SESSION.headers.update({"Authorization": f"Bot {TOKEN}"})
MARKER = f'event-id:{EVENT["id"]}'


def api(method, path, **kwargs):
    response = SESSION.request(method, API + path, timeout=35, **kwargs)
    if not response.ok:
        raise RuntimeError(f"Discord API {response.status_code}: {response.text[:1000]}")
    return response.json() if response.content else None


def channel_id():
    # Der vorhandene Events-Webhook liefert die Kanal-ID, kein neues Secret nötig.
    response = requests.get(WEBHOOK, timeout=20)
    response.raise_for_status()
    value = response.json().get("channel_id")
    if not value:
        raise RuntimeError("EVENTS_WEBHOOK enthält keine channel_id")
    return value


def font(size, bold=True):
    choices = ([
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ] if bold else [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ])
    for path in choices:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def banner(current):
    # Identisches Bannerformat bei allen Status, angelehnt an die Content-Header.
    width, height = 1200, 220
    source = Image.open(ROOT / "Halloween" / "halloween.png").convert("RGB")
    factor = max(width / source.width, height / source.height)
    source = source.resize((round(source.width * factor), round(source.height * factor)), Image.Resampling.LANCZOS)
    left = (source.width - width) // 2
    top = (source.height - height) // 2
    base = source.crop((left, top, left + width, top + height)).convert("RGBA")

    # Lesbarkeit: sanfter dunkler Mittelbereich, ohne die Randmotive zu verdecken.
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    alpha = Image.new("L", (width, height), 0)
    px = alpha.load()
    for x in range(width):
        strength = max(0.0, 1.0 - abs(x - width / 2) / (width * 0.43))
        value = int(135 * (strength ** 0.65))
        for y in range(height):
            px[x, y] = value
    overlay.putalpha(alpha.filter(ImageFilter.GaussianBlur(22)))
    base = Image.alpha_composite(base, overlay)

    labels = {"upcoming": "BALD VERFÜGBAR", "active": "GESTARTET", "finished": "BEENDET"}
    title = EVENT["name"].upper()
    subtitle = f'{EVENT["date_label"]} · {labels[current]}'
    draw = ImageDraw.Draw(base)
    title_font = font(57)
    subtitle_font = font(31)
    title_box = draw.textbbox((0, 0), title, font=title_font, stroke_width=2)
    sub_box = draw.textbbox((0, 0), subtitle, font=subtitle_font, stroke_width=1)
    title_height = title_box[3] - title_box[1]
    sub_height = sub_box[3] - sub_box[1]
    gap = 15
    top_y = (height - title_height - gap - sub_height) / 2

    def centered(text, fnt, y, color, stroke, stroke_width):
        box = draw.textbbox((0, 0), text, font=fnt, stroke_width=stroke_width)
        text_width = draw.textlength(text, font=fnt)
        x = (width - text_width) / 2
        draw.text((x, y - box[1]), text, font=fnt, fill=color,
                  stroke_width=stroke_width, stroke_fill=stroke)

    # Kürbisgold und warmes Creme – hohe Lesbarkeit auch im Discord-Miniaturformat.
    centered(title, title_font, top_y, "#FFC46A", "#271327", 3)
    centered(subtitle, subtitle_font, top_y + title_height + gap,
             "#FFE1A5", "#241123", 2)
    result = io.BytesIO()
    base.convert("RGB").save(result, format="PNG", optimize=True)
    return result.getvalue()


def entry_line(entry):
    if "days" in entry:
        return f'**Tag {entry["days"]}:** {entry["coins_per_day"]} Münzen pro Tag'
    name = entry.get("name", "")
    if "task" in entry:
        return f'**{name}:** {entry["task"]} — **{entry["coins"]}** Münzen'
    if "price" in entry:
        return f'**{name}:** {entry["price"]} Münzen · {entry["limit"]}'
    if "fragments" in entry:
        return f'**{name} ×{entry["quantity"]}:** {entry["fragments"]} Fragmente'
    if "effects" in entry:
        return f'**{name}** ({entry["duration"]}): ' + ", ".join(entry["effects"])
    return f'**{name}** ×{entry.get("quantity", 1):,}'.replace(",", ".")


def detail_embeds():
    embeds = []
    for section in EVENT["sections"]:
        lines = []
        if section.get("description"):
            lines.append(section["description"])
        lines.extend(entry_line(entry) for entry in section["entries"])
        description = "\n".join(lines)
        if len(description) > 4096:
            raise ValueError(f'Eventabschnitt zu lang: {section["title"]}')
        embeds.append({"title": section["title"], "description": description,
                       "color": 0x9852B8})
    return embeds


def payload(current):
    # Nur Bild im ersten Embed: keine doppelte Titel-/Datumsanzeige.
    embeds = [{"image": {"url": "attachment://halloween_banner.png"},
               "color": 0x9852B8, "footer": {"text": MARKER}}]
    if current == "active":
        embeds.extend(detail_embeds())
    if len(embeds) > 10:
        raise ValueError("Discord erlaubt maximal 10 Embeds je Nachricht")
    data = {"embeds": embeds, "allowed_mentions": {"parse": []}, "components": []}
    if current != "active":
        data["components"] = [{"type": 1, "components": [{
            "type": 2, "style": 2, "label": "Eventdetails anzeigen",
            "custom_id": f'event:details:{EVENT["id"]}'
        }]}]
    return data


def existing_message(channel):
    before = None
    for _ in range(10):
        params = {"limit": 100}
        if before:
            params["before"] = before
        messages = api("GET", f"/channels/{channel}/messages", params=params)
        if not messages:
            return None
        for msg in messages:
            if any(embed.get("footer", {}).get("text") == MARKER for embed in msg.get("embeds", [])):
                return msg["id"]
        before = messages[-1]["id"]
    return None


def publish():
    current = status()
    channel = channel_id()
    data = payload(current)
    message_id = existing_message(channel)
    data["attachments"] = [{"id": 0, "filename": "halloween_banner.png"}]
    files = {
        "payload_json": (None, json.dumps(data, ensure_ascii=False)),
        "files[0]": ("halloween_banner.png", banner(current), "image/png"),
    }
    if message_id:
        result = api("PATCH", f"/channels/{channel}/messages/{message_id}", files=files)
        print(f'Event aktualisiert: {result["id"]} ({current})')
    else:
        result = api("POST", f"/channels/{channel}/messages", files=files)
        print(f'Event veröffentlicht: {result["id"]} ({current})')


if __name__ == "__main__":
    publish()
