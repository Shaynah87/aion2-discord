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
#
# Später müssen wir nur noch HIER die offiziellen
# deutschen Global-Namen eintragen.
# ============================================================

DISPLAY_NAMES = {
    "rift": "Spacetime Rift",
    "rift_card": "SPACETIME RIFT",

    "shugo": "Shugo Festival",
    "shugo_card": "SHUGO FESTIVAL",

    "daily_reset": "Täglicher Reset",
    "weekly_reset": "Wöchentlicher Reset",

    "reset_card": "RESETS",
    "daily_card": "TÄGLICH",
    "weekly_card": "WÖCHENTLICH"
}


# ============================================================
# HINTERGRUNDBILDER
# ============================================================

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

RIFT_CARD_FILE = "spacetime_rift_card.png"
SHUGO_CARD_FILE = "shugo_games_card.png"
RESET_CARD_FILE = "resets_card.png"

SECONDARY_GAP = 62


# ============================================================
# DATEIEN
# ============================================================

def load_data():
    with open(
        DATA_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def load_state():
    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except FileNotFoundError:
        return {}


def save_state(data):
    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            indent=2
        )


# ============================================================
# SCHRIFTEN
# ============================================================

def load_font(size, bold=False):
    if bold:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        ]
    else:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
        ]

    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(
                path,
                size=size
            )

    return ImageFont.load_default()


# ============================================================
# ZEITFUNKTIONEN
# ============================================================

def parse_time_today(
    time_string,
    timezone
):
    hour, minute = map(
        int,
        time_string.split(":")
    )

    now = datetime.now(timezone)

    return now.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0
    )


def discord_time(dt):
    unix = int(
        dt.timestamp()
    )

    return f"<t:{unix}:t>"


def format_time_range(
    start,
    end
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
        microsecond=0
    )

    if candidate <= now:
        candidate += timedelta(days=1)

    return candidate


def next_weekly_reset(timezone):
    now = datetime.now(timezone)

    # Dienstag = 1
    target_weekday = 1

    days_ahead = (
        target_weekday -
        now.weekday()
    ) % 7

    candidate = (
        now +
        timedelta(days=days_ahead)
    ).replace(
        hour=23,
        minute=0,
        second=0,
        microsecond=0
    )

    if candidate <= now:
        candidate += timedelta(days=7)

    return candidate


# ============================================================
# SPACETIME RIFT
# ============================================================

def build_rift_times(
    rift_data,
    timezone
):
    now = datetime.now(timezone)

    first_start = parse_time_today(
        rift_data["first_start"],
        timezone
    )

    interval = timedelta(
        hours=rift_data[
            "interval_hours"
        ]
    )

    duration = timedelta(
        minutes=rift_data[
            "duration_minutes"
        ]
    )

    starts = []

    start = (
        first_start -
        timedelta(days=1)
    )

    end_limit = (
        first_start +
        timedelta(days=2)
    )

    while start <= end_limit:
        starts.append(start)
        start += interval

    active_start = None
    active_end = None

    for start_time in starts:

        end_time = (
            start_time +
            duration
        )

        if (
            start_time <= now <
            end_time
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
            following_start
    }


# ============================================================
# SHUGO FESTIVAL
#
# Aktiv:
# :15 bis :24:59
# :45 bis :54:59
#
# Also immer genau 10 Minuten.
# ============================================================

def build_shugo_times(
    shugo_data,
    timezone
):
    now = datetime.now(timezone)

    candidates = []

    for day_offset in range(-1, 2):

        day = (
            now +
            timedelta(days=day_offset)
        )

        for hour in range(24):

            for minute in shugo_data[
                "start_minutes"
            ]:

                candidate = day.replace(
                    hour=hour,
                    minute=minute,
                    second=0,
                    microsecond=0
                )

                candidates.append(
                    candidate
                )

    candidates.sort()

    active_start = None
    active_end = None

    for start_time in candidates:

        end_time = (
            start_time +
            timedelta(minutes=10)
        )

        if (
            start_time <= now <
            end_time
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
            following_start
    }


