import os
import json
import urllib.request
import urllib.error
import time
import uuid

from io import BytesIO
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont, ImageFilter


# ============================================================
# GRUNDEINSTELLUNGEN
# ============================================================

WEBHOOK_URL = os.environ.get("TRACKER_WEBHOOK")

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "tracker_data.json"
STATE_FILE = BASE_DIR / "tracker_message.json"

MAX_NETWORK_ATTEMPTS = 3
RETRY_DELAYS = (5, 15)

DISPLAY_NAMES = {
    "overview_card": "ÜBERSICHT",
    "rift": "Raumzeit-Riss",
    "rift_card": "RAUMZEIT-RISS",
    "shugo": "Shugofesta",
    "shugo_card": "SHUGOFESTA",
    "daily_reset": "Täglicher Reset",
    "weekly_reset": "Wöchentlicher Reset",
    "reset_card": "RESETS",
    "daily_card": "TÄGLICH",
    "weekly_card": "WÖCHENTLICH",
}

OVERVIEW_BACKGROUND_URL = (
    "https://raw.githubusercontent.com/"
    "Shaynah87/aion2-discord/main/Tracker/event_overview.png"
)

RIFT_BACKGROUND_URL = (
    "https://raw.githubusercontent.com/"
    "Shaynah87/aion2-discord/main/Tracker/spacetime_rift.png"
)

SHUGO_BACKGROUND_URL = (
    "https://raw.githubusercontent.com/"
    "Shaynah87/aion2-discord/main/Tracker/shugo_games.png"
)

RESET_BACKGROUND_URL = (
    "https://raw.githubusercontent.com/"
    "Shaynah87/aion2-discord/main/Tracker/resets.png"
)

OVERVIEW_CARD_FILE = BASE_DIR / "event_overview_card.png"
RIFT_CARD_FILE = BASE_DIR / "spacetime_rift_card.png"
SHUGO_CARD_FILE = BASE_DIR / "shugo_games_card.png"
RESET_CARD_FILE = BASE_DIR / "resets_card.png"

CLOSE_GAP = 20
SECTION_GAP = 56
ACTIVE_EVENT_GAP = 34
NEXT_ENTRY_GAP = 18

MAX_OVERVIEW_EVENTS = 5
RESET_OVERVIEW_LEAD_HOURS = 3

RIFT_COLOR = (255, 78, 88, 255)
SHUGO_COLOR = (229, 177, 62, 255)
RESET_COLOR = (64, 145, 255, 255)

COMPACT_CARD_WIDTH = 1200
COMPACT_CARD_HEIGHT = 440


# ============================================================
# DATEN UND STATUS
# ============================================================

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_state(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ============================================================
# SCHRIFTEN UND TEXTHILFEN
# ============================================================

def load_font(size, bold=False):
    if bold:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
    else:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]

    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)

    return ImageFont.load_default()


def text_y_after(draw, previous_bbox, next_text, next_font, visual_gap):
    probe = draw.textbbox((0, 0), next_text, font=next_font)
    return previous_bbox[3] + visual_gap - probe[1]


def format_time_range(start, end):
    return (
        f"{start.strftime('%H:%M')} – "
        f"{end.strftime('%H:%M')} Uhr"
    )


def draw_text_with_shadow(
    draw,
    position,
    text,
    font,
    fill,
    shadow_offset=2,
):
    x, y = position

    draw.text(
        (x + shadow_offset, y + shadow_offset),
        text,
        font=font,
        fill=(0, 0, 0, 200),
    )

    draw.text(
        position,
        text,
        font=font,
        fill=fill,
    )


def draw_event_marker(draw, x, y, color, size=16):
    draw.ellipse(
        (x, y, x + size, y + size),
        fill=color,
    )


# ============================================================
# RESET-ZEITEN
# ============================================================

def next_daily_reset(reset_data, timezone):
    now = datetime.now(timezone)
    utc = ZoneInfo("UTC")

    hour, minute = map(
        int,
        reset_data["daily_utc"].split(":"),
    )

    now_utc = now.astimezone(utc)

    candidate_utc = now_utc.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )

    if candidate_utc <= now_utc:
        candidate_utc += timedelta(days=1)

    return candidate_utc.astimezone(timezone)


