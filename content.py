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
FULL_HEIGHT = 535
COMPACT_HEIGHT = 270


# ============================================================
# GEMEINSAME GOLDKANTE DER TITEL
# ============================================================

SERIES_GOLD_OUTLINE = (
    225,
    198,
    143,
    215,
)


# ============================================================
# EARLY ACCESS
# ============================================================

EARLY_TITLE_SIZE = 96
EARLY_TITLE_BOLD = True
EARLY_TITLE_TARGET_WIDTH = 625


# ------------------------------------------------------------
# EARLY – FESTE POSITIONEN
# ------------------------------------------------------------

EARLY_TITLE_TOP = 84

EARLY_DIVIDER_Y = 198
EARLY_DATE_TOP = 232

EARLY_NOCH_TOP = 372
EARLY_DAYS_TOP = 401


# ------------------------------------------------------------
# EARLY – TYPOGRAFIE
# ------------------------------------------------------------

EARLY_DATE_SIZE = 32
EARLY_NOCH_SIZE = 17
EARLY_COUNTDOWN_SIZE = 50


# ============================================================
# EARLY – TITELLOOK
# ============================================================

EARLY_TITLE_SHADOW_OFFSET_X = 2
EARLY_TITLE_SHADOW_OFFSET_Y = 4
EARLY_TITLE_SHADOW_BLUR = 3.2

EARLY_TITLE_SHADOW = (
    4,
    8,
    13,
    195,
)

EARLY_TITLE_GLOW_BLUR = 3.2

EARLY_TITLE_GLOW = (
    250,
    235,
    202,
    40,
)

EARLY_TITLE_OUTLINE = SERIES_GOLD_OUTLINE


# ------------------------------------------------------------
# EARLY – PLATIN-/CHAMPAGNER-VERLAUF
# ------------------------------------------------------------

EARLY_TITLE_TOP_COLOR = (
    249,
    247,
    238,
    255,
)

EARLY_TITLE_UPPER_COLOR = (
    232,
    229,
    216,
    255,
)

EARLY_TITLE_MID_COLOR = (
    204,
    200,
    185,
    255,
)

EARLY_TITLE_BOTTOM_COLOR = (
    161,
    154,
    137,
    255,
)

EARLY_TITLE_SHINE = (
    255,
    252,
    241,
    105,
)

EARLY_TITLE_EDGE_DARK = (
    71,
    65,
    54,
    165,
)


# ============================================================
# EARLY – UNTERE TEXTFARBEN
#
# Nicht mehr Weiß.
# Alles greift die warme Titelfamilie auf.
# ============================================================

EARLY_DATE_TEXT = (
    223,
    211,
    184,
    255,
)

EARLY_COUNTDOWN_TEXT = (
    230,
    218,
    191,
    255,
)

EARLY_NOCH_TEXT = (
    196,
    181,
    151,
    255,
)


# ============================================================
# EARLY – TRENNER
#
# Linie und Raute gehören farblich zusammen.
# ============================================================

EARLY_DIVIDER_WIDTH = 305
EARLY_DIVIDER_CENTER_GAP = 22
EARLY_DIVIDER_THICKNESS = 2

EARLY_DIVIDER_DIAMOND_SIZE = 8

EARLY_LINE = (
    184,
    154,
    105,
    220,
)

EARLY_DIAMOND_OUTLINE = (
    191,
    159,
    108,
    235,
)

# Gleiche Farbfamilie, aber transparent.
EARLY_DIAMOND_FILL = (
    191,
    159,
    108,
    68,
)

EARLY_DIAMOND_CENTER = (
    225,
    202,
    158,
    180,
)


# ============================================================
# GLOBAL LAUNCH
# ============================================================

GLOBAL_TITLE_SIZE = 96
GLOBAL_TITLE_BOLD = True
GLOBAL_TITLE_TARGET_WIDTH = 470


