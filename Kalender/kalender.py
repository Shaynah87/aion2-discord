import os
import io
import json
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

# ============================================================
# Nyerk24 · Kalender
# Kompakte Wochenübersicht für Discord
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "kalender.png"
STATE_FILE = BASE_DIR / "kalender_message.json"

WEBHOOK_URL = os.environ.get("KALENDER_WEBHOOK", "").strip()
TIMEZONE = ZoneInfo("Europe/Berlin")

# ----------------------------
# Layout
# ----------------------------
WIDTH = 1500
MARGIN_X = 48
TOP = 42
HEADER_H = 132

NAME_COL_W = 265
DAY_COL_W = (WIDTH - (MARGIN_X * 2) - NAME_COL_W) // 7

ROW_H = 58
SPECIAL_ROW_H = 64
SECTION_GAP = 18
BOTTOM_PAD = 42

AVATAR_SIZE = 34
AVATAR_GAP = 12

# ----------------------------
# Farben
# Farbe = Bedeutung, nicht Person
# ----------------------------
BG = (17, 18, 23)
PANEL = (23, 25, 31)
GRID = (49, 52, 62)
TEXT = (239, 241, 246)
TEXT_MUTED = (153, 158, 171)
WEEKEND_BG = (28, 30, 38)
TODAY_BORDER = (223, 187, 92)

ABSENCE = (132, 94, 194)
MAINTENANCE = (78, 126, 186)
RAID = (184, 72, 86)
MEETING = (184, 139, 65)
EVENT = (68, 149, 131)

AVATAR_BG = (63, 67, 78)
SPECIAL_ICON_BG = (47, 51, 62)

# ----------------------------
# Fonts
# ----------------------------
def font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

FONT_TITLE = font(30, True)
FONT_SUBTITLE = font(18, False)
FONT_DAY = font(18, True)
FONT_DATE = font(14, False)
FONT_NAME = font(18, True)
FONT_SMALL = font(14, False)
FONT_BAR = font(13, True)
FONT_ICON = font(14, True)

# ============================================================
# TESTDATEN
# Später werden diese Daten aus Discord / JSON / Bot-Befehlen
# gespeist. Für den Design-Test bleiben sie bewusst statisch.
# ============================================================

SPECIAL_ROWS = [
    {
        "name": "AION 2",
        "icon": "A2",
        "items": [
            {
                "type": "maintenance",
                "label": "WARTUNG · 08:00–12:00",
                "start_day": 2,   # Mittwoch
                "end_day": 2,
            },
        ],
    },
    {
        "name": "GILDE",
        "icon": "G",
        "items": [
            {
                "type": "raid",
                "label": "RAID · 20:00",
                "start_day": 4,   # Freitag
                "end_day": 4,
            },
            {
                "type": "meeting",
                "label": "TREFFEN · 19:30",
                "start_day": 6,   # Sonntag
                "end_day": 6,
            },
        ],
    },
]

MEMBERS = [
    {
        "name": "Shaynah | Laura",
        "initials": "SL",
        "absence": {
            # bewusst länger als die sichtbare Woche:
            # im Balken steht immer der echte Gesamtzeitraum.
            "start_offset": -7,
            "end_offset": 32,
        },
    },
    {
        "name": "Tom",
        "initials": "T",
        "absence": {
            "start_offset": 1,
            "end_offset": 3,
        },
    },
    {
        "name": "Patrick",
        "initials": "P",
        "absence": {
            "start_offset": 4,
            "end_offset": 6,
        },
    },
    {
        "name": "EinSehrLangerDiscordNameZumTesten",
        "initials": "ED",
        "absence": None,
    },
]

TYPE_COLORS = {
    "maintenance": MAINTENANCE,
    "raid": RAID,
    "meeting": MEETING,
    "event": EVENT,
    "absence": ABSENCE,
}

# ============================================================
# Hilfsfunktionen
# ============================================================

