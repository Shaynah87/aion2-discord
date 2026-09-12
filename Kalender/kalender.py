import os
import io
import json
import uuid
import math
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ============================================================
# Nyerk24 · Kalender V9 · 2 Karten / Wochenübersicht + Terminlegende
#
# Neue Logik:
# - Wochenübersicht oben
# - pro Tag nur Symbole / Marker
# - 1 Symbol = groß und mittig
# - 2 Symbole = links / rechts
# - 3 Symbole = Dreieck (2 oben, 1 unten)
# - 4 Symbole = 2x2
# - bei 2/3/4 immer gleiche Symbolgröße
# - darunter vollständige "Termine diese Woche"
# - eigener Block "Aktuelle Abwesenheiten"
# - zwei Layouts testbar:
#       LAYOUT_MODE = "columns"
#       LAYOUT_MODE = "columns"
# - Discord Webhook + persistente message_id bleiben erhalten
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
WEEK_FILE = BASE_DIR / "kalender_woche.png"
ABSENCES_FILE = BASE_DIR / "kalender_abwesenheiten.png"
STATE_FILE = BASE_DIR / "kalender_message.json"

WEBHOOK_URL = os.environ.get("KALENDER_WEBHOOK", "").strip()
TIMEZONE = ZoneInfo("Europe/Berlin")

TRACKER_OVERVIEW_BACKGROUND_URL = (
    "https://raw.githubusercontent.com/"
    "Shaynah87/aion2-discord/main/Tracker/event_overview.png"
)


# ------------------------------------------------------------
# Layout-Schalter
# ------------------------------------------------------------

# "stacked":
# Wochenübersicht -> Termine -> Abwesenheiten
#
# "columns":
# Wochenübersicht -> Termine links / Abwesenheiten rechts
#
LAYOUT_MODE = "stacked"

# ------------------------------------------------------------
# Rendering / Größe
# ------------------------------------------------------------

SCALE = 1
WIDTH = 1200

MARGIN_X = 38
TOP = 34
BOTTOM_PAD = 38

TITLE_H = 76
WEEK_HEADER_H = 62
WEEK_CELL_H = 132
SECTION_GAP = 24

CARD_RADIUS = 15
INNER_PAD = 22

EVENT_ROW_H = 62
ABSENCE_ROW_H = 62

def S(value):
    return int(round(value * SCALE))

# ------------------------------------------------------------
# Farben
# ------------------------------------------------------------

BG = (17, 18, 22)
PANEL = (24, 26, 31)
PANEL_SOFT = (28, 30, 36)

TEXT = (240, 242, 247)
TEXT_MUTED = (154, 160, 171)
TEXT_FAINT = (116, 122, 132)

GRID = (55, 59, 69)

WEEKEND_BG = (24, 38, 42)
WEEKEND_HEADER = (30, 48, 52)

TODAY_BORDER = (65, 205, 194)
TODAY_FILL = (22, 47, 48)

# Kategorien
RELEASE = (90, 155, 214)
SEASON = (145, 105, 202)
RAID = (190, 78, 91)
GUILD = (188, 145, 68)
EVENT = (67, 151, 133)
ABSENCE = (132, 94, 194)

TYPE_COLORS = {
    "release": RELEASE,
    "season": SEASON,
    "raid": RAID,
    "guild": GUILD,
    "event": EVENT,
}

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

FONT_TITLE = font(29, True)
FONT_SUBTITLE = font(15, False)

FONT_DAY = font(16, True)
FONT_DATE = font(13, False)

FONT_SECTION = font(22, True)
FONT_EVENT = font(18, True)
FONT_EVENT_META = font(14, False)
FONT_ABSENCE = font(18, True)
FONT_ABSENCE_DATE = font(14, False)

FONT_SYMBOL_BIG = font(31, True)
FONT_SYMBOL_SMALL = font(22, True)

# ============================================================
# TESTDATEN
#
# start_day:
#   0 = Montag
#   1 = Dienstag
#   ...
#   6 = Sonntag
#
# Die Testdaten enthalten absichtlich:
#   1 Termin an einem Tag
#   2 Termine an einem Tag
#   3 Termine an einem Tag
#   4 Termine an einem Tag
#
# So kann die neue Symbollogik sofort geprüft werden.
# ============================================================

