import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageFilter,
    ImageChops,
)


# ============================================================
# DATEIEN / EINSTELLUNGEN
# ============================================================

DATA_FILE = "content_data.json"

WEBHOOK_URL = os.environ.get("CONTENT_WEBHOOK")

EARLY_ACCESS_OUTPUT = "early_access_card.png"
GLOBAL_LAUNCH_OUTPUT = "global_launch_card.png"


# ============================================================
# KARTENFORMAT
# ============================================================

CARD_WIDTH = 1200

# Große Karte
FULL_HEIGHT = 535

# Eingeklappte Karte nach Start
COMPACT_HEIGHT = 270


# ============================================================
# GEMEINSAME TYPOGRAFIE
# ============================================================

DATE_SIZE = 32
NOCH_SIZE = 17
COUNTDOWN_SIZE = 50

# Datum -> NOCH bekommt bewusst deutlich mehr Luft.
GAP_DATE_NOCH = 52

# NOCH und Countdown gehören optisch zusammen.
GAP_NOCH_DAYS = 10


# ============================================================
# EARLY ACCESS – TITEL
# ============================================================

EARLY_TITLE_SIZE = 68
EARLY_TITLE_SPACING = 3


# ============================================================
# GLOBAL LAUNCH – GROSSE KARTE
#
# GLOBAL
#
# LAUNCH
#
# Beide bleiben 82 px groß.
#
# GLOBAL bekommt etwas mehr Tracking, damit beide Zeilen
# optisch gleichwertig wirken.
# ============================================================

GLOBAL_TITLE_SIZE = 82

GLOBAL_TITLE_SPACING_GLOBAL = 14
GLOBAL_TITLE_SPACING_LAUNCH = 8

# GLOBAL <-> LAUNCH etwas weiter auseinander
GLOBAL_TITLE_LINE_GAP = 14

# LAUNCH -> Zierlinie
GLOBAL_GAP_TITLE_DIVIDER = 24

# Zierlinie
GLOBAL_DIVIDER_WIDTH = 300
GLOBAL_DIVIDER_CENTER_GAP = 14

# Zierlinie -> Datum
GLOBAL_GAP_DIVIDER_DATE = 30

# Der gesamte Block wird nahezu geometrisch zentriert.
# Nur ein minimaler optischer Versatz nach unten.
GLOBAL_GROUP_Y_OFFSET = 3


# ============================================================
# EARLY ACCESS – GROSSE KARTE
# ============================================================

EARLY_GAP_TITLE_DATE = 18


# ============================================================
# KOMPAKTE KARTE
# ============================================================

COMPACT_TITLE_SIZE = 43
COMPACT_STATUS_SIZE = 28

COMPACT_TITLE_SPACING = 5
COMPACT_GAP = 18


# ============================================================
# KOMPAKTER BILDAUSSCHNITT
# ============================================================

COMPACT_CROP_CENTER = {
    "early_access": 0.50,
    "global_launch": 0.50,
}


# ============================================================
# FARBEN
# ============================================================

EARLY_TEXT = (
    238,
    235,
    224,
    255,
)

EARLY_MUTED = (
    187,
    186,
    180,
    255,
)

GLOBAL_DARK = (
    35,
    55,
    83,
    255,
)

GLOBAL_TEXT = (
    42,
    59,
    83,
    255,
)

GLOBAL_MUTED = (
    82,
    95,
    114,
    255,
)

GLOBAL_LINE = (
    50,
    72,
    103,
    165,
)


# ============================================================
# DATEN LADEN
# ============================================================

