import os
import json
import uuid
import urllib.request

from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


# ============================================================
# GRUNDEINSTELLUNGEN
# ============================================================

WEBHOOK_URL = os.environ.get("KALENDER_WEBHOOK")

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_FILE = BASE_DIR / "kalender.png"
STATE_FILE = BASE_DIR / "kalender_message.json"

TIMEZONE = ZoneInfo("Europe/Berlin")


# ============================================================
# TESTDATEN
#
# Diese Daten sind nur dafür da, unser Layout im Discord
# anzuschauen.
#
# start / end:
# 0 = Montag
# 1 = Dienstag
# ...
# 6 = Sonntag
# ============================================================

MEMBERS = [
    {
        "name": "Laura",
        "start": 0,
        "end": 3,
    },
    {
        "name": "Tom",
        "start": 2,
        "end": 5,
    },
    {
        "name": "Patrick",
        "start": 4,
        "end": 6,
    },
]


# ============================================================
# BILDGRÖSSE
# ============================================================

WIDTH = 1500
HEIGHT = 760

LEFT = 260
RIGHT = 70
TOP = 205

DAY_WIDTH = (WIDTH - LEFT - RIGHT) / 7
ROW_HEIGHT = 125


# ============================================================
# FARBEN
# ============================================================

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


# ============================================================
# SCHRIFTEN
# ============================================================

def load_font(size, bold=False):

    if bold:
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


FONT_TITLE = load_font(42, True)
FONT_SUBTITLE = load_font(20)
FONT_DAY = load_font(19, True)
FONT_DATE = load_font(34, True)
FONT_NAME = load_font(27, True)
FONT_BAR = load_font(18, True)
FONT_COUNT = load_font(17, True)


# ============================================================
# STATE
# ============================================================

def load_state():

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    except FileNotFoundError:

        return {}


def save_state(data):

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
        )


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def centered_text(
    draw,
    x,
    y,
    text,
    font,
    fill,
):

    box = draw.textbbox(
        (0, 0),
        text,
        font=font,
    )

    text_width = (
        box[2] - box[0]
    )

    draw.text(
        (
            x - text_width / 2,
            y,
        ),
        text,
        font=font,
        fill=fill,
    )


def rounded(
    draw,
    box,
    radius,
    fill,
    outline=None,
    width=1,
):

    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


# ============================================================
# AKTUELLE WOCHE
# ============================================================

def get_current_week():

    now = datetime.now(
        TIMEZONE
    )

    monday = (
        now
        - timedelta(
            days=now.weekday()
        )
    )

    days = []

    labels = [
        "MO",
        "DI",
        "MI",
        "DO",
        "FR",
        "SA",
        "SO",
    ]

    for index in range(7):

        date = (
            monday
            + timedelta(
                days=index
            )
        )

        days.append(
            {
                "label": labels[index],
                "date": date,
            }
        )

    return days


# ============================================================
# WOCHENKARTE ERSTELLEN
# ============================================================

