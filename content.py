import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops


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

# Eingeklappter Zweizeiler
COMPACT_HEIGHT = 270


# ============================================================
# GEMEINSAME GEOMETRIE
#
# Early Access + Global Launch laufen bei den Größen gemeinsam.
# ============================================================

TITLE_SIZE = 72
DATE_SIZE = 31
NOCH_SIZE = 18
COUNTDOWN_SIZE = 52

TITLE_SPACING = 3
NOCH_SPACING = 4

GAP_TITLE_DATE = 18
GAP_DATE_NOCH = 39
GAP_NOCH_DAYS = 7


# ============================================================
# TITELPOSITION
#
# Global sitzt deutlich höher.
# Early bleibt für den Moment auf seiner bisherigen Position.
# ============================================================

EARLY_TITLE_Y_OFFSET = 0
GLOBAL_TITLE_Y_OFFSET = -80


# ============================================================
# ZWEIZEILER
#
# Wird später separat gestaltet.
# ============================================================

COMPACT_TITLE_SIZE = 44
COMPACT_STATUS_SIZE = 34

COMPACT_TITLE_SPACING = 6
COMPACT_GAP = 22


# ============================================================
# KOMPAKTER HINTERGRUND
# ============================================================

COMPACT_CROP_CENTER = {
    "early_access": 0.50,
    "global_launch": 0.50,
}


# ============================================================
# FARBEN
# ============================================================

WHITE = (
    248,
    248,
    250,
    255,
)

SOFT_WHITE = (
    222,
    223,
    228,
    255,
)

GRAY = (
    185,
    188,
    195,
    255,
)


# ------------------------------------------------------------
# EARLY ACCESS
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# GLOBAL LAUNCH
# ------------------------------------------------------------

GLOBAL_TEXT = (
    57,
    66,
    82,
    255,
)

GLOBAL_MUTED = (
    94,
    101,
    116,
    255,
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
):

    if bold:

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
# ZWEIZEILER-HINTERGRUND
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
# ZENTRIERTER TEXT
# ============================================================

