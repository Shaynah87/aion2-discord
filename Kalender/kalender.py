import os
import io
import json
import uuid
import math
import hashlib
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ============================================================
# Nyerk24 · Kalender V29 · Rollierende 14 Tage + Special Launch Days
#
# Neue Logik:
# - Wochenübersicht oben
# - pro Tag nur Symbole / Marker
# - 1 Symbol = groß und mittig
# - 2 Symbole = links / rechts
# - 3 Symbole = Dreieck (2 oben, 1 unten)
# - 4 Symbole = 2x2
# - bei 2/3/4 immer gleiche Symbolgröße
# - darunter Terminauflösung ohne zusätzliche Überschrift
# - darunter kleine Vorschau der Folgewoche nur mit Datum + Icons
# - eigener Block "Aktuelle Abwesenheiten"
# - zwei Layouts testbar:
#       LAYOUT_MODE = "columns"
#       LAYOUT_MODE = "columns"
# - Discord Webhook + persistente message_id bleiben erhalten
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent
EARLY_ACCESS_IMAGE = REPO_DIR / "Content" / "Launch" / "early_access.png"
GLOBAL_LAUNCH_IMAGE = REPO_DIR / "Content" / "Launch" / "global_launch.png"
WEEK_FILE = BASE_DIR / "kalender_woche.png"
ABSENCES_FILE = BASE_DIR / "kalender_abwesenheiten.png"
STATE_FILE = BASE_DIR / "kalender_message.json"

WEBHOOK_URL = os.environ.get("KALENDER_WEBHOOK", "").strip()
KALENDER_API_KEY = os.environ.get("KALENDER_API_KEY", "").strip()
KALENDER_DATA_URL = "https://nyerk24-service.laura-stephan.workers.dev/kalender-data"
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

MARGIN_X = 28
TOP = 24
BOTTOM_PAD = 24

TITLE_H = 64
WEEK_HEADER_H = 56
WEEK_CELL_H = 104
NEXT_WEEK_DATE_H = 34
NEXT_WEEK_ICON_H = 62
SECTION_GAP = 18

CARD_RADIUS = 15
INNER_PAD = 22

EVENT_ROW_H = 58
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
MEETING = (188, 145, 68)
EVENT = (67, 151, 133)
APPOINTMENT = (154, 160, 171)
ABSENCE = (132, 94, 194)

TYPE_COLORS = {
    "release": RELEASE,
    "season": SEASON,
    "raid": RAID,
    "besprechung": MEETING,
    "event": EVENT,
    "termin": APPOINTMENT,
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
FONT_ABSENCE_GROUP = font(14, True)
FONT_DAY_EVENT = font(13, True)
FONT_DAY_EVENT_TIME = font(12, False)
FONT_UPCOMING_DATE = font(13, True)

# V28: kompakt, aber dynamisch wachsend
ROLLING_DAYS = 14
DAY_ROW_BASE_H = 92
DAY_ROW_EVENT_LINE_H = 23
DAY_ROW_EVENT_GAP = 7
DAY_EVENT_TIME_H = 17
DAY_HEADER_H = 43
DAY_ROW_PAD_BOTTOM = 10
UPCOMING_ROW_H = 38



# ============================================================
# Livedaten aus Cloudflare D1
# ============================================================

EVENTS = []
ABSENCES = []

def parse_iso_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=TIMEZONE)

    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]