def load_json(filename, default=None):

    try:

        with open(
            filename,
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    except FileNotFoundError:

        return (
            default
            if default is not None
            else {}
        )


# ============================================================
# ZEIT / COUNTDOWN
# ============================================================

def get_now(timezone_name):

    timezone = ZoneInfo(
        timezone_name
    )

    return datetime.now(
        timezone
    )


def parse_date(
    date_string,
    timezone_name,
):

    timezone = ZoneInfo(
        timezone_name
    )

    return datetime.strptime(
        date_string,
        "%Y-%m-%d",
    ).replace(
        tzinfo=timezone
    )


def get_milestone_status(
    milestone,
    now,
    timezone_name,
):

    target = parse_date(
        milestone["date"],
        timezone_name,
    )

    days = (
        target.date()
        - now.date()
    ).days

    if days > 1:

        return {
            "state": "countdown",
            "days": days,
            "text": f"Noch {days} Tage",
        }

    if days == 1:

        return {
            "state": "countdown",
            "days": 1,
            "text": "Noch 1 Tag",
        }

    if days == 0:

        return {
            "state": "today",
            "days": 0,
            "text": "HEUTE",
        }

    return {
        "state": "started",
        "days": None,
        "text": "GESTARTET",
    }


# ============================================================
# CONTENT AUFBEREITEN
# ============================================================

def build_content_state(data):

    timezone_name = data.get(
        "timezone",
        "Europe/Berlin",
    )

    now = get_now(
        timezone_name
    )

    result = {
        "updated_at": now.isoformat(),
        "milestones": [],
        "active_content": None,
    }

    for milestone in data.get(
        "milestones",
        [],
    ):

        status = get_milestone_status(
            milestone,
            now,
            timezone_name,
        )

        result["milestones"].append(
            {
                "key":
                    milestone["key"],

                "title":
                    milestone["title"],

                "date":
                    milestone["date"],

                "date_display":
                    milestone["date_display"],

                "background":
                    milestone.get(
                        "background"
                    ),

                "state":
                    status["state"],

                "days":
                    status.get(
                        "days"
                    ),

                "status_text":
                    status["text"],
            }
        )

    active_phases = []

    for phase in data.get(
        "content_phases",
        [],
    ):

        if not phase.get(
            "enabled",
            False,
        ):
            continue

        start = parse_date(
            phase["start_date"],
            timezone_name,
        )

        if start.date() <= now.date():

            active_phases.append(
                (
                    start,
                    phase,
                )
            )

    if active_phases:

        active_phases.sort(
            key=lambda item:
                item[0]
        )

        result["active_content"] = (
            active_phases[-1][1]
        )

    return result


# ============================================================
# SCHRIFTEN
# ============================================================

def load_font(
    size,
    bold=False,
    serif=False,
):

    if serif:

        if bold:

            paths = [
                (
                    "/usr/share/fonts/"
                    "truetype/dejavu/"
                    "DejaVuSerif-Bold.ttf"
                ),
                (
                    "/usr/share/fonts/"
                    "truetype/liberation2/"
                    "LiberationSerif-Bold.ttf"
                ),
            ]

        else:

            paths = [
                (
                    "/usr/share/fonts/"
                    "truetype/dejavu/"
                    "DejaVuSerif.ttf"
                ),
                (
                    "/usr/share/fonts/"
                    "truetype/liberation2/"
                    "LiberationSerif-Regular.ttf"
                ),
            ]

    elif bold:

        paths = [
            (
                "/usr/share/fonts/"
                "truetype/dejavu/"
                "DejaVuSans-Bold.ttf"
            ),
            (
                "/usr/share/fonts/"
                "truetype/liberation2/"
                "LiberationSans-Bold.ttf"
            ),
        ]

    else:

        paths = [
            (
                "/usr/share/fonts/"
                "truetype/dejavu/"
                "DejaVuSans.ttf"
            ),
            (
                "/usr/share/fonts/"
                "truetype/liberation2/"
                "LiberationSans-Regular.ttf"
            ),
        ]

    for path in paths:

        if os.path.exists(path):

            return ImageFont.truetype(
                path,
                size=size,
            )

    return ImageFont.load_default()


# ============================================================
# HINTERGRUND
# ============================================================

def load_background(filename):

    if not filename:

        raise RuntimeError(
            "Kein Hintergrundbild "
            "für Content gesetzt."
        )

    if not os.path.exists(filename):

        raise RuntimeError(
            f"Hintergrund fehlt: {filename}"
        )

    image = Image.open(
        filename
    ).convert(
        "RGBA"
    )

    if image.size != (
        CARD_WIDTH,
        FULL_HEIGHT,
    ):

        image = image.resize(
            (
                CARD_WIDTH,
                FULL_HEIGHT,
            ),
            Image.Resampling.LANCZOS,
        )

    return image


# ============================================================
# KOMPAKTEN HINTERGRUND AUSSCHNEIDEN
# ============================================================

def crop_compact_background(
    image,
    milestone_key,
):

    width, height = image.size

    center_factor = (
        COMPACT_CROP_CENTER.get(
            milestone_key,
            0.50,
        )
    )

    center_y = (
        height
        * center_factor
    )

    top = int(
        round(
            center_y
            - COMPACT_HEIGHT / 2
        )
    )

    top = max(
        0,
        min(
            height - COMPACT_HEIGHT,
            top,
        ),
    )

    return image.crop(
        (
            0,
            top,
            width,
            top + COMPACT_HEIGHT,
        )
    )


# ============================================================
# BUCHSTABENABSTAND
# ============================================================

def spaced_text_width(
    draw,
    text,
    font,
    spacing,
):

    width = 0

    for index, char in enumerate(text):

        width += draw.textlength(
            char,
            font=font,
        )

        if index < len(text) - 1:

            width += spacing

    return width


def draw_spaced_text(
    draw,
    x,
    y,
    text,
    font,
    fill,
    spacing,
):

    for index, char in enumerate(text):

        draw.text(
            (
                x,
                y,
            ),
            char,
            font=font,
            fill=fill,
        )

        x += draw.textlength(
            char,
            font=font,
        )

        if index < len(text) - 1:

            x += spacing


# ============================================================
# ZENTRIERTE POSITION
# ============================================================

def centered_text_x(
    draw,
    text,
    font,
    width=CARD_WIDTH,
):

    bbox = draw.textbbox(
        (
            0,
            0,
        ),
        text,
        font=font,
    )

    text_width = (
        bbox[2]
        - bbox[0]
    )

    return (
        (
            width
            - text_width
        )
        / 2
        - bbox[0]
    )


def draw_centered_text(
    draw,
    text,
    y,
    font,
    fill,
    width=CARD_WIDTH,
):

    x = centered_text_x(
        draw,
        text,
        font,
        width,
    )

    draw.text(
        (
            x,
            y,
        ),
        text,
        font=font,
        fill=fill,
    )


# ============================================================
# WEICHER TEXTSCHATTEN
# ============================================================

def draw_soft_centered_text(
    image,
    text,
    y,
    font,
    fill,
    shadow_fill,
    shadow_blur=2.5,
    shadow_offset=1,
):

    width, height = image.size

    probe = ImageDraw.Draw(
        image
    )

    x = centered_text_x(
        probe,
        text,
        font,
        width,
    )

    shadow = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        (
            0,
            0,
            0,
            0,
        ),
    )

    shadow_draw = ImageDraw.Draw(
        shadow
    )

    shadow_draw.text(
        (
            x,
            y + shadow_offset,
        ),
        text,
        font=font,
        fill=shadow_fill,
    )

    shadow = shadow.filter(
        ImageFilter.GaussianBlur(
            shadow_blur
        )
    )

    image = Image.alpha_composite(
        image,
        shadow,
    )

    draw = ImageDraw.Draw(
        image
    )

    draw.text(
        (
            x,
            y,
        ),
        text,
        font=font,
        fill=fill,
    )

    return image


