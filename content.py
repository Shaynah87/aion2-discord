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
# GEMEINSAME TYPOGRAFIE
# ============================================================

DATE_SIZE = 30
NOCH_SIZE = 17
COUNTDOWN_SIZE = 50

GAP_DATE_NOCH = 36
GAP_NOCH_DAYS = 7


# ============================================================
# EARLY ACCESS
#
# Bleibt unverändert.
# ============================================================

EARLY_TITLE_SIZE = 68
EARLY_TITLE_SPACING = 3
EARLY_GAP_TITLE_DATE = 18


# ============================================================
# GLOBAL LAUNCH
# ============================================================

GLOBAL_TITLE_SIZE = 96
GLOBAL_TITLE_BOLD = True
GLOBAL_TITLE_TARGET_WIDTH = 470


# ------------------------------------------------------------
# FESTE VERTIKALE POSITIONEN
# ------------------------------------------------------------

GLOBAL_GLOBAL_TOP = 52
GLOBAL_LAUNCH_TOP = 137

# Etwas mehr Luft nach dem Titel
GLOBAL_DIVIDER_Y = 243

# Datum ebenfalls etwas tiefer.
# Das Datum selbst gestalten wir anschließend noch neu.
GLOBAL_DATE_TOP = 272

# Countdown bleibt exakt auf dem bisherigen Stand
GLOBAL_NOCH_TOP = 382
GLOBAL_DAYS_TOP = 408


# ------------------------------------------------------------
# GLOBAL – DATUM / COUNTDOWN
# ------------------------------------------------------------

GLOBAL_DATE_SIZE = 32
GLOBAL_NOCH_SIZE = 16
GLOBAL_COUNTDOWN_SIZE = 46


# ============================================================
# GLOBAL – ORNAMENT-TRENNER
# ============================================================

GLOBAL_DIVIDER_WIDTH = 290
GLOBAL_DIVIDER_CENTER_GAP = 25

GLOBAL_DIVIDER_THICKNESS = 1

GLOBAL_DIVIDER_INNER_LENGTH = 42
GLOBAL_DIVIDER_INNER_OFFSET = 5

GLOBAL_DIVIDER_DIAMOND_OUTER = 7
GLOBAL_DIVIDER_DIAMOND_INNER = 3


# ============================================================
# GLOBAL – TITELTIEFE
#
# Neuer Aufbau:
#
# 1. ruhiger tiefer Schatten
# 2. dunkler unterer Buchstabenbereich
# 3. hellerer oberer Buchstabenbereich
# 4. feines Licht-Highlight
#
# Dadurch entsteht Tiefe IM Buchstaben,
# nicht nur außen herum.
# ============================================================

GLOBAL_TITLE_SHADOW_OFFSET_X = 2
GLOBAL_TITLE_SHADOW_OFFSET_Y = 4
GLOBAL_TITLE_SHADOW_BLUR = 3.2

GLOBAL_TITLE_SHADOW = (
    10,
    24,
    46,
    135,
)

# obere Schriftfarbe
GLOBAL_TITLE_TOP_COLOR = (
    50,
    74,
    105,
    255,
)

# mittlere Schriftfarbe
GLOBAL_TITLE_MID_COLOR = (
    31,
    51,
    79,
    255,
)

# untere Schriftfarbe
GLOBAL_TITLE_BOTTOM_COLOR = (
    18,
    34,
    57,
    255,
)

# sehr feines Kantenlicht
GLOBAL_TITLE_HIGHLIGHT = (
    244,
    249,
    255,
    135,
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
    32,
    50,
    76,
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
    48,
    70,
    101,
    190,
)

GLOBAL_LINE_SOFT = (
    74,
    95,
    124,
    100,
)

GLOBAL_ORNAMENT_LIGHT = (
    224,
    235,
    247,
    210,
)

