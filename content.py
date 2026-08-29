import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter


# ============================================================
# DATEIEN / EINSTELLUNGEN
# ============================================================

DATA_FILE = "content_data.json"

WEBHOOK_URL = os.environ.get("CONTENT_WEBHOOK")

# Bestehende Early-Access-Nachricht
CONTENT_MESSAGE_ID = os.environ.get("CONTENT_MESSAGE_ID")

# Neue separate Global-Launch-Nachricht
CONTENT_GLOBAL_MESSAGE_ID = os.environ.get(
    "CONTENT_GLOBAL_MESSAGE_ID"
)

EARLY_ACCESS_OUTPUT = "early_access_card.png"
GLOBAL_LAUNCH_OUTPUT = "global_launch_card.png"


# ============================================================
# KARTENFORMAT
# ============================================================

CARD_WIDTH = 1200

# Vierzeiler
FULL_HEIGHT = 535

# Eingeklappter Zweizeiler
COMPACT_HEIGHT = 270


# ============================================================
# GEMEINSAME TYPOGRAFIE
#
# Global Launch bleibt für den ersten Test zunächst
# im bisherigen Layout.
#
# Early Access bekommt bewusst einen eigenen,
# ruhigeren Test-Look.
# ============================================================

# ------------------------------------------------------------
# GLOBAL LAUNCH – bisherige Geometrie
# ------------------------------------------------------------

TITLE_SIZE = 82
DATE_SIZE = 38
NOCH_SIZE = 19
COUNTDOWN_SIZE = 54

TITLE_SPACING = 10

GAP_TITLE_DATE = 21
GAP_DATE_NOCH = 42
GAP_NOCH_DAYS = 8


# ------------------------------------------------------------
# EARLY ACCESS – neuer Test-Look
# ------------------------------------------------------------

EARLY_TITLE_SIZE = 76
EARLY_DATE_SIZE = 30
EARLY_NOCH_SIZE = 17
EARLY_COUNTDOWN_SIZE = 50

EARLY_TITLE_SPACING = 9
EARLY_NOCH_SPACING = 5

EARLY_GAP_TITLE_DATE = 16
EARLY_GAP_DATE_DIVIDER = 20
EARLY_GAP_DIVIDER_NOCH = 18
EARLY_GAP_NOCH_DAYS = 7

EARLY_DIVIDER_WIDTH = 230
EARLY_DIVIDER_GAP = 12


# ============================================================
# ZWEIZEILER
# ============================================================

COMPACT_TITLE_SIZE = 44
COMPACT_STATUS_SIZE = 34

COMPACT_TITLE_SPACING = 6
COMPACT_GAP = 22


# ============================================================
# KOMPAKTER HINTERGRUND
#
# 0.50 = vertikal exakt aus der Mitte des Masters croppen.
#
# Diese beiden Werte können wir später getrennt feinjustieren,
# damit Kugel bzw. Figuren beim Einklappen perfekt sitzen.
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

EARLY_IVORY = (
    238,
    235,
    224,
    255,
)

EARLY_MUTED = (
    184,
    184,
    181,
    255,
)

