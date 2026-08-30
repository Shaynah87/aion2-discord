import os
import json
import math
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
MESSAGE_STATE_FILE = "content_message.json"

WEBHOOK_URL = os.environ.get("CONTENT_WEBHOOK")

EARLY_ACCESS_OUTPUT = "early_access_card.png"
GLOBAL_LAUNCH_OUTPUT = "global_launch_card.png"
EARLY_COMPACT_PREVIEW_OUTPUT = "early_access_compact_preview.png"
GLOBAL_COMPACT_PREVIEW_OUTPUT = "global_launch_compact_preview.png"


# ============================================================
# KARTENFORMAT
# ============================================================

CARD_WIDTH = 1200
FULL_HEIGHT = 535
COMPACT_HEIGHT = 220


# ============================================================
# COUNTDOWN
# ============================================================

COUNTDOWN_DAYS_SIZE = 54
COUNTDOWN_NOCH_SIZE = 17
COUNTDOWN_NOCH_DAYS_GAP = 10


# ============================================================
# GLOBAL – POSITION DES OBEREN BLOCKS
#
# GLOBAL bleibt exakt auf der bisherigen Position.
# ============================================================

GLOBAL_VISIBLE_TOP = 60


# ============================================================
# GLOBAL – GOLDENE TITELKANTE
# ============================================================

GLOBAL_GOLD_OUTLINE = (
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

EARLY_DATE_SIZE = 32
EARLY_NOCH_SIZE = COUNTDOWN_NOCH_SIZE
EARLY_COUNTDOWN_SIZE = COUNTDOWN_DAYS_SIZE


# ------------------------------------------------------------
# EARLY – ABSTÄNDE
# ------------------------------------------------------------

EARLY_GAP_TITLE_DIVIDER = 28
EARLY_GAP_DIVIDER_DATE = 28


# ============================================================
# EARLY – TITEL
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


# ------------------------------------------------------------
# EARLY – WEISSE LESEKANTE
#
# Nur EARLY ACCESS.
# ------------------------------------------------------------

EARLY_READABILITY_OUTLINE = (
    255,
    255,
    255,
    115,
)

EARLY_READABILITY_STROKE_WIDTH = 1


# ------------------------------------------------------------
# EARLY – DUNKLE LESEKANTE
#
# Nur Datum / NOCH / Countdown.
# ------------------------------------------------------------

EARLY_LOWER_READABILITY_OUTLINE = (
    4,
    9,
    15,
    190,
)

EARLY_LOWER_READABILITY_STROKE_WIDTH = 1


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


# ------------------------------------------------------------
# EARLY – DATUM / COUNTDOWN
# ------------------------------------------------------------

EARLY_DATE_TEXT = (
    213,
    207,
    190,
    255,
)

EARLY_COUNTDOWN_TEXT = (
    218,
    212,
    194,
    255,
)

EARLY_NOCH_TEXT = (
    222,
    217,
    204,
    255,
)

EARLY_NOCH_SHADOW = (
    0,
    0,
    0,
    230,
)


# ============================================================
# EARLY – TRENNER
# ============================================================

EARLY_DIVIDER_WIDTH = 410
EARLY_DIVIDER_DOT_RADIUS = 1.8
EARLY_DIVIDER_MAX_HALF_HEIGHT = 2.6
EARLY_DIVIDER_SHOULDER_LENGTH = 18
EARLY_DIVIDER_TAPER_POWER = 1.32

EARLY_LINE = (
    213,
    207,
    190,
    255,
)


# ============================================================
# GLOBAL LAUNCH
# ============================================================

GLOBAL_TITLE_SIZE = 96
GLOBAL_TITLE_BOLD = True
GLOBAL_TITLE_TARGET_WIDTH = 470

GLOBAL_DATE_SIZE = 32
GLOBAL_NOCH_SIZE = COUNTDOWN_NOCH_SIZE
GLOBAL_COUNTDOWN_SIZE = COUNTDOWN_DAYS_SIZE


# ------------------------------------------------------------
# GLOBAL – ABSTÄNDE
#
# GLOBAL / LAUNCH bleibt wie bisher.
# Trenner sitzt mit identischem Abstand zwischen
# LAUNCH und Datum.
# ------------------------------------------------------------

GLOBAL_TITLE_LINE_GAP = 13

GLOBAL_GAP_LAUNCH_DIVIDER = 28
GLOBAL_GAP_DIVIDER_DATE = 28


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


# ------------------------------------------------------------
# GLOBAL – DATUM / COUNTDOWN
# ------------------------------------------------------------

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
# ============================================================

GLOBAL_DIVIDER_WIDTH = 410
GLOBAL_DIVIDER_DOT_RADIUS = 1.8
GLOBAL_DIVIDER_MAX_HALF_HEIGHT = 2.2
GLOBAL_DIVIDER_SHOULDER_LENGTH = 18
GLOBAL_DIVIDER_TAPER_POWER = 1.32

GLOBAL_LINE = (
    42,
    59,
    83,
    255,
)


# ============================================================
# KOMPAKTE KARTE
# ============================================================

COMPACT_TITLE_SIZE = 43
COMPACT_STATUS_SIZE = 28

COMPACT_TITLE_SPACING = 5
COMPACT_GAP = 18

# Nur für unsere aktuelle Sichtkontrolle:
# True = zusätzlich zu den beiden echten Content-Nachrichten werden
# zwei separate Zweizeiler UNTEN DRUNTER gepostet.
# Die bestehenden Early-/Global-Nachrichten werden dadurch NICHT
# auf Compact umgestellt und ihre gespeicherten Message-IDs bleiben
# unangetastet. Nach dem Test einfach wieder auf False setzen.
TEST_COMPACT_PREVIEW = True

COMPACT_CROP_CENTER = {
    # Kugel: optische Mitte des Masters.
    "early_access": 0.50,

    # Global: Ausschnitt etwas höher, damit die Gesichter
    # der beiden Hauptfiguren im 220px-Zweizeiler bleiben.
    "global_launch": 0.40,
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
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
            ]

        else:

            paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
            ]

    elif bold:

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
# HINTERGRUND
# ============================================================