def next_weekly_reset(reset_data, timezone):
    now = datetime.now(timezone)
    utc = ZoneInfo("UTC")

    weekday_map = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }

    target_weekday = weekday_map[
        reset_data["weekly_day"]
    ]

    hour, minute = map(
        int,
        reset_data["weekly_utc"].split(":"),
    )

    now_utc = now.astimezone(utc)

    days_ahead = (
        target_weekday - now_utc.weekday()
    ) % 7

    candidate_utc = (
        now_utc + timedelta(days=days_ahead)
    ).replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )

    if candidate_utc <= now_utc:
        candidate_utc += timedelta(days=7)

    return candidate_utc.astimezone(timezone)


# ============================================================
# RAUMZEIT-RISS
# ============================================================

def build_rift_times(rift_data, timezone):
    now = datetime.now(timezone)
    utc = ZoneInfo("UTC")
    now_utc = now.astimezone(utc)

    hour, minute = map(
        int,
        rift_data["first_start_utc"].split(":"),
    )

    first_start_utc = now_utc.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )

    interval = timedelta(
        hours=rift_data["interval_hours"]
    )

    duration = timedelta(
        minutes=rift_data["duration_minutes"]
    )

    starts_utc = []

    start_utc = (
        first_start_utc - timedelta(days=1)
    )

    end_limit_utc = (
        first_start_utc + timedelta(days=2)
    )

    while start_utc <= end_limit_utc:
        starts_utc.append(start_utc)
        start_utc += interval

    starts = [
        start_time.astimezone(timezone)
        for start_time in starts_utc
    ]

    active_start = None
    active_end = None

    for start_time in starts:
        end_time = start_time + duration

        if start_time <= now < end_time:
            active_start = start_time
            active_end = end_time
            break

    future_starts = sorted(
        start_time
        for start_time in starts
        if start_time > now
    )

    return {
        "active_start": active_start,
        "active_end": active_end,
        "next_start": future_starts[0],
        "following_start": future_starts[1],
    }


# ============================================================
# SHUGOFESTA
# ============================================================

def build_shugo_times(shugo_data, timezone):
    now = datetime.now(timezone)

    start_minute = shugo_data["start_minute"]

    duration = timedelta(
        minutes=shugo_data["duration_minutes"]
    )

    candidates = []

    for day_offset in range(-1, 2):
        day = now + timedelta(days=day_offset)

        for hour in range(24):
            candidates.append(
                day.replace(
                    hour=hour,
                    minute=start_minute,
                    second=0,
                    microsecond=0,
                )
            )

    candidates.sort()

    active_start = None
    active_end = None

    for start_time in candidates:
        end_time = start_time + duration

        if start_time <= now < end_time:
            active_start = start_time
            active_end = end_time
            break

    future_starts = sorted(
        start_time
        for start_time in candidates
        if start_time > now
    )

    return {
        "active_start": active_start,
        "active_end": active_end,
        "next_start": future_starts[0],
        "following_start": future_starts[1],
    }


# ============================================================
# ÜBERSICHTSDATEN
# ============================================================

def build_event_overview(
    rift_times,
    shugo_times,
    daily_reset,
    weekly_reset,
    timezone,
):
    now = datetime.now(timezone)

    active_events = []
    upcoming_events = []

    if rift_times["active_start"]:
        active_events.append({
            "key": "rift",
            "name": DISPLAY_NAMES["rift"],
            "end": rift_times["active_end"],
            "color": RIFT_COLOR,
        })

    if shugo_times["active_start"]:
        active_events.append({
            "key": "shugo",
            "name": DISPLAY_NAMES["shugo"],
            "end": shugo_times["active_end"],
            "color": SHUGO_COLOR,
        })

    upcoming_events.append({
        "key": "rift",
        "name": DISPLAY_NAMES["rift"],
        "time": rift_times["next_start"],
        "color": RIFT_COLOR,
    })

    upcoming_events.append({
        "key": "shugo",
        "name": DISPLAY_NAMES["shugo"],
        "time": shugo_times["next_start"],
        "color": SHUGO_COLOR,
    })

    if (
        timedelta(0)
        <= daily_reset - now
        <= timedelta(hours=RESET_OVERVIEW_LEAD_HOURS)
    ):
        if daily_reset == weekly_reset:
            upcoming_events.append({
                "key": "weekly_reset",
                "name": DISPLAY_NAMES["weekly_reset"],
                "time": weekly_reset,
                "color": RESET_COLOR,
            })
        else:
            upcoming_events.append({
                "key": "daily_reset",
                "name": DISPLAY_NAMES["daily_reset"],
                "time": daily_reset,
                "color": RESET_COLOR,
            })

    upcoming_events.sort(
        key=lambda item: item["time"]
    )

    return {
        "active": active_events,
        "next": upcoming_events[:MAX_OVERVIEW_EVENTS],
    }


