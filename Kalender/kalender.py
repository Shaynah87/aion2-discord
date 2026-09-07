from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# --------------------------------------------------
# TESTDATEN – nur für unsere erste Kalenderansicht
# --------------------------------------------------

DAYS = [
    ("MO", "07"),
    ("DI", "08"),
    ("MI", "09"),
    ("DO", "10"),
    ("FR", "11"),
    ("SA", "12"),
    ("SO", "13"),
]

MEMBERS = [
    {
        "name": "Laura",
        "start": 0,   # Montag
        "end": 3,     # Donnerstag
    },
    {
        "name": "Tom",
        "start": 2,   # Mittwoch
        "end": 5,     # Samstag
    },
    {
        "name": "Patrick",
        "start": 4,   # Freitag
        "end": 6,     # Sonntag
    },
]


# --------------------------------------------------
# DATEIEN / GRÖSSE
# --------------------------------------------------

OUTPUT = Path(__file__).parent / "kalender_test.png"

WIDTH = 1500
HEIGHT = 760

LEFT = 260
RIGHT = 70
TOP = 205

DAY_WIDTH = (WIDTH - LEFT - RIGHT) / 7
ROW_HEIGHT = 125


# --------------------------------------------------
# FARBEN
# --------------------------------------------------

BG = (17, 18, 22)
PANEL = (24, 25, 31)

TEXT = (242, 242, 244)
TEXT_MUTED = (145, 148, 158)

GRID = (53, 55, 64)
WEEKEND = (29, 30, 37)

GOLD = (214, 170, 79)
BAR = (105, 82, 156)
BAR_BORDER = (147, 120, 204)

COUNT_BG = (34, 35, 42)
COUNT_ACTIVE = (73, 57, 103)


# --------------------------------------------------
# FONT
# --------------------------------------------------

def get_font(size, bold=False):
    possible = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",

        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]

    for path in possible:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass

    return ImageFont.load_default()


FONT_TITLE = get_font(42, True)
FONT_SUBTITLE = get_font(20)
FONT_DAY = get_font(19, True)
FONT_DATE = get_font(34, True)
FONT_NAME = get_font(27, True)
FONT_BAR = get_font(18, True)
FONT_COUNT = get_font(17, True)


# --------------------------------------------------
# HILFSFUNKTIONEN
# --------------------------------------------------

def centered_text(draw, xy, text, font, fill):
    x, y = xy
    box = draw.textbbox((0, 0), text, font=font)
    width = box[2] - box[0]
    draw.text((x - width / 2, y), text, font=font, fill=fill)


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


# --------------------------------------------------
# BILD
# --------------------------------------------------

img = Image.new("RGB", (WIDTH, HEIGHT), BG)
draw = ImageDraw.Draw(img)


# --------------------------------------------------
# HEADER
# --------------------------------------------------

draw.text(
    (70, 55),
    "WOCHENÜBERSICHT",
    font=FONT_TITLE,
    fill=TEXT,
)

draw.text(
    (72, 112),
    "07.–13. SEPTEMBER 2026",
    font=FONT_SUBTITLE,
    fill=GOLD,
)

draw.text(
    (72, 148),
    "Abwesenheiten der Gildenmitglieder",
    font=FONT_SUBTITLE,
    fill=TEXT_MUTED,
)


# --------------------------------------------------
# KALENDER-PANEL
# --------------------------------------------------

panel_top = TOP - 20
panel_bottom = TOP + len(MEMBERS) * ROW_HEIGHT + 105

rounded(
    draw,
    (55, panel_top, WIDTH - 55, panel_bottom),
    24,
    PANEL,
)


# --------------------------------------------------
# TAGE
# --------------------------------------------------

for i, (day_name, day_number) in enumerate(DAYS):

    x1 = LEFT + i * DAY_WIDTH
    x2 = x1 + DAY_WIDTH

    # Wochenende leicht absetzen
    if i >= 5:
        draw.rectangle(
            (x1, panel_top + 1, x2, panel_bottom - 1),
            fill=WEEKEND,
        )

    cx = x1 + DAY_WIDTH / 2

    centered_text(
        draw,
        (cx, TOP + 5),
        day_name,
        FONT_DAY,
        TEXT_MUTED,
    )

    centered_text(
        draw,
        (cx, TOP + 34),
        day_number,
        FONT_DATE,
        TEXT,
    )

    # vertikale Trennlinien
    if i > 0:
        draw.line(
            (x1, TOP, x1, panel_bottom - 70),
            fill=GRID,
            width=1,
        )


# Linie unter Datum
draw.line(
    (75, TOP + 92, WIDTH - 75, TOP + 92),
    fill=GRID,
    width=2,
)


# --------------------------------------------------
# MITGLIEDER + ABWESENHEITSBALKEN
# --------------------------------------------------

for row, member in enumerate(MEMBERS):

    row_y = TOP + 110 + row * ROW_HEIGHT

    # Name
    draw.text(
        (85, row_y + 29),
        member["name"],
        font=FONT_NAME,
        fill=TEXT,
    )

    # dezente horizontale Trennlinie
    if row > 0:
        draw.line(
            (75, row_y - 12, WIDTH - 75, row_y - 12),
            fill=GRID,
            width=1,
        )

    start_x = LEFT + member["start"] * DAY_WIDTH + 12
    end_x = LEFT + (member["end"] + 1) * DAY_WIDTH - 12

    bar_y1 = row_y + 20
    bar_y2 = row_y + 78

    rounded(
        draw,
        (start_x, bar_y1, end_x, bar_y2),
        18,
        BAR,
        BAR_BORDER,
        2,
    )

    # Balkenbeschriftung
    bar_width = end_x - start_x

    if bar_width > 190:
        centered_text(
            draw,
            ((start_x + end_x) / 2, bar_y1 + 18),
            "ABWESEND",
            FONT_BAR,
            TEXT,
        )


# --------------------------------------------------
# ABWESEND-PRO-TAG ZÄHLEN
# --------------------------------------------------

counts = []

for day_index in range(7):
    count = sum(
        1
        for member in MEMBERS
        if member["start"] <= day_index <= member["end"]
    )
    counts.append(count)


count_y = panel_bottom - 52

draw.text(
    (85, count_y + 5),
    "Abwesend",
    font=FONT_COUNT,
    fill=TEXT_MUTED,
)

for i, count in enumerate(counts):

    cx = LEFT + i * DAY_WIDTH + DAY_WIDTH / 2

    box_width = 80
    box_height = 36

    fill = COUNT_ACTIVE if count >= 2 else COUNT_BG

    rounded(
        draw,
        (
            cx - box_width / 2,
            count_y,
            cx + box_width / 2,
            count_y + box_height,
        ),
        13,
        fill,
    )

    centered_text(
        draw,
        (cx, count_y + 8),
        str(count),
        FONT_COUNT,
        TEXT if count else TEXT_MUTED,
    )


# --------------------------------------------------
# SPEICHERN
# --------------------------------------------------

img.save(OUTPUT, quality=95)

print(f"Kalender erstellt: {OUTPUT}")
