import os
import json
import urllib.request
import uuid
from io import BytesIO
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


WEBHOOK_URL = os.environ.get("AION_SCHEDULE_WEBHOOK")

DATA_FILE = "schedule_data.json"
STATE_FILE = "schedule_message.json"


# ============================================================
# ANZEIGENAMEN
# ============================================================

DISPLAY_NAMES = {
    "overview_card": "ÜBERSICHT",

    "rift": "Spacetime Rift",
    "rift_card": "SPACETIME RIFT",

    "shugo": "Shugo Festival",
    "shugo_card": "SHUGO FESTIVAL",

    "daily_reset": "Täglicher Reset",
    "weekly_reset": "Wöchentlicher Reset",

    "reset_card": "RESETS",
    "daily_card": "TÄGLICH",
    "weekly_card": "WÖCHENTLICH",
}


# ============================================================
# HINTERGRUNDBILDER
# ============================================================

OVERVIEW_BACKGROUND_URL = (
    "https://raw.githubusercontent.com/"
    "Shaynah87/aion2-discord/main/event_overview.png"
)

RIFT_BACKGROUND_URL = (
    "https://raw.githubusercontent.com/"
    "Shaynah87/aion2-discord/main/spacetime_rift.png"
)

SHUGO_BACKGROUND_URL = (
    "https://raw.githubusercontent.com/"
    "Shaynah87/aion2-discord/main/shugo_games.png"
)

RESET_BACKGROUND_URL = (
    "https://raw.githubusercontent.com/"
    "Shaynah87/aion2-discord/main/resets.png"
)


# ============================================================
# AUSGABEDATEIEN
# ============================================================

OVERVIEW_CARD_FILE = "event_overview_card.png"
RIFT_CARD_FILE = "spacetime_rift_card.png"
SHUGO_CARD_FILE = "shugo_games_card.png"
RESET_CARD_FILE = "resets_card.png"


# ============================================================
# GEMEINSAMES VISUELLES RASTER
#
# SHUGO ist die Referenz.
#
# CLOSE_GAP
#   enger Abstand innerhalb eines zusammengehörigen Blocks:
#   Titel -> Untertitel
#   Status -> Uhrzeit
#   Blocktitel -> Inhalt
#
# SECTION_GAP
#   Abstand zwischen eigenständigen Bereichen:
#   Untertitel -> NÄCHSTES
#   RESETS -> TÄGLICH
#   ÜBERSICHT -> ALS NÄCHSTES / JETZT AKTIV
#   täglicher Block -> wöchentlicher Block
#
# AFTER_CONTENT_GAP
#   Abstand nach dem eigentlichen Hauptinhalt zu
#   "Danach" / "Nächster".
#
# Die Werte beziehen sich auf die SICHTBAREN Textkanten,
# nicht einfach auf Y-Koordinaten.
# ============================================================

CLOSE_GAP = 20
SECTION_GAP = 47
AFTER_CONTENT_GAP = 67

ACTIVE_EVENT_GAP = 34
NEXT_ENTRY_GAP = 18

SHUGO_TIME_TO_GAMES_GAP = 34
SHUGO_GAME_LINE_STEP = 43


# ============================================================
# EVENT-FARBEN
# ============================================================

RIFT_COLOR = (
    255,
    78,
    88,
    255,
)

SHUGO_COLOR = (
    229,
    177,
    62,
    255,
)

RESET_COLOR = (
    64,
    145,
    255,
    255,
)


# ============================================================
# DATEIEN
# ============================================================

def load_data():
    with open(
        DATA_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def load_state():
    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8",
        ) as f:
            return json.load(f)

    except FileNotFoundError:
        return {}


def save_state(data):
    with open(
        STATE_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            indent=2,
        )


# ============================================================
# SCHRIFTEN
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
            return ImageFont.truetype(
                path,
                size=size,
            )

    return ImageFont.load_default()


# ============================================================
# SICHTBARE TEXTABSTÄNDE
# ============================================================

def text_y_after(
    draw,
    previous_bbox,
    next_text,
    next_font,
    visual_gap,
):
    """
    Berechnet die Y-Position des nächsten Textes so,
    dass zwischen der sichtbaren Unterkante des vorherigen
    Textes und der sichtbaren Oberkante des nächsten Textes
    exakt visual_gap Pixel liegen.
    """

    probe = draw.textbbox(
        (0, 0),
        next_text,
        font=next_font,
    )

    return (
        previous_bbox[3]
        + visual_gap
        - probe[1]
    )


# ============================================================
# ZEITFUNKTIONEN
# ============================================================

def parse_time_today(
    time_string,
    timezone,
):
    hour, minute = map(
        int,
        time_string.split(":"),
    )

    now = datetime.now(timezone)

    return now.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )


def format_time_range(
    start,
    end,
):
    return (
        f"{start.strftime('%H:%M')} – "
        f"{end.strftime('%H:%M')} Uhr"
    )