# ============================================================
# NETZWERK
# ============================================================

def run_with_retry(operation, description):
    for attempt in range(
        1,
        MAX_NETWORK_ATTEMPTS + 1,
    ):
        try:
            result = operation()

            if attempt > 1:
                print(
                    f"{description}: erfolgreich im Versuch "
                    f"{attempt}/{MAX_NETWORK_ATTEMPTS}."
                )

            return result

        except urllib.error.HTTPError as exc:
            retryable = (
                exc.code == 429
                or 500 <= exc.code <= 599
            )

            if (
                not retryable
                or attempt >= MAX_NETWORK_ATTEMPTS
            ):
                raise

            delay = RETRY_DELAYS[attempt - 1]

            retry_after = exc.headers.get(
                "Retry-After"
            )

            if retry_after:
                try:
                    delay = max(
                        delay,
                        float(retry_after),
                    )
                except (TypeError, ValueError):
                    pass

            time.sleep(delay)

        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
        ):
            if attempt >= MAX_NETWORK_ATTEMPTS:
                raise

            delay = RETRY_DELAYS[attempt - 1]
            time.sleep(delay)


def load_image_from_url(url):
    def download():
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AION2-Schedule-Bot"
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:
            return response.read()

    image_data = run_with_retry(
        download,
        "Hintergrundbild laden",
    )

    return Image.open(
        BytesIO(image_data)
    ).convert("RGBA")


def load_overview_background():
    return load_image_from_url(
        OVERVIEW_BACKGROUND_URL
    )


def load_rift_background():
    return load_image_from_url(
        RIFT_BACKGROUND_URL
    )


def load_shugo_background():
    return load_image_from_url(
        SHUGO_BACKGROUND_URL
    )


def load_reset_background():
    return load_image_from_url(
        RESET_BACKGROUND_URL
    )


# ============================================================
# BILDHILFEN
# ============================================================

def crop_and_resize(
    image,
    target_width,
    target_height,
):
    source_width, source_height = image.size

    source_ratio = (
        source_width / source_height
    )

    target_ratio = (
        target_width / target_height
    )

    if source_ratio > target_ratio:
        new_width = int(
            source_height * target_ratio
        )

        left = (
            source_width - new_width
        ) // 2

        image = image.crop((
            left,
            0,
            left + new_width,
            source_height,
        ))

    else:
        new_height = int(
            source_width / target_ratio
        )

        top = (
            source_height - new_height
        ) // 2

        image = image.crop((
            0,
            top,
            source_width,
            top + new_height,
        ))

    return image.resize(
        (target_width, target_height),
        Image.Resampling.LANCZOS,
    )


def prepare_overview_background(
    image,
    target_width,
    target_height,
):
    source_width, source_height = image.size

    crop_left = int(source_width * 0.025)
    crop_right = int(source_width * 0.025)
    crop_top = int(source_height * 0.03)
    crop_bottom = int(source_height * 0.03)

    image = image.crop((
        crop_left,
        crop_top,
        source_width - crop_right,
        source_height - crop_bottom,
    ))

    return image.resize(
        (target_width, target_height),
        Image.Resampling.LANCZOS,
    )


def add_strong_left_gradient(
    image,
    solid_ratio,
    fade_ratio,
    max_alpha,
    tone,
):
    width, height = image.size

    overlay = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0),
    )

    pixels = overlay.load()

    solid_end = int(
        width * solid_ratio
    )

    fade_end = int(
        width * fade_ratio
    )

    for x in range(fade_end):
        if x <= solid_end:
            alpha = max_alpha
        else:
            progress = (
                (x - solid_end)
                / (fade_end - solid_end)
            )

            alpha = int(
                max_alpha
                * (1.0 - progress) ** 1.65
            )

        for y in range(height):
            pixels[x, y] = (
                tone[0],
                tone[1],
                tone[2],
                alpha,
            )

    return Image.alpha_composite(
        image,
        overlay,
    )


# ============================================================
# ÜBERSICHTSKARTE
# BISHERIGE GESTALTUNG BEIBEHALTEN
# ============================================================