# ============================================================
# GESPERRTER ZENTRIERTER TEXT
# ============================================================

def draw_centered_spaced_text(
    image,
    text,
    y,
    font,
    fill,
    spacing,
):

    probe = ImageDraw.Draw(
        image
    )

    text_width = spaced_text_width(
        probe,
        text,
        font,
        spacing,
    )

    x = (
        CARD_WIDTH / 2
        - text_width / 2
    )

    draw = ImageDraw.Draw(
        image
    )

    draw_spaced_text(
        draw,
        x,
        y,
        text,
        font,
        fill,
        spacing,
    )

    return image


# ============================================================
# EARLY ACCESS – GOLD
# ============================================================

def create_spaced_text_mask(
    size,
    text,
    font,
    center_x,
    y,
    spacing,
):

    width, height = size

    mask = Image.new(
        "L",
        (
            width,
            height,
        ),
        0,
    )

    draw = ImageDraw.Draw(
        mask
    )

    text_width = spaced_text_width(
        draw,
        text,
        font,
        spacing,
    )

    x = (
        center_x
        - text_width / 2
    )

    draw_spaced_text(
        draw,
        x,
        y,
        text,
        font,
        255,
        spacing,
    )

    return mask


def draw_gold_title(
    image,
    text,
    font,
    center_x,
    y,
    spacing,
):

    width, height = image.size

    mask = create_spaced_text_mask(
        image.size,
        text,
        font,
        center_x,
        y,
        spacing,
    )

    bbox = mask.getbbox()

    if not bbox:

        return image

    shifted_mask = Image.new(
        "L",
        (
            width,
            height,
        ),
        0,
    )

    shifted_mask.paste(
        mask,
        (
            0,
            2,
        ),
    )

    shadow_mask = shifted_mask.filter(
        ImageFilter.GaussianBlur(
            3.5
        )
    )

    shadow = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        (
            5,
            8,
            13,
            0,
        ),
    )

    shadow.putalpha(
        shadow_mask.point(
            lambda value:
                int(
                    value
                    * 0.55
                )
        )
    )

    image = Image.alpha_composite(
        image,
        shadow,
    )

    top = bbox[1]
    bottom = bbox[3]

    visible_height = max(
        1,
        bottom - top,
    )

    gold = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        (
            0,
            0,
            0,
            0,
        ),
    )

    pixels = gold.load()

    top_color = (
        248,
        224,
        158,
    )

    middle_color = (
        226,
        183,
        92,
    )

    bottom_color = (
        182,
        132,
        55,
    )

    for yy in range(
        top,
        bottom,
    ):

        progress = (
            (
                yy - top
            )
            / max(
                1,
                visible_height - 1,
            )
        )

        if progress < 0.48:

            local = (
                progress
                / 0.48
            )

            start = top_color
            end = middle_color

        else:

            local = (
                (
                    progress
                    - 0.48
                )
                / 0.52
            )

            start = middle_color
            end = bottom_color

        color = tuple(
            int(
                start[channel]
                + (
                    end[channel]
                    - start[channel]
                )
                * local
            )
            for channel in range(3)
        ) + (255,)

        for xx in range(
            bbox[0],
            bbox[2],
        ):

            pixels[
                xx,
                yy
            ] = color

    gold.putalpha(
        mask
    )

    return Image.alpha_composite(
        image,
        gold,
    )