# ============================================================
# RESET-ZEITEN
# ============================================================

def next_daily_reset(timezone):
    now = datetime.now(timezone)

    candidate = now.replace(
        hour=23,
        minute=0,
        second=0,
        microsecond=0,
    )

    if candidate <= now:
        candidate += timedelta(days=1)

    return candidate


def next_weekly_reset(timezone):
    now = datetime.now(timezone)

    target_weekday = 1

    days_ahead = (
        target_weekday
        - now.weekday()
    ) % 7

    candidate = (
        now
        + timedelta(days=days_ahead)
    ).replace(
        hour=23,
        minute=0,
        second=0,
        microsecond=0,
    )

    if candidate <= now:
        candidate += timedelta(days=7)

    return candidate


# ============================================================
# SPACETIME RIFT
# ============================================================

def build_rift_times(
    rift_data,
    timezone,
):
    now = datetime.now(timezone)

    first_start = parse_time_today(
        rift_data["first_start"],
        timezone,
    )

    interval = timedelta(
        hours=rift_data[
            "interval_hours"
        ],
    )

    duration = timedelta(
        minutes=rift_data[
            "duration_minutes"
        ],
    )

    starts = []

    start = (
        first_start
        - timedelta(days=1)
    )

    end_limit = (
        first_start
        + timedelta(days=2)
    )

    while start <= end_limit:
        starts.append(start)
        start += interval

    active_start = None
    active_end = None

    for start_time in starts:
        end_time = (
            start_time
            + duration
        )

        if (
            start_time
            <= now
            < end_time
        ):
            active_start = start_time
            active_end = end_time
            break

    future_starts = [
        start_time
        for start_time in starts
        if start_time > now
    ]

    future_starts.sort()

    next_start = future_starts[0]
    following_start = future_starts[1]

    return {
        "active_start":
            active_start,

        "active_end":
            active_end,

        "next_start":
            next_start,

        "following_start":
            following_start,
    }


# ============================================================
# SHUGO FESTIVAL
# ============================================================

def build_shugo_times(
    shugo_data,
    timezone,
):
    now = datetime.now(timezone)

    candidates = []

    for day_offset in range(-1, 2):

        day = (
            now
            + timedelta(
                days=day_offset
            )
        )

        for hour in range(24):

            for minute in shugo_data[
                "start_minutes"
            ]:

                candidate = day.replace(
                    hour=hour,
                    minute=minute,
                    second=0,
                    microsecond=0,
                )

                candidates.append(
                    candidate
                )

    candidates.sort()

    active_start = None
    active_end = None

    for start_time in candidates:

        end_time = (
            start_time
            + timedelta(minutes=10)
        )

        if (
            start_time
            <= now
            < end_time
        ):
            active_start = start_time
            active_end = end_time
            break

    future_starts = [
        start_time
        for start_time in candidates
        if start_time > now
    ]

    future_starts.sort()

    next_start = future_starts[0]
    following_start = future_starts[1]

    return {
        "active_start":
            active_start,

        "active_end":
            active_end,

        "next_start":
            next_start,

        "following_start":
            following_start,
    }


def shugo_rotation_for_time(
    dt,
    shugo_data,
):
    if dt.minute == 15:
        return shugo_data[
            "rotation_15"
        ]

    return shugo_data[
        "rotation_45"
    ]


# ============================================================
# ÜBERSICHT DATEN
# ============================================================

def build_event_overview(
    rift_times,
    shugo_times,
    daily_reset,
    weekly_reset,
):
    active_events = []
    upcoming_events = []

    if rift_times[
        "active_start"
    ]:

        active_events.append(
            {
                "key": "rift",
                "name":
                    DISPLAY_NAMES["rift"],
                "end":
                    rift_times["active_end"],
                "color":
                    RIFT_COLOR,
            }
        )

    if shugo_times[
        "active_start"
    ]:

        active_events.append(
            {
                "key": "shugo",
                "name":
                    DISPLAY_NAMES["shugo"],
                "end":
                    shugo_times["active_end"],
                "color":
                    SHUGO_COLOR,
            }
        )

    upcoming_events.append(
        {
            "key": "rift",
            "name":
                DISPLAY_NAMES["rift"],
            "time":
                rift_times["next_start"],
            "color":
                RIFT_COLOR,
        }
    )

    upcoming_events.append(
        {
            "key": "shugo",
            "name":
                DISPLAY_NAMES["shugo"],
            "time":
                shugo_times["next_start"],
            "color":
                SHUGO_COLOR,
        }
    )

    upcoming_events.append(
        {
            "key": "daily_reset",
            "name":
                DISPLAY_NAMES[
                    "daily_reset"
                ],
            "time":
                daily_reset,
            "color":
                RESET_COLOR,
        }
    )

    upcoming_events.append(
        {
            "key": "weekly_reset",
            "name":
                DISPLAY_NAMES[
                    "weekly_reset"
                ],
            "time":
                weekly_reset,
            "color":
                RESET_COLOR,
        }
    )

    upcoming_events.sort(
        key=lambda item:
            item["time"]
    )

    next_events = (
        upcoming_events[:2]
    )

    return {
        "active":
            active_events,

        "next":
            next_events,
    }