def create_overview_card(event_overview):
    active_events = event_overview["active"]
    next_events = event_overview["next"]

    title_font = load_font(56, bold=True)
    status_font = load_font(31, bold=True)
    active_name_font = load_font(48, bold=True)
    active_until_font = load_font(30)
    secondary_font = load_font(30)
    secondary_bold_font = load_font(30, bold=True)

    white = (250, 249, 252, 255)
    soft_white = (225, 222, 225, 255)
    status_gray = (170, 170, 176, 255)

    title_x = 74
    title_y = 58
    title_text = DISPLAY_NAMES["overview_card"]

    measure_image = Image.new(
        "RGBA",
        (1200, 4000),
        (0, 0, 0, 0),
    )

    measure_draw = ImageDraw.Draw(
        measure_image
    )

    title_bbox = measure_draw.textbbox(
        (title_x, title_y),
        title_text,
        font=title_font,
    )

    if active_events:
        status_text = "JETZT AKTIV"

        status_y = text_y_after(
            measure_draw,
            title_bbox,
            status_text,
            status_font,
            SECTION_GAP,
        )

        status_bbox = measure_draw.textbbox(
            (76, status_y),
            status_text,
            font=status_font,
        )

        first_active_text = (
            active_events[0]["name"].upper()
        )

        current_y = text_y_after(
            measure_draw,
            status_bbox,
            first_active_text,
            active_name_font,
            CLOSE_GAP,
        )

        last_active_bottom = None

        for event_index, event in enumerate(
            active_events
        ):
            event_name = event["name"].upper()

            if event_index > 0:
                event_probe = measure_draw.textbbox(
                    (0, 0),
                    event_name,
                    font=active_name_font,
                )

                current_y = (
                    last_active_bottom
                    + ACTIVE_EVENT_GAP
                    - event_probe[1]
                )

            name_bbox = measure_draw.textbbox(
                (108, current_y),
                event_name,
                font=active_name_font,
            )

            until_y = name_bbox[3] + 4

            until_text = (
                f"bis {event['end'].strftime('%H:%M')} Uhr"
            )

            until_bbox = measure_draw.textbbox(
                (108, until_y),
                until_text,
                font=active_until_font,
            )

            last_active_bottom = until_bbox[3]

        next_title_text = "→ Als Nächstes:"
        next_title_font = secondary_bold_font
        next_title_color = white

        next_title_probe = measure_draw.textbbox(
            (0, 0),
            next_title_text,
            font=next_title_font,
        )

        next_section_y = (
            last_active_bottom
            + SECTION_GAP
            - next_title_probe[1]
        )

    else:
        next_title_text = "ALS NÄCHSTES"
        next_title_font = status_font
        next_title_color = status_gray

        next_section_y = text_y_after(
            measure_draw,
            title_bbox,
            next_title_text,
            next_title_font,
            SECTION_GAP,
        )

    next_title_bbox = measure_draw.textbbox(
        (76, next_section_y),
        next_title_text,
        font=next_title_font,
    )

    if next_events:
        first_next_text = (
            f"{next_events[0]['name']} · "
            f"{next_events[0]['time'].strftime('%H:%M')} Uhr"
        )

        current_y = text_y_after(
            measure_draw,
            next_title_bbox,
            first_next_text,
            secondary_font,
            CLOSE_GAP,
        )

        last_next_bottom = next_title_bbox[3]

        for event_index, event in enumerate(
            next_events
        ):
            next_text = (
                f"{event['name']} · "
                f"{event['time'].strftime('%H:%M')} Uhr"
            )

            if event_index > 0:
                next_probe = measure_draw.textbbox(
                    (0, 0),
                    next_text,
                    font=secondary_font,
                )

                current_y = (
                    last_next_bottom
                    + NEXT_ENTRY_GAP
                    - next_probe[1]
                )

            next_bbox = measure_draw.textbbox(
                (106, current_y),
                next_text,
                font=secondary_font,
            )

            last_next_bottom = next_bbox[3]

    else:
        last_next_bottom = next_title_bbox[3]

    target_width = 1200

    target_height = max(
        last_next_bottom + 58,
        360,
    )

    image = load_overview_background()

    image = prepare_overview_background(
        image,
        target_width,
        target_height,
    )

    image = add_strong_left_gradient(
        image,
        solid_ratio=0.28,
        fade_ratio=0.78,
        max_alpha=230,
        tone=(2, 2, 3),
    )

    draw = ImageDraw.Draw(
        image,
        "RGBA",
    )

    draw_text_with_shadow(
        draw,
        (title_x, title_y),
        title_text,
        title_font,
        white,
    )

    title_bbox = draw.textbbox(
        (title_x, title_y),
        title_text,
        font=title_font,
    )

    if active_events:
        status_text = "JETZT AKTIV"

        status_y = text_y_after(
            draw,
            title_bbox,
            status_text,
            status_font,
            SECTION_GAP,
        )

        draw_text_with_shadow(
            draw,
            (76, status_y),
            status_text,
            status_font,
            status_gray,
        )

        status_bbox = draw.textbbox(
            (76, status_y),
            status_text,
            font=status_font,
        )

        first_active_text = (
            active_events[0]["name"].upper()
        )

        current_y = text_y_after(
            draw,
            status_bbox,
            first_active_text,
            active_name_font,
            CLOSE_GAP,
        )

        last_active_bottom = None

        for event_index, event in enumerate(
            active_events
        ):
            event_name = event["name"].upper()

            if event_index > 0:
                event_probe = draw.textbbox(
                    (0, 0),
                    event_name,
                    font=active_name_font,
                )

                current_y = (
                    last_active_bottom
                    + ACTIVE_EVENT_GAP
                    - event_probe[1]
                )

            draw_event_marker(
                draw,
                78,
                current_y + 18,
                event["color"],
                size=18,
            )

            draw_text_with_shadow(
                draw,
                (108, current_y),
                event_name,
                active_name_font,
                white,
            )

            name_bbox = draw.textbbox(
                (108, current_y),
                event_name,
                font=active_name_font,
            )

            until_y = name_bbox[3] + 4

            until_text = (
                f"bis {event['end'].strftime('%H:%M')} Uhr"
            )

            draw_text_with_shadow(
                draw,
                (108, until_y),
                until_text,
                active_until_font,
                soft_white,
            )

            until_bbox = draw.textbbox(
                (108, until_y),
                until_text,
                font=active_until_font,
            )

            last_active_bottom = until_bbox[3]

        next_title_text = "→ Als Nächstes:"
        next_title_font = secondary_bold_font
        next_title_color = white

        next_title_probe = draw.textbbox(
            (0, 0),
            next_title_text,
            font=next_title_font,
        )

        next_section_y = (
            last_active_bottom
            + SECTION_GAP
            - next_title_probe[1]
        )

    else:
        next_title_text = "ALS NÄCHSTES"
        next_title_font = status_font
        next_title_color = status_gray

        next_section_y = text_y_after(
            draw,
            title_bbox,
            next_title_text,
            next_title_font,
            SECTION_GAP,
        )

    draw_text_with_shadow(
        draw,
        (76, next_section_y),
        next_title_text,
        next_title_font,
        next_title_color,
    )

    next_title_bbox = draw.textbbox(
        (76, next_section_y),
        next_title_text,
        font=next_title_font,
    )

    if next_events:
        first_next_text = (
            f"{next_events[0]['name']} · "
            f"{next_events[0]['time'].strftime('%H:%M')} Uhr"
        )

        current_y = text_y_after(
            draw,
            next_title_bbox,
            first_next_text,
            secondary_font,
            CLOSE_GAP,
        )

        last_next_bottom = next_title_bbox[3]

        for event_index, event in enumerate(
            next_events
        ):
            next_text = (
                f"{event['name']} · "
                f"{event['time'].strftime('%H:%M')} Uhr"
            )

            if event_index > 0:
                next_probe = draw.textbbox(
                    (0, 0),
                    next_text,
                    font=secondary_font,
                )

                current_y = (
                    last_next_bottom
                    + NEXT_ENTRY_GAP
                    - next_probe[1]
                )

            draw_event_marker(
                draw,
                78,
                current_y + 8,
                event["color"],
                size=16,
            )

            draw_text_with_shadow(
                draw,
                (106, current_y),
                next_text,
                secondary_font,
                soft_white,
            )

            next_bbox = draw.textbbox(
                (106, current_y),
                next_text,
                font=secondary_font,
            )

            last_next_bottom = next_bbox[3]

    image.convert("RGB").save(
        OVERVIEW_CARD_FILE,
        "PNG",
        optimize=True,
    )