def shugo_rotation_for_time(
    dt,
    shugo_data
):
    if dt.minute == 15:
        return shugo_data[
            "rotation_15"
        ]

    return shugo_data[
        "rotation_45"
    ]


# ============================================================
# EVENT-ZENTRALE
#
# Sammelt:
# - alle aktuell aktiven Events
# - die nächsten kommenden Events
#
# Später können wir hier Abyss, Bosse usw.
# einfach ergänzen.
# ============================================================

def build_event_overview(
    rift_times,
    shugo_times,
    daily_reset,
    weekly_reset
):
    active_events = []

    upcoming_events = []


    # --------------------------------------------------------
    # RIFT AKTIV
    # --------------------------------------------------------

    if rift_times[
        "active_start"
    ]:

        active_events.append(
            {
                "icon": "🌀",
                "name":
                    DISPLAY_NAMES["rift"],
                "end":
                    rift_times["active_end"]
            }
        )


    # --------------------------------------------------------
    # SHUGO AKTIV
    # --------------------------------------------------------

    if shugo_times[
        "active_start"
    ]:

        active_events.append(
            {
                "icon": "🐹",
                "name":
                    DISPLAY_NAMES["shugo"],
                "end":
                    shugo_times["active_end"]
            }
        )


    # --------------------------------------------------------
    # KOMMENDE RIFTS
    # --------------------------------------------------------

    upcoming_events.append(
        {
            "icon": "🌀",
            "name":
                DISPLAY_NAMES["rift"],
            "time":
                rift_times["next_start"]
        }
    )

    upcoming_events.append(
        {
            "icon": "🌀",
            "name":
                DISPLAY_NAMES["rift"],
            "time":
                rift_times["following_start"]
        }
    )


    # --------------------------------------------------------
    # KOMMENDE SHUGOS
    # --------------------------------------------------------

    upcoming_events.append(
        {
            "icon": "🐹",
            "name":
                DISPLAY_NAMES["shugo"],
            "time":
                shugo_times["next_start"]
        }
    )

    upcoming_events.append(
        {
            "icon": "🐹",
            "name":
                DISPLAY_NAMES["shugo"],
            "time":
                shugo_times["following_start"]
        }
    )


    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    upcoming_events.append(
        {
            "icon": "🔄",
            "name":
                DISPLAY_NAMES[
                    "daily_reset"
                ],
            "time":
                daily_reset
        }
    )

    upcoming_events.append(
        {
            "icon": "🔄",
            "name":
                DISPLAY_NAMES[
                    "weekly_reset"
                ],
            "time":
                weekly_reset
        }
    )


    # --------------------------------------------------------
    # ZEITLICH SORTIEREN
    # --------------------------------------------------------

    upcoming_events.sort(
        key=lambda item:
            item["time"]
    )


    # Nur die zwei nächsten Ereignisse oben anzeigen.
    next_events = upcoming_events[:2]


    return {
        "active":
            active_events,

        "next":
            next_events
    }


# ============================================================
# HINTERGRÜNDE LADEN
# ============================================================

def load_image_from_url(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "AION2-Schedule-Bot"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        image_data = response.read()

    return Image.open(
        BytesIO(image_data)
    ).convert("RGBA")


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
    target_height
):
    source_width, source_height = (
        image.size
    )

    source_ratio = (
        source_width /
        source_height
    )

    target_ratio = (
        target_width /
        target_height
    )

    if source_ratio > target_ratio:

        new_width = int(
            source_height *
            target_ratio
        )

        left = (
            source_width -
            new_width
        ) // 2

        image = image.crop(
            (
                left,
                0,
                left + new_width,
                source_height
            )
        )

    else:

        new_height = int(
            source_width /
            target_ratio
        )

        top = (
            source_height -
            new_height
        ) // 2

        image = image.crop(
            (
                0,
                top,
                source_width,
                top + new_height
            )
        )

    return image.resize(
        (
            target_width,
            target_height
        ),
        Image.Resampling.LANCZOS
    )


# ============================================================
# EINHEITLICHER DUNKLER VERLAUF
# ============================================================