# ============================================================
# GLOBAL – TITEL
# ============================================================

def draw_global_title_line(
    image,
    text,
    font,
    center_x,
    y,
    spacing,
):

    width, height = image.size

    probe = ImageDraw.Draw(
        image
    )

    text_width = spaced_text_width(
        probe,
        text,
        font,
        spacing,
    )

    x = (
        center_x
        - text_width / 2
    )

    shadow = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        (
            0,
            0,
            0,
            0,
        ),
    )

    shadow_draw = ImageDraw.Draw(
        shadow
    )

    draw_spaced_text(
        shadow_draw,
        x,
        y + 2,
        text,
        font,
        (
            255,
            255,
            255,
            125,
        ),
        spacing,
    )

    shadow = shadow.filter(
        ImageFilter.GaussianBlur(
            1.5
        )
    )

    image = Image.alpha_composite(
        image,
        shadow,
    )

    draw = ImageDraw.Draw(
        image
    )

    draw_spaced_text(
        draw,
        x,
        y,
        text,
        font,
        GLOBAL_DARK,
        spacing,
    )

    return image


# ============================================================
# GLOBAL – ZIERLINIE
# ============================================================

def draw_global_divider(
    image,
    center_y,
):

    width, height = image.size

    layer = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        (
            0,
            0,
            0,
            0,
        ),
    )

    draw = ImageDraw.Draw(
        layer
    )

    center_x = (
        width / 2
    )

    half = (
        GLOBAL_DIVIDER_WIDTH / 2
    )

    gap = (
        GLOBAL_DIVIDER_CENTER_GAP
    )

    draw.line(
        (
            center_x - half,
            center_y,
            center_x - gap,
            center_y,
        ),
        fill=GLOBAL_LINE,
        width=1,
    )

    draw.line(
        (
            center_x + gap,
            center_y,
            center_x + half,
            center_y,
        ),
        fill=GLOBAL_LINE,
        width=1,
    )

    diamond = 4

    draw.polygon(
        [
            (
                center_x,
                center_y - diamond,
            ),
            (
                center_x + diamond,
                center_y,
            ),
            (
                center_x,
                center_y + diamond,
            ),
            (
                center_x - diamond,
                center_y,
            ),
        ],
        fill=(
            46,
            68,
            100,
            195,
        ),
    )

    return Image.alpha_composite(
        image,
        layer,
    )


# ============================================================
# EARLY ACCESS – VOLLE KARTE
# ============================================================