# ============================================================
# KOMPAKTE HINTERGRUNDBILDER
# KEIN ABSCHNEIDEN DER MOTIVE
# ============================================================

def fit_background(
    image,
    width=COMPACT_CARD_WIDTH,
    height=COMPACT_CARD_HEIGHT,
    focus_x=0.70,
    focus_y=0.50,
):
    """
    Verkleinert das vollständige Originalbild proportional.

    Der sichtbare Vordergrund wird nicht beschnitten.
    Freie Bereiche werden durch einen weichgezeichneten,
    abgedunkelten Hintergrund ergänzt.
    """

    image = image.convert("RGBA")

    iw, ih = image.size

    scale = min(
        width / iw,
        height / ih,
    )

    nw = max(1, round(iw * scale))
    nh = max(1, round(ih * scale))

    fitted = image.resize(
        (nw, nh),
        Image.Resampling.LANCZOS,
    )

    base = crop_and_resize(
        image,
        width,
        height,
    )

    base = base.filter(
        ImageFilter.GaussianBlur(24)
    )

    dark_background = Image.new(
        "RGBA",
        (width, height),
        (6, 8, 13, 255),
    )

    base = Image.blend(
        base,
        dark_background,
        0.42,
    )

    x = round(
        (width - nw) * focus_x
    )

    y = round(
        (height - nh) * focus_y
    )

    base.alpha_composite(
        fitted,
        (x, y),
    )

    return base