def add_strong_left_gradient(
    image,
    solid_ratio,
    fade_ratio,
    max_alpha,
    tone
):
    width, height = image.size

    overlay = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    pixels = overlay.load()

    solid_end = int(
        width *
        solid_ratio
    )

    fade_end = int(
        width *
        fade_ratio
    )

    for x in range(fade_end):

        if x <= solid_end:

            alpha = max_alpha

        else:

            progress = (
                (x - solid_end) /
                (fade_end - solid_end)
            )

            alpha = int(
                max_alpha *
                ((1.0 - progress) ** 1.65)
            )

        for y in range(height):

            pixels[x, y] = (
                tone[0],
                tone[1],
                tone[2],
                alpha
            )

    return Image.alpha_composite(
        image,
        overlay
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
    shadow_offset=2
):
    x, y = position

    draw.text(
        (
            x + shadow_offset,
            y + shadow_offset
        ),
        text,
        font=font,
        fill=(
            0,
            0,
            0,
            200
        )
    )

    draw.text(
        position,
        text,
        font=font,
        fill=fill
    )


# ============================================================
# SPACETIME-RIFT-KARTE
# ============================================================

def create_rift_card(
    rift_data,
    rift_times
):
    image = load_rift_background()

    target_width = 1200
    target_height = 540

    image = crop_and_resize(
        image,
        target_width,
        target_height
    )

    image = add_strong_left_gradient(
        image,
        solid_ratio=0.28,
        fade_ratio=0.78,
        max_alpha=238,
        tone=(2, 1, 3)
    )

    draw = ImageDraw.Draw(
        image,
        "RGBA"
    )

    title_font = load_font(
        56,
        bold=True
    )

    subtitle_font = load_font(
        29,
        bold=False
    )

    status_font = load_font(
        31,
        bold=True
    )

    time_font = load_font(
        48,
        bold=True
    )

    secondary_font = load_font(
        30,
        bold=False
    )

    white = (
        250,
        248,
        251,
        255
    )

    red = (
        255,
        78,
        88,
        255
    )

    light_red = (
        255,
        135,
        140,
        255
    )

    secondary_color = (
        225,
        222,
        225,
        255
    )

    draw_text_with_shadow(
        draw,
        (78, 62),
        DISPLAY_NAMES[
            "rift_card"
        ],
        title_font,
        white
    )

    draw_text_with_shadow(
        draw,
        (80, 132),
        (
            f"Alle "
            f"{rift_data['interval_hours']} Stunden"
        ),
        subtitle_font,
        light_red
    )

    if rift_times[
        "active_start"
    ]:

        main_label = "JETZT AKTIV"

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

        secondary_label = "Nächster"

        secondary_start = (
            rift_times[
                "next_start"
            ]
        )

    else:

        main_label = "NÄCHSTER"

        main_start = (
            rift_times[
                "next_start"
            ]
        )

        main_end = (
            main_start +
            timedelta(
                minutes=rift_data[
                    "duration_minutes"
                ]
            )
        )

        secondary_label = "Danach"

        secondary_start = (
            rift_times[
                "following_start"
            ]
        )

    secondary_end = (
        secondary_start +
        timedelta(
            minutes=rift_data[
                "duration_minutes"
            ]
        )
    )

    draw_text_with_shadow(
        draw,
        (80, 218),
        main_label,
        status_font,
        red
    )

    main_time_text = format_time_range(
        main_start,
        main_end
    )

    main_time_position = (
        78,
        260
    )

    draw_text_with_shadow(
        draw,
        main_time_position,
        main_time_text,
        time_font,
        white
    )

    main_bbox = draw.textbbox(
        main_time_position,
        main_time_text,
        font=time_font
    )

    secondary_y = (
        main_bbox[3] +
        SECONDARY_GAP
    )

    secondary_text = (
        f"→ {secondary_label}: "
        f"{format_time_range(
            secondary_start,
            secondary_end
        )}"
    )

    draw_text_with_shadow(
        draw,
        (80, secondary_y),
        secondary_text,
        secondary_font,
        secondary_color
    )

    image = image.convert(
        "RGB"
    )

    image.save(
        RIFT_CARD_FILE,
        "PNG",
        optimize=True
    )