# ============================================================
# HINTERGRÜNDE LADEN
# ============================================================

def load_image_from_url(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "AION2-Schedule-Bot",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:

        image_data = response.read()

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
# BILD AUF ZIELFORMAT ZUSCHNEIDEN
# ============================================================

def crop_and_resize(
    image,
    target_width,
    target_height,
):
    source_width, source_height = (
        image.size
    )

    source_ratio = (
        source_width
        / source_height
    )

    target_ratio = (
        target_width
        / target_height
    )

    if source_ratio > target_ratio:

        new_width = int(
            source_height
            * target_ratio
        )

        left = (
            source_width
            - new_width
        ) // 2

        image = image.crop(
            (
                left,
                0,
                left + new_width,
                source_height,
            )
        )

    else:

        new_height = int(
            source_width
            / target_ratio
        )

        top = (
            source_height
            - new_height
        ) // 2

        image = image.crop(
            (
                0,
                top,
                source_width,
                top + new_height,
            )
        )

    return image.resize(
        (
            target_width,
            target_height,
        ),
        Image.Resampling.LANCZOS,
    )


# ============================================================
# ÜBERSICHT-HINTERGRUND
# ============================================================

def prepare_overview_background(
    image,
    target_width,
    target_height,
):
    source_width, source_height = (
        image.size
    )

    crop_left = int(
        source_width * 0.025
    )

    crop_right = int(
        source_width * 0.025
    )

    crop_top = int(
        source_height * 0.03
    )

    crop_bottom = int(
        source_height * 0.03
    )

    image = image.crop(
        (
            crop_left,
            crop_top,
            source_width - crop_right,
            source_height - crop_bottom,
        )
    )

    return image.resize(
        (
            target_width,
            target_height,
        ),
        Image.Resampling.LANCZOS,
    )


# ============================================================
# LINKER SCHWARZVERLAUF
# ============================================================

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
        width
        * solid_ratio
    )

    fade_end = int(
        width
        * fade_ratio
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
                * (
                    (1.0 - progress)
                    ** 1.65
                )
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
# TEXT MIT SCHATTEN
# ============================================================

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
        (
            x + shadow_offset,
            y + shadow_offset,
        ),
        text,
        font=font,
        fill=(
            0,
            0,
            0,
            200,
        ),
    )

    draw.text(
        position,
        text,
        font=font,
        fill=fill,
    )


# ============================================================
# EVENT-PUNKT
# ============================================================

def draw_event_marker(
    draw,
    x,
    y,
    color,
    size=16,
):
    draw.ellipse(
        (
            x,
            y,
            x + size,
            y + size,
        ),
        fill=color,
    )


# ============================================================
# ÜBERSICHT
# ============================================================