# ============================================================
# TEXTBLÖCKE VERTIKAL ZENTRIEREN
# ============================================================

def draw_centered_text_block(
    draw,
    lines,
    height,
    x=78,
    gaps=None,
):
    """
    Misst alle sichtbaren Textzeilen.

    Der gesamte Block wird so positioniert, dass der
    sichtbare Abstand oben und unten gleich groß ist.
    """

    if gaps is None:
        gaps = [10] * (len(lines) - 1)

    boxes = [
        draw.textbbox(
            (0, 0),
            value,
            font=font,
        )
        for value, font, _ in lines
    ]

    sizes = [
        box[3] - box[1]
        for box in boxes
    ]

    block_height = (
        sum(sizes) + sum(gaps)
    )

    visual_top = (
        height - block_height
    ) / 2

    for (
        (value, font, color),
        box,
        line_height,
        gap,
    ) in zip(
        lines,
        boxes,
        sizes,
        gaps + [0],
    ):
        y = round(
            visual_top - box[1]
        )

        draw_text_with_shadow(
            draw,
            (x, y),
            value,
            font,
            color,
        )

        visual_top += (
            line_height + gap
        )


# ============================================================
# RAUMZEIT-RISS-KARTE
# ============================================================

def create_rift_card(
    rift_data,
    rift_times,
):
    width = COMPACT_CARD_WIDTH
    height = COMPACT_CARD_HEIGHT

    image = fit_background(
        load_rift_background(),
        width,
        height,
        focus_x=0.70,
    )

    image = add_strong_left_gradient(
        image,
        solid_ratio=0.28,
        fade_ratio=0.78,
        max_alpha=238,
        tone=(2, 1, 3),
    )

    draw = ImageDraw.Draw(
        image,
        "RGBA",
    )

    title_font = load_font(56, True)
    subtitle_font = load_font(29)
    status_font = load_font(31, True)
    time_font = load_font(48, True)
    secondary_font = load_font(30)

    if rift_times["active_start"]:
        label = "JETZT AKTIV"
        start = rift_times["active_start"]
        end = rift_times["active_end"]

        second_label = "Nächster"
        second_start = rift_times["next_start"]

    else:
        label = "NÄCHSTER"
        start = rift_times["next_start"]

        end = start + timedelta(
            minutes=rift_data["duration_minutes"]
        )

        second_label = "Danach"
        second_start = rift_times["following_start"]

    second_end = second_start + timedelta(
        minutes=rift_data["duration_minutes"]
    )

    lines = [
        (
            DISPLAY_NAMES["rift_card"],
            title_font,
            (250, 248, 251, 255),
        ),
        (
            f"Alle {rift_data['interval_hours']} Stunden",
            subtitle_font,
            (255, 135, 140, 255),
        ),
        (
            label,
            status_font,
            (255, 78, 88, 255),
        ),
        (
            format_time_range(start, end),
            time_font,
            (250, 248, 251, 255),
        ),
        (
            (
                f"→ {second_label}: "
                f"{format_time_range(second_start, second_end)}"
            ),
            secondary_font,
            (225, 222, 225, 255),
        ),
    ]

    draw_centered_text_block(
        draw,
        lines,
        height,
        gaps=[10, 26, 10, 22],
    )

    image.convert("RGB").save(
        RIFT_CARD_FILE,
        "PNG",
        optimize=True,
    )


# ============================================================
# SHUGOFESTA-KARTE
# ============================================================