def draw_centered_text(
    draw,
    text,
    y,
    font,
    fill,
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

    x = (
        (
            width
            - text_width
        )
        / 2
        - bbox[0]
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
# TEXTMASKE MIT BUCHSTABENABSTAND
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


# ============================================================
# EARLY ACCESS – GOLD
# ============================================================

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

    # --------------------------------------------------------
    # WEICHER SCHATTEN
    # --------------------------------------------------------

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
            4.0
        )
    )

    shadow_alpha = shadow_mask.point(
        lambda value:
            int(
                value
                * 0.58
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
        shadow_alpha
    )

    image = Image.alpha_composite(
        image,
        shadow,
    )

    # --------------------------------------------------------
    # GOLDVERLAUF
    # --------------------------------------------------------

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
# GLOBAL LAUNCH – PLATIN V3
#
# - kräftiger
# - kontrastreicher
# - 2 px Außenkontur
# - kein Glow
# - kein großer 3D-Versatz
# - kleiner direkter Schatten
# ============================================================

def draw_platinum_title(
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

    # --------------------------------------------------------
    # DIREKTER SCHATTEN
    # --------------------------------------------------------

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
            1.8
        )
    )

    shadow_alpha = shadow_mask.point(
        lambda value:
            int(
                value
                * 0.58
            )
    )

    shadow = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        (
            24,
            30,
            42,
            0,
        ),
    )

    shadow.putalpha(
        shadow_alpha
    )

    image = Image.alpha_composite(
        image,
        shadow,
    )

    # --------------------------------------------------------
    # 2-PX-AUSSENKONTUR
    # --------------------------------------------------------

    expanded = mask.filter(
        ImageFilter.MaxFilter(
            5
        )
    )

    outline_mask = ImageChops.subtract(
        expanded,
        mask,
    )

    outline_alpha = outline_mask.point(
        lambda value:
            int(
                value
                * 0.92
            )
    )

    outline = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        (
            48,
            58,
            76,
            0,
        ),
    )

    outline.putalpha(
        outline_alpha
    )

    image = Image.alpha_composite(
        image,
        outline,
    )

    # --------------------------------------------------------
    # KONTRASTREICHER PLATINVERLAUF
    # --------------------------------------------------------

    top = bbox[1]
    bottom = bbox[3]

    visible_height = max(
        1,
        bottom - top,
    )

    platinum = Image.new(
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

    pixels = platinum.load()

    # Sehr helle Oberkante
    color_1 = (
        252,
        253,
        255,
    )

    # Helles Silber
    color_2 = (
        220,
        226,
        234,
    )

    # Stahlgrau
    color_3 = (
        139,
        151,
        168,
    )

    # Dunklere Unterkante
    color_4 = (
        82,
        96,
        116,
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

        if progress < 0.25:

            local = (
                progress
                / 0.25
            )

            start = color_1
            end = color_2

        elif progress < 0.65:

            local = (
                (
                    progress
                    - 0.25
                )
                / 0.40
            )

            start = color_2
            end = color_3

        else:

            local = (
                (
                    progress
                    - 0.65
                )
                / 0.35
            )

            start = color_3
            end = color_4

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

    platinum.putalpha(
        mask
    )

    image = Image.alpha_composite(
        image,
        platinum,
    )

    # --------------------------------------------------------
    # SEHR DEZENTE LICHTKANTE
    # --------------------------------------------------------

    highlight_mask = mask.filter(
        ImageFilter.GaussianBlur(
            0.5
        )
    )

    highlight_alpha = highlight_mask.point(
        lambda value:
            int(
                value
                * 0.10
            )
    )

    highlight = Image.new(
        "RGBA",
        (
            width,
            height,
        ),
        (
            255,
            255,
            255,
            0,
        ),
    )

    highlight.putalpha(
        highlight_alpha
    )

    image = Image.alpha_composite(
        image,
        highlight,
    )

    return image


# ============================================================
# WEICHER ZENTRIERTER TEXT
#
# Datum / NOCH / Countdown bleiben vorerst bestehen.
# ============================================================

def draw_soft_centered_text(
    image,
    text,
    y,
    font,
    fill,
    shadow_fill,
    shadow_blur=3.5,
):

    width, height = image.size

    probe = ImageDraw.Draw(
        image
    )

    bbox = probe.textbbox(
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

    x = (
        (
            width
            - text_width
        )
        / 2
        - bbox[0]
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
            y + 1,
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
# NOCH MIT BUCHSTABENABSTAND
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
# VIERZEILER
#
# Early Access + Global Launch:
# - identische Titelgröße
# - identische restliche Schriftgrößen
#
# Global darf wegen des Motivs vertikal anders positioniert sein.
# ============================================================

def create_full_card(milestone):

    image = load_background(
        milestone["background"]
    )

    # Beide Titel wieder BOLD.
    # Beide exakt 72 px.
    title_font = load_font(
        TITLE_SIZE,
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

    # --------------------------------------------------------
    # SICHTBARE TEXTHÖHEN
    # --------------------------------------------------------

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
            + GAP_TITLE_DATE
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
            + GAP_TITLE_DATE
            + date_height
            + GAP_DATE_NOCH
            + days_height
        )

    # --------------------------------------------------------
    # GRUPPE VERTIKAL ZENTRIEREN
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # TITELPOSITION
    # --------------------------------------------------------

    if milestone["key"] == "global_launch":

        rendered_title_y = (
            title_y
            + GLOBAL_TITLE_Y_OFFSET
        )

    else:

        rendered_title_y = (
            title_y
            + EARLY_TITLE_Y_OFFSET
        )

    # --------------------------------------------------------
    # RESTLICHE POSITIONEN
    #
    # Diese verändern wir in diesem Test noch nicht.
    # --------------------------------------------------------

    date_visible_top = (
        visible_top
        + title_height
        + GAP_TITLE_DATE
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

    # --------------------------------------------------------
    # TITEL
    # --------------------------------------------------------

    if milestone["key"] == "early_access":

        image = draw_gold_title(
            image,
            title_text,
            title_font,
            CARD_WIDTH / 2,
            rendered_title_y,
            TITLE_SPACING,
        )

    elif milestone["key"] == "global_launch":

        image = draw_platinum_title(
            image,
            title_text,
            title_font,
            CARD_WIDTH / 2,
            rendered_title_y,
            TITLE_SPACING,
        )

    # --------------------------------------------------------
    # RESTLICHE BESCHRIFTUNG
    #
    # Noch unverändert.
    # --------------------------------------------------------

    if milestone["key"] == "global_launch":

        normal_fill = GLOBAL_TEXT
        muted_fill = GLOBAL_MUTED

        normal_shadow = (
            255,
            255,
            255,
            105,
        )

    else:

        normal_fill = EARLY_TEXT
        muted_fill = EARLY_MUTED

        normal_shadow = (
            0,
            0,
            0,
            125,
        )

    image = draw_soft_centered_text(
        image,
        date_text,
        date_y,
        date_font,
        normal_fill,
        normal_shadow,
        shadow_blur=3.5,
    )

    if noch_text:

        image = draw_centered_spaced_text(
            image,
            noch_text,
            noch_y,
            noch_font,
            muted_fill,
            NOCH_SPACING,
        )

    image = draw_soft_centered_text(
        image,
        days_text,
        days_y,
        days_font,
        normal_fill,
        normal_shadow,
        shadow_blur=4.0,
    )

    return image.convert(
        "RGB"
    )


# ============================================================
# ZWEIZEILER
#
# Vorerst unangetastet.
# Den endgültigen Ausschnitt machen wir später.
# ============================================================

def create_compact_card(milestone):

    master = load_background(
        milestone["background"]
    )

    image = crop_compact_background(
        master,
        milestone["key"],
    )

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

    if milestone["key"] == "early_access":

        image = draw_gold_title(
            image,
            title_text,
            title_font,
            CARD_WIDTH / 2,
            title_y,
            COMPACT_TITLE_SPACING,
        )

        status_fill = EARLY_TEXT

    else:

        image = draw_platinum_title(
            image,
            title_text,
            title_font,
            CARD_WIDTH / 2,
            title_y,
            COMPACT_TITLE_SPACING,
        )

        status_fill = GLOBAL_TEXT

    draw = ImageDraw.Draw(
        image
    )

    draw_centered_text(
        draw,
        status_text,
        status_y,
        status_font,
        status_fill,
    )

    return image.convert(
        "RGB"
    )


# ============================================================
# MILESTONE RENDERN
# ============================================================

def render_milestone(milestone):

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

def save_milestone_card(milestone):

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
# Jede Karte wird als EIGENE Discord-Nachricht gesendet.
# Dadurch stehen Early Access und Global Launch untereinander.
#
# Alte Testnachrichten werden derzeit manuell gelöscht.
#
# Sobald das Design fertig ist, stellen wir wieder auf feste
# Message-IDs für den Cron-Betrieb um.
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

def print_status(content_state):

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