def create_overview_card(
    event_overview,
):
    active_events = (
        event_overview["active"]
    )

    next_events = (
        event_overview["next"]
    )

    title_font = load_font(
        56,
        bold=True,
    )

    status_font = load_font(
        31,
        bold=True,
    )

    active_name_font = load_font(
        48,
        bold=True,
    )

    active_until_font = load_font(
        30,
        bold=False,
    )

    secondary_font = load_font(
        30,
        bold=False,
    )

    secondary_bold_font = load_font(
        30,
        bold=True,
    )

    white = (
        250,
        249,
        252,
        255,
    )

    soft_white = (
        225,
        222,
        225,
        255,
    )

    status_gray = (
        170,
        170,
        176,
        255,
    )

    title_x = 74
    title_y = 58

    measure_image = Image.new(
        "RGBA",
        (
            1200,
            3000,
        ),
        (
            0,
            0,
            0,
            0,
        ),
    )

    measure_draw = ImageDraw.Draw(
        measure_image
    )

    title_text = (
        DISPLAY_NAMES[
            "overview_card"
        ]
    )

    title_bbox = (
        measure_draw.textbbox(
            (
                title_x,
                title_y,
            ),
            title_text,
            font=title_font,
        )
    )

    # --------------------------------------------------------
    # AKTIVER ZUSTAND
    # --------------------------------------------------------

    if active_events:

        status_text = (
            "JETZT AKTIV"
        )

        status_y = text_y_after(
            measure_draw,
            title_bbox,
            status_text,
            status_font,
            SECTION_GAP,
        )

        status_bbox = (
            measure_draw.textbbox(
                (
                    76,
                    status_y,
                ),
                status_text,
                font=status_font,
            )
        )

        active_probe_text = (
            active_events[0][
                "name"
            ].upper()
        )

        current_y = text_y_after(
            measure_draw,
            status_bbox,
            active_probe_text,
            active_name_font,
            CLOSE_GAP,
        )

        last_active_bottom = None

        for event_index, event in enumerate(
            active_events
        ):

            event_name = (
                event["name"].upper()
            )

            if event_index > 0:

                probe = (
                    measure_draw.textbbox(
                        (
                            0,
                            0,
                        ),
                        event_name,
                        font=active_name_font,
                    )
                )

                current_y = (
                    last_active_bottom
                    + ACTIVE_EVENT_GAP
                    - probe[1]
                )

            name_bbox = (
                measure_draw.textbbox(
                    (
                        108,
                        current_y,
                    ),
                    event_name,
                    font=active_name_font,
                )
            )

            until_y = (
                name_bbox[3]
                + 4
            )

            until_text = (
                f"bis "
                f"{event['end'].strftime('%H:%M')} Uhr"
            )

            until_bbox = (
                measure_draw.textbbox(
                    (
                        108,
                        until_y,
                    ),
                    until_text,
                    font=active_until_font,
                )
            )

            last_active_bottom = (
                until_bbox[3]
            )

        next_title_text = (
            "→ Als Nächstes"
        )

        next_title_font = (
            secondary_bold_font
        )

        next_title_color = (
            white
        )

        next_title_probe = (
            measure_draw.textbbox(
                (
                    0,
                    0,
                ),
                next_title_text,
                font=next_title_font,
            )
        )

        next_section_y = (
            last_active_bottom
            + SECTION_GAP
            - next_title_probe[1]
        )

    # --------------------------------------------------------
    # NICHTS AKTIV
    # --------------------------------------------------------

    else:

        next_title_text = (
            "ALS NÄCHSTES"
        )

        next_title_font = (
            status_font
        )

        next_title_color = (
            status_gray
        )

        next_section_y = text_y_after(
            measure_draw,
            title_bbox,
            next_title_text,
            next_title_font,
            SECTION_GAP,
        )

    next_title_bbox = (
        measure_draw.textbbox(
            (
                76,
                next_section_y,
            ),
            next_title_text,
            font=next_title_font,
        )
    )

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

    last_next_bottom = (
        next_title_bbox[3]
    )

    for event_index, event in enumerate(
        next_events
    ):

        next_text = (
            f"{event['name']} · "
            f"{event['time'].strftime('%H:%M')} Uhr"
        )

        if event_index > 0:

            probe = (
                measure_draw.textbbox(
                    (
                        0,
                        0,
                    ),
                    next_text,
                    font=secondary_font,
                )
            )

            current_y = (
                last_next_bottom
                + NEXT_ENTRY_GAP
                - probe[1]
            )

        next_bbox = (
            measure_draw.textbbox(
                (
                    106,
                    current_y,
                ),
                next_text,
                font=secondary_font,
            )
        )

        last_next_bottom = (
            next_bbox[3]
        )

    target_width = 1200

    target_height = (
        last_next_bottom
        + 58
    )

    target_height = max(
        target_height,
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
        (
            title_x,
            title_y,
        ),
        title_text,
        title_font,
        white,
    )

    if active_events:

        status_text = (
            "JETZT AKTIV"
        )

        status_y = text_y_after(
            draw,
            draw.textbbox(
                (
                    title_x,
                    title_y,
                ),
                title_text,
                font=title_font,
            ),
            status_text,
            status_font,
            SECTION_GAP,
        )

        draw_text_with_shadow(
            draw,
            (
                76,
                status_y,
            ),
            status_text,
            status_font,
            status_gray,
        )

        status_bbox = (
            draw.textbbox(
                (
                    76,
                    status_y,
                ),
                status_text,
                font=status_font,
            )
        )

        first_active_text = (
            active_events[0][
                "name"
            ].upper()
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

            event_name = (
                event["name"].upper()
            )

            if event_index > 0:

                probe = draw.textbbox(
                    (
                        0,
                        0,
                    ),
                    event_name,
                    font=active_name_font,
                )

                current_y = (
                    last_active_bottom
                    + ACTIVE_EVENT_GAP
                    - probe[1]
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
                (
                    108,
                    current_y,
                ),
                event_name,
                active_name_font,
                white,
            )

            name_bbox = draw.textbbox(
                (
                    108,
                    current_y,
                ),
                event_name,
                font=active_name_font,
            )

            until_y = (
                name_bbox[3]
                + 4
            )

            until_text = (
                f"bis "
                f"{event['end'].strftime('%H:%M')} Uhr"
            )

            draw_text_with_shadow(
                draw,
                (
                    108,
                    until_y,
                ),
                until_text,
                active_until_font,
                soft_white,
            )

            until_bbox = draw.textbbox(
                (
                    108,
                    until_y,
                ),
                until_text,
                font=active_until_font,
            )

            last_active_bottom = (
                until_bbox[3]
            )

        next_title_probe = (
            draw.textbbox(
                (
                    0,
                    0,
                ),
                next_title_text,
                font=next_title_font,
            )
        )

        next_section_y = (
            last_active_bottom
            + SECTION_GAP
            - next_title_probe[1]
        )

    else:

        title_bbox = draw.textbbox(
            (
                title_x,
                title_y,
            ),
            title_text,
            font=title_font,
        )

        next_section_y = text_y_after(
            draw,
            title_bbox,
            next_title_text,
            next_title_font,
            SECTION_GAP,
        )

    draw_text_with_shadow(
        draw,
        (
            76,
            next_section_y,
        ),
        next_title_text,
        next_title_font,
        next_title_color,
    )

    next_title_bbox = draw.textbbox(
        (
            76,
            next_section_y,
        ),
        next_title_text,
        font=next_title_font,
    )

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

    last_next_bottom = (
        next_title_bbox[3]
    )

    for event_index, event in enumerate(
        next_events
    ):

        next_text = (
            f"{event['name']} · "
            f"{event['time'].strftime('%H:%M')} Uhr"
        )

        if event_index > 0:

            probe = draw.textbbox(
                (
                    0,
                    0,
                ),
                next_text,
                font=secondary_font,
            )

            current_y = (
                last_next_bottom
                + NEXT_ENTRY_GAP
                - probe[1]
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
            (
                106,
                current_y,
            ),
            next_text,
            secondary_font,
            soft_white,
        )

        next_bbox = draw.textbbox(
            (
                106,
                current_y,
            ),
            next_text,
            font=secondary_font,
        )

        last_next_bottom = (
            next_bbox[3]
        )

    image = image.convert(
        "RGB"
    )

    image.save(
        OVERVIEW_CARD_FILE,
        "PNG",
        optimize=True,
    )


# ============================================================
# SPACETIME-RIFT-KARTE
# ============================================================

def create_rift_card(
    rift_data,
    rift_times,
):
    image = load_rift_background()

    target_width = 1200
    target_height = 540

    image = crop_and_resize(
        image,
        target_width,
        target_height,
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

    title_font = load_font(
        56,
        bold=True,
    )

    subtitle_font = load_font(
        29,
        bold=False,
    )

    status_font = load_font(
        31,
        bold=True,
    )

    time_font = load_font(
        48,
        bold=True,
    )

    secondary_font = load_font(
        30,
        bold=False,
    )

    white = (
        250,
        248,
        251,
        255,
    )

    red = (
        255,
        78,
        88,
        255,
    )

    light_red = (
        255,
        135,
        140,
        255,
    )

    secondary_color = (
        225,
        222,
        225,
        255,
    )

    title_text = (
        DISPLAY_NAMES[
            "rift_card"
        ]
    )

    subtitle_text = (
        f"Alle "
        f"{rift_data['interval_hours']} Stunden"
    )

    title_y = 62

    title_bbox = draw.textbbox(
        (
            78,
            title_y,
        ),
        title_text,
        font=title_font,
    )

    subtitle_y = text_y_after(
        draw,
        title_bbox,
        subtitle_text,
        subtitle_font,
        CLOSE_GAP,
    )

    subtitle_bbox = draw.textbbox(
        (
            80,
            subtitle_y,
        ),
        subtitle_text,
        font=subtitle_font,
    )

    if rift_times[
        "active_start"
    ]:

        main_label = (
            "JETZT AKTIV"
        )

        main_start = (
            rift_times[
                "active_start"
            ]
        )

        main_end = (
            rift_times[
                "active_end"
            ]
        )

        secondary_label = (
            "Nächster"
        )

        secondary_start = (
            rift_times[
                "next_start"
            ]
        )

    else:

        main_label = (
            "NÄCHSTER"
        )

        main_start = (
            rift_times[
                "next_start"
            ]
        )

        main_end = (
            main_start
            + timedelta(
                minutes=rift_data[
                    "duration_minutes"
                ]
            )
        )

        secondary_label = (
            "Danach"
        )

        secondary_start = (
            rift_times[
                "following_start"
            ]
        )

    secondary_end = (
        secondary_start
        + timedelta(
            minutes=rift_data[
                "duration_minutes"
            ]
        )
    )

    status_y = text_y_after(
        draw,
        subtitle_bbox,
        main_label,
        status_font,
        SECTION_GAP,
    )

    status_bbox = draw.textbbox(
        (
            80,
            status_y,
        ),
        main_label,
        font=status_font,
    )

    main_time_text = (
        format_time_range(
            main_start,
            main_end,
        )
    )

    main_y = text_y_after(
        draw,
        status_bbox,
        main_time_text,
        time_font,
        CLOSE_GAP,
    )

    draw_text_with_shadow(
        draw,
        (
            78,
            title_y,
        ),
        title_text,
        title_font,
        white,
    )

    draw_text_with_shadow(
        draw,
        (
            80,
            subtitle_y,
        ),
        subtitle_text,
        subtitle_font,
        light_red,
    )

    draw_text_with_shadow(
        draw,
        (
            80,
            status_y,
        ),
        main_label,
        status_font,
        red,
    )

    draw_text_with_shadow(
        draw,
        (
            78,
            main_y,
        ),
        main_time_text,
        time_font,
        white,
    )

    main_bbox = draw.textbbox(
        (
            78,
            main_y,
        ),
        main_time_text,
        font=time_font,
    )

    secondary_text = (
        f"→ {secondary_label}: "
        f"{format_time_range(
            secondary_start,
            secondary_end,
        )}"
    )

    secondary_y = text_y_after(
        draw,
        main_bbox,
        secondary_text,
        secondary_font,
        AFTER_CONTENT_GAP,
    )

    draw_text_with_shadow(
        draw,
        (
            80,
            secondary_y,
        ),
        secondary_text,
        secondary_font,
        secondary_color,
    )

    image = image.convert(
        "RGB"
    )

    image.save(
        RIFT_CARD_FILE,
        "PNG",
        optimize=True,
    )