def create_calendar():

    days = get_current_week()

    image = Image.new(
        "RGB",
        (
            WIDTH,
            HEIGHT,
        ),
        BG,
    )

    draw = ImageDraw.Draw(
        image
    )

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    draw.text(
        (
            70,
            55,
        ),
        "WOCHENÜBERSICHT",
        font=FONT_TITLE,
        fill=TEXT,
    )

    first_day = (
        days[0]["date"]
    )

    last_day = (
        days[-1]["date"]
    )

    month_names = {
        1: "JANUAR",
        2: "FEBRUAR",
        3: "MÄRZ",
        4: "APRIL",
        5: "MAI",
        6: "JUNI",
        7: "JULI",
        8: "AUGUST",
        9: "SEPTEMBER",
        10: "OKTOBER",
        11: "NOVEMBER",
        12: "DEZEMBER",
    }

    if (
        first_day.month
        == last_day.month
    ):

        date_text = (
            f"{first_day.day:02d}.–"
            f"{last_day.day:02d}. "
            f"{month_names[first_day.month]} "
            f"{last_day.year}"
        )

    else:

        date_text = (
            f"{first_day.day:02d}. "
            f"{month_names[first_day.month]} – "
            f"{last_day.day:02d}. "
            f"{month_names[last_day.month]} "
            f"{last_day.year}"
        )

    draw.text(
        (
            72,
            112,
        ),
        date_text,
        font=FONT_SUBTITLE,
        fill=GOLD,
    )

    draw.text(
        (
            72,
            148,
        ),
        "Abwesenheiten der Gildenmitglieder",
        font=FONT_SUBTITLE,
        fill=TEXT_MUTED,
    )

    # --------------------------------------------------------
    # PANEL
    # --------------------------------------------------------

    panel_top = (
        TOP - 20
    )

    panel_bottom = (
        TOP
        + len(MEMBERS) * ROW_HEIGHT
        + 105
    )

    rounded(
        draw,
        (
            55,
            panel_top,
            WIDTH - 55,
            panel_bottom,
        ),
        24,
        PANEL,
    )

    # --------------------------------------------------------
    # TAGE
    # --------------------------------------------------------

    for index, day in enumerate(
        days
    ):

        x1 = (
            LEFT
            + index * DAY_WIDTH
        )

        x2 = (
            x1
            + DAY_WIDTH
        )

        # Wochenende abdunkeln
        if index >= 5:

            draw.rectangle(
                (
                    x1,
                    panel_top + 1,
                    x2,
                    panel_bottom - 1,
                ),
                fill=WEEKEND,
            )

        center_x = (
            x1
            + DAY_WIDTH / 2
        )

        centered_text(
            draw,
            center_x,
            TOP + 5,
            day["label"],
            FONT_DAY,
            TEXT_MUTED,
        )

        centered_text(
            draw,
            center_x,
            TOP + 34,
            f"{day['date'].day:02d}",
            FONT_DATE,
            TEXT,
        )

        if index > 0:

            draw.line(
                (
                    x1,
                    TOP,
                    x1,
                    panel_bottom - 70,
                ),
                fill=GRID,
                width=1,
            )

    # Linie unter Tagen
    draw.line(
        (
            75,
            TOP + 92,
            WIDTH - 75,
            TOP + 92,
        ),
        fill=GRID,
        width=2,
    )

    # --------------------------------------------------------
    # MITGLIEDER
    # --------------------------------------------------------

    for row, member in enumerate(
        MEMBERS
    ):

        row_y = (
            TOP
            + 110
            + row * ROW_HEIGHT
        )

        draw.text(
            (
                85,
                row_y + 29,
            ),
            member["name"],
            font=FONT_NAME,
            fill=TEXT,
        )

        if row > 0:

            draw.line(
                (
                    75,
                    row_y - 12,
                    WIDTH - 75,
                    row_y - 12,
                ),
                fill=GRID,
                width=1,
            )

        start_x = (
            LEFT
            + member["start"] * DAY_WIDTH
            + 12
        )

        end_x = (
            LEFT
            + (member["end"] + 1) * DAY_WIDTH
            - 12
        )

        bar_y1 = (
            row_y + 20
        )

        bar_y2 = (
            row_y + 78
        )

        rounded(
            draw,
            (
                start_x,
                bar_y1,
                end_x,
                bar_y2,
            ),
            18,
            BAR,
            BAR_BORDER,
            2,
        )

        bar_width = (
            end_x - start_x
        )

        if bar_width > 190:

            centered_text(
                draw,
                (
                    start_x
                    + end_x
                ) / 2,
                bar_y1 + 18,
                "ABWESEND",
                FONT_BAR,
                TEXT,
            )

    # --------------------------------------------------------
    # ANZAHL ABWESEND PRO TAG
    # --------------------------------------------------------

    counts = []

    for day_index in range(7):

        count = sum(
            1
            for member in MEMBERS
            if (
                member["start"]
                <= day_index
                <= member["end"]
            )
        )

        counts.append(
            count
        )

    count_y = (
        panel_bottom - 52
    )

    draw.text(
        (
            85,
            count_y + 5,
        ),
        "Abwesend",
        font=FONT_COUNT,
        fill=TEXT_MUTED,
    )

    for index, count in enumerate(
        counts
    ):

        center_x = (
            LEFT
            + index * DAY_WIDTH
            + DAY_WIDTH / 2
        )

        box_width = 80
        box_height = 36

        if count >= 2:
            fill = COUNT_ACTIVE

        else:
            fill = COUNT_BG

        rounded(
            draw,
            (
                center_x - box_width / 2,
                count_y,
                center_x + box_width / 2,
                count_y + box_height,
            ),
            13,
            fill,
        )

        centered_text(
            draw,
            center_x,
            count_y + 8,
            str(count),
            FONT_COUNT,
            TEXT if count else TEXT_MUTED,
        )

    # --------------------------------------------------------
    # SPEICHERN
    # --------------------------------------------------------

    image.save(
        OUTPUT_FILE,
        "PNG",
        optimize=True,
    )

    print(
        f"Kalender erstellt: "
        f"{OUTPUT_FILE}"
    )