def create_early_access_full_card(
    milestone
):

    image = load_background(
        milestone["background"]
    )

    title_font = load_font(
        EARLY_TITLE_SIZE,
        bold=True,
    )

    date_font = load_font(
        DATE_SIZE,
        bold=True,
    )

    noch_font = load_font(
        NOCH_SIZE,
        bold=True,
    )

    days_font = load_font(
        COUNTDOWN_SIZE,
        bold=True,
    )

    title_text = (
        milestone["title"].upper()
    )

    date_text = (
        milestone[
            "date_display"
        ].upper()
    )

    if milestone["state"] == "countdown":

        days = milestone["days"]

        days_text = (
            f"{days} "
            f"{'TAG' if days == 1 else 'TAGE'}"
        )

        noch_text = "NOCH"

    else:

        days_text = "HEUTE"
        noch_text = ""

    probe = ImageDraw.Draw(
        image
    )

    title_bbox = probe.textbbox(
        (
            0,
            0,
        ),
        title_text,
        font=title_font,
    )

    date_bbox = probe.textbbox(
        (
            0,
            0,
        ),
        date_text,
        font=date_font,
    )

    days_bbox = probe.textbbox(
        (
            0,
            0,
        ),
        days_text,
        font=days_font,
    )

    title_height = (
        title_bbox[3]
        - title_bbox[1]
    )

    date_height = (
        date_bbox[3]
        - date_bbox[1]
    )

    days_height = (
        days_bbox[3]
        - days_bbox[1]
    )

    if noch_text:

        noch_bbox = probe.textbbox(
            (
                0,
                0,
            ),
            noch_text,
            font=noch_font,
        )

        noch_height = (
            noch_bbox[3]
            - noch_bbox[1]
        )

        group_height = (
            title_height
            + EARLY_GAP_TITLE_DATE
            + date_height
            + GAP_DATE_NOCH
            + noch_height
            + GAP_NOCH_DAYS
            + days_height
        )

    else:

        noch_bbox = (
            0,
            0,
            0,
            0,
        )

        noch_height = 0

        group_height = (
            title_height
            + EARLY_GAP_TITLE_DATE
            + date_height
            + GAP_DATE_NOCH
            + days_height
        )

    visible_top = (
        (
            FULL_HEIGHT
            - group_height
        )
        / 2
    )

    title_y = (
        visible_top
        - title_bbox[1]
    )

    date_visible_top = (
        visible_top
        + title_height
        + EARLY_GAP_TITLE_DATE
    )

    date_y = (
        date_visible_top
        - date_bbox[1]
    )

    if noch_text:

        noch_visible_top = (
            date_visible_top
            + date_height
            + GAP_DATE_NOCH
        )

        noch_y = (
            noch_visible_top
            - noch_bbox[1]
        )

        days_visible_top = (
            noch_visible_top
            + noch_height
            + GAP_NOCH_DAYS
        )

    else:

        days_visible_top = (
            date_visible_top
            + date_height
            + GAP_DATE_NOCH
        )

    days_y = (
        days_visible_top
        - days_bbox[1]
    )

    image = draw_gold_title(
        image,
        title_text,
        title_font,
        CARD_WIDTH / 2,
        title_y,
        EARLY_TITLE_SPACING,
    )

    image = draw_soft_centered_text(
        image,
        date_text,
        date_y,
        date_font,
        EARLY_TEXT,
        (
            0,
            0,
            0,
            125,
        ),
        shadow_blur=3.0,
    )

    if noch_text:

        image = draw_centered_spaced_text(
            image,
            noch_text,
            noch_y,
            noch_font,
            EARLY_MUTED,
            4,
        )

    image = draw_soft_centered_text(
        image,
        days_text,
        days_y,
        days_font,
        EARLY_TEXT,
        (
            0,
            0,
            0,
            140,
        ),
        shadow_blur=3.5,
    )

    return image.convert(
        "RGB"
    )


# ============================================================
# GLOBAL LAUNCH – VOLLE KARTE
#
#       GLOBAL
#
#       LAUNCH
#
#    -----◆-----
#
#   5. OKTOBER 2026
#
#
#       NOCH
#      36 TAGE
#
# ============================================================

