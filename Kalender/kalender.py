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
# Nyerk24 · Kalender V5
# Desktop-first Wochenübersicht mit guter Mobile-Tauglichkeit
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "kalender.png"
STATE_FILE = BASE_DIR / "kalender_message.json"

WEBHOOK_URL = os.environ.get("KALENDER_WEBHOOK", "").strip()
TIMEZONE = ZoneInfo("Europe/Berlin")

# ------------------------------------------------------------
# Logische Zielgröße
# Intern wird mit 2x Auflösung gerendert und anschließend sauber
# auf Zielgröße verkleinert -> deutlich schärfere Kanten/Schrift.
# ------------------------------------------------------------

SCALE = 2

WIDTH = 1200
MARGIN_X = 34
TOP = 34
HEADER_H = 116

NAME_COL_W = 220
DAY_COL_W = (WIDTH - (MARGIN_X * 2) - NAME_COL_W) // 7

ROW_H = 56
SPECIAL_ROW_H = 60
SECTION_GAP = 16
BOTTOM_PAD = 34

ICON_SIZE = 30
ICON_GAP = 10

def S(value):
    return int(round(value * SCALE))

# ------------------------------------------------------------
# Farben
# ------------------------------------------------------------

BG = (17, 18, 23)
PANEL = (23, 25, 31)
GRID = (49, 52, 62)
TEXT = (239, 241, 246)
TEXT_MUTED = (153, 158, 171)

WEEKEND_BG = (24, 38, 42)
WEEKEND_HEADER = (31, 50, 54)

TODAY_BORDER = (65, 205, 194)

ABSENCE = (132, 94, 194)
MAINTENANCE = (78, 126, 186)
RAID = (184, 72, 86)
MEETING = (184, 139, 65)
EVENT = (68, 149, 131)

ICON_BG = (63, 67, 78)
SPECIAL_ICON_BG = (47, 51, 62)

# ------------------------------------------------------------
# Fonts
# ------------------------------------------------------------

def font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",

        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold else
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, S(size))
    return ImageFont.load_default()

FONT_TITLE = font(28, True)
FONT_SUBTITLE = font(16, False)
FONT_DAY = font(17, True)
FONT_DATE = font(13, False)
FONT_NAME = font(17, True)
FONT_BAR = font(12, True)
FONT_ICON = font(12, True)

# ============================================================
# TESTDATEN
# ============================================================

SPECIAL_ROWS = [
    {
        "name": "AION 2",
        "icon": "A2",
        "items": [
            {
                "type": "maintenance",
                "label": "WARTUNG · 08–12",
                "start_day": 2,
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
                "start_day": 4,
                "end_day": 4,
            },
            {
                "type": "meeting",
                "label": "TREFFEN · 19:30",
                "start_day": 6,
                "end_day": 6,
            },
        ],
    },
]

