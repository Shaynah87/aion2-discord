import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageFilter


# ============================================================
# DATEIEN / EINSTELLUNGEN
# ============================================================

DATA_FILE = "content_data.json"
MESSAGE_FILE = "content_message.json"

WEBHOOK_URL = os.environ.get("CONTENT_WEBHOOK")

EARLY_ACCESS_OUTPUT = "early_access_card.png"
GLOBAL_LAUNCH_OUTPUT = "global_launch_card.png"


# ============================================================
# KARTENFORMAT
# ============================================================

CARD_WIDTH = 1200

# Vor dem Start:
# großer Vierzeiler
FULL_HEIGHT = 535

# Nach dem Start:
# komplette Karte inklusive Hintergrund klappt ein
COMPACT_HEIGHT = 270


# ============================================================
# GEMEINSAME TYPOGRAFIE
# Early Access und Global Launch sind 1:1 identisch
# ============================================================

TITLE_SIZE = 82
DATE_SIZE = 38
NOCH_SIZE = 19
COUNTDOWN_SIZE = 54

TITLE_SPACING = 10

GAP_TITLE_DATE = 21
GAP_DATE_NOCH = 42
GAP_NOCH_DAYS = 8


# ============================================================
# ZWEIZEILER
# ============================================================

COMPACT_TITLE_SIZE = 44
COMPACT_STATUS_SIZE = 34

COMPACT_GAP = 22


# ============================================================
# CROP FÜR DEN EINGEKLAPPTEN HINTERGRUND
#
# 0.50 = exakt aus der Mitte des 535px-Masters.
#
# Falls wir später feststellen:
# Early Access Kugel 5px höher,
# Global Launch Gesichter 10px tiefer,
# ändern wir NUR diese beiden Werte.
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


# ============================================================
# DATEN LADEN
# ============================================================