def create_global_launch_full_card(
    milestone
):

    image = load_background(
        milestone["background"]
    )

    title_font = load_font(
        GLOBAL_TITLE_SIZE,
        bold=False,
        serif=True,
    )

    date_font = load_font(
        DATE_SIZE,
        bold=True,
    )

    noch_font = load_font(
        NOCH_SIZE,
        bold=True,
    )

    days_font = load_font(
        COUNTDOWN_SIZE,
        bold=True,
    )

    date_text = (
        milestone[
            "date_display"
        ].upper()
    )

    if milestone["state"] == "countdown":

        days = milestone["days"]

        days_text = (
            f"{days} "
            f"{'TAG' if days == 1 else 'TAGE'}"
        )

        noch_text = "NOCH"

    else:

        days_text = "HEUTE"
        noch_text = ""

    probe = ImageDraw.Draw(
        image
    )

    global_bbox = probe.textbbox(
        (
            0,
            0,
        ),
        "GLOBAL",
        font=title_font,
    )

    launch_bbox = probe.textbbox(
        (
            0,
            0,
        ),
        "LAUNCH",
        font=title_font,
    )

    date_bbox = probe.textbbox(
        (
            0,
            0,
        ),
        date_text,
        font=date_font,
    )

    days_bbox = probe.textbbox(
        (
            0,
            0,
        ),
        days_text,
        font=days_font,
    )

    global_height = (
        global_bbox[3]
        - global_bbox[1]
    )

    launch_height = (
        launch_bbox[3]
        - launch_bbox[1]
    )

    date_height = (
        date_bbox[3]
        - date_bbox[1]
    )

    days_height = (
        days_bbox[3]
        - days_bbox[1]
    )

    if noch_text:

        noch_bbox = probe.textbbox(
            (
                0,
                0,
            ),
            noch_text,
            font=noch_font,
        )

        noch_height = (
            noch_bbox[3]
            - noch_bbox[1]
        )

    else:

        noch_bbox = (
            0,
            0,
            0,
            0,
        )

        noch_height = 0

    divider_height = 8

    if noch_text:

        group_height = (
            global_height
            + GLOBAL_TITLE_LINE_GAP
            + launch_height
            + GLOBAL_GAP_TITLE_DIVIDER
            + divider_height
            + GLOBAL_GAP_DIVIDER_DATE
            + date_height
            + GAP_DATE_NOCH
            + noch_height
            + GAP_NOCH_DAYS
            + days_height
        )

    else:

        group_height = (
            global_height
            + GLOBAL_TITLE_LINE_GAP
            + launch_height
            + GLOBAL_GAP_TITLE_DIVIDER
            + divider_height
            + GLOBAL_GAP_DIVIDER_DATE
            + date_height
            + GAP_DATE_NOCH
            + days_height
        )

    visible_top = (
        (
            FULL_HEIGHT
            - group_height
        )
        / 2
        + GLOBAL_GROUP_Y_OFFSET
    )

    # --------------------------------------------------------
    # GLOBAL
    # --------------------------------------------------------

    global_y = (
        visible_top
        - global_bbox[1]
    )

    # --------------------------------------------------------
    # LAUNCH
    # --------------------------------------------------------

    launch_visible_top = (
        visible_top
        + global_height
        + GLOBAL_TITLE_LINE_GAP
    )

    launch_y = (
        launch_visible_top
        - launch_bbox[1]
    )

    # --------------------------------------------------------
    # ZIERLINIE
    # --------------------------------------------------------

    divider_y = (
        launch_visible_top
        + launch_height
        + GLOBAL_GAP_TITLE_DIVIDER
        + divider_height / 2
    )

    # --------------------------------------------------------
    # DATUM
    # --------------------------------------------------------

    date_visible_top = (
        divider_y
        + divider_height / 2
        + GLOBAL_GAP_DIVIDER_DATE
    )

    date_y = (
        date_visible_top
        - date_bbox[1]
    )

    # --------------------------------------------------------
    # NOCH / TAGE
    # --------------------------------------------------------

    if noch_text:

        noch_visible_top = (
            date_visible_top
            + date_height
            + GAP_DATE_NOCH
        )

        noch_y = (
            noch_visible_top
            - noch_bbox[1]
        )

        days_visible_top = (
            noch_visible_top
            + noch_height
            + GAP_NOCH_DAYS
        )

    else:

        days_visible_top = (
            date_visible_top
            + date_height
            + GAP_DATE_NOCH
        )

    days_y = (
        days_visible_top
        - days_bbox[1]
    )

    # --------------------------------------------------------
    # GLOBAL
    # --------------------------------------------------------

    image = draw_global_title_line(
        image,
        "GLOBAL",
        title_font,
        CARD_WIDTH / 2,
        global_y,
        GLOBAL_TITLE_SPACING_GLOBAL,
    )

    # --------------------------------------------------------
    # LAUNCH
    # --------------------------------------------------------

    image = draw_global_title_line(
        image,
        "LAUNCH",
        title_font,
        CARD_WIDTH / 2,
        launch_y,
        GLOBAL_TITLE_SPACING_LAUNCH,
    )

    # --------------------------------------------------------
    # ZIERLINIE
    # --------------------------------------------------------

    image = draw_global_divider(
        image,
        divider_y,
    )

    # --------------------------------------------------------
    # DATUM
    # --------------------------------------------------------

    image = draw_soft_centered_text(
        image,
        date_text,
        date_y,
        date_font,
        GLOBAL_TEXT,
        (
            255,
            255,
            255,
            135,
        ),
        shadow_blur=1.7,
        shadow_offset=1,
    )

    # --------------------------------------------------------
    # NOCH
    # --------------------------------------------------------

    if noch_text:

        image = draw_centered_spaced_text(
            image,
            noch_text,
            noch_y,
            noch_font,
            GLOBAL_MUTED,
            5,
        )

    # --------------------------------------------------------
    # COUNTDOWN
    # --------------------------------------------------------

    image = draw_soft_centered_text(
        image,
        days_text,
        days_y,
        days_font,
        GLOBAL_TEXT,
        (
            255,
            255,
            255,
            140,
        ),
        shadow_blur=1.8,
        shadow_offset=1,
    )

    return image.convert(
        "RGB"
    )