EVENTS = [
    # Montag: 1
    {
        "day": 0,
        "type": "release",
        "symbol": "◆",
        "title": "Early Access",
        "time": "",
    },

    # Dienstag: 2
    {
        "day": 1,
        "type": "season",
        "symbol": "✦",
        "title": "Season 2 Start",
        "time": "",
    },
    {
        "day": 1,
        "type": "guild",
        "symbol": "●",
        "title": "Gildenbesprechung",
        "time": "19:30",
    },

    # Mittwoch: 3
    {
        "day": 2,
        "type": "raid",
        "symbol": "⚔",
        "title": "Gilden-Raid",
        "time": "20:00",
    },
    {
        "day": 2,
        "type": "event",
        "symbol": "★",
        "title": "Gilden-Event",
        "time": "21:00",
    },
    {
        "day": 2,
        "type": "guild",
        "symbol": "●",
        "title": "Treffen",
        "time": "22:00",
    },

    # Freitag: 4
    {
        "day": 4,
        "type": "release",
        "symbol": "◆",
        "title": "Global Launch",
        "time": "",
    },
    {
        "day": 4,
        "type": "raid",
        "symbol": "⚔",
        "title": "Abyss Raid",
        "time": "19:00",
    },
    {
        "day": 4,
        "type": "event",
        "symbol": "★",
        "title": "Community Event",
        "time": "20:30",
    },
    {
        "day": 4,
        "type": "guild",
        "symbol": "●",
        "title": "Gildentreffen",
        "time": "22:00",
    },
]

ABSENCES = [
    {
        "name": "Shaynah | Laura",
        "start_offset": -7,
        "end_offset": 8,
    },
    {
        "name": "Tom",
        "start_offset": 2,
        "end_offset": 5,
    },
]

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
        return (
            f"{monday.day:02d}.–{sunday.day:02d}. "
            f"{months[monday.month - 1]} {monday.year}"
        )

    return (
        f"{monday.day:02d}. {months[monday.month - 1]} – "
        f"{sunday.day:02d}. {months[sunday.month - 1]} {sunday.year}"
    )

def text_width(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0]