# ------------------------------------------------------------
# GLOBAL – FESTE POSITIONEN
# ------------------------------------------------------------

GLOBAL_GLOBAL_TOP = 52
GLOBAL_LAUNCH_TOP = 137

GLOBAL_DIVIDER_Y = 243
GLOBAL_DATE_TOP = 272

GLOBAL_NOCH_TOP = 382
GLOBAL_DAYS_TOP = 408


# ------------------------------------------------------------
# GLOBAL – TYPOGRAFIE
# ------------------------------------------------------------

GLOBAL_DATE_SIZE = 32
GLOBAL_NOCH_SIZE = 16
GLOBAL_COUNTDOWN_SIZE = 50


# ============================================================
# GLOBAL – TITELLOOK
# ============================================================

GLOBAL_TITLE_SHADOW_OFFSET_X = 2
GLOBAL_TITLE_SHADOW_OFFSET_Y = 4
GLOBAL_TITLE_SHADOW_BLUR = 3.0

GLOBAL_TITLE_SHADOW = (
    7,
    20,
    39,
    185,
)

GLOBAL_TITLE_GLOW_BLUR = 3.0

GLOBAL_TITLE_GLOW = (
    212,
    229,
    248,
    38,
)

GLOBAL_TITLE_OUTLINE = SERIES_GOLD_OUTLINE


# ------------------------------------------------------------
# GLOBAL – NAVY-/BLAUGRAU-VERLAUF
# ------------------------------------------------------------

GLOBAL_TITLE_TOP_COLOR = (
    84,
    112,
    148,
    255,
)

GLOBAL_TITLE_UPPER_COLOR = (
    57,
    84,
    119,
    255,
)

GLOBAL_TITLE_MID_COLOR = (
    30,
    52,
    82,
    255,
)

GLOBAL_TITLE_BOTTOM_COLOR = (
    11,
    27,
    49,
    255,
)

GLOBAL_TITLE_SHINE = (
    226,
    239,
    252,
    90,
)

GLOBAL_TITLE_EDGE_DARK = (
    5,
    17,
    32,
    160,
)


# ============================================================
# GLOBAL – UNTERE TEXTFARBEN
# ============================================================

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


# ============================================================
# GLOBAL – TRENNER
#
# Linie und Raute greifen das Global-Blau auf.
# ============================================================

GLOBAL_DIVIDER_WIDTH = 305
GLOBAL_DIVIDER_CENTER_GAP = 22
GLOBAL_DIVIDER_THICKNESS = 2

GLOBAL_DIVIDER_DIAMOND_SIZE = 8

GLOBAL_LINE = (
    45,
    67,
    99,
    220,
)

GLOBAL_DIAMOND_OUTLINE = (
    45,
    67,
    99,
    235,
)

GLOBAL_DIAMOND_FILL = (
    45,
    67,
    99,
    62,
)

GLOBAL_DIAMOND_CENTER = (
    95,
    118,
    150,
    175,
)


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
# KOMPAKTER HINTERGRUND
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


def spacing_for_target_width(
    draw,
    text,
    font,
    target_width,
):

    if len(text) <= 1:

        return 0

    glyph_width = 0

    for char in text:

        glyph_width += draw.textlength(
            char,
            font=font,
        )

    spacing = (
        target_width
        - glyph_width
    ) / (
        len(text) - 1
    )

    return max(
        0,
        spacing,
    )


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


# ============================================================
# WEICHER ZENTRIERTER TEXT
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
    shadow_fill=None,
    shadow_blur=0,
    shadow_offset=1,
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

    if shadow_fill is not None:

        shadow = Image.new(
            "RGBA",
            image.size,
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
            y + shadow_offset,
            text,
            font,
            shadow_fill,
            spacing,
        )

        if shadow_blur > 0:

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
# TITELMASKE
# ============================================================

def create_title_mask(
    image_size,
    text,
    font,
    center_x,
    y,
    spacing,
):

    width, height = image_size

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