# ============================================================
# VOLLE KARTE
# ============================================================

def create_full_card(
    milestone
):

    if milestone["key"] == "global_launch":

        return create_global_launch_full_card(
            milestone
        )

    return create_early_access_full_card(
        milestone
    )


# ============================================================
# KOMPAKTE KARTE
#
# Nach Start:
#
# GLOBAL LAUNCH
# 5. OKTOBER 2026 · GESTARTET
#
# bzw.
#
# EARLY ACCESS
# 30. SEPTEMBER 2026 · GESTARTET
# ============================================================

def create_compact_card(
    milestone
):

    master = load_background(
        milestone["background"]
    )

    image = crop_compact_background(
        master,
        milestone["key"],
    )

    if milestone["key"] == "global_launch":

        title_font = load_font(
            COMPACT_TITLE_SIZE,
            bold=False,
            serif=True,
        )

    else:

        title_font = load_font(
            COMPACT_TITLE_SIZE,
            bold=True,
        )

    status_font = load_font(
        COMPACT_STATUS_SIZE,
        bold=True,
    )

    title_text = (
        milestone["title"].upper()
    )

    status_text = (
        f"{milestone['date_display'].upper()} "
        f"· GESTARTET"
    )

    probe = ImageDraw.Draw(
        image
    )

    title_bbox = probe.textbbox(
        (
            0,
            0,
        ),
        title_text,
        font=title_font,
    )

    status_bbox = probe.textbbox(
        (
            0,
            0,
        ),
        status_text,
        font=status_font,
    )

    title_height = (
        title_bbox[3]
        - title_bbox[1]
    )

    status_height = (
        status_bbox[3]
        - status_bbox[1]
    )

    group_height = (
        title_height
        + COMPACT_GAP
        + status_height
    )

    visible_top = (
        (
            COMPACT_HEIGHT
            - group_height
        )
        / 2
    )

    title_y = (
        visible_top
        - title_bbox[1]
    )

    status_visible_top = (
        visible_top
        + title_height
        + COMPACT_GAP
    )

    status_y = (
        status_visible_top
        - status_bbox[1]
    )

    if milestone["key"] == "global_launch":

        image = draw_global_title_line(
            image,
            title_text,
            title_font,
            CARD_WIDTH / 2,
            title_y,
            COMPACT_TITLE_SPACING,
        )

        image = draw_soft_centered_text(
            image,
            status_text,
            status_y,
            status_font,
            GLOBAL_TEXT,
            (
                255,
                255,
                255,
                125,
            ),
            shadow_blur=1.6,
        )

    else:

        image = draw_gold_title(
            image,
            title_text,
            title_font,
            CARD_WIDTH / 2,
            title_y,
            COMPACT_TITLE_SPACING,
        )

        image = draw_soft_centered_text(
            image,
            status_text,
            status_y,
            status_font,
            EARLY_TEXT,
            (
                0,
                0,
                0,
                130,
            ),
            shadow_blur=3.0,
        )

    return image.convert(
        "RGB"
    )


# ============================================================
# MILESTONE RENDERN
# ============================================================

def render_milestone(
    milestone
):

    if milestone["state"] in (
        "countdown",
        "today",
    ):

        return create_full_card(
            milestone
        )

    return create_compact_card(
        milestone
    )


# ============================================================
# SPEICHERN
# ============================================================