GLOBAL_ORNAMENT_DARK = (
    39,
    61,
    92,
    225,
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
# GLOBAL – TITELMASKE
# ============================================================

def create_global_title_mask(
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
# GLOBAL – TITEL MIT INNERER TIEFE
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

    mask = create_global_title_mask(
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


    # --------------------------------------------------------
    # 1. RUHIGER DUNKLER SCHATTEN
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
            GLOBAL_TITLE_SHADOW_OFFSET_X,
            GLOBAL_TITLE_SHADOW_OFFSET_Y,
        ),
    )

    shadow_mask = shadow_mask.filter(
        ImageFilter.GaussianBlur(
            GLOBAL_TITLE_SHADOW_BLUR
        )
    )

    shadow_layer = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        GLOBAL_TITLE_SHADOW,
    )

    shadow_layer.putalpha(
        shadow_mask.point(
            lambda value:
                int(
                    value
                    * (
                        GLOBAL_TITLE_SHADOW[3]
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
    # 2. INNERER BLAUER VERLAUF
    #
    # Oben heller, unten tiefer/dunkler.
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

    gradient_pixels = gradient.load()

    top = bbox[1]
    bottom = bbox[3]

    visible_height = max(
        1,
        bottom - top,
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

            start = (
                GLOBAL_TITLE_TOP_COLOR
            )

            end = (
                GLOBAL_TITLE_MID_COLOR
            )

        else:

            local = (
                (
                    progress
                    - 0.48
                )
                / 0.52
            )

            start = (
                GLOBAL_TITLE_MID_COLOR
            )

            end = (
                GLOBAL_TITLE_BOTTOM_COLOR
            )

        color = tuple(
            int(
                start[channel]
                + (
                    end[channel]
                    - start[channel]
                )
                * local
            )
            for channel in range(4)
        )

        for xx in range(
            bbox[0],
            bbox[2],
        ):

            gradient_pixels[
                xx,
                yy
            ] = color

    gradient.putalpha(
        mask
    )

    image = Image.alpha_composite(
        image,
        gradient,
    )


    # --------------------------------------------------------
    # 3. FEINES OBERES KANTENLICHT
    #
    # Nur 1 Pixel oberhalb der Buchstaben.
    # Kein vollständiger weißer Rand.
    # --------------------------------------------------------

    highlight_mask = Image.new(
        "L",
        (
            width,
            height,
        ),
        0,
    )

    highlight_mask.paste(
        mask,
        (
            0,
            -1,
        ),
    )

    # Bereiche entfernen, die von der Hauptmaske bedeckt werden.
    highlight_pixels = highlight_mask.load()
    main_pixels = mask.load()

    for yy in range(
        max(
            0,
            bbox[1] - 2,
        ),
        min(
            height,
            bbox[3] + 1,
        ),
    ):

        for xx in range(
            max(
                0,
                bbox[0] - 2,
            ),
            min(
                width,
                bbox[2] + 2,
            ),
        ):

            if main_pixels[
                xx,
                yy
            ] > 0:

                highlight_pixels[
                    xx,
                    yy
                ] = 0

    highlight_layer = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        GLOBAL_TITLE_HIGHLIGHT,
    )

    highlight_layer.putalpha(
        highlight_mask.point(
            lambda value:
                int(
                    value
                    * (
                        GLOBAL_TITLE_HIGHLIGHT[3]
                        / 255
                    )
                )
        )
    )

    image = Image.alpha_composite(
        image,
        highlight_layer,
    )


    # --------------------------------------------------------
    # 4. SEHR DEZENTER LICHTREFLEX IM OBEREN DRITTEL
    #
    # Kein harter Balken.
    # Nur ein schmaler transparenter Reflex.
    # --------------------------------------------------------

    shine_layer = Image.new(
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

    shine_draw = ImageDraw.Draw(
        shine_layer
    )

    shine_y = int(
        top
        + visible_height
        * 0.30
    )

    shine_draw.line(
        (
            bbox[0],
            shine_y,
            bbox[2],
            shine_y,
        ),
        fill=(
            230,
            240,
            251,
            48,
        ),
        width=1,
    )

    shine_layer.putalpha(
        Image.composite(
            shine_layer.getchannel(
                "A"
            ),
            Image.new(
                "L",
                (
                    width,
                    height,
                ),
                0,
            ),
            mask,
        )
    )

    image = Image.alpha_composite(
        image,
        shine_layer,
    )

    return image


# ============================================================
# GLOBAL – FANTASY-ORNAMENT-TRENNER
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

    center_x = width / 2

    half_width = (
        GLOBAL_DIVIDER_WIDTH / 2
    )

    gap = (
        GLOBAL_DIVIDER_CENTER_GAP
    )


    # --------------------------------------------------------
    # HAUPTLINIEN
    # --------------------------------------------------------

    left_start = (
        center_x
        - half_width
    )

    left_end = (
        center_x
        - gap
    )

    right_start = (
        center_x
        + gap
    )

    right_end = (
        center_x
        + half_width
    )

    draw.line(
        (
            left_start,
            center_y,
            left_end,
            center_y,
        ),
        fill=GLOBAL_LINE,
        width=GLOBAL_DIVIDER_THICKNESS,
    )

    draw.line(
        (
            right_start,
            center_y,
            right_end,
            center_y,
        ),
        fill=GLOBAL_LINE,
        width=GLOBAL_DIVIDER_THICKNESS,
    )


    # --------------------------------------------------------
    # ZWEITE FEINE INNERE LINIEN
    # --------------------------------------------------------

    inner = (
        GLOBAL_DIVIDER_INNER_LENGTH
    )

    offset = (
        GLOBAL_DIVIDER_INNER_OFFSET
    )

    draw.line(
        (
            center_x
            - gap
            - inner,

            center_y
            + offset,

            center_x
            - gap,

            center_y
            + offset,
        ),
        fill=GLOBAL_LINE_SOFT,
        width=1,
    )

    draw.line(
        (
            center_x
            + gap,

            center_y
            + offset,

            center_x
            + gap
            + inner,

            center_y
            + offset,
        ),
        fill=GLOBAL_LINE_SOFT,
        width=1,
    )


    # --------------------------------------------------------
    # KLEINE ENDKAPPEN
    # --------------------------------------------------------

    cap_height = 3

    draw.line(
        (
            center_x - gap,
            center_y - cap_height,
            center_x - gap,
            center_y + cap_height,
        ),
        fill=GLOBAL_LINE,
        width=1,
    )

    draw.line(
        (
            center_x + gap,
            center_y - cap_height,
            center_x + gap,
            center_y + cap_height,
        ),
        fill=GLOBAL_LINE,
        width=1,
    )


    # --------------------------------------------------------
    # ÄUSSERE RAUTE
    # --------------------------------------------------------

    outer = (
        GLOBAL_DIVIDER_DIAMOND_OUTER
    )

    draw.polygon(
        [
            (
                center_x,
                center_y - outer,
            ),
            (
                center_x + outer,
                center_y,
            ),
            (
                center_x,
                center_y + outer,
            ),
            (
                center_x - outer,
                center_y,
            ),
        ],
        fill=GLOBAL_ORNAMENT_DARK,
    )


    # --------------------------------------------------------
    # INNERE RAUTE
    # --------------------------------------------------------

    inner_diamond = (
        GLOBAL_DIVIDER_DIAMOND_INNER
    )

    draw.polygon(
        [
            (
                center_x,
                center_y - inner_diamond,
            ),
            (
                center_x + inner_diamond,
                center_y,
            ),
            (
                center_x,
                center_y + inner_diamond,
            ),
            (
                center_x - inner_diamond,
                center_y,
            ),
        ],
        fill=GLOBAL_ORNAMENT_LIGHT,
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
    # ORNAMENT-TRENNER
    # ========================================================

    image = draw_global_divider(
        image,
        GLOBAL_DIVIDER_Y,
    )


    # ========================================================
    # DATUM
    #
    # Noch bewusst schlicht.
    # Das gestalten wir im nächsten Schritt separat.
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
            GLOBAL_DARK,
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