# ============================================================
# FARBE MISCHEN
# ============================================================

def mix_rgba(
    color_a,
    color_b,
    amount,
):

    return tuple(
        int(
            color_a[channel]
            + (
                color_b[channel]
                - color_a[channel]
            )
            * amount
        )
        for channel in range(4)
    )


# ============================================================
# PREMIUM-TITELEFFEKT
# ============================================================

def draw_gradient_title(
    image,
    text,
    font,
    center_x,
    y,
    spacing,
    shadow_offset_x,
    shadow_offset_y,
    shadow_blur,
    shadow_color,
    glow_blur,
    glow_color,
    outline_color,
    top_color,
    upper_color,
    mid_color,
    bottom_color,
    shine_color,
    edge_dark_color,
):

    width, height = image.size

    mask = create_title_mask(
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

    top = bbox[1]
    bottom = bbox[3]

    visible_height = max(
        1,
        bottom - top,
    )


    # ========================================================
    # SCHATTEN
    # ========================================================

    shadow_mask = Image.new(
        "L",
        (
            width,
            height,
        ),
        0,
    )

    shadow_mask.paste(
        mask,
        (
            shadow_offset_x,
            shadow_offset_y,
        ),
    )

    shadow_mask = shadow_mask.filter(
        ImageFilter.GaussianBlur(
            shadow_blur
        )
    )

    shadow_layer = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        (
            shadow_color[0],
            shadow_color[1],
            shadow_color[2],
            0,
        ),
    )

    shadow_layer.putalpha(
        shadow_mask.point(
            lambda value:
                int(
                    value
                    * (
                        shadow_color[3]
                        / 255
                    )
                )
        )
    )

    image = Image.alpha_composite(
        image,
        shadow_layer,
    )


    # ========================================================
    # GLOW
    # ========================================================

    glow_mask = mask.filter(
        ImageFilter.GaussianBlur(
            glow_blur
        )
    )

    glow_layer = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        (
            glow_color[0],
            glow_color[1],
            glow_color[2],
            0,
        ),
    )

    glow_layer.putalpha(
        glow_mask.point(
            lambda value:
                int(
                    value
                    * (
                        glow_color[3]
                        / 255
                    )
                )
        )
    )

    image = Image.alpha_composite(
        image,
        glow_layer,
    )


    # ========================================================
    # GOLDKONTUR AM TITEL
    # ========================================================

    expanded_mask = mask.filter(
        ImageFilter.MaxFilter(
            3
        )
    )

    outline_mask = ImageChops.subtract(
        expanded_mask,
        mask,
    )

    outline_layer = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        (
            outline_color[0],
            outline_color[1],
            outline_color[2],
            0,
        ),
    )

    outline_layer.putalpha(
        outline_mask.point(
            lambda value:
                int(
                    value
                    * (
                        outline_color[3]
                        / 255
                    )
                )
        )
    )

    image = Image.alpha_composite(
        image,
        outline_layer,
    )


    # ========================================================
    # VERLAUF
    # ========================================================

    gradient = Image.new(
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

    gradient_draw = ImageDraw.Draw(
        gradient
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

        if progress <= 0.25:

            local = progress / 0.25

            color = mix_rgba(
                top_color,
                upper_color,
                local,
            )

        elif progress <= 0.58:

            local = (
                progress - 0.25
            ) / 0.33

            color = mix_rgba(
                upper_color,
                mid_color,
                local,
            )

        else:

            local = (
                progress - 0.58
            ) / 0.42

            color = mix_rgba(
                mid_color,
                bottom_color,
                local,
            )

        gradient_draw.line(
            (
                bbox[0],
                yy,
                bbox[2],
                yy,
            ),
            fill=color,
            width=1,
        )

    gradient.putalpha(
        mask
    )

    image = Image.alpha_composite(
        image,
        gradient,
    )


    # ========================================================
    # DUNKLE UNTERKANTE
    # ========================================================

    lower_shift = Image.new(
        "L",
        (
            width,
            height,
        ),
        0,
    )

    lower_shift.paste(
        mask,
        (
            0,
            1,
        ),
    )

    lower_edge = ImageChops.subtract(
        lower_shift,
        mask,
    )

    lower_edge_layer = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        (
            edge_dark_color[0],
            edge_dark_color[1],
            edge_dark_color[2],
            0,
        ),
    )

    lower_edge_layer.putalpha(
        lower_edge.point(
            lambda value:
                int(
                    value
                    * (
                        edge_dark_color[3]
                        / 255
                    )
                )
        )
    )

    image = Image.alpha_composite(
        image,
        lower_edge_layer,
    )


    # ========================================================
    # LICHTREFLEX
    # ========================================================

    shine_mask = Image.new(
        "L",
        (
            width,
            height,
        ),
        0,
    )

    shine_draw = ImageDraw.Draw(
        shine_mask
    )

    shine_center = int(
        top
        + visible_height
        * 0.26
    )

    shine_height = max(
        3,
        int(
            visible_height
            * 0.09
        ),
    )

    shine_draw.rectangle(
        (
            bbox[0],
            shine_center - shine_height,
            bbox[2],
            shine_center + shine_height,
        ),
        fill=100,
    )

    shine_mask = shine_mask.filter(
        ImageFilter.GaussianBlur(
            3.2
        )
    )

    shine_mask = ImageChops.multiply(
        shine_mask,
        mask,
    )

    shine_layer = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        (
            shine_color[0],
            shine_color[1],
            shine_color[2],
            0,
        ),
    )

    shine_layer.putalpha(
        shine_mask.point(
            lambda value:
                int(
                    value
                    * (
                        shine_color[3]
                        / 255
                    )
                )
        )
    )

    image = Image.alpha_composite(
        image,
        shine_layer,
    )

    return image