def monday_of_week(dt: datetime) -> datetime:
    return (dt - timedelta(days=dt.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

def fmt_date(dt: datetime) -> str:
    return dt.strftime("%d.%m.")

def week_title(monday: datetime) -> str:
    sunday = monday + timedelta(days=6)
    months = [
        "JANUAR", "FEBRUAR", "MÄRZ", "APRIL", "MAI", "JUNI",
        "JULI", "AUGUST", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DEZEMBER"
    ]
    if monday.month == sunday.month:
        return f"{monday.day:02d}.–{sunday.day:02d}. {months[monday.month - 1]} {monday.year}"
    return (
        f"{monday.day:02d}. {months[monday.month - 1]} – "
        f"{sunday.day:02d}. {months[sunday.month - 1]} {sunday.year}"
    )

def text_width(draw: ImageDraw.ImageDraw, text: str, fnt) -> int:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0]

def ellipsize(draw: ImageDraw.ImageDraw, text: str, fnt, max_width: int) -> str:
    if text_width(draw, text, fnt) <= max_width:
        return text

    suffix = "…"
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        candidate = text[:mid].rstrip() + suffix
        if text_width(draw, candidate, fnt) <= max_width:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + suffix

def rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def draw_identity(draw, y, row_h, name, initials, special=False):
    icon_x = MARGIN_X + 14
    icon_y = y + (row_h - AVATAR_SIZE) // 2
    icon_fill = SPECIAL_ICON_BG if special else AVATAR_BG

    draw.ellipse(
        (icon_x, icon_y, icon_x + AVATAR_SIZE, icon_y + AVATAR_SIZE),
        fill=icon_fill
    )

    tw = text_width(draw, initials, FONT_ICON)
    draw.text(
        (icon_x + (AVATAR_SIZE - tw) / 2, icon_y + 8),
        initials,
        font=FONT_ICON,
        fill=TEXT
    )

    name_x = icon_x + AVATAR_SIZE + AVATAR_GAP
    max_name_w = NAME_COL_W - (name_x - MARGIN_X) - 18
    visible_name = ellipsize(draw, name, FONT_NAME, max_name_w)

    box = draw.textbbox((0, 0), visible_name, font=FONT_NAME)
    th = box[3] - box[1]
    draw.text(
        (name_x, y + (row_h - th) / 2 - 2),
        visible_name,
        font=FONT_NAME,
        fill=TEXT
    )

def bar_x(day_index: int) -> int:
    return MARGIN_X + NAME_COL_W + day_index * DAY_COL_W

def draw_bar(draw, row_y, row_h, start_day, end_day, label, color):
    start_day = max(0, min(6, start_day))
    end_day = max(0, min(6, end_day))
    if end_day < start_day:
        return

    x1 = bar_x(start_day) + 8
    x2 = bar_x(end_day + 1) - 8

    bar_h = 26
    y1 = row_y + (row_h - bar_h) // 2
    y2 = y1 + bar_h

    rounded_rect(draw, (x1, y1, x2, y2), 8, color)

    max_w = max(0, x2 - x1 - 18)
    visible = ellipsize(draw, label, FONT_BAR, max_w)
    if max_w >= 25:
        draw.text((x1 + 9, y1 + 5), visible, font=FONT_BAR, fill=(255, 255, 255))

def draw_absence_bar(draw, row_y, row_h, week_start, absence):
    start_dt = week_start + timedelta(days=absence["start_offset"])
    end_dt = week_start + timedelta(days=absence["end_offset"])

    visible_start = max(start_dt, week_start)
    visible_end = min(end_dt, week_start + timedelta(days=6))

    if visible_end < week_start or visible_start > week_start + timedelta(days=6):
        return

    start_day = (visible_start.date() - week_start.date()).days
    end_day = (visible_end.date() - week_start.date()).days

    label = f"ABWESEND · {fmt_date(start_dt)} – {fmt_date(end_dt)}"

    x1 = bar_x(start_day) + 8
    x2 = bar_x(end_day + 1) - 8
    bar_h = 24
    y1 = row_y + (row_h - bar_h) // 2
    y2 = y1 + bar_h

    rounded_rect(draw, (x1, y1, x2, y2), 8, ABSENCE)

    # Fortsetzungsmarker, falls Abwesenheit außerhalb der sichtbaren Woche weiterläuft.
    if start_dt < week_start:
        draw.polygon(
            [(x1 + 5, (y1 + y2) // 2),
             (x1 + 12, y1 + 5),
             (x1 + 12, y2 - 5)],
            fill=(255, 255, 255)
        )
    if end_dt > week_start + timedelta(days=6):
        draw.polygon(
            [(x2 - 5, (y1 + y2) // 2),
             (x2 - 12, y1 + 5),
             (x2 - 12, y2 - 5)],
            fill=(255, 255, 255)
        )

    text_pad_left = 18 if start_dt < week_start else 9
    text_pad_right = 18 if end_dt > week_start + timedelta(days=6) else 9
    max_w = max(0, x2 - x1 - text_pad_left - text_pad_right)
    visible = ellipsize(draw, label, FONT_BAR, max_w)

    if max_w >= 25:
        draw.text(
            (x1 + text_pad_left, y1 + 4),
            visible,
            font=FONT_BAR,
            fill=(255, 255, 255)
        )

# ============================================================
# Rendering
# ============================================================

def render_calendar():
    now = datetime.now(TIMEZONE)
    week_start = monday_of_week(now)

    total_h = (
        TOP
        + HEADER_H
        + (2 * SPECIAL_ROW_H)
        + SECTION_GAP
        + (len(MEMBERS) * ROW_H)
        + BOTTOM_PAD
    )

    image = Image.new("RGB", (WIDTH, total_h), BG)
    draw = ImageDraw.Draw(image)

    # Header
    draw.text((MARGIN_X, TOP), "WOCHENÜBERSICHT", font=FONT_TITLE, fill=TEXT)
    draw.text(
        (MARGIN_X, TOP + 42),
        week_title(week_start),
        font=FONT_SUBTITLE,
        fill=TEXT_MUTED
    )

    grid_top = TOP + HEADER_H
    special_h_total = len(SPECIAL_ROWS) * SPECIAL_ROW_H
    member_top = grid_top + special_h_total + SECTION_GAP
    grid_bottom = member_top + len(MEMBERS) * ROW_H

    # Hintergrund-Panel
    rounded_rect(
        draw,
        (MARGIN_X, grid_top - 8, WIDTH - MARGIN_X, grid_bottom + 8),
        16,
        PANEL
    )

    # Wochenend-Hinterlegung
    for day in (5, 6):
        x1 = bar_x(day)
        x2 = x1 + DAY_COL_W
        draw.rectangle((x1, grid_top - 8, x2, grid_bottom + 8), fill=WEEKEND_BG)

    # Tag-Kopf
    day_names = ["MO", "DI", "MI", "DO", "FR", "SA", "SO"]
    header_y = grid_top - 70

    for i, day_name in enumerate(day_names):
        day_dt = week_start + timedelta(days=i)
        x = bar_x(i)
        cx = x + DAY_COL_W / 2

        dw = text_width(draw, day_name, FONT_DAY)
        date_txt = day_dt.strftime("%d.%m.")
        date_w = text_width(draw, date_txt, FONT_DATE)

        draw.text((cx - dw / 2, header_y), day_name, font=FONT_DAY, fill=TEXT)
        draw.text((cx - date_w / 2, header_y + 27), date_txt, font=FONT_DATE, fill=TEXT_MUTED)

    # Vertikale Tageslinien
    for i in range(8):
        x = MARGIN_X + NAME_COL_W + i * DAY_COL_W
        draw.line((x, grid_top - 8, x, grid_bottom + 8), fill=GRID, width=1)

    # Aktueller Tag: Rahmen über die komplette sichtbare Kalenderfläche
    if week_start.date() <= now.date() <= (week_start + timedelta(days=6)).date():
        today_idx = now.weekday()
        x1 = bar_x(today_idx) + 2
        x2 = x1 + DAY_COL_W - 4
        draw.rounded_rectangle(
            (x1, grid_top - 8, x2, grid_bottom + 8),
            radius=9,
            outline=TODAY_BORDER,
            width=3
        )

    # AION 2 + GILDE
    y = grid_top
    for row in SPECIAL_ROWS:
        draw_identity(
            draw,
            y,
            SPECIAL_ROW_H,
            row["name"],
            row["icon"],
            special=True
        )

        for item in row["items"]:
            draw_bar(
                draw,
                y,
                SPECIAL_ROW_H,
                item["start_day"],
                item["end_day"],
                item["label"],
                TYPE_COLORS[item["type"]],
            )

        draw.line(
            (MARGIN_X, y + SPECIAL_ROW_H, WIDTH - MARGIN_X, y + SPECIAL_ROW_H),
            fill=GRID,
            width=1
        )
        y += SPECIAL_ROW_H

    # Bereichstrenner
    draw.line(
        (MARGIN_X, y + SECTION_GAP // 2, WIDTH - MARGIN_X, y + SECTION_GAP // 2),
        fill=GRID,
        width=1
    )

    # Member / Abwesenheiten
    y = member_top
    for member in MEMBERS:
        draw_identity(
            draw,
            y,
            ROW_H,
            member["name"],
            member["initials"],
            special=False
        )

        if member.get("absence"):
            draw_absence_bar(
                draw,
                y,
                ROW_H,
                week_start,
                member["absence"]
            )

        draw.line(
            (MARGIN_X, y + ROW_H, WIDTH - MARGIN_X, y + ROW_H),
            fill=GRID,
            width=1
        )
        y += ROW_H

    image.save(OUTPUT_FILE, quality=95)
    print(f"Kalender erstellt: {OUTPUT_FILE}")

# ============================================================
# Discord Webhook
# ============================================================

def load_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_state(data):
    STATE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def multipart_body(payload_json, image_bytes):
    boundary = f"----Nyerk24Boundary{uuid.uuid4().hex}"
    body = io.BytesIO()

    def write_part(headers, content):
        body.write(f"--{boundary}\r\n".encode())
        for key, value in headers.items():
            body.write(f"{key}: {value}\r\n".encode())
        body.write(b"\r\n")
        body.write(content)
        body.write(b"\r\n")

    write_part(
        {
            "Content-Disposition": 'form-data; name="payload_json"',
            "Content-Type": "application/json",
        },
        json.dumps(payload_json).encode("utf-8")
    )

    write_part(
        {
            "Content-Disposition": 'form-data; name="files[0]"; filename="kalender.png"',
            "Content-Type": "image/png",
        },
        image_bytes
    )

    body.write(f"--{boundary}--\r\n".encode())
    return body.getvalue(), boundary

def webhook_request(url, method="POST"):
    payload = {
        "content": "",
        "embeds": [
            {
                "image": {
                    "url": "attachment://kalender.png"
                }
            }
        ],
        "attachments": [
            {
                "id": 0,
                "filename": "kalender.png"
            }
        ]
    }

    image_bytes = OUTPUT_FILE.read_bytes()
    body, boundary = multipart_body(payload, image_bytes)

    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Nyerk24-Kalender/1.0",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8")
        if raw:
            return json.loads(raw)
        return {}

def post_or_update():
    if not WEBHOOK_URL:
        raise RuntimeError("KALENDER_WEBHOOK ist nicht gesetzt.")

    state = load_state()
    message_id = state.get("message_id")

    if message_id:
        edit_url = f"{WEBHOOK_URL}/messages/{message_id}"
        try:
            webhook_request(edit_url, method="PATCH")
            print(f"Discord-Kalender aktualisiert: {message_id}")
            return
        except urllib.error.HTTPError as exc:
            # Wenn die Nachricht manuell in Discord gelöscht wurde,
            # legen wir automatisch eine neue an.
            if exc.code != 404:
                raise
            print("Gespeicherte Discord-Nachricht existiert nicht mehr. Erstelle neue Nachricht.")

    result = webhook_request(f"{WEBHOOK_URL}?wait=true", method="POST")
    new_id = result.get("id")
    if not new_id:
        raise RuntimeError("Discord hat keine message_id zurückgegeben.")

    save_state({"message_id": new_id})
    print(f"Neue Discord-Kalendernachricht erstellt: {new_id}")

# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    render_calendar()
    post_or_update()