# ============================================================
# SHUGO-FESTIVAL-KARTE
# ============================================================

def create_shugo_card(
    shugo_data,
    shugo_times
):
    image = load_shugo_background()

    target_width = 1200
    target_height = 620

    image = crop_and_resize(
        image,
        target_width,
        target_height
    )

    image = add_strong_left_gradient(
        image,
        solid_ratio=0.28,
        fade_ratio=0.78,
        max_alpha=225,
        tone=(3, 3, 2)
    )

    draw = ImageDraw.Draw(
        image,
        "RGBA"
    )

    title_font = load_font(
        56,
        bold=True
    )

    subtitle_font = load_font(
        29,
        bold=False
    )

    status_font = load_font(
        31,
        bold=True
    )

    time_font = load_font(
        48,
        bold=True
    )

    game_font = load_font(
        31,
        bold=False
    )

    secondary_font = load_font(
        30,
        bold=False
    )

    white = (
        250,
        248,
        245,
        255
    )

    gold = (
        229,
        177,
        62,
        255
    )

    light_gold = (
        243,
        210,
        126,
        255
    )

    secondary_color = (
        225,
        222,
        225,
        255
    )

    draw_text_with_shadow(
        draw,
        (72, 48),
        DISPLAY_NAMES[
            "shugo_card"
        ],
        title_font,
        white
    )

    draw_text_with_shadow(
        draw,
        (74, 116),
        "Alle 30 Minuten",
        subtitle_font,
        light_gold
    )

    if shugo_times[
        "active_start"
    ]:

        main_label = "JETZT AKTIV"

        main_start = (
            shugo_times[
                "active_start"
            ]
        )

        secondary_label = "Nächstes"

        secondary_start = (
            shugo_times[
                "next_start"
            ]
        )

    else:

        main_label = "NÄCHSTES"

        main_start = (
            shugo_times[
                "next_start"
            ]
        )

        secondary_label = "Danach"

        secondary_start = (
            shugo_times[
                "following_start"
            ]
        )

    current_rotation = (
        shugo_rotation_for_time(
            main_start,
            shugo_data
        )
    )

    draw_text_with_shadow(
        draw,
        (74, 190),
        main_label,
        status_font,
        gold
    )

    main_time_text = (
        f"{main_start.strftime('%H:%M')} Uhr"
    )

    main_time_position = (
        72,
        230
    )

    draw_text_with_shadow(
        draw,
        main_time_position,
        main_time_text,
        time_font,
        white
    )

    y = 305

    last_game_text = None
    last_game_position = None

    for game in current_rotation:

        game_text = (
            f"• {game}"
        )

        game_position = (
            82,
            y
        )

        draw_text_with_shadow(
            draw,
            game_position,
            game_text,
            game_font,
            white
        )

        last_game_text = game_text
        last_game_position = game_position

        y += 43

    last_game_bbox = draw.textbbox(
        last_game_position,
        last_game_text,
        font=game_font
    )

    secondary_y = (
        last_game_bbox[3] +
        SECONDARY_GAP
    )

    secondary_text = (
        f"→ {secondary_label}: "
        f"{secondary_start.strftime('%H:%M')} Uhr"
    )

    draw_text_with_shadow(
        draw,
        (82, secondary_y),
        secondary_text,
        secondary_font,
        secondary_color
    )

    image = image.convert(
        "RGB"
    )

    image.save(
        SHUGO_CARD_FILE,
        "PNG",
        optimize=True
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
        target_height
    )

    image = add_strong_left_gradient(
        image,
        solid_ratio=0.32,
        fade_ratio=0.82,
        max_alpha=245,
        tone=(1, 3, 7)
    )

    draw = ImageDraw.Draw(
        image,
        "RGBA"
    )

    title_font = load_font(
        56,
        bold=True
    )

    label_font = load_font(
        30,
        bold=True
    )

    time_font = load_font(
        46,
        bold=True
    )

    white = (
        248,
        250,
        255,
        255
    )

    blue = (
        64,
        145,
        255,
        255
    )

    light_blue = (
        110,
        190,
        255,
        255
    )

    draw_text_with_shadow(
        draw,
        (74, 58),
        DISPLAY_NAMES[
            "reset_card"
        ],
        title_font,
        white
    )

    draw_text_with_shadow(
        draw,
        (76, 170),
        DISPLAY_NAMES[
            "daily_card"
        ],
        label_font,
        light_blue
    )

    draw_text_with_shadow(
        draw,
        (74, 212),
        "23:00 Uhr",
        time_font,
        white
    )

    draw_text_with_shadow(
        draw,
        (76, 330),
        DISPLAY_NAMES[
            "weekly_card"
        ],
        label_font,
        blue
    )

    draw_text_with_shadow(
        draw,
        (74, 372),
        "Dienstag · 23:00 Uhr",
        time_font,
        white
    )

    image = image.convert(
        "RGB"
    )

    image.save(
        RESET_CARD_FILE,
        "PNG",
        optimize=True
    )