# ============================================================
# SHUGO-FESTIVAL-KARTE
#
# MASTER-REFERENZ FÜR DIE ABSTÄNDE
# ============================================================

def create_shugo_card(
    shugo_data,
    shugo_times,
):
    image = load_shugo_background()

    target_width = 1200
    target_height = 620

    image = crop_and_resize(
        image,
        target_width,
        target_height,
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

    title_font = load_font(
        56,
        bold=True,
    )

    subtitle_font = load_font(
        29,
        bold=False,
    )

    status_font = load_font(
        31,
        bold=True,
    )

    time_font = load_font(
        48,
        bold=True,
    )

    game_font = load_font(
        31,
        bold=False,
    )

    secondary_font = load_font(
        30,
        bold=False,
    )

    white = (
        250,
        248,
        245,
        255,
    )

    gold = (
        229,
        177,
        62,
        255,
    )

    light_gold = (
        243,
        210,
        126,
        255,
    )

    secondary_color = (
        225,
        222,
        225,
        255,
    )

    title_text = (
        DISPLAY_NAMES[
            "shugo_card"
        ]
    )

    subtitle_text = (
        "Alle 30 Minuten"
    )

    title_y = 48

    title_bbox = draw.textbbox(
        (
            72,
            title_y,
        ),
        title_text,
        font=title_font,
    )

    subtitle_y = text_y_after(
        draw,
        title_bbox,
        subtitle_text,
        subtitle_font,
        CLOSE_GAP,
    )

    subtitle_bbox = draw.textbbox(
        (
            74,
            subtitle_y,
        ),
        subtitle_text,
        font=subtitle_font,
    )

    if shugo_times[
        "active_start"
    ]:

        main_label = (
            "JETZT AKTIV"
        )

        main_start = (
            shugo_times[
                "active_start"
            ]
        )

        secondary_label = (
            "Nächstes"
        )

        secondary_start = (
            shugo_times[
                "next_start"
            ]
        )

    else:

        main_label = (
            "NÄCHSTES"
        )

        main_start = (
            shugo_times[
                "next_start"
            ]
        )

        secondary_label = (
            "Danach"
        )

        secondary_start = (
            shugo_times[
                "following_start"
            ]
        )

    status_y = text_y_after(
        draw,
        subtitle_bbox,
        main_label,
        status_font,
        SECTION_GAP,
    )

    status_bbox = draw.textbbox(
        (
            74,
            status_y,
        ),
        main_label,
        font=status_font,
    )

    main_time_text = (
        f"{main_start.strftime('%H:%M')} Uhr"
    )

    main_y = text_y_after(
        draw,
        status_bbox,
        main_time_text,
        time_font,
        CLOSE_GAP,
    )

    current_rotation = (
        shugo_rotation_for_time(
            main_start,
            shugo_data,
        )
    )

    draw_text_with_shadow(
        draw,
        (
            72,
            title_y,
        ),
        title_text,
        title_font,
        white,
    )

    draw_text_with_shadow(
        draw,
        (
            74,
            subtitle_y,
        ),
        subtitle_text,
        subtitle_font,
        light_gold,
    )

    draw_text_with_shadow(
        draw,
        (
            74,
            status_y,
        ),
        main_label,
        status_font,
        gold,
    )

    draw_text_with_shadow(
        draw,
        (
            72,
            main_y,
        ),
        main_time_text,
        time_font,
        white,
    )

    main_bbox = draw.textbbox(
        (
            72,
            main_y,
        ),
        main_time_text,
        font=time_font,
    )

    first_game_text = None

    if current_rotation:
        first_game_text = (
            f"• {current_rotation[0]}"
        )

        game_probe = draw.textbbox(
            (
                0,
                0,
            ),
            first_game_text,
            font=game_font,
        )

        y = (
            main_bbox[3]
            + SHUGO_TIME_TO_GAMES_GAP
            - game_probe[1]
        )

    else:
        y = (
            main_bbox[3]
            + SHUGO_TIME_TO_GAMES_GAP
        )

    last_game_text = None
    last_game_position = None

    for game in current_rotation:

        game_text = (
            f"• {game}"
        )

        game_position = (
            82,
            y,
        )

        draw_text_with_shadow(
            draw,
            game_position,
            game_text,
            game_font,
            white,
        )

        last_game_text = (
            game_text
        )

        last_game_position = (
            game_position
        )

        y += SHUGO_GAME_LINE_STEP

    secondary_text = (
        f"→ {secondary_label}: "
        f"{secondary_start.strftime('%H:%M')} Uhr"
    )

    if last_game_text is not None:

        last_game_bbox = (
            draw.textbbox(
                last_game_position,
                last_game_text,
                font=game_font,
            )
        )

        secondary_y = text_y_after(
            draw,
            last_game_bbox,
            secondary_text,
            secondary_font,
            AFTER_CONTENT_GAP,
        )

    else:

        secondary_y = text_y_after(
            draw,
            main_bbox,
            secondary_text,
            secondary_font,
            AFTER_CONTENT_GAP,
        )

    draw_text_with_shadow(
        draw,
        (
            82,
            secondary_y,
        ),
        secondary_text,
        secondary_font,
        secondary_color,
    )

    image = image.convert(
        "RGB"
    )

    image.save(
        SHUGO_CARD_FILE,
        "PNG",
        optimize=True,
    )


# ============================================================
# RESET-KARTE
# ============================================================

def create_reset_card():
    image = load_reset_background()

    target_width = 1200
    target_height = 540

    image = crop_and_resize(
        image,
        target_width,
        target_height,
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

    title_font = load_font(
        56,
        bold=True,
    )

    label_font = load_font(
        30,
        bold=True,
    )

    time_font = load_font(
        46,
        bold=True,
    )

    white = (
        248,
        250,
        255,
        255,
    )

    blue = (
        64,
        145,
        255,
        255,
    )

    light_blue = (
        110,
        190,
        255,
        255,
    )

    title_text = (
        DISPLAY_NAMES[
            "reset_card"
        ]
    )

    daily_label_text = (
        DISPLAY_NAMES[
            "daily_card"
        ]
    )

    daily_time_text = (
        "23:00 Uhr"
    )

    weekly_label_text = (
        DISPLAY_NAMES[
            "weekly_card"
        ]
    )

    weekly_time_text = (
        "Dienstag · 23:00 Uhr"
    )

    title_y = 58

    title_bbox = draw.textbbox(
        (
            74,
            title_y,
        ),
        title_text,
        font=title_font,
    )

    # TÄGLICH ist ein EIGENER BLOCK.
    # Deshalb hier SECTION_GAP und NICHT CLOSE_GAP.

    daily_label_y = text_y_after(
        draw,
        title_bbox,
        daily_label_text,
        label_font,
        SECTION_GAP,
    )

    daily_label_bbox = draw.textbbox(
        (
            76,
            daily_label_y,
        ),
        daily_label_text,
        font=label_font,
    )

    daily_time_y = text_y_after(
        draw,
        daily_label_bbox,
        daily_time_text,
        time_font,
        CLOSE_GAP,
    )

    daily_time_bbox = draw.textbbox(
        (
            74,
            daily_time_y,
        ),
        daily_time_text,
        font=time_font,
    )

    # WÖCHENTLICH beginnt wieder einen eigenen Block.

    weekly_label_y = text_y_after(
        draw,
        daily_time_bbox,
        weekly_label_text,
        label_font,
        SECTION_GAP,
    )

    weekly_label_bbox = draw.textbbox(
        (
            76,
            weekly_label_y,
        ),
        weekly_label_text,
        font=label_font,
    )

    weekly_time_y = text_y_after(
        draw,
        weekly_label_bbox,
        weekly_time_text,
        time_font,
        CLOSE_GAP,
    )

    draw_text_with_shadow(
        draw,
        (
            74,
            title_y,
        ),
        title_text,
        title_font,
        white,
    )

    draw_text_with_shadow(
        draw,
        (
            76,
            daily_label_y,
        ),
        daily_label_text,
        label_font,
        light_blue,
    )

    draw_text_with_shadow(
        draw,
        (
            74,
            daily_time_y,
        ),
        daily_time_text,
        time_font,
        white,
    )

    draw_text_with_shadow(
        draw,
        (
            76,
            weekly_label_y,
        ),
        weekly_label_text,
        label_font,
        blue,
    )

    draw_text_with_shadow(
        draw,
        (
            74,
            weekly_time_y,
        ),
        weekly_time_text,
        time_font,
        white,
    )

    image = image.convert(
        "RGB"
    )

    image.save(
        RESET_CARD_FILE,
        "PNG",
        optimize=True,
    )


# ============================================================
# EMBEDS ERSTELLEN
# ============================================================

def build_embeds(data):
    timezone = ZoneInfo(
        data["timezone"]
    )

    rift_data = data[
        "rift"
    ]

    shugo_data = data[
        "shugo_games"
    ]

    # --------------------------------------------------------
    # RIFT
    # --------------------------------------------------------

    rift_times = build_rift_times(
        rift_data,
        timezone,
    )

    create_rift_card(
        rift_data,
        rift_times,
    )

    # --------------------------------------------------------
    # SHUGO
    # --------------------------------------------------------

    shugo_times = build_shugo_times(
        shugo_data,
        timezone,
    )

    create_shugo_card(
        shugo_data,
        shugo_times,
    )

    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    daily_reset = next_daily_reset(
        timezone
    )

    weekly_reset = next_weekly_reset(
        timezone
    )

    create_reset_card()

    # --------------------------------------------------------
    # ÜBERSICHT
    # --------------------------------------------------------

    event_overview = build_event_overview(
        rift_times,
        shugo_times,
        daily_reset,
        weekly_reset,
    )

    create_overview_card(
        event_overview
    )

    # --------------------------------------------------------
    # EMBEDS
    # --------------------------------------------------------

    overview_embed = {
        "color":
            8027525,

        "image": {
            "url":
                "attachment://event_overview_card.png"
        }
    }

    rift_embed = {
        "color":
            14555706,

        "image": {
            "url":
                "attachment://spacetime_rift_card.png"
        }
    }

    shugo_embed = {
        "color":
            14525510,

        "image": {
            "url":
                "attachment://shugo_games_card.png"
        }
    }

    reset_embed = {
        "color":
            4231679,

        "image": {
            "url":
                "attachment://resets_card.png"
        }
    }

    return [
        overview_embed,
        rift_embed,
        shugo_embed,
        reset_embed,
    ]


# ============================================================
# MULTIPART DISCORD REQUEST
# ============================================================

def webhook_request_with_files(
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
            f'Content-Disposition: form-data; '
            f'name="payload_json"\r\n'
            f"Content-Type: application/json\r\n\r\n"
        ).encode("utf-8")
    )

    body.extend(
        json.dumps(
            payload
        ).encode("utf-8")
    )

    body.extend(
        b"\r\n"
    )

    for index, file_path in enumerate(
        file_paths
    ):

        with open(
            file_path,
            "rb",
        ) as f:

            file_data = f.read()

        body.extend(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; '
                f'name="files[{index}]"; '
                f'filename="{os.path.basename(file_path)}"\r\n'
                f"Content-Type: image/png\r\n\r\n"
            ).encode("utf-8")
        )

        body.extend(
            file_data
        )

        body.extend(
            b"\r\n"
        )

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
            "Content-Type":
                f"multipart/form-data; "
                f"boundary={boundary}",

            "User-Agent":
                "AION2-Schedule-Bot",
        },
    )

    with urllib.request.urlopen(
        req,
        timeout=60,
    ) as response:

        response_data = (
            response.read()
        )

        if not response_data:
            return {}

        return json.loads(
            response_data.decode(
                "utf-8"
            )
        )


