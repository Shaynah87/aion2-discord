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


# ============================================================
# KARTENFORMAT
# ============================================================

CARD_WIDTH = 1200

# Für den großen Countdown erstmal dieselbe Höhe wie unser
# endgültiger Early-Access-Master.
CARD_HEIGHT = 535


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

DARK_GOLD = (
    194,
    139,
    55,
    255,
)

MID_GOLD = (
    225,
    178,
    89,
    255,
)

LIGHT_GOLD = (
    255,
    229,
    168,
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

    days = (
        difference.days
    )

    if days > 1:

        return {
            "state":
                "countdown",

            "days":
                days,

            "text":
                f"Noch {days} Tage",
        }

    if days == 1:

        return {
            "state":
                "countdown",

            "days":
                1,

            "text":
                "Noch 1 Tag",
        }

    if days == 0:

        return {
            "state":
                "today",

            "days":
                0,

            "text":
                "HEUTE",
        }

    return {
        "state":
            "started",

        "days":
            None,

        "text":
            "GESTARTET",
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
        "updated_at":
            now.isoformat(),

        "milestones":
            [],

        "active_content":
            None,
    }

    for milestone in data.get(
        "milestones",
        [],
    ):

        status = (
            get_milestone_status(
                milestone,
                now,
                timezone_name,
            )
        )

        result[
            "milestones"
        ].append(
            {
                "key":
                    milestone[
                        "key"
                    ],

                "title":
                    milestone[
                        "title"
                    ],

                "date":
                    milestone[
                        "date"
                    ],

                "date_display":
                    milestone[
                        "date_display"
                    ],

                "background":
                    milestone.get(
                        "background"
                    ),

                "state":
                    status[
                        "state"
                    ],

                "days":
                    status.get(
                        "days"
                    ),

                "status_text":
                    status[
                        "text"
                    ],
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
            phase[
                "start_date"
            ],
            timezone_name,
        )

        if (
            start.date()
            <= now.date()
        ):

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

        result[
            "active_content"
        ] = (
            active_phases[
                -1
            ][1]
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

    return (
        ImageFont.load_default()
    )


# ============================================================
# HINTERGRUND
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

    if image.size != (
        CARD_WIDTH,
        CARD_HEIGHT,
    ):

        image = image.resize(
            (
                CARD_WIDTH,
                CARD_HEIGHT,
            ),
            Image.Resampling.LANCZOS,
        )

    return image


# ============================================================
# SYMMETRISCHER SCHWARZVERLAUF
# ============================================================

def add_center_gradient(
    image,
):
    width, height = (
        image.size
    )

    overlay = Image.new(
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

    pixels = (
        overlay.load()
    )

    center_x = (
        width - 1
    ) / 2

    for x in range(
        width
    ):

        distance = (
            abs(
                x
                - center_x
            )
            / center_x
        )

        # Mitte bleibt deutlich offener,
        # beide Außenkanten werden exakt
        # spiegelgleich dunkler.
        alpha = int(
            32
            + 190
            * (
                distance
                ** 1.72
            )
        )

        for y in range(
            height
        ):

            pixels[
                x,
                y
            ] = (
                0,
                0,
                0,
                alpha,
            )

    return (
        Image.alpha_composite(
            image,
            overlay,
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

        width += (
            draw.textlength(
                char,
                font=font,
            )
        )

        if (
            index
            < len(text) - 1
        ):

            width += (
                spacing
            )

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

        x += (
            draw.textlength(
                char,
                font=font,
            )
        )

        if (
            index
            < len(text) - 1
        ):

            x += spacing


# ============================================================
# GOLD-TITEL
# ============================================================

def draw_gold_title(
    image,
    text,
    font,
    center_x,
    y,
    spacing,
):
    width, height = (
        image.size
    )

    probe = ImageDraw.Draw(
        image
    )

    text_width = (
        spaced_text_width(
            probe,
            text,
            font,
            spacing,
        )
    )

    x = (
        center_x
        - text_width / 2
    )

    # ----------------------------------------
    # Tiefenkante
    # ----------------------------------------

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

    depth_draw = (
        ImageDraw.Draw(
            depth
        )
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

    image = (
        Image.alpha_composite(
            image,
            depth,
        )
    )

    # ----------------------------------------
    # Gold-Glow
    # ----------------------------------------

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

        glow_draw = (
            ImageDraw.Draw(
                glow
            )
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

        glow = (
            glow.filter(
                ImageFilter.GaussianBlur(
                    blur_radius
                )
            )
        )

        image = (
            Image.alpha_composite(
                image,
                glow,
            )
        )

    # ----------------------------------------
    # Schriftmaske
    # ----------------------------------------

    mask = Image.new(
        "L",
        (
            width,
            height,
        ),
        0,
    )

    mask_draw = (
        ImageDraw.Draw(
            mask
        )
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

    # ----------------------------------------
    # Metallischer Goldverlauf
    # ----------------------------------------

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

    gold_pixels = (
        gold.load()
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

    image = (
        Image.alpha_composite(
            image,
            gold,
        )
    )

    return image


# ============================================================
# ZENTRIERTER NORMALTEXT
# ============================================================

def draw_centered_text(
    draw,
    text,
    y,
    font,
    fill,
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
            CARD_WIDTH
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
# EARLY ACCESS – GROSSER COUNTDOWN
# ============================================================

def create_early_access_card(
    milestone,
):
    background = (
        load_background(
            milestone[
                "background"
            ]
        )
    )

    image = (
        add_center_gradient(
            background
        )
    )

    title_font = (
        load_font(
            82,
            bold=True,
        )
    )

    date_font = (
        load_font(
            38,
            bold=True,
        )
    )

    noch_font = (
        load_font(
            19,
            bold=True,
        )
    )

    days_font = (
        load_font(
            54,
            bold=True,
        )
    )

    # ----------------------------------------
    # sichtbare Höhen ausmessen
    # ----------------------------------------

    probe = (
        ImageDraw.Draw(
            image
        )
    )

    title_text = (
        milestone[
            "title"
        ]
    )

    date_text = (
        milestone[
            "date_display"
        ].upper()
    )

    if (
        milestone[
            "state"
        ]
        == "countdown"
    ):

        days_text = (
            f"{milestone['days']} "
            f"{'TAG' if milestone['days'] == 1 else 'TAGE'}"
        )

        noch_text = (
            "NOCH"
        )

    elif (
        milestone[
            "state"
        ]
        == "today"
    ):

        days_text = (
            "HEUTE"
        )

        noch_text = (
            ""
        )

    else:

        days_text = (
            "GESTARTET"
        )

        noch_text = (
            ""
        )

    title_bbox = (
        probe.textbbox(
            (
                0,
                0,
            ),
            title_text,
            font=title_font,
        )
    )

    date_bbox = (
        probe.textbbox(
            (
                0,
                0,
            ),
            date_text,
            font=date_font,
        )
    )

    noch_bbox = (
        probe.textbbox(
            (
                0,
                0,
            ),
            (
                noch_text
                if noch_text
                else "NOCH"
            ),
            font=noch_font,
        )
    )

    days_bbox = (
        probe.textbbox(
            (
                0,
                0,
            ),
            days_text,
            font=days_font,
        )
    )

    title_height = (
        title_bbox[3]
        - title_bbox[1]
    )

    date_height = (
        date_bbox[3]
        - date_bbox[1]
    )

    noch_height = (
        noch_bbox[3]
        - noch_bbox[1]
        if noch_text
        else 0
    )

    days_height = (
        days_bbox[3]
        - days_bbox[1]
    )

    GAP_TITLE_DATE = 21
    GAP_DATE_NOCH = 42
    GAP_NOCH_DAYS = 8

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
            CARD_HEIGHT
            - group_height
        )
        / 2
    )

    # ----------------------------------------
    # Y-Positionen
    # ----------------------------------------

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

    # ----------------------------------------
    # EARLY ACCESS GOLD
    # ----------------------------------------

    image = draw_gold_title(
        image,
        title_text,
        title_font,
        CARD_WIDTH / 2,
        title_y,
        spacing=10,
    )

    draw = (
        ImageDraw.Draw(
            image
        )
    )

    # ----------------------------------------
    # Datum
    # ----------------------------------------

    draw_centered_text(
        draw,
        date_text,
        date_y,
        date_font,
        WHITE,
    )

    # ----------------------------------------
    # NOCH
    # ----------------------------------------

    if noch_text:

        draw_centered_text(
            draw,
            noch_text,
            noch_y,
            noch_font,
            GRAY,
        )

    # ----------------------------------------
    # Countdown
    # ----------------------------------------

    draw_centered_text(
        draw,
        days_text,
        days_y,
        days_font,
        WHITE,
    )

    image = (
        image.convert(
            "RGB"
        )
    )

    image.save(
        EARLY_ACCESS_OUTPUT,
        "PNG",
        optimize=True,
    )

    print(
        f"Early-Access-Karte erstellt: "
        f"{EARLY_ACCESS_OUTPUT}"
    )


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
        content_state[
            "milestones"
        ]
    ):

        print("")
        print(
            milestone[
                "title"
            ]
        )
        print(
            milestone[
                "date_display"
            ]
        )
        print(
            milestone[
                "status_text"
            ]
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

    content_state = (
        build_content_state(
            data
        )
    )

    print_status(
        content_state
    )

    early_access = None

    for milestone in (
        content_state[
            "milestones"
        ]
    ):

        if (
            milestone[
                "key"
            ]
            == "early_access"
        ):

            early_access = (
                milestone
            )

            break

    if early_access is None:

        raise RuntimeError(
            "Early Access fehlt "
            "in content_data.json."
        )

    create_early_access_card(
        early_access
    )


if __name__ == "__main__":
    main()