# ============================================================
# DISCORD MULTIPART REQUEST
# ============================================================

def webhook_request_with_file(
    url,
    payload,
    file_path,
    method="POST",
):

    boundary = (
        "----Nyerk24CalendarBoundary"
        + uuid.uuid4().hex
    )

    body = bytearray()

    # payload_json
    body.extend(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; '
            f'name="payload_json"\r\n'
            f"Content-Type: application/json\r\n\r\n"
        ).encode(
            "utf-8"
        )
    )

    body.extend(
        json.dumps(
            payload
        ).encode(
            "utf-8"
        )
    )

    body.extend(
        b"\r\n"
    )

    # Datei
    with open(
        file_path,
        "rb",
    ) as file:

        file_data = (
            file.read()
        )

    body.extend(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; '
            f'name="files[0]"; '
            f'filename="{file_path.name}"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode(
            "utf-8"
        )
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
        ).encode(
            "utf-8"
        )
    )

    request = urllib.request.Request(
        url,
        data=bytes(
            body
        ),
        method=method,
        headers={
            "Content-Type":
                f"multipart/form-data; "
                f"boundary={boundary}",

            "User-Agent":
                "Nyerk24-Calendar",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=60,
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
# DISCORD PAYLOAD
# ============================================================

def build_payload():

    return {
        "embeds": [
            {
                "color": 8027525,

                "image": {
                    "url":
                        "attachment://kalender.png"
                },
            }
        ],

        "attachments": [
            {
                "id": 0,
                "filename":
                    OUTPUT_FILE.name,
            }
        ],
    }


# ============================================================
# HAUPTPROGRAMM
# ============================================================

def main():

    if not WEBHOOK_URL:

        raise RuntimeError(
            "KALENDER_WEBHOOK fehlt."
        )

    # Kalenderbild erzeugen
    create_calendar()

    # gespeicherte Discord-Nachricht laden
    state = load_state()

    message_id = state.get(
        "message_id"
    )

    payload = build_payload()

    # --------------------------------------------------------
    # BESTEHENDE NACHRICHT AKTUALISIEREN
    # --------------------------------------------------------

    if message_id:

        edit_url = (
            f"{WEBHOOK_URL}"
            f"/messages/{message_id}"
        )

        webhook_request_with_file(
            edit_url,
            payload,
            OUTPUT_FILE,
            method="PATCH",
        )

        print(
            "Bestehende Kalender-Nachricht "
            "aktualisiert."
        )

    # --------------------------------------------------------
    # ERSTE NACHRICHT ERSTELLEN
    # --------------------------------------------------------

    else:

        create_url = (
            f"{WEBHOOK_URL}"
            f"?wait=true"
        )

        result = (
            webhook_request_with_file(
                create_url,
                payload,
                OUTPUT_FILE,
                method="POST",
            )
        )

        save_state(
            {
                "message_id":
                    result["id"]
            }
        )

        print(
            "Neue Kalender-Nachricht erstellt."
        )


if __name__ == "__main__":
    main()