# ============================================================
# EVENT-ÜBERSICHT ALS DISCORD-EMBED
#
# Das ist vorerst noch das normale Discord-Element.
# Sobald die Logik gefällt, ersetzen wir es durch
# unsere eigene schöne Grafik.
# ============================================================

def create_overview_embed(
    event_overview
):
    description_lines = []

    active_events = (
        event_overview["active"]
    )

    next_events = (
        event_overview["next"]
    )


    # --------------------------------------------------------
    # AKTIVE EVENTS
    # --------------------------------------------------------

    if active_events:

        description_lines.append(
            "**JETZT AKTIV**"
        )

        for event in active_events:

            description_lines.append(
                (
                    f"{event['icon']} "
                    f"**{event['name']}** "
                    f"· bis "
                    f"{event['end'].strftime('%H:%M')} Uhr"
                )
            )

        description_lines.append(
            ""
        )


    # --------------------------------------------------------
    # NÄCHSTE EVENTS
    # --------------------------------------------------------

    description_lines.append(
        "**ALS NÄCHSTES**"
    )

    for event in next_events:

        description_lines.append(
            (
                f"{event['icon']} "
                f"**{event['name']}** "
                f"· "
                f"{discord_time(
                    event['time']
                )}"
            )
        )


    return {
        "description":
            "\n".join(
                description_lines
            )
    }


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
        timezone
    )

    create_rift_card(
        rift_data,
        rift_times
    )


    # --------------------------------------------------------
    # SHUGO
    # --------------------------------------------------------

    shugo_times = build_shugo_times(
        shugo_data,
        timezone
    )

    create_shugo_card(
        shugo_data,
        shugo_times
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
    # EVENT-ZENTRALE
    # --------------------------------------------------------

    event_overview = build_event_overview(
        rift_times,
        shugo_times,
        daily_reset,
        weekly_reset
    )

    overview_embed = (
        create_overview_embed(
            event_overview
        )
    )


    # --------------------------------------------------------
    # DETAIL-KARTEN
    # --------------------------------------------------------

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
        # Exakt dasselbe Blau wie WÖCHENTLICH:
        # RGB 64,145,255 = #4091FF
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
        reset_embed
    ]


# ============================================================
# MULTIPART DISCORD REQUEST
# ============================================================

def webhook_request_with_files(
    url,
    payload,
    file_paths,
    method="POST"
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
            "rb"
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
                "AION2-Schedule-Bot"
        }
    )

    with urllib.request.urlopen(
        req,
        timeout=60
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
                    RIFT_CARD_FILE
            },

            {
                "id": 1,
                "filename":
                    SHUGO_CARD_FILE
            },

            {
                "id": 2,
                "filename":
                    RESET_CARD_FILE
            }
        ]
    }

    message_id = state.get(
        "message_id"
    )

    files = [
        RIFT_CARD_FILE,
        SHUGO_CARD_FILE,
        RESET_CARD_FILE
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
            method="PATCH"
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
                method="POST"
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