def create_shugo_card(
    shugo_data,
    shugo_times,
):
    width = COMPACT_CARD_WIDTH
    height = COMPACT_CARD_HEIGHT

    image = fit_background(
        load_shugo_background(),
        width,
        height,
        focus_x=0.75,
    )

    image = add_strong_left_gradient(
        image,
        solid_ratio=0.28,
        fade_ratio=0.78,
        max_alpha=225,
        tone=(3, 3, 2),
    )

    draw = ImageDraw.Draw(
        image,
        "RGBA",
    )

    title_font = load_font(56, True)
    subtitle_font = load_font(29)
    status_font = load_font(31, True)
    time_font = load_font(48, True)
    secondary_font = load_font(30)

    if shugo_times["active_start"]:
        label = "JETZT AKTIV"
        start = shugo_times["active_start"]

        second_label = "Nächstes"
        second_start = shugo_times["next_start"]

    else:
        label = "NÄCHSTES"
        start = shugo_times["next_start"]

        second_label = "Danach"
        second_start = shugo_times["following_start"]

    lines = [
        (
            DISPLAY_NAMES["shugo_card"],
            title_font,
            (250, 248, 245, 255),
        ),
        (
            "Stündlich",
            subtitle_font,
            (243, 210, 126, 255),
        ),
        (
            label,
            status_font,
            (229, 177, 62, 255),
        ),
        (
            f"{start.strftime('%H:%M')} Uhr",
            time_font,
            (250, 248, 245, 255),
        ),
        (
            (
                f"→ {second_label}: "
                f"{second_start.strftime('%H:%M')} Uhr"
            ),
            secondary_font,
            (225, 222, 225, 255),
        ),
    ]

    draw_centered_text_block(
        draw,
        lines,
        height,
        gaps=[10, 26, 10, 22],
    )

    image.convert("RGB").save(
        SHUGO_CARD_FILE,
        "PNG",
        optimize=True,
    )


# ============================================================
# RESET-KARTE
# ============================================================

def create_reset_card(
    daily_reset,
    weekly_reset,
):
    width = COMPACT_CARD_WIDTH
    height = COMPACT_CARD_HEIGHT

    image = fit_background(
        load_reset_background(),
        width,
        height,
        focus_x=0.75,
    )

    image = add_strong_left_gradient(
        image,
        solid_ratio=0.32,
        fade_ratio=0.82,
        max_alpha=245,
        tone=(1, 3, 7),
    )

    draw = ImageDraw.Draw(
        image,
        "RGBA",
    )

    title_font = load_font(56, True)
    label_font = load_font(30, True)
    time_font = load_font(46, True)

    weekdays = [
        "Montag",
        "Dienstag",
        "Mittwoch",
        "Donnerstag",
        "Freitag",
        "Samstag",
        "Sonntag",
    ]

    weekly_day = weekdays[
        weekly_reset.weekday()
    ]

    lines = [
        (
            DISPLAY_NAMES["reset_card"],
            title_font,
            (248, 250, 255, 255),
        ),
        (
            DISPLAY_NAMES["daily_card"],
            label_font,
            (110, 190, 255, 255),
        ),
        (
            f"{daily_reset.strftime('%H:%M')} Uhr",
            time_font,
            (248, 250, 255, 255),
        ),
        (
            DISPLAY_NAMES["weekly_card"],
            label_font,
            (64, 145, 255, 255),
        ),
        (
            (
                f"{weekly_day} · "
                f"{weekly_reset.strftime('%H:%M')} Uhr"
            ),
            time_font,
            (248, 250, 255, 255),
        ),
    ]

    draw_centered_text_block(
        draw,
        lines,
        height,
        gaps=[22, 8, 22, 8],
    )

    image.convert("RGB").save(
        RESET_CARD_FILE,
        "PNG",
        optimize=True,
    )


# ============================================================
# ALLE VIER KARTEN ERSTELLEN
# ============================================================