def save_milestone_card(
    milestone
):

    image = render_milestone(
        milestone
    )

    if milestone["key"] == "early_access":

        filename = (
            EARLY_ACCESS_OUTPUT
        )

    elif milestone["key"] == "global_launch":

        filename = (
            GLOBAL_LAUNCH_OUTPUT
        )

    else:

        filename = (
            f"{milestone['key']}_card.png"
        )

    image.save(
        filename,
        "PNG",
        optimize=True,
    )

    print(
        f"{milestone['title']}: "
        f"{filename} "
        f"({image.width}x{image.height})"
    )

    return filename


# ============================================================
# DISCORD
#
# TESTPHASE:
#
# Beide Karten werden jeweils als eigene Nachricht gepostet.
# Alte Testnachrichten löschen wir derzeit manuell.
# ============================================================

def webhook_wait_url():

    separator = (
        "&"
        if "?" in WEBHOOK_URL
        else "?"
    )

    return (
        WEBHOOK_URL
        + separator
        + "wait=true"
    )


def post_discord_image(
    image_file,
    discord_filename,
):

    payload = {
        "content": "",
        "allowed_mentions": {
            "parse": []
        },
        "attachments": [
            {
                "id": 0,
                "filename": discord_filename,
            }
        ],
    }

    with open(
        image_file,
        "rb",
    ) as image_handle:

        files = {
            "files[0]": (
                discord_filename,
                image_handle,
                "image/png",
            )
        }

        response = requests.post(
            webhook_wait_url(),
            data={
                "payload_json":
                    json.dumps(payload)
            },
            files=files,
            timeout=30,
        )

    if response.status_code not in (
        200,
        201,
    ):

        raise RuntimeError(
            "Discord Content konnte "
            "nicht erstellt werden.\n"
            f"HTTP {response.status_code}\n"
            f"{response.text}"
        )

    message = response.json()

    message_id = message.get(
        "id"
    )

    if not message_id:

        raise RuntimeError(
            "Discord hat keine "
            "Message-ID zurückgegeben."
        )

    return message_id


def send_content_to_discord(
    early_access_file,
    global_launch_file,
):

    if not WEBHOOK_URL:

        raise RuntimeError(
            "GitHub Secret CONTENT_WEBHOOK fehlt."
        )

    print("")
    print(
        "Early Access wird gesendet ..."
    )

    early_message_id = post_discord_image(
        early_access_file,
        "early_access.png",
    )

    print(
        f"Early Access Message-ID: "
        f"{early_message_id}"
    )

    print("")
    print(
        "Global Launch wird gesendet ..."
    )

    global_message_id = post_discord_image(
        global_launch_file,
        "global_launch.png",
    )

    print(
        f"Global Launch Message-ID: "
        f"{global_message_id}"
    )

    print("")
    print(
        "========================================"
    )
    print(
        "BEIDE TESTKARTEN GESENDET"
    )
    print(
        "========================================"
    )


# ============================================================
# STATUSAUSGABE
# ============================================================

def print_status(
    content_state
):

    print("")
    print(
        "========================================"
    )
    print(
        "AION 2 CONTENT"
    )
    print(
        "========================================"
    )

    for milestone in (
        content_state["milestones"]
    ):

        print("")
        print(
            milestone["title"]
        )
        print(
            milestone["date_display"]
        )
        print(
            milestone["status_text"]
        )

    print("")
    print(
        "========================================"
    )


# ============================================================
# HAUPTPROGRAMM
# ============================================================

def main():

    data = load_json(
        DATA_FILE,
        {},
    )

    if not data:

        raise RuntimeError(
            "content_data.json "
            "ist leer oder fehlt."
        )

    content_state = build_content_state(
        data
    )

    print_status(
        content_state
    )

    wanted_keys = {
        "early_access",
        "global_launch",
    }

    rendered_files = {}

    for milestone in (
        content_state["milestones"]
    ):

        if milestone["key"] not in wanted_keys:

            continue

        filename = save_milestone_card(
            milestone
        )

        rendered_files[
            milestone["key"]
        ] = filename

    missing = (
        wanted_keys
        - set(
            rendered_files.keys()
        )
    )

    if missing:

        raise RuntimeError(
            "Folgende Milestones fehlen "
            "in content_data.json: "
            + ", ".join(
                sorted(missing)
            )
        )

    send_content_to_discord(
        rendered_files[
            "early_access"
        ],
        rendered_files[
            "global_launch"
        ],
    )


if __name__ == "__main__":
    main()