EARLY_GOLD = (
    225,
    183,
    92,
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

    # Unsere beiden Master sollen 1200x535 sein.
    #
    # Falls einer davon noch abweicht,
    # wird er zunächst auf das Arbeitsformat gebracht.
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
#
# WICHTIG:
# Der 535px-Master wird NICHT auf 270px gestaucht.
#
# Python schneidet einen 270px hohen Ausschnitt heraus.
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
# EARLY ACCESS – GOLD
#
# Ruhiger Metall-Look ohne harte 3D-Tiefenkante.
# Der Titel soll Teil des Motivs wirken und nicht darauf kleben.
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

    # --------------------------------------------------------
    # Weicher Schatten direkt hinter der Schrift
    # --------------------------------------------------------

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
            4,
            7,
            13,
            150,
        ),
        spacing,
    )

    shadow = shadow.filter(
        ImageFilter.GaussianBlur(
            5.0
        )
    )

    image = Image.alpha_composite(
        image,
        shadow,
    )

    # --------------------------------------------------------
    # Sehr dezenter warmer Schein
    # --------------------------------------------------------

    glow = Image.new(
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

    glow_draw = ImageDraw.Draw(
        glow
    )

    draw_spaced_text(
        glow_draw,
        x,
        y,
        text,
        font,
        (
            236,
            190,
            92,
            75,
        ),
        spacing,
    )

    glow = glow.filter(
        ImageFilter.GaussianBlur(
            8.0
        )
    )

    image = Image.alpha_composite(
        image,
        glow,
    )

    # --------------------------------------------------------
    # Schriftmaske
    # --------------------------------------------------------

    mask = Image.new(
        "L",
        (
            width,
            height,
        ),
        0,
    )

    mask_draw = ImageDraw.Draw(
        mask
    )

    draw_spaced_text(
        mask_draw,
        x,
        y,
        text,
        font,
        255,
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

    gold_pixels = gold.load()

    # Goldverlauf:
    # oben weich hell,
    # Mitte warm,
    # unten etwas tiefer.
    #
    # Kein harter Chrome-/WordArt-Effekt.
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

        if progress < 0.45:

            local = (
                progress
                / 0.45
            )

            color = (
                int(
                    246
                    - 18 * local
                ),
                int(
                    219
                    - 33 * local
                ),
                int(
                    148
                    - 42 * local
                ),
                255,
            )

        else:

            local = (
                (
                    progress
                    - 0.45
                )
                / 0.55
            )

            color = (
                int(
                    228
                    - 38 * local
                ),
                int(
                    186
                    - 44 * local
                ),
                int(
                    106
                    - 39 * local
                ),
                255,
            )

        for xx in range(
            bbox[0],
            bbox[2],
        ):

            gold_pixels[
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
# EARLY ACCESS – WEICHE NEBENTYPOGRAFIE
# ============================================================

def draw_soft_centered_text(
    image,
    text,
    y,
    font,
    fill,
    shadow_alpha=120,
    shadow_blur=4.0,
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
        fill=(
            0,
            0,
            0,
            shadow_alpha,
        ),
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


def draw_early_noch(
    image,
    text,
    font,
    y,
):

    width, height = image.size

    probe = ImageDraw.Draw(
        image
    )

    text_width = spaced_text_width(
        probe,
        text,
        font,
        EARLY_NOCH_SPACING,
    )

    x = (
        width / 2
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
        y + 1,
        text,
        font,
        (
            0,
            0,
            0,
            115,
        ),
        EARLY_NOCH_SPACING,
    )

    shadow = shadow.filter(
        ImageFilter.GaussianBlur(
            3.0
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
        EARLY_MUTED,
        EARLY_NOCH_SPACING,
    )

    return image


# ============================================================
# EARLY ACCESS – DEZENTES ORNAMENT
# ============================================================

def draw_early_divider(
    image,
    center_y,
):

    width, height = image.size
    center_x = width / 2

    line_layer = Image.new(
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
        line_layer
    )

    half = (
        EARLY_DIVIDER_WIDTH
        / 2
    )

    gap = EARLY_DIVIDER_GAP

    line_color = (
        214,
        178,
        101,
        135,
    )

    draw.line(
        (
            center_x - half,
            center_y,
            center_x - gap,
            center_y,
        ),
        fill=line_color,
        width=1,
    )

    draw.line(
        (
            center_x + gap,
            center_y,
            center_x + half,
            center_y,
        ),
        fill=line_color,
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
            231,
            194,
            112,
            185,
        ),
    )

    glow = line_layer.filter(
        ImageFilter.GaussianBlur(
            3.0
        )
    )

    image = Image.alpha_composite(
        image,
        glow,
    )

    return Image.alpha_composite(
        image,
        line_layer,
    )


# ============================================================
# GLOBAL LAUNCH – PLATIN
#
# Bleibt für den ersten Test noch in der bisherigen Form.
# Sobald Early Access sitzt, wird Global daran angepasst.
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

    # --------------------------------------------------------
    # Tiefenkante
    # --------------------------------------------------------

    depth = Image.new(
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

    depth_draw = ImageDraw.Draw(
        depth
    )

    draw_spaced_text(
        depth_draw,
        x + 4,
        y + 4,
        text,
        font,
        (
            7,
            9,
            15,
            145,
        ),
        spacing,
    )

    depth = depth.filter(
        ImageFilter.GaussianBlur(
            1.1
        )
    )

    image = Image.alpha_composite(
        image,
        depth,
    )

    # --------------------------------------------------------
    # Kalter, dezenter Glow
    # --------------------------------------------------------

    for blur_radius, alpha in [
        (
            12,
            35,
        ),
        (
            5,
            55,
        ),
        (
            2,
            65,
        ),
    ]:

        glow = Image.new(
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

        glow_draw = ImageDraw.Draw(
            glow
        )

        draw_spaced_text(
            glow_draw,
            x,
            y,
            text,
            font,
            (
                215,
                226,
                240,
                alpha,
            ),
            spacing,
        )

        glow = glow.filter(
            ImageFilter.GaussianBlur(
                blur_radius
            )
        )

        image = Image.alpha_composite(
            image,
            glow,
        )

    # --------------------------------------------------------
    # Maske
    # --------------------------------------------------------

    mask = Image.new(
        "L",
        (
            width,
            height,
        ),
        0,
    )

    mask_draw = ImageDraw.Draw(
        mask
    )

    draw_spaced_text(
        mask_draw,
        x,
        y,
        text,
        font,
        255,
        spacing,
    )

    bbox = mask.getbbox()

    if not bbox:
        return image

    top = bbox[1]
    bottom = bbox[3]

    visible_height = (
        bottom
        - top
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

    platinum_pixels = (
        platinum.load()
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

        if progress < 0.18:

            local = (
                progress
                / 0.18
            )

            color = (
                int(
                    205
                    + 45 * local
                ),
                int(
                    213
                    + 39 * local
                ),
                int(
                    225
                    + 30 * local
                ),
                255,
            )

        elif progress < 0.40:

            local = (
                (
                    progress
                    - 0.18
                )
                / 0.22
            )

            color = (
                int(
                    250
                    - 73 * local
                ),
                int(
                    252
                    - 68 * local
                ),
                int(
                    255
                    - 61 * local
                ),
                255,
            )

        elif progress < 0.56:

            local = (
                (
                    progress
                    - 0.40
                )
                / 0.16
            )

            color = (
                int(
                    177
                    + 74 * local
                ),
                int(
                    184
                    + 69 * local
                ),
                int(
                    194
                    + 61 * local
                ),
                255,
            )

        elif progress < 0.75:

            local = (
                (
                    progress
                    - 0.56
                )
                / 0.19
            )

            color = (
                int(
                    251
                    - 102 * local
                ),
                int(
                    253
                    - 94 * local
                ),
                int(
                    255
                    - 84 * local
                ),
                255,
            )

        else:

            local = (
                (
                    progress
                    - 0.75
                )
                / 0.25
            )

            color = (
                int(
                    149
                    + 73 * local
                ),
                int(
                    159
                    + 68 * local
                ),
                int(
                    171
                    + 61 * local
                ),
                255,
            )

        for xx in range(
            bbox[0],
            bbox[2],
        ):

            platinum_pixels[
                xx,
                yy
            ] = color

    platinum.putalpha(
        mask
    )

    return Image.alpha_composite(
        image,
        platinum,
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
        EARLY_DATE_SIZE,
        bold=False,
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

        # Am Starttag bleibt die große Karte bestehen.
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

    divider_height = 8

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
            + EARLY_GAP_DATE_DIVIDER
            + divider_height
            + EARLY_GAP_DIVIDER_NOCH
            + noch_height
            + EARLY_GAP_NOCH_DAYS
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
            + EARLY_GAP_DATE_DIVIDER
            + divider_height
            + EARLY_GAP_DIVIDER_NOCH
            + days_height
        )

    # --------------------------------------------------------
    # Gesamte Gruppe vertikal zentrieren
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

    date_visible_top = (
        visible_top
        + title_height
        + EARLY_GAP_TITLE_DATE
    )

    date_y = (
        date_visible_top
        - date_bbox[1]
    )

    divider_y = (
        date_visible_top
        + date_height
        + EARLY_GAP_DATE_DIVIDER
        + divider_height / 2
    )

    after_divider_top = (
        divider_y
        + divider_height / 2
        + EARLY_GAP_DIVIDER_NOCH
    )

    if noch_text:

        noch_y = (
            after_divider_top
            - noch_bbox[1]
        )

        days_visible_top = (
            after_divider_top
            + noch_height
            + EARLY_GAP_NOCH_DAYS
        )

    else:

        days_visible_top = (
            after_divider_top
        )

    days_y = (
        days_visible_top
        - days_bbox[1]
    )

    # --------------------------------------------------------
    # Titel
    # --------------------------------------------------------

    image = draw_gold_title(
        image,
        title_text,
        title_font,
        CARD_WIDTH / 2,
        title_y,
        EARLY_TITLE_SPACING,
    )

    # --------------------------------------------------------
    # Datum
    # --------------------------------------------------------

    image = draw_soft_centered_text(
        image,
        date_text,
        date_y,
        date_font,
        EARLY_IVORY,
        shadow_alpha=125,
        shadow_blur=3.5,
    )

    # --------------------------------------------------------
    # Zierlinie
    # --------------------------------------------------------

    image = draw_early_divider(
        image,
        divider_y,
    )

    # --------------------------------------------------------
    # NOCH
    # --------------------------------------------------------

    if noch_text:

        image = draw_early_noch(
            image,
            noch_text,
            noch_font,
            noch_y,
        )

    # --------------------------------------------------------
    # Countdown
    # --------------------------------------------------------

    image = draw_soft_centered_text(
        image,
        days_text,
        days_y,
        days_font,
        EARLY_IVORY,
        shadow_alpha=145,
        shadow_blur=4.5,
    )

    return image.convert(
        "RGB"
    )


# ============================================================
# GLOBAL LAUNCH – VOLLE KARTE
#
# Für diesen ersten Design-Test noch unverändert.
# ============================================================

def create_global_launch_full_card(
    milestone
):

    image = load_background(
        milestone["background"]
    )

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

    probe = ImageDraw.Draw(
        image
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

    image = draw_platinum_title(
        image,
        title_text,
        title_font,
        CARD_WIDTH / 2,
        title_y,
        TITLE_SPACING,
    )

    draw = ImageDraw.Draw(
        image
    )

    draw_centered_text(
        draw,
        date_text,
        date_y,
        date_font,
        WHITE,
    )

    if noch_text:

        draw_centered_text(
            draw,
            noch_text,
            noch_y,
            noch_font,
            GRAY,
        )

    draw_centered_text(
        draw,
        days_text,
        days_y,
        days_font,
        WHITE,
    )

    return image.convert(
        "RGB"
    )


# ============================================================
# VIERZEILER
# ============================================================

def create_full_card(
    milestone
):

    if milestone["key"] == "early_access":

        return create_early_access_full_card(
            milestone
        )

    return create_global_launch_full_card(
        milestone
    )


# ============================================================
# ZWEIZEILER
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

    # --------------------------------------------------------
    # Titel
    # --------------------------------------------------------

    if milestone["key"] == "early_access":

        image = draw_gold_title(
            image,
            title_text,
            title_font,
            CARD_WIDTH / 2,
            title_y,
            COMPACT_TITLE_SPACING,
        )

    elif milestone["key"] == "global_launch":

        image = draw_platinum_title(
            image,
            title_text,
            title_font,
            CARD_WIDTH / 2,
            title_y,
            COMPACT_TITLE_SPACING,
        )

    draw = ImageDraw.Draw(
        image
    )

    draw_centered_text(
        draw,
        status_text,
        status_y,
        status_font,
        WHITE,
    )

    return image.convert(
        "RGB"
    )


# ============================================================
# MILESTONE RENDERN
# ============================================================

def render_milestone(milestone):

    # Vor Start + am Starttag:
    # volle 535px-Karte
    if milestone["state"] in (
        "countdown",
        "today",
    ):

        return create_full_card(
            milestone
        )

    # Nach Start:
    # komplette Karte klappt auf 270px ein
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
# Jede Karte bekommt eine eigene Discord-Nachricht.
# Dadurch zeigt Discord sie untereinander statt als Galerie.
#
# Bestehendes CONTENT_MESSAGE_ID wird weiterhin für Early Access
# verwendet, damit der bisherige Eintrag nicht verloren geht.
#
# Für Global Launch kommt einmalig
# CONTENT_GLOBAL_MESSAGE_ID hinzu.
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


def patch_discord_image(
    message_id,
    image_file,
    discord_filename,
):

    url = (
        f"{WEBHOOK_URL}"
        f"/messages/"
        f"{message_id}"
    )

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

        response = requests.patch(
            url,
            data={
                "payload_json":
                    json.dumps(payload)
            },
            files=files,
            timeout=30,
        )

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

    # --------------------------------------------------------
    # EARLY ACCESS
    # --------------------------------------------------------

    if CONTENT_MESSAGE_ID:

        patch_discord_image(
            CONTENT_MESSAGE_ID,
            early_access_file,
            "early_access.png",
        )

        early_message_id = (
            CONTENT_MESSAGE_ID
        )

    else:

        early_message_id = post_discord_image(
            early_access_file,
            "early_access.png",
        )

    # --------------------------------------------------------
    # GLOBAL LAUNCH
    # --------------------------------------------------------

    if CONTENT_GLOBAL_MESSAGE_ID:

        patch_discord_image(
            CONTENT_GLOBAL_MESSAGE_ID,
            global_launch_file,
            "global_launch.png",
        )

        global_message_id = (
            CONTENT_GLOBAL_MESSAGE_ID
        )

    else:

        global_message_id = post_discord_image(
            global_launch_file,
            "global_launch.png",
        )

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
    print("")
    print(
        "Early Access Message-ID:"
    )
    print(
        early_message_id
    )
    print("")
    print(
        "Global Launch Message-ID:"
    )
    print(
        global_message_id
    )
    print("")

    if not CONTENT_MESSAGE_ID:

        print(
            "Diese ID als GitHub Secret "
            "CONTENT_MESSAGE_ID speichern:"
        )
        print(
            early_message_id
        )
        print("")

    if not CONTENT_GLOBAL_MESSAGE_ID:

        print(
            "Diese ID als GitHub Secret "
            "CONTENT_GLOBAL_MESSAGE_ID speichern:"
        )
        print(
            global_message_id
        )
        print("")

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