def build_embeds(data):
    timezone = ZoneInfo(
        data["timezone"]
    )

    rift_data = data["rift"]
    shugo_data = data["shugo_festa"]
    reset_data = data["resets"]

    rift_times = build_rift_times(
        rift_data,
        timezone,
    )

    create_rift_card(
        rift_data,
        rift_times,
    )

    shugo_times = build_shugo_times(
        shugo_data,
        timezone,
    )

    create_shugo_card(
        shugo_data,
        shugo_times,
    )

    daily_reset = next_daily_reset(
        reset_data,
        timezone,
    )

    weekly_reset = next_weekly_reset(
        reset_data,
        timezone,
    )

    create_reset_card(
        daily_reset,
        weekly_reset,
    )

    event_overview = build_event_overview(
        rift_times,
        shugo_times,
        daily_reset,
        weekly_reset,
        timezone,
    )

    create_overview_card(
        event_overview
    )

    overview_embed = {
        "color": 8027525,
        "image": {
            "url": "attachment://event_overview_card.png"
        },
    }

    rift_embed = {
        "color": 14555706,
        "image": {
            "url": "attachment://spacetime_rift_card.png"
        },
    }

    shugo_embed = {
        "color": 14525510,
        "image": {
            "url": "attachment://shugo_games_card.png"
        },
    }

    reset_embed = {
        "color": 4231679,
        "image": {
            "url": "attachment://resets_card.png"
        },
    }

    return [
        overview_embed,
        rift_embed,
        shugo_embed,
        reset_embed,
    ]


# ============================================================
# DISCORD-WEBHOOK
# ============================================================

def _webhook_request_with_files_once(
    url,
    payload,
    file_paths,
    method="POST",
):
    boundary = (
        "----AION2Boundary"
        + uuid.uuid4().hex
    )

    body = bytearray()

    body.extend(
        (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; "
            f'name="payload_json"\r\n'
            f"Content-Type: application/json\r\n\r\n"
        ).encode("utf-8")
    )

    body.extend(
        json.dumps(payload).encode("utf-8")
    )

    body.extend(b"\r\n")

    for index, file_path in enumerate(
        file_paths
    ):
        with open(file_path, "rb") as f:
            file_data = f.read()

        body.extend(
            (
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; "
                f'name="files[{index}]"; '
                f'filename="{os.path.basename(file_path)}"\r\n'
                f"Content-Type: image/png\r\n\r\n"
            ).encode("utf-8")
        )

        body.extend(file_data)
        body.extend(b"\r\n")

    body.extend(
        (
            f"--{boundary}--\r\n"
        ).encode("utf-8")
    )

    req = urllib.request.Request(
        url,
        data=bytes(body),
        method=method,
        headers={
            "Content-Type": (
                f"multipart/form-data; boundary={boundary}"
            ),
            "User-Agent": "AION2-Schedule-Bot",
        },
    )

    with urllib.request.urlopen(
        req,
        timeout=60,
    ) as response:
        response_data = response.read()

        if not response_data:
            return {}

        return json.loads(
            response_data.decode("utf-8")
        )


def webhook_request_with_files(
    url,
    payload,
    file_paths,
    method="POST",
):
    return run_with_retry(
        lambda: _webhook_request_with_files_once(
            url,
            payload,
            file_paths,
            method=method,
        ),
        f"Discord {method}",
    )


# ============================================================
# HAUPTPROGRAMM
# ============================================================

def main():
    if not WEBHOOK_URL:
        raise RuntimeError(
            "TRACKER_WEBHOOK fehlt."
        )

    data = load_data()
    state = load_state()

    embeds = build_embeds(data)

    payload = {
        "content": "",
        "embeds": embeds,
        "attachments": [
            {
                "id": 0,
                "filename": OVERVIEW_CARD_FILE.name,
            },
            {
                "id": 1,
                "filename": RIFT_CARD_FILE.name,
            },
            {
                "id": 2,
                "filename": SHUGO_CARD_FILE.name,
            },
            {
                "id": 3,
                "filename": RESET_CARD_FILE.name,
            },
        ],
    }

    message_id = state.get(
        "message_id"
    )

    files = [
        OVERVIEW_CARD_FILE,
        RIFT_CARD_FILE,
        SHUGO_CARD_FILE,
        RESET_CARD_FILE,
    ]

    if message_id:
        edit_url = (
            f"{WEBHOOK_URL}"
            f"/messages/{message_id}"
        )

        webhook_request_with_files(
            edit_url,
            payload,
            files,
            method="PATCH",
        )

        print(
            "Bestehende Veranstaltungs-Nachricht aktualisiert."
        )

    else:
        create_url = (
            f"{WEBHOOK_URL}?wait=true"
        )

        result = webhook_request_with_files(
            create_url,
            payload,
            files,
            method="POST",
        )

        save_state({
            "message_id": result["id"]
        })

        print(
            "Neue Veranstaltungs-Nachricht erstellt."
        )


if __name__ == "__main__":
    main()