MEMBERS = [
    {
        "name": "Shaynah | Laura",
        "initials": "SL",
        "items": [
            {
                "type": "absence",
                "start_offset": -7,
                "end_offset": 32,
            }
        ],
    },
    {
        "name": "Tom",
        "initials": "T",
        "items": [
            {
                "type": "absence",
                "start_offset": 1,
                "end_offset": 3,
            }
        ],
    },
    {
        "name": "Patrick",
        "initials": "P",
        "items": [
            {
                "type": "absence",
                "start_offset": 4,
                "end_offset": 6,
            }
        ],
    },
    {
        "name": "EinSehrLangerDiscordNameZumTesten",
        "initials": "ED",
        "items": [],
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

def text_width(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0]

def ellipsize(draw, text, fnt, max_width_logical):
    max_width = S(max_width_logical)
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

def bar_x(day_index):
    return MARGIN_X + NAME_COL_W + day_index * DAY_COL_W

def slot_centers(row_y, row_h, count):
    # gewünschtes Verhalten:
    # 1 = Mitte
    # 2 = oben + Mitte
    # 3 = oben + Mitte + unten
    count = max(1, min(3, count))
    center = row_y + row_h / 2
    gap = 15

    if count == 1:
        return [center]
    if count == 2:
        return [center - gap, center]
    return [center - gap, center, center + gap]

def rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(
        tuple(S(v) for v in xy),
        radius=S(radius),
        fill=fill,
        outline=outline,
        width=S(width)
    )

def draw_line(draw, xy, fill, width=1):
    draw.line(tuple(S(v) for v in xy), fill=fill, width=S(width))

def draw_identity(draw, y, row_h, name, initials, special=False):
    icon_x = MARGIN_X + 10
    icon_y = y + (row_h - ICON_SIZE) / 2
    icon_fill = SPECIAL_ICON_BG if special else ICON_BG

    draw.ellipse(
        (S(icon_x), S(icon_y), S(icon_x + ICON_SIZE), S(icon_y + ICON_SIZE)),
        fill=icon_fill
    )

    tw = text_width(draw, initials, FONT_ICON)
    bbox = draw.textbbox((0, 0), initials, font=FONT_ICON)
    th = bbox[3] - bbox[1]

    draw.text(
        (S(icon_x + ICON_SIZE / 2) - tw / 2,
         S(icon_y + ICON_SIZE / 2) - th / 2 - S(1)),
        initials,
        font=FONT_ICON,
        fill=TEXT
    )

    name_x = icon_x + ICON_SIZE + ICON_GAP
    max_name_w = NAME_COL_W - (name_x - MARGIN_X) - 10
    visible_name = ellipsize(draw, name, FONT_NAME, max_name_w)

    bbox = draw.textbbox((0, 0), visible_name, font=FONT_NAME)
    th = bbox[3] - bbox[1]

    draw.text(
        (S(name_x), S(y + row_h / 2) - th / 2 - S(1)),
        visible_name,
        font=FONT_NAME,
        fill=TEXT
    )

def draw_bar(draw, row_y, row_h, start_day, end_day, label, color, slot_center):
    start_day = max(0, min(6, start_day))
    end_day = max(0, min(6, end_day))
    if end_day < start_day:
        return

    x1 = bar_x(start_day) + 5
    x2 = bar_x(end_day + 1) - 5

    bar_h = 14
    y1 = slot_center - bar_h / 2
    y2 = slot_center + bar_h / 2

    rounded_rect(draw, (x1, y1, x2, y2), 5, color)

    max_w = max(0, x2 - x1 - 8)
    visible = ellipsize(draw, label, FONT_BAR, max_w)

    if max_w >= 20:
        bbox = draw.textbbox((0, 0), visible, font=FONT_BAR)
        th = bbox[3] - bbox[1]
        draw.text(
            (S(x1 + 4), S(slot_center) - th / 2 - S(1)),
            visible,
            font=FONT_BAR,
            fill=(255, 255, 255)
        )

def absence_dates(week_start, item):
    start_dt = week_start + timedelta(days=item["start_offset"])
    end_dt = week_start + timedelta(days=item["end_offset"])
    return start_dt, end_dt

def draw_absence(draw, row_y, row_h, week_start, item, slot_center):
    start_dt, end_dt = absence_dates(week_start, item)

    visible_start = max(start_dt, week_start)
    visible_end = min(end_dt, week_start + timedelta(days=6))

    if visible_end < week_start or visible_start > week_start + timedelta(days=6):
        return

    start_day = (visible_start.date() - week_start.date()).days
    end_day = (visible_end.date() - week_start.date()).days

    x1 = bar_x(start_day) + 5
    x2 = bar_x(end_day + 1) - 5

    bar_h = 14
    y1 = slot_center - bar_h / 2
    y2 = slot_center + bar_h / 2

    rounded_rect(draw, (x1, y1, x2, y2), 5, ABSENCE)

    continued_left = start_dt < week_start
    continued_right = end_dt > week_start + timedelta(days=6)

    if continued_left:
        draw.polygon(
            [
                (S(x1 + 3), S(slot_center)),
                (S(x1 + 7), S(y1 + 2)),
                (S(x1 + 7), S(y2 - 2)),
            ],
            fill=(255, 255, 255)
        )

    if continued_right:
        draw.polygon(
            [
                (S(x2 - 3), S(slot_center)),
                (S(x2 - 7), S(y1 + 2)),
                (S(x2 - 7), S(y2 - 2)),
            ],
            fill=(255, 255, 255)
        )

    label = f"ABWESEND · {fmt_date(start_dt)}–{fmt_date(end_dt)}"

    left_pad = 10 if continued_left else 4
    right_pad = 10 if continued_right else 4
    max_w = max(0, x2 - x1 - left_pad - right_pad)
    visible = ellipsize(draw, label, FONT_BAR, max_w)

    if max_w >= 20:
        bbox = draw.textbbox((0, 0), visible, font=FONT_BAR)
        th = bbox[3] - bbox[1]
        draw.text(
            (S(x1 + left_pad), S(slot_center) - th / 2 - S(1)),
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
        + (len(SPECIAL_ROWS) * SPECIAL_ROW_H)
        + SECTION_GAP
        + (len(MEMBERS) * ROW_H)
        + BOTTOM_PAD
    )

    image = Image.new("RGB", (S(WIDTH), S(total_h)), BG)
    draw = ImageDraw.Draw(image)

    draw.text((S(MARGIN_X), S(TOP)), "WOCHENÜBERSICHT", font=FONT_TITLE, fill=TEXT)
    draw.text(
        (S(MARGIN_X), S(TOP + 34)),
        week_title(week_start),
        font=FONT_SUBTITLE,
        fill=TEXT_MUTED
    )

    grid_top = TOP + HEADER_H
    special_h_total = len(SPECIAL_ROWS) * SPECIAL_ROW_H
    member_top = grid_top + special_h_total + SECTION_GAP
    grid_bottom = member_top + len(MEMBERS) * ROW_H
    header_y = grid_top - 54

    rounded_rect(
        draw,
        (MARGIN_X, grid_top - 6, WIDTH - MARGIN_X, grid_bottom + 6),
        13,
        PANEL
    )

    # Wochenende bis in den Kopf hinein markieren
    for day in (5, 6):
        x1 = bar_x(day)
        x2 = x1 + DAY_COL_W
        draw.rectangle(
            (S(x1), S(header_y - 6), S(x2), S(grid_top - 6)),
            fill=WEEKEND_HEADER
        )
        draw.rectangle(
            (S(x1), S(grid_top - 6), S(x2), S(grid_bottom + 6)),
            fill=WEEKEND_BG
        )

    # Tageskopf
    day_names = ["MO", "DI", "MI", "DO", "FR", "SA", "SO"]

    for i, day_name in enumerate(day_names):
        day_dt = week_start + timedelta(days=i)
        x = bar_x(i)
        cx = x + DAY_COL_W / 2

        dw = text_width(draw, day_name, FONT_DAY)
        date_txt = day_dt.strftime("%d.%m.")
        date_w = text_width(draw, date_txt, FONT_DATE)

        draw.text(
            (S(cx) - dw / 2, S(header_y)),
            day_name,
            font=FONT_DAY,
            fill=TEXT
        )
        draw.text(
            (S(cx) - date_w / 2, S(header_y + 22)),
            date_txt,
            font=FONT_DATE,
            fill=TEXT_MUTED
        )

    # Tageslinien
    for i in range(8):
        x = MARGIN_X + NAME_COL_W + i * DAY_COL_W
        draw_line(draw, (x, grid_top - 6, x, grid_bottom + 6), GRID, 1)

    # AION 2 + GILDE
    y = grid_top
    for row in SPECIAL_ROWS:
        draw_identity(draw, y, SPECIAL_ROW_H, row["name"], row["icon"], special=True)

        items = row["items"][:3]
        centers = slot_centers(y, SPECIAL_ROW_H, len(items))

        for item, center in zip(items, centers):
            draw_bar(
                draw,
                y,
                SPECIAL_ROW_H,
                item["start_day"],
                item["end_day"],
                item["label"],
                TYPE_COLORS[item["type"]],
                center
            )

        draw_line(
            draw,
            (MARGIN_X, y + SPECIAL_ROW_H, WIDTH - MARGIN_X, y + SPECIAL_ROW_H),
            GRID,
            1
        )
        y += SPECIAL_ROW_H

    # Trenner
    draw_line(
        draw,
        (MARGIN_X, y + SECTION_GAP / 2, WIDTH - MARGIN_X, y + SECTION_GAP / 2),
        GRID,
        1
    )

    # Member
    y = member_top
    for member in MEMBERS:
        draw_identity(draw, y, ROW_H, member["name"], member["initials"], special=False)

        items = member.get("items", [])[:3]
        centers = slot_centers(y, ROW_H, len(items) if items else 1)

        for item, center in zip(items, centers):
            if item["type"] == "absence":
                draw_absence(draw, y, ROW_H, week_start, item, center)
            else:
                draw_bar(
                    draw,
                    y,
                    ROW_H,
                    item["start_day"],
                    item["end_day"],
                    item["label"],
                    TYPE_COLORS[item["type"]],
                    center
                )

        draw_line(
            draw,
            (MARGIN_X, y + ROW_H, WIDTH - MARGIN_X, y + ROW_H),
            GRID,
            1
        )
        y += ROW_H

    # HEUTE-Rahmen ganz zum Schluss über Rasterlinien
    if week_start.date() <= now.date() <= (week_start + timedelta(days=6)).date():
        today_idx = now.weekday()
        x1 = bar_x(today_idx) + 1
        x2 = x1 + DAY_COL_W - 2

        draw.rounded_rectangle(
            (S(x1), S(grid_top - 6), S(x2), S(grid_bottom + 6)),
            radius=S(7),
            outline=TODAY_BORDER,
            width=S(2)
        )

        # Nur Balken des heutigen Tages nochmals darüberzeichnen
        y2 = grid_top
        for row in SPECIAL_ROWS:
            items = row["items"][:3]
            centers = slot_centers(y2, SPECIAL_ROW_H, len(items))
            for item, center in zip(items, centers):
                if item["start_day"] <= today_idx <= item["end_day"]:
                    draw_bar(
                        draw,
                        y2,
                        SPECIAL_ROW_H,
                        item["start_day"],
                        item["end_day"],
                        item["label"],
                        TYPE_COLORS[item["type"]],
                        center
                    )
            y2 += SPECIAL_ROW_H

        y2 = member_top
        today_dt = week_start + timedelta(days=today_idx)

        for member in MEMBERS:
            items = member.get("items", [])[:3]
            centers = slot_centers(y2, ROW_H, len(items) if items else 1)

            for item, center in zip(items, centers):
                if item["type"] == "absence":
                    start_dt, end_dt = absence_dates(week_start, item)
                    if start_dt.date() <= today_dt.date() <= end_dt.date():
                        draw_absence(draw, y2, ROW_H, week_start, item, center)
                else:
                    if item["start_day"] <= today_idx <= item["end_day"]:
                        draw_bar(
                            draw,
                            y2,
                            ROW_H,
                            item["start_day"],
                            item["end_day"],
                            item["label"],
                            TYPE_COLORS[item["type"]],
                            center
                        )
            y2 += ROW_H

    # echtes 2x-Supersampling -> Zielgröße
    image = image.resize(
        (WIDTH, total_h),
        Image.Resampling.LANCZOS
    )

    image.save(OUTPUT_FILE, optimize=True)
    print(f"Kalender erstellt: {OUTPUT_FILE}")

# ============================================================
# Discord Webhook / State
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
            if exc.code != 404:
                raise
            print("Gespeicherte Discord-Nachricht existiert nicht mehr. Erstelle neue Nachricht.")

    result = webhook_request(f"{WEBHOOK_URL}?wait=true", method="POST")
    new_id = result.get("id")
    if not new_id:
        raise RuntimeError("Discord hat keine message_id zurückgegeben.")

    save_state({"message_id": new_id})
    print(f"Neue Discord-Kalendernachricht erstellt: {new_id}")

if __name__ == "__main__":
    render_calendar()
    post_or_update()