def load_background(filename):

    if not filename:

        raise RuntimeError(
            "Kein Hintergrundbild für Content gesetzt."
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
    stroke_width=0,
    stroke_fill=None,
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
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )

        x += draw.textlength(
            char,
            font=font,
        )

        if index < len(text) - 1:

            x += spacing


# ============================================================
# TEXT-METRIKEN
# ============================================================

def get_visible_text_metrics(
    draw,
    text,
    font,
):

    bbox = draw.textbbox(
        (
            0,
            0,
        ),
        text,
        font=font,
    )

    return {
        "bbox": bbox,
        "height": (
            bbox[3]
            - bbox[1]
        ),
    }


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
# ZENTRIERTER TEXT
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
    stroke_width=0,
    stroke_fill=None,
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
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )

    return image


# ============================================================
# ZENTRIERTER TEXT MIT BUCHSTABENABSTAND
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
    stroke_width=0,
    stroke_fill=None,
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
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
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
# FARBMISCHUNG
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
    outline_width,
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


    # --------------------------------------------------------
    # SCHATTEN
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # GLOW
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # AUSSENKONTUR
    # --------------------------------------------------------

    if (
        outline_color is not None
        and outline_width > 0
    ):

        filter_size = (
            outline_width * 2
            + 1
        )

        expanded_mask = mask.filter(
            ImageFilter.MaxFilter(
                filter_size
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


    # --------------------------------------------------------
    # FARBVERLAUF
    # --------------------------------------------------------

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

            local = (
                progress
                / 0.25
            )

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


    # --------------------------------------------------------
    # DUNKLE UNTERKANTE
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # LICHTREFLEX
    # --------------------------------------------------------

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
            EARLY_READABILITY_OUTLINE,

        outline_width=
            EARLY_READABILITY_STROKE_WIDTH,

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
            GLOBAL_GOLD_OUTLINE,

        outline_width=1,

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
# ============================================================

def draw_blade_divider(
    image,
    center_y,
    divider_width,
    dot_radius,
    max_half_height,
    shoulder_length,
    taper_power,
    color,
):

    width, height = image.size

    scale = 4

    scaled_width = (
        width * scale
    )

    scaled_height = (
        height * scale
    )

    center_x = (
        width / 2
        * scale
    )

    center_y_scaled = (
        center_y
        * scale
    )

    half_total_width = (
        divider_width
        / 2
        * scale
    )

    dot_radius_scaled = (
        dot_radius
        * scale
    )

    max_half_height_scaled = (
        max_half_height
        * scale
    )

    shoulder_length_scaled = (
        shoulder_length
        * scale
    )

    layer = Image.new(
        "RGBA",
        (
            scaled_width,
            scaled_height,
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

    max_distance = int(
        half_total_width
    )

    for distance in range(
        0,
        max_distance + 1,
    ):

        d = float(
            distance
        )

        if d <= dot_radius_scaled:

            inside = max(
                0.0,
                (
                    dot_radius_scaled
                    * dot_radius_scaled
                )
                - (
                    d * d
                ),
            )

            half_height = math.sqrt(
                inside
            )

        elif d <= (
            dot_radius_scaled
            + shoulder_length_scaled
        ):

            local = (
                (
                    d
                    - dot_radius_scaled
                )
                / shoulder_length_scaled
            )

            smooth = (
                local
                * local
                * (
                    3.0
                    - 2.0 * local
                )
            )

            half_height = (
                max_half_height_scaled
                * smooth
            )

        else:

            taper_start = (
                dot_radius_scaled
                + shoulder_length_scaled
            )

            taper_length = max(
                1.0,
                half_total_width
                - taper_start,
            )

            progress = (
                (
                    d
                    - taper_start
                )
                / taper_length
            )

            progress = max(
                0.0,
                min(
                    1.0,
                    progress,
                ),
            )

            remaining = (
                1.0
                - progress
            )

            half_height = (
                max_half_height_scaled
                * (
                    remaining
                    ** taper_power
                )
            )

        if distance >= max_distance:

            half_height = 0

        if half_height <= 0:

            continue

        x_left = int(
            round(
                center_x
                - distance
            )
        )

        x_right = int(
            round(
                center_x
                + distance
            )
        )

        y_top = int(
            round(
                center_y_scaled
                - half_height
            )
        )

        y_bottom = int(
            round(
                center_y_scaled
                + half_height
            )
        )

        draw.line(
            (
                x_left,
                y_top,
                x_left,
                y_bottom,
            ),
            fill=color,
            width=1,
        )

        if x_right != x_left:

            draw.line(
                (
                    x_right,
                    y_top,
                    x_right,
                    y_bottom,
                ),
                fill=color,
                width=1,
            )

    layer = layer.resize(
        (
            width,
            height,
        ),
        Image.Resampling.LANCZOS,
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

    return draw_blade_divider(
        image=image,
        center_y=center_y,

        divider_width=
            EARLY_DIVIDER_WIDTH,

        dot_radius=
            EARLY_DIVIDER_DOT_RADIUS,

        max_half_height=
            EARLY_DIVIDER_MAX_HALF_HEIGHT,

        shoulder_length=
            EARLY_DIVIDER_SHOULDER_LENGTH,

        taper_power=
            EARLY_DIVIDER_TAPER_POWER,

        color=
            EARLY_LINE,
    )


# ============================================================
# GLOBAL – TRENNER
# ============================================================

def draw_global_divider(
    image,
    center_y,
):

    return draw_blade_divider(
        image=image,
        center_y=center_y,

        divider_width=
            GLOBAL_DIVIDER_WIDTH,

        dot_radius=
            GLOBAL_DIVIDER_DOT_RADIUS,

        max_half_height=
            GLOBAL_DIVIDER_MAX_HALF_HEIGHT,

        shoulder_length=
            GLOBAL_DIVIDER_SHOULDER_LENGTH,

        taper_power=
            GLOBAL_DIVIDER_TAPER_POWER,

        color=
            GLOBAL_LINE,
    )


# ============================================================
# COUNTDOWN-LAYOUT
#
# NEU:
#
# visible_bottom_margin ist der Abstand, der unten exakt
# eingehalten werden soll.
#
# Global:
#   oberer Abstand GLOBAL = unterer Abstand 36 TAGE
#
# Early:
#   oberer Abstand EARLY ACCESS = unterer Abstand 31 TAGE
# ============================================================

def calculate_countdown_layout(
    image,
    noch_text,
    noch_font,
    days_text,
    days_font,
    visible_bottom_margin,
):

    draw = ImageDraw.Draw(
        image
    )

    days_metrics = get_visible_text_metrics(
        draw,
        days_text,
        days_font,
    )

    days_height = (
        days_metrics["height"]
    )

    days_visible_bottom = (
        FULL_HEIGHT
        - visible_bottom_margin
    )

    days_visible_top = (
        days_visible_bottom
        - days_height
    )

    days_y = (
        days_visible_top
        - days_metrics["bbox"][1]
    )

    if noch_text:

        noch_metrics = get_visible_text_metrics(
            draw,
            noch_text,
            noch_font,
        )

        noch_height = (
            noch_metrics["height"]
        )

        noch_visible_top = (
            days_visible_top
            - COUNTDOWN_NOCH_DAYS_GAP
            - noch_height
        )

        noch_y = (
            noch_visible_top
            - noch_metrics["bbox"][1]
        )

    else:

        noch_y = 0

    return {
        "noch_y": noch_y,
        "days_y": days_y,
        "days_visible_bottom":
            days_visible_bottom,
    }


# ============================================================
# GLOBAL – OBERER BLOCK
#
# GLOBAL bleibt exakt auf Position 60.
# ============================================================

def calculate_global_upper_layout(
    image,
    title_font,
    date_text,
    date_font,
):

    draw = ImageDraw.Draw(
        image
    )

    global_metrics = get_visible_text_metrics(
        draw,
        "GLOBAL",
        title_font,
    )

    launch_metrics = get_visible_text_metrics(
        draw,
        "LAUNCH",
        title_font,
    )

    date_metrics = get_visible_text_metrics(
        draw,
        date_text,
        date_font,
    )

    global_height = (
        global_metrics["height"]
    )

    launch_height = (
        launch_metrics["height"]
    )

    global_visible_top = (
        GLOBAL_VISIBLE_TOP
    )

    launch_visible_top = (
        global_visible_top
        + global_height
        + GLOBAL_TITLE_LINE_GAP
    )

    divider_y = (
        launch_visible_top
        + launch_height
        + GLOBAL_GAP_LAUNCH_DIVIDER
    )

    date_visible_top = (
        divider_y
        + GLOBAL_GAP_DIVIDER_DATE
    )

    global_y = (
        global_visible_top
        - global_metrics["bbox"][1]
    )

    launch_y = (
        launch_visible_top
        - launch_metrics["bbox"][1]
    )

    date_y = (
        date_visible_top
        - date_metrics["bbox"][1]
    )

    title_block_visible_bottom = (
        launch_visible_top
        + launch_height
    )

    title_block_center_y = (
        global_visible_top
        + title_block_visible_bottom
    ) / 2

    return {
        "global_y":
            global_y,

        "launch_y":
            launch_y,

        "divider_y":
            divider_y,

        "date_y":
            date_y,

        "global_visible_top":
            global_visible_top,

        "title_block_center_y":
            title_block_center_y,
    }


# ============================================================
# EARLY – OBERER BLOCK
#
# EARLY ACCESS bleibt exakt auf der Mittellinie des
# GLOBAL/LAUNCH-Zweizeilers.
# ============================================================

def calculate_early_upper_layout(
    image,
    title_text,
    title_font,
    date_text,
    date_font,
    global_title_center_y,
):

    draw = ImageDraw.Draw(
        image
    )

    title_metrics = get_visible_text_metrics(
        draw,
        title_text,
        title_font,
    )

    date_metrics = get_visible_text_metrics(
        draw,
        date_text,
        date_font,
    )

    title_height = (
        title_metrics["height"]
    )

    title_visible_top = (
        global_title_center_y
        - title_height / 2
    )

    divider_y = (
        title_visible_top
        + title_height
        + EARLY_GAP_TITLE_DIVIDER
    )

    date_visible_top = (
        divider_y
        + EARLY_GAP_DIVIDER_DATE
    )

    title_y = (
        title_visible_top
        - title_metrics["bbox"][1]
    )

    date_y = (
        date_visible_top
        - date_metrics["bbox"][1]
    )

    return {
        "title_y":
            title_y,

        "divider_y":
            divider_y,

        "date_y":
            date_y,

        "title_visible_top":
            title_visible_top,
    }


# ============================================================
# GLOBAL-TITELMITTE
# ============================================================

def get_global_title_center_y():

    dummy = Image.new(
        "RGBA",
        (
            CARD_WIDTH,
            FULL_HEIGHT,
        ),
        (
            0,
            0,
            0,
            0,
        ),
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

    layout = calculate_global_upper_layout(
        image=dummy,
        title_font=title_font,
        date_text="5. OKTOBER 2026",
        date_font=date_font,
    )

    return layout[
        "title_block_center_y"
    ]


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

    title_spacing = spacing_for_target_width(
        probe,
        title_text,
        title_font,
        EARLY_TITLE_TARGET_WIDTH,
    )

    global_title_center_y = (
        get_global_title_center_y()
    )

    upper_layout = calculate_early_upper_layout(
        image=image,
        title_text=title_text,
        title_font=title_font,
        date_text=date_text,
        date_font=date_font,
        global_title_center_y=
            global_title_center_y,
    )


    # --------------------------------------------------------
    # EARLY – SYMMETRISCHER AUSSENABSTAND
    #
    # Abstand oben von EARLY ACCESS wird 1:1 als Abstand
    # unten unter 31 TAGE verwendet.
    # --------------------------------------------------------

    early_top_margin = (
        upper_layout[
            "title_visible_top"
        ]
    )


    countdown_layout = calculate_countdown_layout(
        image=image,
        noch_text=noch_text,
        noch_font=noch_font,
        days_text=days_text,
        days_font=days_font,
        visible_bottom_margin=
            early_top_margin,
    )


    # --------------------------------------------------------
    # TITEL
    # --------------------------------------------------------

    image = draw_early_title(
        image,
        title_text,
        title_font,
        CARD_WIDTH / 2,
        upper_layout["title_y"],
        title_spacing,
    )


    # --------------------------------------------------------
    # TRENNER
    # --------------------------------------------------------

    image = draw_early_divider(
        image,
        upper_layout["divider_y"],
    )


    # --------------------------------------------------------
    # DATUM
    # --------------------------------------------------------

    image = draw_soft_centered_text(
        image,
        date_text,
        upper_layout["date_y"],
        date_font,
        EARLY_DATE_TEXT,
        (
            0,
            0,
            0,
            175,
        ),
        shadow_blur=2.5,
        shadow_offset=1,

        stroke_width=
            EARLY_LOWER_READABILITY_STROKE_WIDTH,

        stroke_fill=
            EARLY_LOWER_READABILITY_OUTLINE,
    )


    # --------------------------------------------------------
    # NOCH
    # --------------------------------------------------------

    if noch_text:

        image = draw_centered_spaced_text(
            image,
            noch_text,
            countdown_layout["noch_y"],
            noch_font,
            EARLY_NOCH_TEXT,
            5,

            shadow_fill=
                EARLY_NOCH_SHADOW,

            shadow_blur=1.4,
            shadow_offset=1,

            stroke_width=
                EARLY_LOWER_READABILITY_STROKE_WIDTH,

            stroke_fill=
                EARLY_LOWER_READABILITY_OUTLINE,
        )


    # --------------------------------------------------------
    # COUNTDOWN
    # --------------------------------------------------------

    image = draw_soft_centered_text(
        image,
        days_text,
        countdown_layout["days_y"],
        days_font,
        EARLY_COUNTDOWN_TEXT,
        (
            0,
            0,
            0,
            185,
        ),
        shadow_blur=3.0,
        shadow_offset=1,

        stroke_width=
            EARLY_LOWER_READABILITY_STROKE_WIDTH,

        stroke_fill=
            EARLY_LOWER_READABILITY_OUTLINE,
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

    upper_layout = calculate_global_upper_layout(
        image=image,
        title_font=title_font,
        date_text=date_text,
        date_font=date_font,
    )


    # --------------------------------------------------------
    # GLOBAL – SYMMETRISCHER AUSSENABSTAND
    #
    # GLOBAL bleibt oben exakt bei 60 px.
    #
    # Also endet 36 TAGE exakt 60 px vor der Unterkante.
    # --------------------------------------------------------

    global_top_margin = (
        upper_layout[
            "global_visible_top"
        ]
    )


    countdown_layout = calculate_countdown_layout(
        image=image,
        noch_text=noch_text,
        noch_font=noch_font,
        days_text=days_text,
        days_font=days_font,
        visible_bottom_margin=
            global_top_margin,
    )


    # --------------------------------------------------------
    # GLOBAL
    # --------------------------------------------------------

    image = draw_global_title_line(
        image,
        "GLOBAL",
        title_font,
        CARD_WIDTH / 2,
        upper_layout["global_y"],
        global_spacing,
    )


    # --------------------------------------------------------
    # LAUNCH
    # --------------------------------------------------------

    image = draw_global_title_line(
        image,
        "LAUNCH",
        title_font,
        CARD_WIDTH / 2,
        upper_layout["launch_y"],
        launch_spacing,
    )


    # --------------------------------------------------------
    # TRENNER
    # --------------------------------------------------------

    image = draw_global_divider(
        image,
        upper_layout["divider_y"],
    )


    # --------------------------------------------------------
    # DATUM
    # --------------------------------------------------------

    image = draw_soft_centered_text(
        image,
        date_text,
        upper_layout["date_y"],
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
            countdown_layout["noch_y"],
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
        countdown_layout["days_y"],
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


def save_compact_preview_card(
    milestone
):

    image = create_compact_card(
        milestone
    )

    if milestone["key"] == "early_access":

        filename = (
            EARLY_COMPACT_PREVIEW_OUTPUT
        )

    elif milestone["key"] == "global_launch":

        filename = (
            GLOBAL_COMPACT_PREVIEW_OUTPUT
        )

    else:

        filename = (
            f"{milestone['key']}_compact_preview.png"
        )

    image.save(
        filename,
        "PNG",
        optimize=True,
    )

    print(
        f"{milestone['title']} Compact-Test: "
        f"{filename} "
        f"({image.width}x{image.height})"
    )

    return filename


# ============================================================
# DISCORD
#
# Early Access und Global Launch bleiben jeweils dauerhaft
# dieselbe Discord-Nachricht.
#
# Beim ersten Lauf wird eine Nachricht erstellt und ihre
# Message-ID in content_message.json gespeichert.
# Bei allen weiteren Läufen wird genau diese Nachricht per
# PATCH aktualisiert.
#
# Falls eine gespeicherte Discord-Nachricht manuell gelöscht
# wurde, liefert Discord 404. Dann wird nur diese eine Nachricht
# neu erstellt und die neue Message-ID gespeichert.
# ============================================================

def load_message_state():

    state = load_json(
        MESSAGE_STATE_FILE,
        {},
    )

    if not isinstance(state, dict):

        return {}

    return state


def save_message_state(state):

    with open(
        MESSAGE_STATE_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            state,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")


def webhook_wait_url():

    if not WEBHOOK_URL:

        raise RuntimeError(
            "GitHub Secret CONTENT_WEBHOOK fehlt."
        )

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


def discord_message_url(message_id):

    if not WEBHOOK_URL:

        raise RuntimeError(
            "GitHub Secret CONTENT_WEBHOOK fehlt."
        )

    base_url = WEBHOOK_URL.split(
        "?",
        1,
    )[0]

    return (
        f"{base_url}/messages/{message_id}"
    )


def build_discord_image_payload(
    discord_filename,
):

    return {
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


def post_discord_image(
    image_file,
    discord_filename,
):

    payload = build_discord_image_payload(
        discord_filename
    )

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

    return str(message_id)


def patch_discord_image(
    message_id,
    image_file,
    discord_filename,
):

    payload = build_discord_image_payload(
        discord_filename
    )

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

        response = requests.patch(
            discord_message_url(
                message_id
            ),
            data={
                "payload_json":
                    json.dumps(payload)
            },
            files=files,
            timeout=30,
        )

    if response.status_code == 404:

        return False

    if response.status_code not in (
        200,
        204,
    ):

        raise RuntimeError(
            "Discord Content konnte "
            "nicht aktualisiert werden.\n"
            f"HTTP {response.status_code}\n"
            f"{response.text}"
        )

    return True


def update_or_create_discord_image(
    state,
    state_key,
    image_file,
    discord_filename,
    label,
):

    message_id = state.get(
        state_key
    )

    if message_id:

        print(
            f"{label} wird aktualisiert ..."
        )

        updated = patch_discord_image(
            message_id,
            image_file,
            discord_filename,
        )

        if updated:

            print(
                f"{label} aktualisiert. "
                f"Message-ID: {message_id}"
            )

            return False

        print(
            f"{label}: gespeicherte "
            "Discord-Nachricht wurde nicht "
            "gefunden. Sie wird neu erstellt."
        )

    else:

        print(
            f"{label}: noch keine "
            "Message-ID gespeichert. "
            "Nachricht wird erstellt ..."
        )

    new_message_id = post_discord_image(
        image_file,
        discord_filename,
    )

    state[state_key] = new_message_id

    print(
        f"{label} erstellt. "
        f"Message-ID: {new_message_id}"
    )

    return True


def send_compact_previews_to_discord(
    early_access_file,
    global_launch_file,
):

    if not WEBHOOK_URL:

        raise RuntimeError(
            "GitHub Secret CONTENT_WEBHOOK fehlt."
        )

    print(
        ""
    )
    print(
        "Compact-Test: separate Zweizeiler werden "
        "unter den echten Content-Nachrichten gepostet ..."
    )

    early_preview_id = post_discord_image(
        early_access_file,
        "early_access_compact_preview.png",
    )

    print(
        "Early Access Compact-Test erstellt. "
        f"Message-ID: {early_preview_id}"
    )

    global_preview_id = post_discord_image(
        global_launch_file,
        "global_launch_compact_preview.png",
    )

    print(
        "Global Launch Compact-Test erstellt. "
        f"Message-ID: {global_preview_id}"
    )

    print(
        "Compact-Test fertig. Die beiden Testnachrichten "
        "können in Discord einfach gelöscht werden."
    )


def send_content_to_discord(
    early_access_file,
    global_launch_file,
):

    if not WEBHOOK_URL:

        raise RuntimeError(
            "GitHub Secret CONTENT_WEBHOOK fehlt."
        )

    state = load_message_state()

    print("")

    early_changed = update_or_create_discord_image(
        state=state,
        state_key="early_access_message_id",
        image_file=early_access_file,
        discord_filename="early_access.png",
        label="Early Access",
    )

    if early_changed:

        save_message_state(
            state
        )

    print("")

    global_changed = update_or_create_discord_image(
        state=state,
        state_key="global_launch_message_id",
        image_file=global_launch_file,
        discord_filename="global_launch.png",
        label="Global Launch",
    )

    if global_changed:

        save_message_state(
            state
        )

    # Falls die Datei bisher noch nicht existierte und beide IDs
    # bereits aus einem vorhandenen State kamen, bleibt sie
    # unangetastet. In jedem anderen Fall wurde sie oben direkt
    # nach dem Erstellen einer neuen Nachricht gespeichert.

    print("")
    print(
        "========================================"
    )
    print(
        "CONTENT-NACHRICHTEN AKTUALISIERT"
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
            "content_data.json ist leer oder fehlt."
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
    milestone_by_key = {}

    for milestone in (
        content_state["milestones"]
    ):

        if milestone["key"] not in wanted_keys:

            continue

        milestone_by_key[
            milestone["key"]
        ] = milestone

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

    if TEST_COMPACT_PREVIEW:

        early_compact_preview = save_compact_preview_card(
            milestone_by_key[
                "early_access"
            ]
        )

        global_compact_preview = save_compact_preview_card(
            milestone_by_key[
                "global_launch"
            ]
        )

        send_compact_previews_to_discord(
            early_compact_preview,
            global_compact_preview,
        )


if __name__ == "__main__":
    main()