def load_json(
    filename,
    default=None,
):
    try:
        with open(
            filename,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(
                file
            )

    except FileNotFoundError:
        return (
            default
            if default is not None
            else {}
        )


def save_json(
    filename,
    data,
):
    with open(
        filename,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


# ============================================================
# ZEIT / COUNTDOWN
# ============================================================

def get_now(
    timezone_name,
):
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

    difference = (
        target.date()
        - now.date()
    )

    days = difference.days

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

def build_content_state(
    data,
):
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
        if os.path.exists(
            path
        ):
            return ImageFont.truetype(
                path,
                size=size,
            )

    return ImageFont.load_default()


# ============================================================
# HINTERGRUND LADEN
# ============================================================

def load_background(
    filename,
):
    if not filename:
        raise RuntimeError(
            "Kein Hintergrundbild "
            "für Content gesetzt."
        )

    if not os.path.exists(
        filename
    ):
        raise RuntimeError(
            f"Hintergrund fehlt: "
            f"{filename}"
        )

    image = Image.open(
        filename
    ).convert(
        "RGBA"
    )

    # Master immer exakt auf 1200 x 535.
    #
    # Wichtig:
    # kein Stretching auf andere Proportionen.
    # Das Repo-Bild sollte bereits 1200x535 sein.
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
#
# Der Zweizeiler wird NICHT auf 270px gestaucht.
# Wir schneiden aus dem 535px-Master einen 270px-Bereich.
# ============================================================

def crop_compact_background(
    image,
    milestone_key,
):
    width, height = image.size

    target_height = COMPACT_HEIGHT

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
            - target_height / 2
        )
    )

    top = max(
        0,
        min(
            height - target_height,
            top,
        ),
    )

    bottom = (
        top
        + target_height
    )

    return image.crop(
        (
            0,
            top,
            width,
            bottom,
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

    for index, char in enumerate(
        text
    ):
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
    for index, char in enumerate(
        text
    ):
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
            42,
            24,
            7,
            125,
        ),
        spacing,
    )

    depth = depth.filter(
        ImageFilter.GaussianBlur(
            1.2
        )
    )

    image = Image.alpha_composite(
        image,
        depth,
    )

    # --------------------------------------------------------
    # Gold-Glow
    # --------------------------------------------------------

    for (
        blur_radius,
        alpha,
    ) in [
        (
            18,
            58,
        ),
        (
            8,
            105,
        ),
        (
            3,
            105,
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
                225,
                165,
                65,
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

    # --------------------------------------------------------
    # Metallischer Goldverlauf
    # --------------------------------------------------------

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

        if progress < 0.22:
            local = (
                progress
                / 0.22
            )

            color = (
                int(
                    239
                    + 16 * local
                ),
                int(
                    195
                    + 38 * local
                ),
                int(
                    106
                    + 64 * local
                ),
                255,
            )

        elif progress < 0.52:
            local = (
                (
                    progress
                    - 0.22
                )
                / 0.30
            )

            color = (
                int(
                    255
                    - 7 * local
                ),
                int(
                    233
                    + 9 * local
                ),
                int(
                    170
                    + 18 * local
                ),
                255,
            )

        elif progress < 0.72:
            local = (
                (
                    progress
                    - 0.52
                )
                / 0.20
            )

            color = (
                int(
                    248
                    - 26 * local
                ),
                int(
                    242
                    - 52 * local
                ),
                int(
                    188
                    - 65 * local
                ),
                255,
            )

        else:
            local = (
                (
                    progress
                    - 0.72
                )
                / 0.28
            )

            color = (
                int(
                    222
                    - 28 * local
                ),
                int(
                    190
                    - 43 * local
                ),
                int(
                    123
                    - 49 * local
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

    image = Image.alpha_composite(
        image,
        gold,
    )

    return image


# ============================================================
# GLOBAL LAUNCH – SILBER / PLATIN
#
# Gleiche Geometrie wie Gold.
# Nur die Metallfarbe unterscheidet sich.
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
    # Tiefe
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
            8,
            10,
            17,
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
    # sehr dezenter kalter Glow
    # --------------------------------------------------------

    for (
        blur_radius,
        alpha,
    ) in [
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

    image = Image.alpha_composite(
        image,
        platinum,
    )

    return image


# ============================================================
# VIERZEILER
#
# EARLY ACCESS und GLOBAL LAUNCH:
# exakt dieselbe Geometrie
# ============================================================

def create_full_card(
    milestone,
):
    background = load_background(
        milestone["background"]
    )

    image = background.copy()

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

    # --------------------------------------------------------
    # COUNTDOWN / HEUTE
    # --------------------------------------------------------

    if milestone["state"] == "countdown":
        days = milestone["days"]

        days_text = (
            f"{days} "
            f"{'TAG' if days == 1 else 'TAGE'}"
        )

        noch_text = "NOCH"

    else:
        # Auf dem Starttag bleibt die große Karte noch stehen.
        # Sie zeigt HEUTE.
        days_text = "HEUTE"
        noch_text = ""

    # --------------------------------------------------------
    # sichtbare Textgrößen
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

    title_height = (
        title_bbox[3]
        - title_bbox[1]
    )

    date_height = (
        date_bbox[3]
        - date_bbox[1]
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

    days_bbox = probe.textbbox(
        (
            0,
            0,
        ),
        days_text,
        font=days_font,
    )

    days_height = (
        days_bbox[3]
        - days_bbox[1]
    )

    # --------------------------------------------------------
    # Gesamten Textblock vertikal zentrieren
    # --------------------------------------------------------

    if noch_text:
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

    # --------------------------------------------------------
    # Y-Positionen
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # TITEL
    # --------------------------------------------------------

    if milestone["key"] == "early_access":
        image = draw_gold_title(
            image,
            title_text,
            title_font,
            CARD_WIDTH / 2,
            title_y,
            TITLE_SPACING,
        )

    elif milestone["key"] == "global_launch":
        image = draw_platinum_title(
            image,
            title_text,
            title_font,
            CARD_WIDTH / 2,
            title_y,
            TITLE_SPACING,
        )

    else:
        draw = ImageDraw.Draw(
            image
        )

        draw_centered_text(
            draw,
            title_text,
            title_y,
            title_font,
            WHITE,
        )

    # --------------------------------------------------------
    # Restlicher Text
    # --------------------------------------------------------

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
# ZWEIZEILER / EINGEKLAPPTE KARTE
#
# Hintergrund klappt von 535 auf 270px ein.
# ============================================================

def create_compact_card(
    milestone,
):
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

    date_text = (
        milestone[
            "date_display"
        ].upper()
    )

    status_text = (
        f"{date_text} · GESTARTET"
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
    # Titel-Effekt bleibt auch im Zweizeiler erhalten
    # --------------------------------------------------------

    if milestone["key"] == "early_access":
        image = draw_gold_title(
            image,
            title_text,
            title_font,
            CARD_WIDTH / 2,
            title_y,
            spacing=5,
        )

    elif milestone["key"] == "global_launch":
        image = draw_platinum_title(
            image,
            title_text,
            title_font,
            CARD_WIDTH / 2,
            title_y,
            spacing=5,
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

def render_milestone(
    milestone,
):
    # Vor dem Start und am Starttag:
    # große Karte
    if milestone["state"] in (
        "countdown",
        "today",
    ):
        return create_full_card(
            milestone
        )

    # Nach dem Start:
    # komplette Karte klappt ein
    return create_compact_card(
        milestone
    )


# ============================================================
# SPEICHERN
# ============================================================

def save_milestone_card(
    milestone,
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
# TESTAUSGABE
# ============================================================

def print_status(
    content_state,
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

    found_keys = set()

    for milestone in (
        content_state["milestones"]
    ):
        if milestone["key"] not in wanted_keys:
            continue

        save_milestone_card(
            milestone
        )

        found_keys.add(
            milestone["key"]
        )

    missing = (
        wanted_keys
        - found_keys
    )

    if missing:
        raise RuntimeError(
            "Folgende Milestones fehlen "
            "in content_data.json: "
            + ", ".join(
                sorted(
                    missing
                )
            )
        )


if __name__ == "__main__":
    main()