# ============================================================
# EARLY – TITEL
# ============================================================

def draw_early_title(
    image,
    text,
    font,
    center_x,
    y,
    spacing,
):

    return draw_gradient_title(
        image=image,
        text=text,
        font=font,
        center_x=center_x,
        y=y,
        spacing=spacing,

        shadow_offset_x=
            EARLY_TITLE_SHADOW_OFFSET_X,

        shadow_offset_y=
            EARLY_TITLE_SHADOW_OFFSET_Y,

        shadow_blur=
            EARLY_TITLE_SHADOW_BLUR,

        shadow_color=
            EARLY_TITLE_SHADOW,

        glow_blur=
            EARLY_TITLE_GLOW_BLUR,

        glow_color=
            EARLY_TITLE_GLOW,

        outline_color=
            EARLY_TITLE_OUTLINE,

        top_color=
            EARLY_TITLE_TOP_COLOR,

        upper_color=
            EARLY_TITLE_UPPER_COLOR,

        mid_color=
            EARLY_TITLE_MID_COLOR,

        bottom_color=
            EARLY_TITLE_BOTTOM_COLOR,

        shine_color=
            EARLY_TITLE_SHINE,

        edge_dark_color=
            EARLY_TITLE_EDGE_DARK,
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

    return draw_gradient_title(
        image=image,
        text=text,
        font=font,
        center_x=center_x,
        y=y,
        spacing=spacing,

        shadow_offset_x=
            GLOBAL_TITLE_SHADOW_OFFSET_X,

        shadow_offset_y=
            GLOBAL_TITLE_SHADOW_OFFSET_Y,

        shadow_blur=
            GLOBAL_TITLE_SHADOW_BLUR,

        shadow_color=
            GLOBAL_TITLE_SHADOW,

        glow_blur=
            GLOBAL_TITLE_GLOW_BLUR,

        glow_color=
            GLOBAL_TITLE_GLOW,

        outline_color=
            GLOBAL_TITLE_OUTLINE,

        top_color=
            GLOBAL_TITLE_TOP_COLOR,

        upper_color=
            GLOBAL_TITLE_UPPER_COLOR,

        mid_color=
            GLOBAL_TITLE_MID_COLOR,

        bottom_color=
            GLOBAL_TITLE_BOTTOM_COLOR,

        shine_color=
            GLOBAL_TITLE_SHINE,

        edge_dark_color=
            GLOBAL_TITLE_EDGE_DARK,
    )


# ============================================================
# TRENNER
#
# Außenkontur und Füllung gehören jeweils zur Karte.
# Die Füllung ist bewusst sehr transparent.
# ============================================================

def draw_divider(
    image,
    center_y,
    divider_width,
    center_gap,
    thickness,
    diamond_size,
    line_color,
    diamond_outline,
    diamond_fill,
    diamond_center,
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

    center_x = width / 2
    half_width = divider_width / 2


    # --------------------------------------------------------
    # LINKE LINIE
    # --------------------------------------------------------

    draw.line(
        (
            center_x - half_width,
            center_y,

            center_x - center_gap,
            center_y,
        ),
        fill=line_color,
        width=thickness,
    )


    # --------------------------------------------------------
    # RECHTE LINIE
    # --------------------------------------------------------

    draw.line(
        (
            center_x + center_gap,
            center_y,

            center_x + half_width,
            center_y,
        ),
        fill=line_color,
        width=thickness,
    )


    # --------------------------------------------------------
    # RAUTEN-PUNKTE
    # --------------------------------------------------------

    points = [
        (
            center_x,
            center_y - diamond_size,
        ),
        (
            center_x + diamond_size,
            center_y,
        ),
        (
            center_x,
            center_y + diamond_size,
        ),
        (
            center_x - diamond_size,
            center_y,
        ),
    ]


    # --------------------------------------------------------
    # TRANSPARENTE INNENFÜLLUNG
    # --------------------------------------------------------

    draw.polygon(
        points,
        fill=diamond_fill,
    )


    # --------------------------------------------------------
    # AUSSENKONTUR IN DER FARBWELT DER KARTE
    # --------------------------------------------------------

    draw.line(
        points + [points[0]],
        fill=diamond_outline,
        width=2,
        joint="curve",
    )


    # --------------------------------------------------------
    # WINZIGER MITTELAKZENT
    #
    # Kein weißer Punkt.
    # Nur eine hellere Variante derselben Farbfamilie.
    # --------------------------------------------------------

    draw.ellipse(
        (
            center_x - 1.5,
            center_y - 1.5,
            center_x + 1.5,
            center_y + 1.5,
        ),
        fill=diamond_center,
    )

    return Image.alpha_composite(
        image,
        layer,
    )


# ============================================================
# EARLY – TRENNER
# ============================================================

def draw_early_divider(
    image,
    center_y,
):

    return draw_divider(
        image=image,
        center_y=center_y,

        divider_width=
            EARLY_DIVIDER_WIDTH,

        center_gap=
            EARLY_DIVIDER_CENTER_GAP,

        thickness=
            EARLY_DIVIDER_THICKNESS,

        diamond_size=
            EARLY_DIVIDER_DIAMOND_SIZE,

        line_color=
            EARLY_LINE,

        diamond_outline=
            EARLY_DIAMOND_OUTLINE,

        diamond_fill=
            EARLY_DIAMOND_FILL,

        diamond_center=
            EARLY_DIAMOND_CENTER,
    )


# ============================================================
# GLOBAL – TRENNER
# ============================================================

def draw_global_divider(
    image,
    center_y,
):

    return draw_divider(
        image=image,
        center_y=center_y,

        divider_width=
            GLOBAL_DIVIDER_WIDTH,

        center_gap=
            GLOBAL_DIVIDER_CENTER_GAP,

        thickness=
            GLOBAL_DIVIDER_THICKNESS,

        diamond_size=
            GLOBAL_DIVIDER_DIAMOND_SIZE,

        line_color=
            GLOBAL_LINE,

        diamond_outline=
            GLOBAL_DIAMOND_OUTLINE,

        diamond_fill=
            GLOBAL_DIAMOND_FILL,

        diamond_center=
            GLOBAL_DIAMOND_CENTER,
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
        bold=EARLY_TITLE_BOLD,
    )

    date_font = load_font(
        EARLY_DATE_SIZE,
        bold=True,
    )

    noch_font = load_font(
        EARLY_NOCH_SIZE,
        bold=True,
    )

    days_font = load_font(
        EARLY_COUNTDOWN_SIZE,
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


    # ========================================================
    # TITEL
    # ========================================================

    title_bbox = probe.textbbox(
        (
            0,
            0,
        ),
        title_text,
        font=title_font,
    )

    title_spacing = spacing_for_target_width(
        probe,
        title_text,
        title_font,
        EARLY_TITLE_TARGET_WIDTH,
    )

    title_y = (
        EARLY_TITLE_TOP
        - title_bbox[1]
    )


    # ========================================================
    # DATUM
    # ========================================================

    date_bbox = probe.textbbox(
        (
            0,
            0,
        ),
        date_text,
        font=date_font,
    )

    date_y = (
        EARLY_DATE_TOP
        - date_bbox[1]
    )


    # ========================================================
    # NOCH
    # ========================================================

    if noch_text:

        noch_bbox = probe.textbbox(
            (
                0,
                0,
            ),
            noch_text,
            font=noch_font,
        )

        noch_y = (
            EARLY_NOCH_TOP
            - noch_bbox[1]
        )

    else:

        noch_y = 0


    # ========================================================
    # COUNTDOWN
    # ========================================================

    days_bbox = probe.textbbox(
        (
            0,
            0,
        ),
        days_text,
        font=days_font,
    )

    days_y = (
        EARLY_DAYS_TOP
        - days_bbox[1]
    )


    # ========================================================
    # EARLY ACCESS
    # ========================================================

    image = draw_early_title(
        image,
        title_text,
        title_font,
        CARD_WIDTH / 2,
        title_y,
        title_spacing,
    )


    # ========================================================
    # TRENNER
    # ========================================================

    image = draw_early_divider(
        image,
        EARLY_DIVIDER_Y,
    )


    # ========================================================
    # DATUM
    # ========================================================

    image = draw_soft_centered_text(
        image,
        date_text,
        date_y,
        date_font,
        EARLY_DATE_TEXT,
        (
            0,
            0,
            0,
            180,
        ),
        shadow_blur=2.6,
        shadow_offset=1,
    )


    # ========================================================
    # NOCH
    # ========================================================

    if noch_text:

        image = draw_centered_spaced_text(
            image,
            noch_text,
            noch_y,
            noch_font,
            EARLY_NOCH_TEXT,
            5,
            shadow_fill=(
                0,
                0,
                0,
                205,
            ),
            shadow_blur=2.0,
            shadow_offset=1,
        )


    # ========================================================
    # COUNTDOWN
    # ========================================================

    image = draw_soft_centered_text(
        image,
        days_text,
        days_y,
        days_font,
        EARLY_COUNTDOWN_TEXT,
        (
            0,
            0,
            0,
            195,
        ),
        shadow_blur=3.0,
        shadow_offset=1,
    )

    return image.convert(
        "RGB"
    )


# ============================================================
# GLOBAL LAUNCH – VOLLE KARTE
# ============================================================

def create_global_launch_full_card(
    milestone
):

    image = load_background(
        milestone["background"]
    )

    title_font = load_font(
        GLOBAL_TITLE_SIZE,
        bold=GLOBAL_TITLE_BOLD,
        serif=True,
    )

    date_font = load_font(
        GLOBAL_DATE_SIZE,
        bold=True,
    )

    noch_font = load_font(
        GLOBAL_NOCH_SIZE,
        bold=True,
    )

    days_font = load_font(
        GLOBAL_COUNTDOWN_SIZE,
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


    # ========================================================
    # GLOBAL / LAUNCH
    # ========================================================

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

    global_spacing = spacing_for_target_width(
        probe,
        "GLOBAL",
        title_font,
        GLOBAL_TITLE_TARGET_WIDTH,
    )

    launch_spacing = spacing_for_target_width(
        probe,
        "LAUNCH",
        title_font,
        GLOBAL_TITLE_TARGET_WIDTH,
    )

    global_y = (
        GLOBAL_GLOBAL_TOP
        - global_bbox[1]
    )

    launch_y = (
        GLOBAL_LAUNCH_TOP
        - launch_bbox[1]
    )


    # ========================================================
    # DATUM
    # ========================================================

    date_bbox = probe.textbbox(
        (
            0,
            0,
        ),
        date_text,
        font=date_font,
    )

    date_y = (
        GLOBAL_DATE_TOP
        - date_bbox[1]
    )


    # ========================================================
    # NOCH
    # ========================================================

    if noch_text:

        noch_bbox = probe.textbbox(
            (
                0,
                0,
            ),
            noch_text,
            font=noch_font,
        )

        noch_y = (
            GLOBAL_NOCH_TOP
            - noch_bbox[1]
        )

    else:

        noch_y = 0


    # ========================================================
    # COUNTDOWN
    # ========================================================

    days_bbox = probe.textbbox(
        (
            0,
            0,
        ),
        days_text,
        font=days_font,
    )

    days_y = (
        GLOBAL_DAYS_TOP
        - days_bbox[1]
    )


    # ========================================================
    # GLOBAL
    # ========================================================

    image = draw_global_title_line(
        image,
        "GLOBAL",
        title_font,
        CARD_WIDTH / 2,
        global_y,
        global_spacing,
    )


    # ========================================================
    # LAUNCH
    # ========================================================

    image = draw_global_title_line(
        image,
        "LAUNCH",
        title_font,
        CARD_WIDTH / 2,
        launch_y,
        launch_spacing,
    )


    # ========================================================
    # TRENNER
    # ========================================================

    image = draw_global_divider(
        image,
        GLOBAL_DIVIDER_Y,
    )


    # ========================================================
    # DATUM
    # ========================================================

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


    # ========================================================
    # NOCH
    # ========================================================

    if noch_text:

        image = draw_centered_spaced_text(
            image,
            noch_text,
            noch_y,
            noch_font,
            GLOBAL_MUTED,
            5,
        )


    # ========================================================
    # COUNTDOWN
    # ========================================================

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
            120,
        ),
        shadow_blur=1.5,
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


    # ========================================================
    # GLOBAL COMPACT
    # ========================================================

    if milestone["key"] == "global_launch":

        draw = ImageDraw.Draw(
            image
        )

        title_width = spaced_text_width(
            draw,
            title_text,
            title_font,
            COMPACT_TITLE_SPACING,
        )

        title_x = (
            CARD_WIDTH / 2
            - title_width / 2
        )

        draw_spaced_text(
            draw,
            title_x,
            title_y,
            title_text,
            title_font,
            GLOBAL_TEXT,
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


    # ========================================================
    # EARLY COMPACT
    # ========================================================

    else:

        title_spacing = spacing_for_target_width(
            probe,
            title_text,
            title_font,
            440,
        )

        image = draw_early_title(
            image,
            title_text,
            title_font,
            CARD_WIDTH / 2,
            title_y,
            title_spacing,
        )

        image = draw_soft_centered_text(
            image,
            status_text,
            status_y,
            status_font,
            EARLY_DATE_TEXT,
            (
                0,
                0,
                0,
                150,
            ),
            shadow_blur=2.5,
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