def load_calendar_data():
    if not KALENDER_API_KEY:
        raise RuntimeError("KALENDER_API_KEY ist nicht gesetzt.")

    kalender_token = hashlib.sha256(
        KALENDER_API_KEY.encode("utf-8")
    ).hexdigest()

    request = urllib.request.Request(
        KALENDER_DATA_URL,
        method="GET",
        headers={
            "X-Kalender-Key": kalender_token,
            "Accept": "application/json",
            "User-Agent": "Nyerk24-Kalender/29.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Kalender-Daten konnten nicht geladen werden: HTTP {exc.code} · {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Kalender-Daten konnten nicht geladen werden: {exc}") from exc

    now = datetime.now(TIMEZONE)
    week_start = monday_of_week(now)

    events = []
    for row in payload.get("termine", []):
        try:
            dt = parse_iso_date(str(row["datum"]))
        except (KeyError, TypeError, ValueError):
            continue

        raw_type = str(row.get("termin_typ") or "termin").strip().lower()
        type_aliases = {
            "meeting": "besprechung",
            "guild": "besprechung",
            "appointment": "termin",
            "launch": "release",
        }
        event_type = type_aliases.get(raw_type, raw_type)
        if event_type not in TYPE_COLORS:
            event_type = "termin"

        events.append({
            "date": dt.date(),
            "type": event_type,
            "title": str(row.get("titel") or "Termin"),
            "time": str(row.get("uhrzeit") or "").strip(),
        })

    absences = []
    for row in payload.get("abwesenheiten", []):
        try:
            start_dt = parse_iso_date(str(row["start_datum"]))
            end_dt = parse_iso_date(str(row["end_datum"]))
        except (KeyError, TypeError, ValueError):
            continue

        absences.append({
            "name": str(row.get("discord_name") or "Unbekannt"),
            "start_offset": (start_dt.date() - week_start.date()).days,
            "end_offset": (end_dt.date() - week_start.date()).days,
            "note": str(row.get("notiz") or ""),
        })

    EVENTS.clear()
    EVENTS.extend(events)
    ABSENCES.clear()
    ABSENCES.extend(absences)

    print(f"Kalender-Daten geladen: {len(EVENTS)} Termine, {len(ABSENCES)} Abwesenheiten")

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
# SAUBERE PIL-ICONS + SYMBOLLOGIK 1–4
# ============================================================

ICON_RENDER_SCALE = 4


def _icon_canvas(size):
    px = max(24, int(size * ICON_RENDER_SCALE))
    return Image.new("RGBA", (px, px), (0, 0, 0, 0)), px, ICON_RENDER_SCALE


def _pt(value, scale):
    return int(round(value * scale))


def make_event_icon(event_type, size, color):
    image, px, sc = _icon_canvas(size)
    d = ImageDraw.Draw(image)
    c = tuple(color) + (255,)
    w = max(2, _pt(size * 0.07, sc))
    cx = px / 2
    cy = px / 2

    if event_type == "release":
        # Party-Popper + Konfetti
        cone = [
            (_pt(size * 0.22, sc), _pt(size * 0.78, sc)),
            (_pt(size * 0.38, sc), _pt(size * 0.42, sc)),
            (_pt(size * 0.58, sc), _pt(size * 0.62, sc)),
        ]
        d.polygon(cone, outline=c)
        d.line((_pt(size*.34,sc),_pt(size*.48,sc),_pt(size*.53,sc),_pt(size*.67,sc)), fill=c, width=w)
        for x,y in ((.55,.22),(.72,.18),(.76,.40),(.48,.30),(.67,.31)):
            r=max(1,_pt(size*.035,sc))
            xx,yy=_pt(size*x,sc),_pt(size*y,sc)
            d.ellipse((xx-r,yy-r,xx+r,yy+r), fill=c)
        d.line((_pt(size*.62,sc),_pt(size*.12,sc),_pt(size*.58,sc),_pt(size*.26,sc)), fill=c, width=w)
        d.line((_pt(size*.82,sc),_pt(size*.27,sc),_pt(size*.69,sc),_pt(size*.32,sc)), fill=c, width=w)

    elif event_type == "season":
        # Zielflagge
        x0,y0=_pt(size*.25,sc),_pt(size*.14,sc)
        x1,y1=_pt(size*.25,sc),_pt(size*.84,sc)
        d.line((x0,y0,x1,y1), fill=c, width=w)
        left,top=_pt(size*.29,sc),_pt(size*.18,sc)
        cw,ch=_pt(size*.14,sc),_pt(size*.13,sc)
        for row in range(3):
            for col in range(3):
                box=(left+col*cw, top+row*ch, left+(col+1)*cw, top+(row+1)*ch)
                if (row+col)%2==0: d.rectangle(box, fill=c)
                else: d.rectangle(box, outline=c, width=max(1,w//2))

    elif event_type == "raid":
        # Gekreuzte Schwerter
        d.line((_pt(size*.22,sc),_pt(size*.18,sc),_pt(size*.76,sc),_pt(size*.78,sc)), fill=c, width=w)
        d.line((_pt(size*.78,sc),_pt(size*.18,sc),_pt(size*.24,sc),_pt(size*.78,sc)), fill=c, width=w)
        d.line((_pt(size*.19,sc),_pt(size*.65,sc),_pt(size*.39,sc),_pt(size*.65,sc)), fill=c, width=w)
        d.line((_pt(size*.61,sc),_pt(size*.65,sc),_pt(size*.81,sc),_pt(size*.65,sc)), fill=c, width=w)

    elif event_type == "besprechung":
        # Sprechblase
        box=(_pt(size*.15,sc),_pt(size*.20,sc),_pt(size*.82,sc),_pt(size*.66,sc))
        d.rounded_rectangle(box, radius=_pt(size*.10,sc), outline=c, width=w)
        d.line((_pt(size*.34,sc),_pt(size*.66,sc),_pt(size*.26,sc),_pt(size*.82,sc),_pt(size*.48,sc),_pt(size*.67,sc)), fill=c, width=w)
        for x in (.34,.49,.64):
            r=max(1,_pt(size*.025,sc)); xx,yy=_pt(size*x,sc),_pt(size*.43,sc)
            d.ellipse((xx-r,yy-r,xx+r,yy+r), fill=c)

    elif event_type == "termin":
        # Kalenderblatt
        box=(_pt(size*.18,sc),_pt(size*.24,sc),_pt(size*.82,sc),_pt(size*.80,sc))
        d.rounded_rectangle(box, radius=_pt(size*.07,sc), outline=c, width=w)
        d.line((_pt(size*.18,sc),_pt(size*.40,sc),_pt(size*.82,sc),_pt(size*.40,sc)), fill=c, width=w)
        d.line((_pt(size*.34,sc),_pt(size*.14,sc),_pt(size*.34,sc),_pt(size*.31,sc)), fill=c, width=w)
        d.line((_pt(size*.66,sc),_pt(size*.14,sc),_pt(size*.66,sc),_pt(size*.31,sc)), fill=c, width=w)
        d.ellipse((_pt(size*.46,sc),_pt(size*.53,sc),_pt(size*.54,sc),_pt(size*.61,sc)), fill=c)

    else:
        # Event: Funkelstern
        pts=[]
        for i in range(16):
            angle=-math.pi/2+i*math.pi/8
            r=size*(0.36 if i%2==0 else 0.15)*sc
            pts.append((cx+math.cos(angle)*r, cy+math.sin(angle)*r))
        d.polygon(pts, outline=c)
        r=max(1,_pt(size*.025,sc))
        d.ellipse((_pt(size*.76,sc)-r,_pt(size*.18,sc)-r,_pt(size*.76,sc)+r,_pt(size*.18,sc)+r), fill=c)

    return image.resize((int(size), int(size)), Image.Resampling.LANCZOS)

def draw_event_icon(base_image, event_type, center_x, center_y, size, color):
    icon = make_event_icon(event_type, size, color)
    x = int(round(center_x - icon.width / 2))
    y = int(round(center_y - icon.height / 2))
    base_image.paste(icon, (x, y), icon)


def get_symbol_layout(cell_x, cell_y, cell_w, cell_h, count):
    if count <= 0:
        return [], 0

    cx = cell_x + cell_w / 2
    cy = cell_y + cell_h / 2

    if count == 1:
        return [(cx, cy)], 38

    dx = cell_w * 0.20
    dy = cell_h * 0.20
    icon_size = 27

    if count == 2:
        positions = [(cx - dx, cy), (cx + dx, cy)]
    elif count == 3:
        positions = [(cx - dx, cy - dy), (cx + dx, cy - dy), (cx, cy + dy)]
    else:
        positions = [
            (cx - dx, cy - dy), (cx + dx, cy - dy),
            (cx - dx, cy + dy), (cx + dx, cy + dy),
        ]

    return positions, icon_size


def events_for_day(day_index, week_offset=0):
    return [
        event for event in EVENTS
        if event["day"] == day_index and event.get("week_offset", 0) == week_offset
    ][:4]


def draw_day_symbols(image, events, cell_x, cell_y, cell_w, cell_h, preview=False):
    positions, icon_size = get_symbol_layout(
        cell_x, cell_y, cell_w, cell_h, len(events)
    )

    if preview and len(events) == 1:
        icon_size = 30
    elif preview and len(events) > 1:
        icon_size = 23

    for event, (cx, cy) in zip(events, positions):
        color = TYPE_COLORS.get(event["type"], TEXT)
        draw_event_icon(image, event["type"], cx, cy, icon_size, color)


# ============================================================
# V28 · Rollierende 14-Tage-Übersicht
# ============================================================

DAY_NAMES = ["MO", "DI", "MI", "DO", "FR", "SA", "SO"]


def events_for_date(day_date):
    return sorted(
        [e for e in EVENTS if e.get("date") == day_date],
        key=lambda e: (e.get("time", ""), e.get("title", "")),
    )


def visible_events(today):
    end = today + timedelta(days=ROLLING_DAYS - 1)
    return [e for e in EVENTS if today <= e.get("date", today) <= end]


def upcoming_events(today):
    cutoff = today + timedelta(days=ROLLING_DAYS)
    return sorted(
        [e for e in EVENTS if e.get("date") and e["date"] >= cutoff],
        key=lambda e: (e["date"], e.get("time", ""), e.get("title", "")),
    )


def wrap_text_lines(draw, text, fnt, max_width_logical):
    text = str(text or "").strip()
    if not text:
        return [""]
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if text_width(draw, candidate, fnt) <= S(max_width_logical):
            current = candidate
        else:
            if current:
                lines.append(current)
                current = word
            else:
                # Extrem langer Einzelbegriff: zeichenweise umbrechen, niemals "...".
                chunk = ""
                for ch in word:
                    test = chunk + ch
                    if chunk and text_width(draw, test, fnt) > S(max_width_logical):
                        lines.append(chunk)
                        chunk = ch
                    else:
                        chunk = test
                current = chunk
    if current:
        lines.append(current)
    return lines or [""]


def event_block_height(draw, event, width):
    lines = wrap_text_lines(draw, event.get("title", "Termin"), FONT_DAY_EVENT, max(20, width))
    title_h = len(lines) * 16
    return title_h + (DAY_EVENT_TIME_H if event.get("time") else 0)


def rolling_row_height(draw, start_date, width):
    cell_w = width / 7
    max_content = 0
    for i in range(7):
        day_date = start_date + timedelta(days=i)
        events = list(events_for_date(day_date))
        special = special_launch_kind(day_date, events)
        if special in ("early", "global"):
            # Special-Text wird separat mittig gerendert; für die Mindesthöhe trotzdem berücksichtigen.
            events = [
                e for e in events
                if "early access" not in str(e.get("title") or "").casefold()
                and "global launch" not in str(e.get("title") or "").casefold()
            ]
            events.append({
                "title": "Early Access" if special == "early" else "Global Launch",
                "time": "15:00",
                "type": "release",
            })
        if not events:
            continue
        heights = [event_block_height(draw, event, cell_w - 20) for event in events]
        total = sum(heights) + max(0, len(heights) - 1) * DAY_ROW_EVENT_GAP
        max_content = max(max_content, total)
    if max_content == 0:
        return DAY_ROW_BASE_H
    return max(DAY_ROW_BASE_H, DAY_HEADER_H + 7 + max_content + DAY_ROW_PAD_BOTTOM)


def special_launch_kind(day_date, events):
    # Einmalige Nyerk24-Special-Days: fest im Renderer verankert.
    if day_date == date(2026, 9, 30):
        return "early"
    if day_date == date(2026, 10, 5):
        return "global"

    # Kompatibilität, falls entsprechende D1-Termine noch vorhanden sind.
    for event in events:
        title = str(event.get("title") or "").casefold()
        if "early access" in title:
            return "early"
        if "global launch" in title:
            return "global"
    return None


def draw_special_day_background(image, box, kind):
    path = EARLY_ACCESS_IMAGE if kind == "early" else GLOBAL_LAUNCH_IMAGE
    if not path.exists():
        return
    try:
        src = Image.open(path).convert("RGB")
        x1, y1, x2, y2 = [S(v) for v in box]
        w, h = max(1, x2 - x1), max(1, y2 - y1)

        scale = max(w / src.width, h / src.height)
        resized = src.resize(
            (max(1, int(src.width * scale)), max(1, int(src.height * scale))),
            Image.Resampling.LANCZOS,
        )
        left = max(0, (resized.width - w) // 2)
        top = max(0, (resized.height - h) // 2)
        art = resized.crop((left, top, left + w, top + h)).convert("RGB")

        # Motive bewusst sichtbar halten: Global Launch braucht vor allem mehr
        # Kontrast/Farbe, damit die Figuren nicht im grauen Kalender verschwinden.
        if kind == "global":
            art = ImageEnhance.Contrast(art).enhance(1.30)
            art = ImageEnhance.Color(art).enhance(1.22)
            art = ImageEnhance.Brightness(art).enhance(1.08)
        else:
            art = ImageEnhance.Contrast(art).enhance(1.16)
            art = ImageEnhance.Color(art).enhance(1.14)
            art = ImageEnhance.Brightness(art).enhance(1.06)
        art = art.convert("RGBA")

        # Kein "Sticker": Motiv weich in den vorhandenen Kalender einblenden.
        # Mitte sichtbar, zu allen Rändern hin sanft auslaufend.
        mask = Image.new("L", (w, h), 0)
        px = mask.load()
        feather_x = max(18, int(w * 0.24))
        feather_y = max(14, int(h * 0.22))
        max_alpha = 235
        for yy in range(h):
            fy = min(1.0, yy / feather_y, (h - 1 - yy) / feather_y)
            fy = max(0.0, fy)
            for xx in range(w):
                fx = min(1.0, xx / feather_x, (w - 1 - xx) / feather_x)
                fx = max(0.0, fx)
                px[xx, yy] = int(max_alpha * min(fx, fy))

        base = image.crop((x1, y1, x2, y2)).convert("RGBA")
        merged = Image.composite(art, base, mask)

        # Leichte dunkle Lesefläche ohne das Motiv zuzukleben.
        shade = Image.new("RGBA", (w, h), (6, 8, 12, 6))
        merged = Image.alpha_composite(merged, shade)
        image.paste(merged.convert("RGB"), (x1, y1))
    except Exception as exc:
        print(f"Special-Day-Motiv konnte nicht geladen werden ({path.name}): {exc}")

def draw_compact_event(draw, image, event, x, y, width):
    # V29: kein bedeutungsloser Farbpunkt mehr. Titel bekommt die volle Zellbreite.
    lines = wrap_text_lines(draw, event.get("title", "Termin"), FONT_DAY_EVENT, width)
    cursor_y = y
    for line in lines:
        draw.text((S(x), S(cursor_y)), line, font=FONT_DAY_EVENT, fill=TEXT)
        cursor_y += 16
    time_text = event.get("time", "")
    if time_text:
        draw.text((S(x), S(cursor_y + 1)), time_text, font=FONT_DAY_EVENT_TIME, fill=TEXT_MUTED)
        cursor_y += DAY_EVENT_TIME_H
    return max(16, cursor_y - y)


def draw_rolling_row(image, draw, start_date, now_date, x, y, width):
    cell_w = width / 7
    row_h = rolling_row_height(draw, start_date, width)

    # Hintergründe zuerst. Wochenende nur sehr subtil markieren.
    for idx in range(7):
        day_dt = start_date + timedelta(days=idx)
        day_events = events_for_date(day_dt)
        x1 = x + idx * cell_w
        special = special_launch_kind(day_dt, day_events)
        if special:
            draw_special_day_background(image, (x1, y, x1 + cell_w, y + row_h), special)

    for idx in range(7):
        day_dt = start_date + timedelta(days=idx)
        x1 = x + idx * cell_w
        cx = x1 + cell_w / 2
        day_name_color = (151, 187, 190) if day_dt.weekday() >= 5 else TEXT
        centered_text(draw, cx, y + 14, DAY_NAMES[day_dt.weekday()], FONT_DAY, day_name_color)
        centered_text(draw, cx, y + 32, day_dt.strftime("%d.%m."), FONT_DATE, TEXT_MUTED)

        ev_y = y + DAY_HEADER_H + 7
        day_events = events_for_date(day_dt)
        special = special_launch_kind(day_dt, day_events)

        display_events = list(day_events)

        # Einmalige Special Days sind vollständig unabhängig von D1.
        if special in ("early", "global"):
            # Eventuelle alte D1-Einträge dieser beiden Specials nicht doppelt anzeigen.
            display_events = [
                e for e in display_events
                if "early access" not in str(e.get("title") or "").casefold()
                and "global launch" not in str(e.get("title") or "").casefold()
            ]

            special_title = "Early Access" if special == "early" else "Global Launch"
            special_time = "15:00"

            title_font = FONT_EVENT_META
            time_font = FONT_EVENT_META
            title_box = draw.textbbox((0, 0), special_title, font=title_font)
            title_w = title_box[2] - title_box[0]
            title_h = title_box[3] - title_box[1]
            time_box = draw.textbbox((0, 0), special_time, font=time_font)
            time_w = time_box[2] - time_box[0]
            time_h = time_box[3] - time_box[1]

            content_top = y + DAY_HEADER_H
            content_h = row_h - DAY_HEADER_H
            gap = 4
            total_h = title_h + gap + time_h
            special_y = content_top + max(5, (content_h - total_h) / 2)

            draw.text(
                (S(x1 + (cell_w - title_w) / 2), S(special_y)),
                special_title,
                font=title_font,
                fill=(238, 241, 244),
            )
            draw.text(
                (S(x1 + (cell_w - time_w) / 2), S(special_y + title_h + gap)),
                special_time,
                font=time_font,
                fill=(166, 173, 181),
            )

        for event in display_events:
            used_h = draw_compact_event(draw, image, event, x1 + 10, ev_y, cell_w - 20)
            ev_y += used_h + DAY_ROW_EVENT_GAP

    # Rasterlinien zuletzt zeichnen, damit sie auch am Wochenende / über Motiven sichtbar bleiben.
    # Eigene obere Linie pro Reihe: dadurch kann die zweite Reihe die Trennlinie nicht mehr übermalen.
    draw_line(draw, (x, y, x + width, y), GRID, 1)
    draw_line(draw, (x, y + DAY_HEADER_H, x + width, y + DAY_HEADER_H), GRID, 1)

    draw_line(draw, (x, y + row_h, x + width, y + row_h), GRID, 1)
    for i in range(1, 7):
        lx = x + i * cell_w
        draw_line(draw, (lx, y, lx, y + row_h), GRID, 1)

    if start_date <= now_date <= start_date + timedelta(days=6):
        idx = (now_date - start_date).days
        x1 = x + idx * cell_w
        draw.rounded_rectangle(
            (S(x1 + 2), S(y + 2), S(x1 + cell_w - 2), S(y + row_h - 2)),
            radius=S(8), outline=TODAY_BORDER, width=S(2),
        )
    return row_h

def draw_rolling_calendar(image, draw, today, x, y, width):
    first_h = draw_rolling_row(image, draw, today, today, x, y, width)
    second_start = today + timedelta(days=7)
    second_y = y + first_h
    second_h = draw_rolling_row(image, draw, second_start, today, x, second_y, width)
    return first_h + second_h


# ============================================================
# Kommende Termine außerhalb der sichtbaren 14 Tage
# ============================================================

def upcoming_block_height(today):
    events = upcoming_events(today)
    if not events:
        return 0
    return 42 + len(events) * UPCOMING_ROW_H


def draw_upcoming_block(draw, today, x, y, width):
    events = upcoming_events(today)
    if not events:
        return 0

    draw.text((S(x + INNER_PAD), S(y)), "KOMMENDE TERMINE", font=FONT_SECTION, fill=TEXT)
    cursor = y + 39
    for event in events:
        color = TYPE_COLORS.get(event.get("type"), APPOINTMENT)
        draw.ellipse((S(x + INNER_PAD), S(cursor + 8), S(x + INNER_PAD + 7), S(cursor + 15)), fill=color)
        date_text = event["date"].strftime("%d.%m.%Y")
        draw.text((S(x + INNER_PAD + 15), S(cursor + 1)), date_text, font=FONT_UPCOMING_DATE, fill=TEXT)
        date_w = text_width(draw, date_text, FONT_UPCOMING_DATE)
        title_x = x + INNER_PAD + 24 + date_w / S(1)
        title = event.get("title", "Termin")
        if event.get("time"):
            title += f" · {event['time']}"
        title = ellipsize(draw, title, FONT_EVENT_META, width - (title_x - x) - INNER_PAD)
        draw.text((S(title_x), S(cursor + 1)), title, font=FONT_EVENT_META, fill=TEXT)
        cursor += UPCOMING_ROW_H
    return upcoming_block_height(today)


# ============================================================
# Abwesenheiten
# ============================================================

def absence_dates(week_start, item):
    start_dt = week_start + timedelta(days=item["start_offset"])
    end_dt = week_start + timedelta(days=item["end_offset"])
    return start_dt, end_dt


def relevant_absences(week_start):
    today = datetime.now(TIMEZONE).date()
    result = []
    for absence in ABSENCES:
        start_dt, end_dt = absence_dates(week_start, absence)
        if end_dt.date() >= today:
            result.append(absence)
    result.sort(key=lambda item: absence_dates(week_start, item)[0])
    return result


def split_absences(week_start):
    today = datetime.now(TIMEZONE).date()
    current, upcoming = [], []
    for item in relevant_absences(week_start):
        start_dt, end_dt = absence_dates(week_start, item)
        if start_dt.date() <= today <= end_dt.date():
            current.append(item)
        elif start_dt.date() > today:
            upcoming.append(item)
    current.sort(key=lambda item: absence_dates(week_start, item)[0])
    upcoming.sort(key=lambda item: absence_dates(week_start, item)[0])
    return current, upcoming


ABSENCE_GROUP_TITLE_H = 25
ABSENCE_GROUP_GAP = 10
ABSENCE_TITLE_TO_GROUP = 14
ABSENCE_GROUP_TO_NAMES = 7


def absence_group_height(items):
    if not items:
        return 0
    rows = math.ceil(len(items) / 4)
    return ABSENCE_GROUP_TITLE_H + rows * ABSENCE_ROW_H


def absence_block_height(week_start):
    current, upcoming = split_absences(week_start)
    # Hauptüberschrift + bewusster Abstand zur ersten Gruppe
    height = 35
    if not current and not upcoming:
        return height + 34
    height += ABSENCE_TITLE_TO_GROUP
    if current:
        height += absence_group_height(current)
    if current and upcoming:
        height += ABSENCE_GROUP_GAP
    if upcoming:
        height += absence_group_height(upcoming)
    return height


def draw_absence_group(draw, week_start, items, title, x, y, width):
    if not items:
        return 0

    draw.text((S(x + INNER_PAD), S(y)), title, font=FONT_ABSENCE_GROUP, fill=(205, 209, 217))
    list_y = y + ABSENCE_GROUP_TITLE_H
    gap = 18
    usable_w = width - 2 * INNER_PAD
    col_w = (usable_w - gap * 3) / 4

    for index, item in enumerate(items):
        row, col = divmod(index, 4)
        cell_x = x + INNER_PAD + col * (col_w + gap)
        cell_y = list_y + row * ABSENCE_ROW_H
        start_dt, end_dt = absence_dates(week_start, item)

        marker_x, marker_y = cell_x + 6, cell_y + 20
        draw.ellipse((S(marker_x - 4), S(marker_y - 4), S(marker_x + 4), S(marker_y + 4)), fill=ABSENCE)
        text_x = cell_x + 22
        name = ellipsize(draw, item["name"], FONT_ABSENCE, col_w - 28)
        draw.text((S(text_x), S(cell_y)), name, font=FONT_ABSENCE, fill=TEXT)

        date_label = f"{start_dt.strftime('%d.%m.%Y')} – {end_dt.strftime('%d.%m.%Y')}"
        draw.text((S(text_x), S(cell_y + 27)), date_label, font=FONT_ABSENCE_DATE, fill=(224, 227, 233))

    return absence_group_height(items)


def draw_absences_block(draw, week_start, x, y, width, forced_height=None):
    current, upcoming = split_absences(week_start)
    own_height = absence_block_height(week_start)
    height = max(own_height, forced_height or 0)

    draw.text((S(x + INNER_PAD), S(y)), "ABWESENHEIT", font=FONT_SECTION, fill=TEXT)
    cursor_y = y + 35

    if not current and not upcoming:
        draw.text((S(x + INNER_PAD), S(cursor_y + 4)), "Keine", font=FONT_EVENT_META, fill=TEXT_MUTED)
        return height

    cursor_y += ABSENCE_TITLE_TO_GROUP
    if current:
        cursor_y += draw_absence_group(draw, week_start, current, "AKTUELL", x, cursor_y, width)
    if current and upcoming:
        cursor_y += ABSENCE_GROUP_GAP
    if upcoming:
        cursor_y += draw_absence_group(draw, week_start, upcoming, "KOMMEND", x, cursor_y, width)
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
        return Image.new(
            "RGBA",
            (width, height),
            (10, 11, 14, 255),
        )

    # Der Tracker-Hintergrund selbst besitzt am unteren Rand eine sehr dunkle
    # Abschlusskante. Bei der höheren Kalenderkarte wurde diese mit skaliert
    # und dadurch als schwarzer Streifen sichtbar.
    #
    # Deshalb die Quelle bewusst asymmetrisch beschneiden:
    # seitlich/oben nur minimal, unten deutlich stärker.
    sw, sh = image.size

    trim_left = max(0, int(sw * 0.018))
    trim_right = max(0, int(sw * 0.018))
    trim_top = max(0, int(sh * 0.018))
    trim_bottom = max(0, int(sh * 0.065))

    image = image.crop(
        (
            trim_left,
            trim_top,
            sw - trim_right,
            sh - trim_bottom,
        )
    )

    sw, sh = image.size
    target_ratio = width / height
    source_ratio = sw / sh

    if source_ratio > target_ratio:
        new_w = int(sh * target_ratio)
        left = (sw - new_w) // 2
        image = image.crop(
            (
                left,
                0,
                left + new_w,
                sh,
            )
        )
    else:
        new_h = int(sw / target_ratio)
        top = (sh - new_h) // 2
        image = image.crop(
            (
                0,
                top,
                sw,
                top + new_h,
            )
        )

    image = image.resize(
        (width, height),
        Image.Resampling.LANCZOS,
    )

    # Smoke stays visible, but slightly darkened for readable UI text.
    dark = Image.new(
        "RGBA",
        image.size,
        (5, 6, 9, 105),
    )

    return Image.alpha_composite(
        image,
        dark,
    )


def card_canvas(width, height, background_source):
    # Smoke fills the COMPLETE image area.
    # No extra dark/black outer canvas is added around the card.
    image = crop_and_resize_background(
        background_source.copy() if background_source is not None else None,
        width,
        height,
    )

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    # Very subtle readability gradient only; it does not create a frame.
    fade_end = int(width * 0.72)

    for x in range(fade_end):
        progress = x / max(1, fade_end - 1)
        alpha = int(54 * ((1.0 - progress) ** 1.5))
        od.line(
            (x, 0, x, height),
            fill=(0, 0, 0, alpha),
        )

    return Image.alpha_composite(
        image,
        overlay,
    ).convert("RGB")


# ============================================================
# V28 · Eine dynamische Kalenderkarte
# ============================================================

def render_week_card(week_start, now, background_source):
    today = now.date()
    calendar_h = rolling_row_height(ImageDraw.Draw(Image.new("RGB", (S(WIDTH), S(100)), (0, 0, 0))), today, WIDTH - 2 * MARGIN_X) + rolling_row_height(ImageDraw.Draw(Image.new("RGB", (S(WIDTH), S(100)), (0, 0, 0))), today + timedelta(days=7), WIDTH - 2 * MARGIN_X)
    upcoming_h = upcoming_block_height(today)
    absences_h = absence_block_height(week_start)

    title_to_calendar = 8
    block_gap = 22
    height = TOP + TITLE_H + title_to_calendar + calendar_h
    if upcoming_h:
        height += block_gap + upcoming_h
    height += block_gap + absences_h + BOTTOM_PAD

    image = card_canvas(WIDTH, height, background_source)
    draw = ImageDraw.Draw(image)

    draw.text((MARGIN_X, TOP), "14-TAGE-ÜBERSICHT", font=FONT_TITLE, fill=TEXT)
    range_end = today + timedelta(days=13)
    range_text = f"{today.strftime('%d.%m.')} – {range_end.strftime('%d.%m.%Y')}"
    draw.text((MARGIN_X, TOP + 34), range_text, font=FONT_SUBTITLE, fill=TEXT_MUTED)

    cursor_y = TOP + TITLE_H + title_to_calendar
    cursor_y += draw_rolling_calendar(
        image, draw, today, MARGIN_X, cursor_y, WIDTH - 2 * MARGIN_X
    )

    if upcoming_h:
        cursor_y += block_gap
        cursor_y += draw_upcoming_block(
            draw, today, MARGIN_X, cursor_y, WIDTH - 2 * MARGIN_X
        )

    cursor_y += block_gap
    draw_absences_block(
        draw, week_start, MARGIN_X, cursor_y, WIDTH - 2 * MARGIN_X
    )

    image.save(WEEK_FILE, "PNG", optimize=True)
    print(f"Dynamische V28-Kalenderkarte erstellt: {WEEK_FILE}")


def render_calendar_cards():
    now = datetime.now(TIMEZONE)
    week_start = monday_of_week(now)
    background_source = load_tracker_background()
    render_week_card(week_start, now, background_source)


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
    ]

    payload = {
        "content": "",
        "embeds": [
            {"image": {"url": f"attachment://{WEEK_FILE.name}"}},
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
    load_calendar_data()
    render_calendar_cards()
    post_or_update()
