import os
import io
import json
import uuid
import math
import hashlib
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageFilter


# ============================================================
# Nyerk24 · Kalender V23 · D1-Livedaten + AUTH TEST
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_FILE = BASE_DIR / "kalender.png"
WEEK_FILE = BASE_DIR / "kalender_woche.png"
ABSENCES_FILE = BASE_DIR / "kalender_abwesenheiten.png"
STATE_FILE = BASE_DIR / "kalender_message.json"

WEBHOOK_URL = os.environ.get("KALENDER_WEBHOOK", "").strip()
KALENDER_API_KEY = os.environ.get("KALENDER_API_KEY", "").strip()

KALENDER_DATA_URL = (
    "https://nyerk24-service.laura-stephan.workers.dev/"
    "kalender-data"
)

TIMEZONE = ZoneInfo("Europe/Berlin")

TRACKER_OVERVIEW_BACKGROUND_URL = (
    "https://raw.githubusercontent.com/"
    "Shaynah87/aion2-discord/main/Tracker/event_overview.png"
)


# ============================================================
# Layout
# ============================================================

LAYOUT_MODE = "stacked"

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


# ============================================================
# Farben
# ============================================================

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


# ============================================================
# Fonts
# ============================================================

def font(size: int, bold: bool = False):

    candidates = [
        (
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans-Bold.ttf"
            if bold
            else
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf"
        ),
        (
            "/usr/share/fonts/truetype/liberation2/"
            "LiberationSans-Bold.ttf"
            if bold
            else
            "/usr/share/fonts/truetype/liberation2/"
            "LiberationSans-Regular.ttf"
        ),
    ]

    for path in candidates:

        if Path(path).exists():

            return ImageFont.truetype(
                path,
                S(size),
            )

    return ImageFont.load_default()


FONT_TITLE = font(29, True)
FONT_SUBTITLE = font(15)

FONT_DAY = font(16, True)
FONT_DATE = font(13)

FONT_SECTION = font(22, True)

FONT_EVENT = font(18, True)
FONT_EVENT_META = font(14)

FONT_ABSENCE = font(18, True)
FONT_ABSENCE_DATE = font(14)


# ============================================================
# Daten
# ============================================================

EVENTS = []
ABSENCES = []


# ============================================================
# Datum
# ============================================================