# ============================================================
# HAUPTPROGRAMM
# ============================================================

def main():
    if not WEBHOOK_URL:
        raise RuntimeError(
            "AION_SCHEDULE_WEBHOOK fehlt."
        )

    data = load_data()
    state = load_state()

    embeds = build_embeds(
        data
    )

    payload = {
        "embeds":
            embeds,

        "attachments": [
            {
                "id": 0,
                "filename":
                    OVERVIEW_CARD_FILE,
            },

            {
                "id": 1,
                "filename":
                    RIFT_CARD_FILE,
            },

            {
                "id": 2,
                "filename":
                    SHUGO_CARD_FILE,
            },

            {
                "id": 3,
                "filename":
                    RESET_CARD_FILE,
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

    # --------------------------------------------------------
    # BESTEHENDE NACHRICHT AKTUALISIEREN
    # --------------------------------------------------------

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
            "Bestehende Veranstaltungs-"
            "Nachricht aktualisiert."
        )

    # --------------------------------------------------------
    # NEUE NACHRICHT ERSTELLEN
    # --------------------------------------------------------

    else:

        create_url = (
            f"{WEBHOOK_URL}"
            f"?wait=true"
        )

        result = (
            webhook_request_with_files(
                create_url,
                payload,
                files,
                method="POST",
            )
        )

        save_state(
            {
                "message_id":
                    result["id"]
            }
        )

        print(
            "Neue Veranstaltungs-"
            "Nachricht erstellt."
        )


if __name__ == "__main__":
    main()