def text_height(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[3] - box[1]

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

def rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(
        tuple(S(v) for v in xy),
        radius=S(radius),
        fill=fill,
        outline=outline,
        width=S(width),
    )

def draw_line(draw, xy, fill, width=1):
    draw.line(
        tuple(S(v) for v in xy),
        fill=fill,
        width=S(width),
    )

def centered_text(draw, center_x, center_y, text, fnt, fill):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    draw.text(
        (
            S(center_x) - tw / 2,
            S(center_y) - th / 2 - S(1),
        ),
        text,
        font=fnt,
        fill=fill,
    )

# ============================================================
# Dezenter Tracker-artiger Hintergrund
# Anthrazit + sehr unauffälliger heller Nebel
# ============================================================

def create_background(width, height):
    image = Image.new("RGB", (S(width), S(height)), BG)

    # Nebel auf separater Ebene erzeugen.
    mist = Image.new("RGBA", image.size, (0, 0, 0, 0))
    md = ImageDraw.Draw(mist)

    # Mehrere sehr weiche, helle Flächen.
    # Absichtlich dezent, damit Text/UI klar bleibt.
    blobs = [
        (0.14, 0.28, 0.34, 0.22, 26),
        (0.48, 0.12, 0.42, 0.20, 18),
        (0.78, 0.38, 0.36, 0.25, 22),
        (0.36, 0.76, 0.52, 0.20, 14),
        (0.86, 0.82, 0.30, 0.18, 16),
    ]

    for cx, cy, rw, rh, alpha in blobs:
        x1 = S(width * (cx - rw / 2))
        y1 = S(height * (cy - rh / 2))
        x2 = S(width * (cx + rw / 2))
        y2 = S(height * (cy + rh / 2))

        md.ellipse(
            (x1, y1, x2, y2),
            fill=(220, 225, 230, alpha),
        )

    mist = mist.filter(ImageFilter.GaussianBlur(S(48)))
    image = Image.alpha_composite(image.convert("RGBA"), mist)

    return image.convert("RGB")

# ============================================================
# EVENT-SYMBOLLOGIK 1–4
# ============================================================

def get_symbol_layout(cell_x, cell_y, cell_w, cell_h, count):
    """
    1 Termin:
        ein großes Symbol exakt mittig

    2 Termine:
        zwei gleich große Symbole links / rechts

    3 Termine:
        Dreieck -> zwei oben, eins unten

    4 Termine:
        2x2

    Wichtig:
        2 / 3 / 4 verwenden exakt dieselbe Symbolgröße.
    """

    if count <= 0:
        return [], FONT_SYMBOL_SMALL

    cx = cell_x + cell_w / 2
    cy = cell_y + cell_h / 2

    if count == 1:
        return [(cx, cy)], FONT_SYMBOL_BIG

    dx = cell_w * 0.20
    dy = cell_h * 0.19

    if count == 2:
        positions = [
            (cx - dx, cy),
            (cx + dx, cy),
        ]

    elif count == 3:
        positions = [
            (cx - dx, cy - dy),
            (cx + dx, cy - dy),
            (cx, cy + dy),
        ]

    else:
        positions = [
            (cx - dx, cy - dy),
            (cx + dx, cy - dy),
            (cx - dx, cy + dy),
            (cx + dx, cy + dy),
        ]

    return positions, FONT_SYMBOL_SMALL

def events_for_day(day_index):
    return [event for event in EVENTS if event["day"] == day_index][:4]

def draw_day_symbols(draw, events, cell_x, cell_y, cell_w, cell_h):
    positions, symbol_font = get_symbol_layout(
        cell_x,
        cell_y,
        cell_w,
        cell_h,
        len(events),
    )

    for event, (cx, cy) in zip(events, positions):
        color = TYPE_COLORS.get(event["type"], TEXT)
        centered_text(
            draw,
            cx,
            cy,
            event["symbol"],
            symbol_font,
            color,
        )

# ============================================================
# Wochenübersicht
# ============================================================

def draw_week_overview(draw, week_start, now, x, y, width):
    day_names = ["MO", "DI", "MI", "DO", "FR", "SA", "SO"]

    cell_w = width / 7
    header_h = WEEK_HEADER_H
    body_h = WEEK_CELL_H
    total_h = header_h + body_h

    # Kein grauer Gesamt-Container mehr:
    # Raster, Wochenende und "Heute" liegen direkt auf dem Smoke-Hintergrund.

    # Wochenende dezent markieren.
    for day in (5, 6):
        x1 = x + day * cell_w
        x2 = x1 + cell_w

        draw.rectangle(
            (
                S(x1),
                S(y),
                S(x2),
                S(y + header_h),
            ),
            fill=WEEKEND_HEADER,
        )

        draw.rectangle(
            (
                S(x1),
                S(y + header_h),
                S(x2),
                S(y + total_h),
            ),
            fill=WEEKEND_BG,
        )

    for day_index, day_name in enumerate(day_names):
        day_dt = week_start + timedelta(days=day_index)

        x1 = x + day_index * cell_w
        cx = x1 + cell_w / 2

        if day_dt.date() == now.date():
            draw.rectangle(
                (
                    S(x1 + 1),
                    S(y + 1),
                    S(x1 + cell_w - 1),
                    S(y + total_h - 1),
                ),
                fill=TODAY_FILL,
            )

        centered_text(
            draw,
            cx,
            y + 20,
            day_name,
            FONT_DAY,
            TEXT,
        )

        centered_text(
            draw,
            cx,
            y + 43,
            day_dt.strftime("%d.%m."),
            FONT_DATE,
            TEXT_MUTED,
        )

        draw_day_symbols(
            draw,
            events_for_day(day_index),
            x1,
            y + header_h,
            cell_w,
            body_h,
        )

    draw_line(
        draw,
        (x, y + header_h, x + width, y + header_h),
        GRID,
        1,
    )

    for i in range(1, 7):
        lx = x + i * cell_w
        draw_line(
            draw,
            (lx, y, lx, y + total_h),
            GRID,
            1,
        )

    # Dezente obere und untere Begrenzung statt eines grauen Kastens.
    draw_line(draw, (x, y, x + width, y), GRID, 1)
    draw_line(draw, (x, y + total_h, x + width, y + total_h), GRID, 1)

    if week_start.date() <= now.date() <= (week_start + timedelta(days=6)).date():
        today_idx = now.weekday()
        tx1 = x + today_idx * cell_w + 2
        tx2 = tx1 + cell_w - 4

        draw.rounded_rectangle(
            (
                S(tx1),
                S(y + 2),
                S(tx2),
                S(y + total_h - 2),
            ),
            radius=S(9),
            outline=TODAY_BORDER,
            width=S(2),
        )

        draw_day_symbols(
            draw,
            events_for_day(today_idx),
            x + today_idx * cell_w,
            y + header_h,
            cell_w,
            body_h,
        )

    return total_h

# ============================================================
# Terminliste
# ============================================================

def event_date(week_start, event):
    return week_start + timedelta(days=event["day"])

def sorted_events():
    return sorted(
        EVENTS,
        key=lambda e: (
            e["day"],
            e.get("time", ""),
            e["title"],
        ),
    )

def event_list_height():
    count = max(1, len(EVENTS))
    rows = math.ceil(count / 3)
    return 72 + rows * EVENT_ROW_H + 22


def draw_events_block(draw, week_start, x, y, width):
    height = event_list_height()

    # Kein grauer Panel-Hintergrund mehr.
    # Inhalt liegt direkt auf dem gemeinsamen Smoke-Hintergrund.
    draw.text(
        (S(x + INNER_PAD), S(y + 18)),
        "TERMINE DIESE WOCHE",
        font=FONT_SECTION,
        fill=TEXT,
    )

    events = sorted_events()
    start_y = y + 64

    if not events:
        draw.text(
            (S(x + INNER_PAD), S(start_y + 8)),
            "Keine besonderen Termine in dieser Woche.",
            font=FONT_EVENT_META,
            fill=TEXT_MUTED,
        )
        return height

    columns = min(3, len(events))
    gap = 26
    usable_w = width - 2 * INNER_PAD
    col_w = (usable_w - gap * 2) / 3

    for index, event in enumerate(events):
        row = index // 3
        col = index % 3

        cell_x = x + INNER_PAD + col * (col_w + gap)
        cell_y = start_y + row * EVENT_ROW_H

        dt = event_date(week_start, event)
        color = TYPE_COLORS.get(event["type"], TEXT)

        symbol_x = cell_x + 8
        centered_text(
            draw,
            symbol_x,
            cell_y + EVENT_ROW_H / 2,
            event["symbol"],
            FONT_EVENT,
            color,
        )

        text_x = cell_x + 26

        meta = dt.strftime("%d.%m.")
        if event.get("time"):
            meta += f" · {event['time']}"

        draw.text(
            (S(text_x), S(cell_y + 5)),
            meta,
            font=FONT_EVENT_META,
            fill=TEXT_MUTED,
        )

        title = ellipsize(
            draw,
            event["title"],
            FONT_EVENT,
            col_w - 30,
        )

        draw.text(
            (S(text_x), S(cell_y + 27)),
            title,
            font=FONT_EVENT,
            fill=TEXT,
        )

    return height


# ============================================================
# Abwesenheiten
# ============================================================

def absence_dates(week_start, item):
    start_dt = week_start + timedelta(days=item["start_offset"])
    end_dt = week_start + timedelta(days=item["end_offset"])
    return start_dt, end_dt

def relevant_absences(week_start):
    week_end = week_start + timedelta(days=6)
    result = []

    for absence in ABSENCES:
        start_dt, end_dt = absence_dates(week_start, absence)

        # Relevant, wenn der Zeitraum diese Woche berührt
        # oder darüber hinaus weiterläuft.
        if end_dt.date() >= week_start.date() and start_dt.date() <= week_end.date():
            result.append(absence)

    return result

def absence_block_height(week_start):
    count = max(1, len(relevant_absences(week_start)))
    rows = math.ceil(count / 3)
    return 72 + rows * ABSENCE_ROW_H + 22


def draw_absences_block(draw, week_start, x, y, width, forced_height=None):
    items = relevant_absences(week_start)

    own_height = absence_block_height(week_start)
    height = max(own_height, forced_height or 0)

    # Kein grauer Panel-Hintergrund mehr.
    draw.text(
        (S(x + INNER_PAD), S(y + 18)),
        "AKTUELLE ABWESENHEITEN",
        font=FONT_SECTION,
        fill=TEXT,
    )

    start_y = y + 64

    if not items:
        draw.text(
            (S(x + INNER_PAD), S(start_y + 8)),
            "Keine Abwesenheiten gemeldet.",
            font=FONT_EVENT_META,
            fill=TEXT_MUTED,
        )
        return height

    gap = 26
    usable_w = width - 2 * INNER_PAD
    col_w = (usable_w - gap * 2) / 3

    for index, item in enumerate(items):
        row = index // 3
        col = index % 3

        cell_x = x + INNER_PAD + col * (col_w + gap)
        cell_y = start_y + row * ABSENCE_ROW_H

        start_dt, end_dt = absence_dates(week_start, item)

        marker_x = cell_x + 6
        marker_y = cell_y + 24

        draw.ellipse(
            (
                S(marker_x - 4),
                S(marker_y - 4),
                S(marker_x + 4),
                S(marker_y + 4),
            ),
            fill=ABSENCE,
        )

        text_x = cell_x + 22

        name = ellipsize(
            draw,
            item["name"],
            FONT_ABSENCE,
            col_w - 28,
        )

        draw.text(
            (S(text_x), S(cell_y + 4)),
            name,
            font=FONT_ABSENCE,
            fill=TEXT,
        )

        date_label = f"{fmt_date(start_dt)} – {fmt_date(end_dt)}"

        draw.text(
            (S(text_x), S(cell_y + 29)),
            date_label,
            font=FONT_ABSENCE_DATE,
            fill=TEXT_MUTED,
        )

    return height


# ============================================================
# TRACKER-HINTERGRUND FÜR DIE DREI KALENDERKARTEN
# ============================================================

def load_tracker_background():
    request = urllib.request.Request(
        TRACKER_OVERVIEW_BACKGROUND_URL,
        headers={"User-Agent": "Nyerk24-Kalender/2.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return Image.open(io.BytesIO(response.read())).convert("RGBA")
    except Exception as exc:
        print(f"Tracker-Hintergrund konnte nicht geladen werden: {exc}")
        return None


def crop_and_resize_background(image, width, height):
    if image is None:
        return create_background(width, height).convert("RGBA")

    sw, sh = image.size
    target_ratio = width / height
    source_ratio = sw / sh

    if source_ratio > target_ratio:
        new_w = int(sh * target_ratio)
        left = (sw - new_w) // 2
        image = image.crop((left, 0, left + new_w, sh))
    else:
        new_h = int(sw / target_ratio)
        top = (sh - new_h) // 2
        image = image.crop((0, top, sw, top + new_h))

    image = image.resize((width, height), Image.Resampling.LANCZOS)

    dark = Image.new("RGBA", image.size, (5, 6, 9, 130))
    return Image.alpha_composite(image, dark)


def card_canvas(width, height, background_source):
    image = crop_and_resize_background(
        background_source.copy() if background_source is not None else None,
        width,
        height,
    )

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    fade_end = int(width * 0.72)
    for x in range(fade_end):
        progress = x / max(1, fade_end - 1)
        alpha = int(70 * ((1.0 - progress) ** 1.5))
        od.line((x, 0, x, height), fill=(0, 0, 0, alpha))

    return Image.alpha_composite(image, overlay).convert("RGB")


# ============================================================
# DREI EINZELNE KALENDERKARTEN
# ============================================================

def render_week_card(week_start, now, background_source):
    week_h = WEEK_HEADER_H + WEEK_CELL_H

    # Wochenraster bleibt immer gleich groß.
    # Nur der darunterliegende Termin-/Legendenbereich wächst dynamisch.
    legend_h = event_list_height()
    legend_gap = 22

    height = (
        TOP
        + TITLE_H
        + week_h
        + legend_gap
        + legend_h
        + BOTTOM_PAD
    )

    image = card_canvas(WIDTH, height, background_source)
    draw = ImageDraw.Draw(image)

    draw.text(
        (MARGIN_X, TOP),
        "WOCHENÜBERSICHT",
        font=FONT_TITLE,
        fill=TEXT,
    )

    draw.text(
        (MARGIN_X, TOP + 36),
        week_title(week_start),
        font=FONT_SUBTITLE,
        fill=TEXT_MUTED,
    )

    week_y = TOP + TITLE_H

    draw_week_overview(
        draw,
        week_start,
        now,
        MARGIN_X,
        week_y,
        WIDTH - 2 * MARGIN_X,
    )

    # Dezente Trennlinie zwischen festem Wochenraster und Legende.
    legend_y = week_y + week_h + legend_gap

    draw_line(
        draw,
        (
            MARGIN_X,
            legend_y - 10,
            WIDTH - MARGIN_X,
            legend_y - 10,
        ),
        GRID,
        1,
    )

    # Die Terminliste ist gleichzeitig die Legende für die Symbole oben.
    # Maximal drei Termine nebeneinander, danach nächste Zeile.
    draw_events_block(
        draw,
        week_start,
        MARGIN_X,
        legend_y,
        WIDTH - 2 * MARGIN_X,
    )

    image.save(WEEK_FILE, "PNG", optimize=True)
    print(f"Wochenkarte inkl. Terminlegende erstellt: {WEEK_FILE}")


def render_absences_card(week_start, background_source):
    block_h = absence_block_height(week_start)
    height = TOP + block_h + BOTTOM_PAD

    image = card_canvas(WIDTH, height, background_source)
    draw = ImageDraw.Draw(image)

    draw_absences_block(
        draw,
        week_start,
        MARGIN_X,
        TOP,
        WIDTH - 2 * MARGIN_X,
    )

    image.save(ABSENCES_FILE, "PNG", optimize=True)
    print(f"Abwesenheitskarte erstellt: {ABSENCES_FILE}")


def render_calendar_cards():
    now = datetime.now(TIMEZONE)
    week_start = monday_of_week(now)

    background_source = load_tracker_background()

    render_week_card(week_start, now, background_source)
    render_absences_card(week_start, background_source)


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
        encoding="utf-8",
    )


def multipart_body(payload_json, file_paths):
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
        json.dumps(payload_json).encode("utf-8"),
    )

    for index, file_path in enumerate(file_paths):
        write_part(
            {
                "Content-Disposition": (
                    f'form-data; name="files[{index}]"; '
                    f'filename="{file_path.name}"'
                ),
                "Content-Type": "image/png",
            },
            file_path.read_bytes(),
        )

    body.write(f"--{boundary}--\r\n".encode())

    return body.getvalue(), boundary


def webhook_request(url, method="POST"):
    files = [
        WEEK_FILE,
        ABSENCES_FILE,
    ]

    payload = {
        "content": "",
        "embeds": [
            {"image": {"url": f"attachment://{WEEK_FILE.name}"}},
            {"image": {"url": f"attachment://{ABSENCES_FILE.name}"}},
        ],
        "attachments": [
            {
                "id": index,
                "filename": file_path.name,
            }
            for index, file_path in enumerate(files)
        ],
    }

    body, boundary = multipart_body(payload, files)

    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Nyerk24-Kalender/2.0",
        },
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


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

            print(
                "Gespeicherte Discord-Nachricht existiert nicht mehr. "
                "Erstelle neue Nachricht."
            )

    result = webhook_request(
        f"{WEBHOOK_URL}?wait=true",
        method="POST",
    )

    new_id = result.get("id")

    if not new_id:
        raise RuntimeError("Discord hat keine message_id zurückgegeben.")

    save_state({"message_id": new_id})
    print(f"Neue Discord-Kalendernachricht erstellt: {new_id}")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    render_calendar_cards()
    post_or_update()