def monday_of_week(dt: datetime) -> datetime:

    return (
        dt
        - timedelta(days=dt.weekday())
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def parse_iso_date(value: str) -> datetime:

    return datetime.strptime(
        value,
        "%Y-%m-%d",
    ).replace(
        tzinfo=TIMEZONE,
    )


def german_date(dt):

    return dt.strftime("%d.%m.%Y")


def short_date(dt):

    return dt.strftime("%d.%m.")


# ============================================================
# AUTH TEST
# ============================================================

def auth_fingerprint(value: str) -> str:

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()[:12]


# ============================================================
# Daten aus Cloudflare laden
# ============================================================

def load_calendar_data():

    if not KALENDER_API_KEY:

        raise RuntimeError(
            "KALENDER_API_KEY ist nicht gesetzt."
        )

    print(
        "AUTH TEST SECRET:"
        f" length={len(KALENDER_API_KEY)}"
        f" fingerprint={auth_fingerprint(KALENDER_API_KEY)}"
    )

    request = urllib.request.Request(
        KALENDER_DATA_URL,
        method="GET",
        headers={
            "X-Kalender-Key": KALENDER_API_KEY,
            "Accept": "application/json",
            "User-Agent": "Nyerk24-Kalender/23.0",
        },
    )

    request_key = (
        request.get_header("X-kalender-key")
        or
        request.get_header("X-Kalender-Key")
        or
        ""
    )

    print(
        "AUTH TEST REQUEST:"
        f" length={len(request_key)}"
        f" fingerprint={auth_fingerprint(request_key)}"
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:

            payload = json.loads(
                response
                .read()
                .decode("utf-8")
            )

    except urllib.error.HTTPError as exc:

        detail = (
            exc.read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        raise RuntimeError(
            "Kalender-Daten konnten nicht geladen werden: "
            f"HTTP {exc.code} · {detail}"
        ) from exc

    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
    ) as exc:

        raise RuntimeError(
            "Kalender-Daten konnten nicht geladen werden: "
            f"{exc}"
        ) from exc

    now = datetime.now(TIMEZONE)

    week_start = monday_of_week(now)

    events = []

    for row in payload.get(
        "termine",
        [],
    ):

        try:

            dt = parse_iso_date(
                str(row["datum"])
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):

            continue

        delta = (
            dt.date()
            - week_start.date()
        ).days

        if not 0 <= delta <= 13:

            continue

        raw_type = str(
            row.get("termin_typ")
            or
            "termin"
        ).strip().lower()

        type_aliases = {
            "meeting": "besprechung",
            "guild": "besprechung",
            "appointment": "termin",
            "launch": "release",
        }

        event_type = type_aliases.get(
            raw_type,
            raw_type,
        )

        if event_type not in TYPE_COLORS:

            event_type = "termin"

        events.append({
            "day": delta % 7,
            "week_offset": delta // 7,
            "type": event_type,
            "title": str(
                row.get("titel")
                or
                "Termin"
            ),
            "time": str(
                row.get("uhrzeit")
                or
                ""
            )[:5],
        })

    absences = []

    for row in payload.get(
        "abwesenheiten",
        [],
    ):

        try:

            start_dt = parse_iso_date(
                str(row["start_datum"])
            )

            end_dt = parse_iso_date(
                str(row["end_datum"])
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):

            continue

        absences.append({
            "name": str(
                row.get("discord_name")
                or
                "Unbekannt"
            ),
            "start_offset": (
                start_dt.date()
                - week_start.date()
            ).days,
            "end_offset": (
                end_dt.date()
                - week_start.date()
            ).days,
            "note": str(
                row.get("notiz")
                or
                ""
            ),
        })

    EVENTS.clear()
    EVENTS.extend(events)

    ABSENCES.clear()
    ABSENCES.extend(absences)

    print(
        "Kalender-Daten geladen: "
        f"{len(EVENTS)} Termine, "
        f"{len(ABSENCES)} Abwesenheiten"
    )


# ============================================================
# Text
# ============================================================

def text_width(draw, text, font_obj):

    box = draw.textbbox(
        (0, 0),
        text,
        font=font_obj,
    )

    return box[2] - box[0]


def ellipsize(
    draw,
    text,
    font_obj,
    max_width,
):

    text = str(text)

    if (
        text_width(
            draw,
            text,
            font_obj,
        )
        <= S(max_width)
    ):

        return text

    suffix = "…"

    while text:

        candidate = (
            text[:-1]
            + suffix
        )

        if (
            text_width(
                draw,
                candidate,
                font_obj,
            )
            <= S(max_width)
        ):

            return candidate

        text = text[:-1]

    return suffix


# ============================================================
# Hintergrund
# ============================================================

def download_background():

    try:

        request = urllib.request.Request(
            TRACKER_OVERVIEW_BACKGROUND_URL,
            headers={
                "User-Agent":
                    "Nyerk24-Kalender",
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=20,
        ) as response:

            data = response.read()

        return Image.open(
            io.BytesIO(data)
        ).convert("RGB")

    except Exception as exc:

        print(
            "Hintergrund konnte nicht geladen werden:",
            exc,
        )

        return None


def create_background(
    width,
    height,
):

    source = download_background()

    if source is None:

        return Image.new(
            "RGB",
            (
                S(width),
                S(height),
            ),
            BG,
        )

    target_w = S(width)
    target_h = S(height)

    src_w, src_h = source.size

    scale = max(
        target_w / src_w,
        target_h / src_h,
    )

    new_w = max(
        1,
        int(src_w * scale),
    )

    new_h = max(
        1,
        int(src_h * scale),
    )

    source = source.resize(
        (
            new_w,
            new_h,
        ),
        Image.Resampling.LANCZOS,
    )

    left = max(
        0,
        (new_w - target_w) // 2,
    )

    top = max(
        0,
        (new_h - target_h) // 2,
    )

    source = source.crop(
        (
            left,
            top,
            left + target_w,
            top + target_h,
        )
    )

    overlay = Image.new(
        "RGBA",
        source.size,
        (
            10,
            11,
            15,
            158,
        ),
    )

    source = source.convert("RGBA")

    source = Image.alpha_composite(
        source,
        overlay,
    )

    return source.convert("RGB")


# ============================================================
# Formen
# ============================================================

def rounded_rectangle(
    draw,
    box,
    radius,
    fill,
    outline=None,
    width=1,
):

    draw.rounded_rectangle(
        tuple(S(v) for v in box),
        radius=S(radius),
        fill=fill,
        outline=outline,
        width=S(width),
    )


# ============================================================
# Icon Rendering
# ============================================================

def icon_canvas(
    size,
    factor=4,
):

    return Image.new(
        "RGBA",
        (
            size * factor,
            size * factor,
        ),
        (
            0,
            0,
            0,
            0,
        ),
    )


def draw_calendar_icon(
    size,
    color,
):

    factor = 4

    image = icon_canvas(
        size,
        factor,
    )

    draw = ImageDraw.Draw(image)

    w = size * factor

    pad = int(
        w * 0.18
    )

    top = int(
        w * 0.24
    )

    bottom = int(
        w * 0.82
    )

    radius = max(
        2,
        int(w * 0.09),
    )

    draw.rounded_rectangle(
        (
            pad,
            top,
            w - pad,
            bottom,
        ),
        radius=radius,
        outline=color,
        width=max(
            2,
            int(w * 0.08),
        ),
    )

    line_y = int(
        w * 0.40
    )

    draw.line(
        (
            pad,
            line_y,
            w - pad,
            line_y,
        ),
        fill=color,
        width=max(
            2,
            int(w * 0.06),
        ),
    )

    bind_y1 = int(
        w * 0.14
    )

    bind_y2 = int(
        w * 0.31
    )

    for x in (
        int(w * 0.36),
        int(w * 0.64),
    ):

        draw.line(
            (
                x,
                bind_y1,
                x,
                bind_y2,
            ),
            fill=color,
            width=max(
                2,
                int(w * 0.07),
            ),
        )

    dot_r = max(
        2,
        int(w * 0.035),
    )

    for row in range(2):

        for col in range(3):

            cx = int(
                w
                * (
                    0.34
                    + col * 0.16
                )
            )

            cy = int(
                w
                * (
                    0.53
                    + row * 0.15
                )
            )

            draw.ellipse(
                (
                    cx - dot_r,
                    cy - dot_r,
                    cx + dot_r,
                    cy + dot_r,
                ),
                fill=color,
            )

    return image.resize(
        (
            size,
            size,
        ),
        Image.Resampling.LANCZOS,
    )


def draw_swords_icon(
    size,
    color,
):

    factor = 4

    image = icon_canvas(
        size,
        factor,
    )

    draw = ImageDraw.Draw(image)

    w = size * factor

    stroke = max(
        2,
        int(w * 0.065),
    )

    draw.line(
        (
            int(w * 0.24),
            int(w * 0.18),
            int(w * 0.76),
            int(w * 0.80),
        ),
        fill=color,
        width=stroke,
    )

    draw.line(
        (
            int(w * 0.76),
            int(w * 0.18),
            int(w * 0.24),
            int(w * 0.80),
        ),
        fill=color,
        width=stroke,
    )

    draw.line(
        (
            int(w * 0.17),
            int(w * 0.68),
            int(w * 0.35),
            int(w * 0.84),
        ),
        fill=color,
        width=stroke,
    )

    draw.line(
        (
            int(w * 0.83),
            int(w * 0.68),
            int(w * 0.65),
            int(w * 0.84),
        ),
        fill=color,
        width=stroke,
    )

    return image.resize(
        (
            size,
            size,
        ),
        Image.Resampling.LANCZOS,
    )


def draw_sparkle_icon(
    size,
    color,
):

    factor = 4

    image = icon_canvas(
        size,
        factor,
    )

    draw = ImageDraw.Draw(image)

    w = size * factor

    def star(
        cx,
        cy,
        radius,
    ):

        points = []

        for index in range(8):

            angle = (
                math.pi / 4
                * index
            )

            r = (
                radius
                if index % 2 == 0
                else radius * 0.22
            )

            points.append(
                (
                    cx
                    + math.cos(angle)
                    * r,
                    cy
                    + math.sin(angle)
                    * r,
                )
            )

        draw.polygon(
            points,
            fill=color,
        )

    star(
        w * 0.48,
        w * 0.48,
        w * 0.30,
    )

    star(
        w * 0.76,
        w * 0.25,
        w * 0.12,
    )

    star(
        w * 0.25,
        w * 0.74,
        w * 0.10,
    )

    return image.resize(
        (
            size,
            size,
        ),
        Image.Resampling.LANCZOS,
    )


def draw_chat_icon(
    size,
    color,
):

    factor = 4

    image = icon_canvas(
        size,
        factor,
    )

    draw = ImageDraw.Draw(image)

    w = size * factor

    stroke = max(
        2,
        int(w * 0.065),
    )

    left = int(
        w * 0.15
    )

    top = int(
        w * 0.18
    )

    right = int(
        w * 0.84
    )

    bottom = int(
        w * 0.69
    )

    draw.rounded_rectangle(
        (
            left,
            top,
            right,
            bottom,
        ),
        radius=int(
            w * 0.10
        ),
        outline=color,
        width=stroke,
    )

    tail = [
        (
            int(w * 0.33),
            bottom,
        ),
        (
            int(w * 0.26),
            int(w * 0.85),
        ),
        (
            int(w * 0.49),
            bottom,
        ),
    ]

    draw.polygon(
        tail,
        fill=color,
    )

    for x in (
        0.34,
        0.50,
        0.66,
    ):

        r = int(
            w * 0.035
        )

        cx = int(
            w * x
        )

        cy = int(
            w * 0.44
        )

        draw.ellipse(
            (
                cx - r,
                cy - r,
                cx + r,
                cy + r,
            ),
            fill=color,
        )

    return image.resize(
        (
            size,
            size,
        ),
        Image.Resampling.LANCZOS,
    )


def draw_party_icon(
    size,
    color,
):

    factor = 4

    image = icon_canvas(
        size,
        factor,
    )

    draw = ImageDraw.Draw(image)

    w = size * factor

    cone = [
        (
            int(w * 0.22),
            int(w * 0.78),
        ),
        (
            int(w * 0.42),
            int(w * 0.28),
        ),
        (
            int(w * 0.68),
            int(w * 0.70),
        ),
    ]

    draw.polygon(
        cone,
        fill=color,
    )

    stroke = max(
        2,
        int(w * 0.045),
    )

    confetti = [
        (
            0.60,
            0.18,
            0.70,
            0.08,
        ),
        (
            0.75,
            0.31,
            0.89,
            0.29,
        ),
        (
            0.52,
            0.13,
            0.50,
            0.03,
        ),
        (
            0.79,
            0.53,
            0.90,
            0.60,
        ),
    ]

    for x1, y1, x2, y2 in confetti:

        draw.line(
            (
                int(w * x1),
                int(w * y1),
                int(w * x2),
                int(w * y2),
            ),
            fill=color,
            width=stroke,
        )

    return image.resize(
        (
            size,
            size,
        ),
        Image.Resampling.LANCZOS,
    )


def draw_flag_icon(
    size,
    color,
):

    factor = 4

    image = icon_canvas(
        size,
        factor,
    )

    draw = ImageDraw.Draw(image)

    w = size * factor

    stroke = max(
        2,
        int(w * 0.055),
    )

    pole_x = int(
        w * 0.24
    )

    top = int(
        w * 0.14
    )

    bottom = int(
        w * 0.86
    )

    draw.line(
        (
            pole_x,
            top,
            pole_x,
            bottom,
        ),
        fill=color,
        width=stroke,
    )

    flag_left = pole_x

    flag_top = int(
        w * 0.18
    )

    flag_right = int(
        w * 0.80
    )

    flag_bottom = int(
        w * 0.54
    )

    cols = 4
    rows = 3

    cell_w = (
        flag_right
        - flag_left
    ) / cols

    cell_h = (
        flag_bottom
        - flag_top
    ) / rows

    for row in range(rows):

        for col in range(cols):

            x1 = int(
                flag_left
                + col * cell_w
            )

            y1 = int(
                flag_top
                + row * cell_h
            )

            x2 = int(
                flag_left
                + (col + 1)
                * cell_w
            )

            y2 = int(
                flag_top
                + (row + 1)
                * cell_h
            )

            if (
                row + col
            ) % 2 == 0:

                draw.rectangle(
                    (
                        x1,
                        y1,
                        x2,
                        y2,
                    ),
                    fill=color,
                )

            else:

                draw.rectangle(
                    (
                        x1,
                        y1,
                        x2,
                        y2,
                    ),
                    outline=color,
                    width=max(
                        1,
                        stroke // 2,
                    ),
                )

    return image.resize(
        (
            size,
            size,
        ),
        Image.Resampling.LANCZOS,
    )


def make_event_icon(
    event_type,
    size,
    color,
):

    if event_type == "raid":

        return draw_swords_icon(
            size,
            color,
        )

    if event_type == "event":

        return draw_sparkle_icon(
            size,
            color,
        )

    if event_type == "besprechung":

        return draw_chat_icon(
            size,
            color,
        )

    if event_type == "release":

        return draw_party_icon(
            size,
            color,
        )

    if event_type == "season":

        return draw_flag_icon(
            size,
            color,
        )

    return draw_calendar_icon(
        size,
        color,
    )


def draw_event_icon(
    image,
    event_type,
    center_x,
    center_y,
    size,
    color,
):

    icon = make_event_icon(
        event_type,
        S(size),
        color,
    )

    x = int(
        S(center_x)
        - icon.width / 2
    )

    y = int(
        S(center_y)
        - icon.height / 2
    )

    if image.mode != "RGBA":

        rgba = image.convert(
            "RGBA"
        )

        rgba.alpha_composite(
            icon,
            (
                x,
                y,
            ),
        )

        image.paste(
            rgba.convert("RGB")
        )

    else:

        image.alpha_composite(
            icon,
            (
                x,
                y,
            ),
        )


# ============================================================
# Termine
# ============================================================

def event_date(
    week_start,
    event,
):

    return (
        week_start
        + timedelta(
            days=(
                event["day"]
                + event.get(
                    "week_offset",
                    0,
                )
                * 7
            )
        )
    )


def events_for_day(
    week_offset,
    day_index,
):

    return [
        event
        for event in EVENTS
        if (
            event.get(
                "week_offset",
                0,
            )
            == week_offset
            and
            event["day"]
            == day_index
        )
    ]


def sorted_events(
    week_offset=None,
):

    result = EVENTS

    if week_offset is not None:

        result = [
            event
            for event in EVENTS
            if event.get(
                "week_offset",
                0,
            )
            == week_offset
        ]

    return sorted(
        result,
        key=lambda item: (
            item.get(
                "week_offset",
                0,
            ),
            item["day"],
            item.get(
                "time",
                "",
            ),
            item.get(
                "title",
                "",
            ),
        ),
    )


# ============================================================
# Wochenübersicht
# ============================================================

DAY_NAMES = [
    "MO",
    "DI",
    "MI",
    "DO",
    "FR",
    "SA",
    "SO",
]


def week_title(
    week_start,
):

    end = (
        week_start
        + timedelta(days=13)
    )

    return (
        f"{week_start.strftime('%d.%m.')} "
        f"– "
        f"{end.strftime('%d.%m.%Y')}"
    )


def draw_icon_group(
    image,
    events,
    center_x,
    center_y,
):

    count = len(events)

    if count == 0:

        return

    if count == 1:

        positions = [
            (
                center_x,
                center_y,
                34,
            ),
        ]

    elif count == 2:

        positions = [
            (
                center_x - 24,
                center_y,
                28,
            ),
            (
                center_x + 24,
                center_y,
                28,
            ),
        ]

    elif count == 3:

        positions = [
            (
                center_x - 23,
                center_y - 16,
                26,
            ),
            (
                center_x + 23,
                center_y - 16,
                26,
            ),
            (
                center_x,
                center_y + 20,
                26,
            ),
        ]

    else:

        positions = [
            (
                center_x - 21,
                center_y - 18,
                24,
            ),
            (
                center_x + 21,
                center_y - 18,
                24,
            ),
            (
                center_x - 21,
                center_y + 18,
                24,
            ),
            (
                center_x + 21,
                center_y + 18,
                24,
            ),
        ]

    for event, (
        x,
        y,
        size,
    ) in zip(
        events[:4],
        positions,
    ):

        color = TYPE_COLORS.get(
            event["type"],
            TEXT,
        )

        draw_event_icon(
            image,
            event["type"],
            x,
            y,
            size,
            color,
        )


def draw_week_overview(
    image,
    draw,
    week_start,
    now,
    x,
    y,
    width,
):

    cell_w = width / 7

    header_y = y

    current_y = (
        y
        + WEEK_HEADER_H
    )

    next_date_y = (
        current_y
        + WEEK_CELL_H
    )

    next_icon_y = (
        next_date_y
        + NEXT_WEEK_DATE_H
    )

    total_h = (
        WEEK_HEADER_H
        + WEEK_CELL_H
        + NEXT_WEEK_DATE_H
        + NEXT_WEEK_ICON_H
    )

    rounded_rectangle(
        draw,
        (
            x,
            y,
            x + width,
            y + total_h,
        ),
        CARD_RADIUS,
        PANEL,
    )

    for day_index in range(7):

        cell_x = (
            x
            + day_index
            * cell_w
        )

        current_date = (
            week_start
            + timedelta(
                days=day_index
            )
        )

        next_date = (
            current_date
            + timedelta(days=7)
        )

        weekend = (
            day_index >= 5
        )

        if weekend:

            draw.rectangle(
                (
                    S(cell_x),
                    S(header_y),
                    S(
                        cell_x
                        + cell_w
                    ),
                    S(
                        header_y
                        + WEEK_HEADER_H
                    ),
                ),
                fill=WEEKEND_HEADER,
            )

            draw.rectangle(
                (
                    S(cell_x),
                    S(current_y),
                    S(
                        cell_x
                        + cell_w
                    ),
                    S(
                        current_y
                        + WEEK_CELL_H
                    ),
                ),
                fill=WEEKEND_BG,
            )

            draw.rectangle(
                (
                    S(cell_x),
                    S(next_date_y),
                    S(
                        cell_x
                        + cell_w
                    ),
                    S(
                        next_icon_y
                        + NEXT_WEEK_ICON_H
                    ),
                ),
                fill=WEEKEND_BG,
            )

        is_today = (
            current_date.date()
            == now.date()
        )

        if is_today:

            draw.rectangle(
                (
                    S(cell_x + 2),
                    S(header_y + 2),
                    S(
                        cell_x
                        + cell_w
                        - 2
                    ),
                    S(
                        current_y
                        + WEEK_CELL_H
                        - 2
                    ),
                ),
                fill=TODAY_FILL,
                outline=TODAY_BORDER,
                width=S(2),
            )

        day_name = DAY_NAMES[
            day_index
        ]

        day_name_w = text_width(
            draw,
            day_name,
            FONT_DAY,
        )

        draw.text(
            (
                S(
                    cell_x
                    + cell_w / 2
                )
                - day_name_w / 2,
                S(
                    header_y
                    + 8
                ),
            ),
            day_name,
            font=FONT_DAY,
            fill=TEXT,
        )

        current_text = (
            current_date
            .strftime("%d.%m.")
        )

        current_text_w = text_width(
            draw,
            current_text,
            FONT_DATE,
        )

        draw.text(
            (
                S(
                    cell_x
                    + cell_w / 2
                )
                - current_text_w / 2,
                S(
                    header_y
                    + 31
                ),
            ),
            current_text,
            font=FONT_DATE,
            fill=TEXT_MUTED,
        )

        current_events = events_for_day(
            0,
            day_index,
        )

        draw_icon_group(
            image,
            current_events,
            cell_x
            + cell_w / 2,
            current_y
            + WEEK_CELL_H / 2,
        )

        next_text = (
            next_date
            .strftime("%d.%m.")
        )

        next_text_w = text_width(
            draw,
            next_text,
            FONT_DATE,
        )

        draw.text(
            (
                S(
                    cell_x
                    + cell_w / 2
                )
                - next_text_w / 2,
                S(
                    next_date_y
                    + 8
                ),
            ),
            next_text,
            font=FONT_DATE,
            fill=TEXT_MUTED,
        )

        next_events = events_for_day(
            1,
            day_index,
        )

        draw_icon_group(
            image,
            next_events,
            cell_x
            + cell_w / 2,
            next_icon_y
            + NEXT_WEEK_ICON_H / 2,
        )

        if day_index > 0:

            draw.line(
                (
                    S(cell_x),
                    S(y),
                    S(cell_x),
                    S(
                        y
                        + total_h
                    ),
                ),
                fill=GRID,
                width=S(1),
            )

    draw.line(
        (
            S(x),
            S(
                y
                + WEEK_HEADER_H
            ),
            S(
                x
                + width
            ),
            S(
                y
                + WEEK_HEADER_H
            ),
        ),
        fill=GRID,
        width=S(1),
    )

    draw.line(
        (
            S(x),
            S(next_date_y),
            S(
                x
                + width
            ),
            S(next_date_y),
        ),
        fill=GRID,
        width=S(1),
    )

    return total_h


# ============================================================
# Terminliste
# ============================================================

def event_list_height():

    count = max(
        1,
        len(
            sorted_events()
        ),
    )

    rows = math.ceil(
        count / 4
    )

    return (
        rows
        * EVENT_ROW_H
        + 10
    )


def draw_events_block(
    image,
    draw,
    week_start,
    x,
    y,
    width,
):

    height = event_list_height()

    events = sorted_events()

    start_y = y

    if not events:

        draw.text(
            (
                S(
                    x
                    + INNER_PAD
                ),
                S(
                    start_y
                    + 8
                ),
            ),
            "Keine besonderen Termine.",
            font=FONT_EVENT_META,
            fill=TEXT_MUTED,
        )

        return height

    gap = 18

    usable_w = (
        width
        - 2
        * INNER_PAD
    )

    col_w = (
        usable_w
        - gap * 3
    ) / 4

    for index, event in enumerate(
        events
    ):

        row = index // 4
        col = index % 4

        cell_x = (
            x
            + INNER_PAD
            + col
            * (
                col_w
                + gap
            )
        )

        cell_y = (
            start_y
            + row
            * EVENT_ROW_H
        )

        dt = event_date(
            week_start,
            event,
        )

        color = TYPE_COLORS.get(
            event["type"],
            TEXT,
        )

        draw_event_icon(
            image,
            event["type"],
            cell_x + 11,
            cell_y + 14,
            24,
            color,
        )

        text_x = (
            cell_x
            + 30
        )

        title = ellipsize(
            draw,
            event["title"],
            FONT_EVENT,
            col_w - 34,
        )

        draw.text(
            (
                S(text_x),
                S(
                    cell_y
                    + 4
                ),
            ),
            title,
            font=FONT_EVENT,
            fill=TEXT,
        )

        meta = dt.strftime(
            "%d.%m."
        )

        if event.get("time"):

            meta += (
                f" · "
                f"{event['time']}"
            )

        draw.text(
            (
                S(text_x),
                S(
                    cell_y
                    + 29
                ),
            ),
            meta,
            font=FONT_EVENT_META,
            fill=TEXT_MUTED,
        )

    return height


# ============================================================
# Abwesenheiten
# ============================================================

def absence_dates(
    week_start,
    item,
):

    start_dt = (
        week_start
        + timedelta(
            days=item[
                "start_offset"
            ]
        )
    )

    end_dt = (
        week_start
        + timedelta(
            days=item[
                "end_offset"
            ]
        )
    )

    return (
        start_dt,
        end_dt,
    )


def relevant_absences(
    week_start,
):

    range_end = (
        week_start
        + timedelta(days=13)
    )

    result = []

    for absence in ABSENCES:

        start_dt, end_dt = (
            absence_dates(
                week_start,
                absence,
            )
        )

        if (
            end_dt.date()
            >= week_start.date()
            and
            start_dt.date()
            <= range_end.date()
        ):

            result.append(
                absence
            )

    return result


def absence_block_height(
    week_start,
):

    count = max(
        1,
        len(
            relevant_absences(
                week_start
            )
        ),
    )

    rows = math.ceil(
        count / 4
    )

    return (
        44
        + rows
        * ABSENCE_ROW_H
    )


def draw_absences_block(
    draw,
    week_start,
    x,
    y,
    width,
    forced_height=None,
):

    items = relevant_absences(
        week_start
    )

    own_height = absence_block_height(
        week_start
    )

    height = max(
        own_height,
        forced_height or 0,
    )

    draw.text(
        (
            S(
                x
                + INNER_PAD
            ),
            S(y),
        ),
        "ABWESENHEIT",
        font=FONT_SECTION,
        fill=TEXT,
    )

    content_y = (
        y + 42
    )

    if not items:

        draw.text(
            (
                S(
                    x
                    + INNER_PAD
                ),
                S(
                    content_y
                    + 4
                ),
            ),
            "Keine",
            font=FONT_ABSENCE_DATE,
            fill=TEXT_MUTED,
        )

        return height

    gap = 18

    usable_w = (
        width
        - 2
        * INNER_PAD
    )

    col_w = (
        usable_w
        - gap * 3
    ) / 4

    for index, absence in enumerate(
        items
    ):

        row = index // 4
        col = index % 4

        cell_x = (
            x
            + INNER_PAD
            + col
            * (
                col_w
                + gap
            )
        )

        cell_y = (
            content_y
            + row
            * ABSENCE_ROW_H
        )

        start_dt, end_dt = (
            absence_dates(
                week_start,
                absence,
            )
        )

        draw.ellipse(
            (
                S(cell_x),
                S(
                    cell_y
                    + 8
                ),
                S(
                    cell_x
                    + 12
                ),
                S(
                    cell_y
                    + 20
                ),
            ),
            fill=ABSENCE,
        )

        name_x = (
            cell_x + 22
        )

        name = ellipsize(
            draw,
            absence["name"],
            FONT_ABSENCE,
            col_w - 24,
        )

        draw.text(
            (
                S(name_x),
                S(
                    cell_y
                    + 2
                ),
            ),
            name,
            font=FONT_ABSENCE,
            fill=TEXT,
        )

        date_text = (
            f"{start_dt.strftime('%d.%m.')} "
            f"– "
            f"{end_dt.strftime('%d.%m.')}"
        )

        draw.text(
            (
                S(name_x),
                S(
                    cell_y
                    + 30
                ),
            ),
            date_text,
            font=FONT_ABSENCE_DATE,
            fill=TEXT_MUTED,
        )

    return height


# ============================================================
# Gesamthöhe
# ============================================================

def calculate_total_height(
    week_start,
):

    week_overview_h = (
        WEEK_HEADER_H
        + WEEK_CELL_H
        + NEXT_WEEK_DATE_H
        + NEXT_WEEK_ICON_H
    )

    content_top = (
        TOP
        + TITLE_H
        + week_overview_h
        + SECTION_GAP
    )

    if LAYOUT_MODE == "columns":

        lower_h = max(
            event_list_height(),
            absence_block_height(
                week_start
            ),
        )

    else:

        lower_h = (
            event_list_height()
            + SECTION_GAP
            + absence_block_height(
                week_start
            )
        )

    return (
        content_top
        + lower_h
        + BOTTOM_PAD
    )


# ============================================================
# Kalender rendern
# ============================================================

def render_calendar():

    now = datetime.now(
        TIMEZONE
    )

    week_start = monday_of_week(
        now
    )

    total_h = calculate_total_height(
        week_start
    )

    image = create_background(
        WIDTH,
        total_h,
    )

    draw = ImageDraw.Draw(
        image
    )

    draw.text(
        (
            S(MARGIN_X),
            S(TOP),
        ),
        "WOCHENÜBERSICHT",
        font=FONT_TITLE,
        fill=TEXT,
    )

    draw.text(
        (
            S(MARGIN_X),
            S(
                TOP + 36
            ),
        ),
        week_title(
            week_start
        ),
        font=FONT_SUBTITLE,
        fill=TEXT_MUTED,
    )

    week_y = (
        TOP + TITLE_H
    )

    content_width = (
        WIDTH
        - 2
        * MARGIN_X
    )

    week_h = draw_week_overview(
        image,
        draw,
        week_start,
        now,
        MARGIN_X,
        week_y,
        content_width,
    )

    lower_y = (
        week_y
        + week_h
        + SECTION_GAP
    )

    if LAYOUT_MODE == "columns":

        gap = 18

        left_w = int(
            content_width
            * 0.60
        )

        right_w = (
            content_width
            - left_w
            - gap
        )

        left_h = event_list_height()

        right_h = absence_block_height(
            week_start
        )

        shared_h = max(
            left_h,
            right_h,
        )

        draw_events_block(
            image,
            draw,
            week_start,
            MARGIN_X,
            lower_y,
            left_w,
        )

        draw_absences_block(
            draw,
            week_start,
            MARGIN_X
            + left_w
            + gap,
            lower_y,
            right_w,
            forced_height=shared_h,
        )

    else:

        events_h = draw_events_block(
            image,
            draw,
            week_start,
            MARGIN_X,
            lower_y,
            content_width,
        )

        abs_y = (
            lower_y
            + events_h
            + SECTION_GAP
        )

        draw_absences_block(
            draw,
            week_start,
            MARGIN_X,
            abs_y,
            content_width,
        )

    image.save(
        OUTPUT_FILE,
        optimize=True,
    )

    print(
        f"Kalender erstellt: "
        f"{OUTPUT_FILE}"
    )


# ============================================================
# Discord State
# ============================================================

def load_state():

    if not STATE_FILE.exists():

        return {}

    try:

        return json.loads(
            STATE_FILE.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        return {}


def save_state(
    data,
):

    STATE_FILE.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


# ============================================================
# Multipart
# ============================================================

def multipart_body(
    payload_json,
    image_bytes,
):

    boundary = (
        "----Nyerk24Boundary"
        + uuid.uuid4().hex
    )

    body = io.BytesIO()

    def write_part(
        headers,
        content,
    ):

        body.write(
            f"--{boundary}\r\n"
            .encode()
        )

        for key, value in headers.items():

            body.write(
                f"{key}: {value}\r\n"
                .encode()
            )

        body.write(
            b"\r\n"
        )

        body.write(
            content
        )

        body.write(
            b"\r\n"
        )

    write_part(
        {
            "Content-Disposition":
                'form-data; name="payload_json"',
            "Content-Type":
                "application/json",
        },
        json.dumps(
            payload_json
        ).encode("utf-8"),
    )

    write_part(
        {
            "Content-Disposition":
                (
                    'form-data; '
                    'name="files[0]"; '
                    'filename="kalender.png"'
                ),
            "Content-Type":
                "image/png",
        },
        image_bytes,
    )

    body.write(
        f"--{boundary}--\r\n"
        .encode()
    )

    return (
        body.getvalue(),
        boundary,
    )


# ============================================================
# Discord Webhook
# ============================================================

def webhook_request(
    url,
    method="POST",
):

    payload = {
        "content": "",
        "embeds": [
            {
                "image": {
                    "url":
                        "attachment://kalender.png"
                }
            }
        ],
        "attachments": [
            {
                "id": 0,
                "filename":
                    "kalender.png",
            }
        ],
    }

    image_bytes = (
        OUTPUT_FILE
        .read_bytes()
    )

    body, boundary = (
        multipart_body(
            payload,
            image_bytes,
        )
    )

    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Content-Type":
                (
                    "multipart/form-data; "
                    f"boundary={boundary}"
                ),
            "User-Agent":
                "Nyerk24-Kalender",
        },
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:

            response_body = (
                response
                .read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            return (
                response.status,
                response_body,
            )

    except urllib.error.HTTPError as exc:

        response_body = (
            exc.read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        return (
            exc.code,
            response_body,
        )


def update_discord():

    if not WEBHOOK_URL:

        raise RuntimeError(
            "KALENDER_WEBHOOK ist nicht gesetzt."
        )

    state = load_state()

    message_id = state.get(
        "message_id"
    )

    if message_id:

        patch_url = (
            WEBHOOK_URL
            + "/messages/"
            + str(message_id)
        )

        status, response_body = (
            webhook_request(
                patch_url,
                method="PATCH",
            )
        )

        if 200 <= status < 300:

            print(
                "Bestehende Kalender-Nachricht aktualisiert."
            )

            return

        if status != 404:

            raise RuntimeError(
                "Discord PATCH fehlgeschlagen: "
                f"HTTP {status} · "
                f"{response_body}"
            )

        print(
            "Gespeicherte Kalender-Nachricht "
            "existiert nicht mehr. "
            "Neue Nachricht wird erstellt."
        )

    post_url = (
        WEBHOOK_URL
        + "?wait=true"
    )

    status, response_body = (
        webhook_request(
            post_url,
            method="POST",
        )
    )

    if not (
        200
        <= status
        < 300
    ):

        raise RuntimeError(
            "Discord POST fehlgeschlagen: "
            f"HTTP {status} · "
            f"{response_body}"
        )

    try:

        response_data = json.loads(
            response_body
        )

    except json.JSONDecodeError as exc:

        raise RuntimeError(
            "Discord hat keine gültige "
            "JSON-Antwort geliefert."
        ) from exc

    new_message_id = (
        response_data.get("id")
    )

    if not new_message_id:

        raise RuntimeError(
            "Discord-Antwort enthält "
            "keine message_id."
        )

    save_state({
        "message_id":
            new_message_id,
    })

    print(
        "Neue Kalender-Nachricht erstellt: "
        f"{new_message_id}"
    )


# ============================================================
# Main
# ============================================================

def main():

    print(
        "Nyerk24 Kalender startet."
    )

    load_calendar_data()

    render_calendar()

    update_discord()

    print(
        "Nyerk24 Kalender erfolgreich abgeschlossen."
    )


if __name__ == "__main__":

    main()
