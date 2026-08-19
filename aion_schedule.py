import os
import json
import urllib.request
import uuid
from io import BytesIO
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


WEBHOOK_URL = os.environ.get("AION_SCHEDULE_WEBHOOK")

DATA_FILE = "schedule_data.json"
STATE_FILE = "schedule_message.json"

RIFT_BACKGROUND_URL = (
    "https://raw.githubusercontent.com/"
    "Shaynah87/aion2-discord/main/spacetime_rift.png"
)

RIFT_CARD_FILE = "spacetime_rift_card.png"


# ============================================================
# DATEIEN
# ============================================================

def load_data():
    with open(
        DATA_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def load_state():
    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except FileNotFoundError:
        return {}


def save_state(data):
    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            indent=2
        )


# ============================================================
# SCHRIFTEN
# ============================================================

def load_font(size, bold=False):
    if bold:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        ]
    else:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
        ]

    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(
                path,
                size=size
            )

    return ImageFont.load_default()


# ============================================================
# ZEITFUNKTIONEN
# ============================================================

def parse_time_today(
    time_string,
    timezone
):
    hour, minute = map(
        int,
        time_string.split(":")
    )

    now = datetime.now(timezone)

    return now.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0
    )


def discord_time(dt):
    unix = int(
        dt.timestamp()
    )

    return f"<t:{unix}:t>"


def german_weekday(dt):
    weekdays = {
        0: "Montag",
        1: "Dienstag",
        2: "Mittwoch",
        3: "Donnerstag",
        4: "Freitag",
        5: "Samstag",
        6: "Sonntag"
    }

    return weekdays[
        dt.weekday()
    ]


def format_time_range(
    start,
    end
):
    return (
        f"{start.strftime('%H:%M')} – "
        f"{end.strftime('%H:%M')} Uhr"
    )


# ============================================================
# DAILY RESET
# ============================================================

def next_daily_reset(
    time_string,
    timezone
):
    now = datetime.now(timezone)

    candidate = parse_time_today(
        time_string,
        timezone
    )

    if candidate <= now:
        candidate += timedelta(days=1)

    return candidate


# ============================================================
# WEEKLY RESET
# ============================================================

def next_weekly_reset(
    day_name,
    time_string,
    timezone
):
    weekdays = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6
    }

    now = datetime.now(timezone)

    target_weekday = weekdays[
        day_name
    ]

    hour, minute = map(
        int,
        time_string.split(":")
    )

    days_ahead = (
        target_weekday -
        now.weekday()
    ) % 7

    candidate = (
        now +
        timedelta(days=days_ahead)
    ).replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0
    )

    if candidate <= now:
        candidate += timedelta(days=7)

    return candidate


# ============================================================
# SPACETIME RIFT
# ============================================================

def build_rift_times(
    rift_data,
    timezone
):
    now = datetime.now(timezone)

    first_start = parse_time_today(
        rift_data["first_start"],
        timezone
    )

    interval = timedelta(
        hours=rift_data[
            "interval_hours"
        ]
    )

    duration = timedelta(
        minutes=rift_data[
            "duration_minutes"
        ]
    )

    starts = []

    start = (
        first_start -
        timedelta(days=1)
    )

    end_limit = (
        first_start +
        timedelta(days=2)
    )

    while start <= end_limit:
        starts.append(start)
        start += interval

    active_start = None
    active_end = None

    for start_time in starts:
        end_time = (
            start_time +
            duration
        )

        if (
            start_time <= now <
            end_time
        ):
            active_start = start_time
            active_end = end_time
            break

    future_starts = [
        start_time
        for start_time in starts
        if start_time > now
    ]

    future_starts.sort()

    next_start = future_starts[0]
    following_start = future_starts[1]

    return {
        "active_start":
            active_start,

        "active_end":
            active_end,

        "next_start":
            next_start,

        "following_start":
            following_start
    }


# ============================================================
# SHUGO GAMES
# ============================================================

def next_shugo_starts(
    shugo_data,
    timezone
):
    now = datetime.now(timezone)

    candidates = []

    for day_offset in range(0, 2):

        day = (
            now +
            timedelta(days=day_offset)
        )

        for hour in range(24):

            for minute in shugo_data[
                "start_minutes"
            ]:

                candidate = day.replace(
                    hour=hour,
                    minute=minute,
                    second=0,
                    microsecond=0
                )

                if candidate > now:
                    candidates.append(
                        candidate
                    )

    candidates.sort()

    return (
        candidates[0],
        candidates[1]
    )


def shugo_rotation_for_time(
    dt,
    shugo_data
):
    if dt.minute == 15:
        return shugo_data[
            "rotation_15"
        ]

    return shugo_data[
        "rotation_45"
    ]


# ============================================================
# ALS NÄCHSTES
# ============================================================

def find_next_event(
    rift_next,
    shugo_next,
    daily_reset,
    weekly_reset
):
    events = [
        {
            "time": rift_next,
            "icon": "🌀",
            "name": "Spacetime Rift",
            "color": 14555706
        },

        {
            "time": shugo_next,
            "icon": "🐹",
            "name": "Shugo Games",
            "color": 14058735
        },

        {
            "time": daily_reset,
            "icon": "🔄",
            "name": "Daily Reset",
            "color": 6724044
        },

        {
            "time": weekly_reset,
            "icon": "🔄",
            "name": "Weekly Reset",
            "color": 6724044
        }
    ]

    events.sort(
        key=lambda item: item["time"]
    )

    return events[0]


# ============================================================
# RIFT-HINTERGRUND LADEN
# ============================================================

def load_rift_background():
    request = urllib.request.Request(
        RIFT_BACKGROUND_URL,
        headers={
            "User-Agent":
                "AION2-Schedule-Bot"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:
        image_data = response.read()

    return Image.open(
        BytesIO(image_data)
    ).convert("RGBA")


# ============================================================
# WEICHER TEXT-VERLAUF
# ============================================================

def add_left_gradient(image):
    width, height = image.size

    overlay = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    pixels = overlay.load()

    fade_end = int(
        width * 0.62
    )

    for x in range(fade_end):

        progress = (
            x / fade_end
        )

        alpha = int(
            225 *
            ((1.0 - progress) ** 1.7)
        )

        for y in range(height):
            pixels[x, y] = (
                3,
                2,
                7,
                alpha
            )

    return Image.alpha_composite(
        image,
        overlay
    )


# ============================================================
# TEXT MIT LEICHTEM SCHATTEN
# ============================================================

def draw_text_with_shadow(
    draw,
    position,
    text,
    font,
    fill,
    shadow_offset=2
):
    x, y = position

    draw.text(
        (
            x + shadow_offset,
            y + shadow_offset
        ),
        text,
        font=font,
        fill=(
            0,
            0,
            0,
            190
        )
    )

    draw.text(
        position,
        text,
        font=font,
        fill=fill
    )


# ============================================================
# RIFT-KARTE ERZEUGEN
# ============================================================

def create_rift_card(
    rift_data,
    rift_times
):
    image = load_rift_background()

    target_width = 1200
    target_height = 500

    source_width, source_height = (
        image.size
    )

    source_ratio = (
        source_width /
        source_height
    )

    target_ratio = (
        target_width /
        target_height
    )

    if source_ratio > target_ratio:

        new_width = int(
            source_height *
            target_ratio
        )

        left = (
            source_width -
            new_width
        ) // 2

        image = image.crop(
            (
                left,
                0,
                left + new_width,
                source_height
            )
        )

    else:

        new_height = int(
            source_width /
            target_ratio
        )

        top = (
            source_height -
            new_height
        ) // 2

        image = image.crop(
            (
                0,
                top,
                source_width,
                top + new_height
            )
        )

    image = image.resize(
        (
            target_width,
            target_height
        ),
        Image.Resampling.LANCZOS
    )

    image = add_left_gradient(
        image
    )

    draw = ImageDraw.Draw(
        image,
        "RGBA"
    )

    # --------------------------------------------------------
    # SCHRIFTEN
    # --------------------------------------------------------

    title_font = load_font(
        48,
        bold=True
    )

    subtitle_font = load_font(
        25,
        bold=False
    )

    label_font = load_font(
        24,
        bold=True
    )

    time_font = load_font(
        39,
        bold=True
    )

    small_font = load_font(
        25,
        bold=False
    )

    # --------------------------------------------------------
    # FARBEN
    # --------------------------------------------------------

    white = (
        248,
        246,
        250,
        255
    )

    red = (
        255,
        78,
        88,
        255
    )

    light_red = (
        255,
        135,
        140,
        255
    )

    muted = (
        205,
        195,
        200,
        255
    )

    # --------------------------------------------------------
    # TITEL
    # --------------------------------------------------------

    draw_text_with_shadow(
        draw,
        (72, 64),
        "SPACETIME RIFT",
        title_font,
        white
    )

    draw_text_with_shadow(
        draw,
        (74, 126),
        (
            f"Alle "
            f"{rift_data['interval_hours']} Stunden"
        ),
        subtitle_font,
        light_red
    )

    # --------------------------------------------------------
    # AKTIV ODER NÄCHSTER RIFT
    # --------------------------------------------------------

    if rift_times[
        "active_start"
    ]:

        active_start = (
            rift_times[
                "active_start"
            ]
        )

        active_end = (
            rift_times[
                "active_end"
            ]
        )

        main_label = (
            "JETZT AKTIV"
        )

        main_range = (
            format_time_range(
                active_start,
                active_end
            )
        )

        second_start = (
            rift_times[
                "next_start"
            ]
        )

    else:

        next_start = (
            rift_times[
                "next_start"
            ]
        )

        next_end = (
            next_start +
            timedelta(
                minutes=rift_data[
                    "duration_minutes"
                ]
            )
        )

        main_label = (
            "NÄCHSTER RIFT"
        )

        main_range = (
            format_time_range(
                next_start,
                next_end
            )
        )

        second_start = (
            rift_times[
                "following_start"
            ]
        )

    # --------------------------------------------------------
    # HAUPTZEIT
    # --------------------------------------------------------

    draw_text_with_shadow(
        draw,
        (74, 205),
        main_label,
        label_font,
        red
    )

    draw_text_with_shadow(
        draw,
        (72, 245),
        main_range,
        time_font,
        white
    )

    # --------------------------------------------------------
    # DANACH
    # --------------------------------------------------------

    second_end = (
        second_start +
        timedelta(
            minutes=rift_data[
                "duration_minutes"
            ]
        )
    )

    draw_text_with_shadow(
        draw,
        (74, 345),
        "Danach",
        label_font,
        muted
    )

    draw_text_with_shadow(
        draw,
        (74, 386),
        format_time_range(
            second_start,
            second_end
        ),
        small_font,
        white
    )

    image = image.convert(
        "RGB"
    )

    image.save(
        RIFT_CARD_FILE,
        "PNG",
        optimize=True
    )


# ============================================================
# EMBEDS ERSTELLEN
# ============================================================

def build_embeds(data):
    timezone = ZoneInfo(
        data["timezone"]
    )

    rift_data = data[
        "rift"
    ]

    shugo_data = data[
        "shugo_games"
    ]

    # --------------------------------------------------------
    # RIFT
    # --------------------------------------------------------

    rift_times = build_rift_times(
        rift_data,
        timezone
    )

    rift_next = (
        rift_times[
            "next_start"
        ]
    )

    create_rift_card(
        rift_data,
        rift_times
    )

    # --------------------------------------------------------
    # SHUGO
    # --------------------------------------------------------

    (
        shugo_next,
        shugo_following
    ) = next_shugo_starts(
        shugo_data,
        timezone
    )

    # --------------------------------------------------------
    # RESETS
    # --------------------------------------------------------

    daily_reset = (
        next_daily_reset(
            data["resets"][
                "daily"
            ],
            timezone
        )
    )

    weekly_reset = (
        next_weekly_reset(
            data["resets"][
                "weekly_day"
            ],
            data["resets"][
                "weekly_time"
            ],
            timezone
        )
    )

    # --------------------------------------------------------
    # ALS NÄCHSTES
    # --------------------------------------------------------

    next_event = find_next_event(
        rift_next,
        shugo_next,
        daily_reset,
        weekly_reset
    )

    next_embed = {
        "title":
            "⚡ ALS NÄCHSTES",

        "description": (
            f"{next_event['icon']} "
            f"**{next_event['name']}** · "
            f"{discord_time(
                next_event['time']
            )}"
        ),

        "color":
            next_event["color"]
    }

    # --------------------------------------------------------
    # RIFT
    # --------------------------------------------------------

    rift_embed = {
        "color":
            14555706,

        "image": {
            "url":
                "attachment://spacetime_rift_card.png"
        }
    }

    # --------------------------------------------------------
    # SHUGO
    # --------------------------------------------------------

    next_rotation = (
        shugo_rotation_for_time(
            shugo_next,
            shugo_data
        )
    )

    following_rotation = (
        shugo_rotation_for_time(
            shugo_following,
            shugo_data
        )
    )

    next_games = "\n".join(
        f"• {game}"
        for game in next_rotation
    )

    following_games = "\n".join(
        f"• {game}"
        for game in following_rotation
    )

    shugo_embed = {
        "title":
            "🐹 SHUGO GAMES",

        "description":
            "Alle 30 Minuten",

        "fields": [
            {
                "name": (
                    f"🟣 KOMMEND · "
                    f"{shugo_next.strftime('%H:%M')} Uhr"
                ),

                "value":
                    next_games,

                "inline":
                    True
            },

            {
                "name": (
                    f"⚪ DANACH · "
                    f"{shugo_following.strftime('%H:%M')} Uhr"
                ),

                "value":
                    following_games,

                "inline":
                    True
            }
        ],

        "color":
            14058735
    }

    # --------------------------------------------------------
    # RESETS
    # --------------------------------------------------------

    reset_embed = {
        "title":
            "🔄 RESETS",

        "fields": [
            {
                "name":
                    "Daily Reset",

                "value": (
                    f"**"
                    f"{data['resets']['daily']} Uhr"
                    f"**"
                ),

                "inline":
                    False
            },

            {
                "name":
                    "Weekly Reset",

                "value": (
                    f"**"
                    f"{german_weekday(
                        weekly_reset
                    )} · "
                    f"{data['resets']['weekly_time']} Uhr"
                    f"**"
                ),

                "inline":
                    False
            }
        ],

        "color":
            6724044
    }

    return [
        next_embed,
        rift_embed,
        shugo_embed,
        reset_embed
    ]


# ============================================================
# MULTIPART DISCORD REQUEST
# ============================================================

def webhook_request_with_file(
    url,
    payload,
    file_path,
    method="POST"
):
    boundary = (
        "----AION2Boundary"
        + uuid.uuid4().hex
    )

    with open(
        file_path,
        "rb"
    ) as f:
        file_data = f.read()

    body = bytearray()

    body.extend(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; '
            f'name="payload_json"\r\n'
            f"Content-Type: application/json\r\n\r\n"
        ).encode("utf-8")
    )

    body.extend(
        json.dumps(
            payload
        ).encode("utf-8")
    )

    body.extend(
        b"\r\n"
    )

    body.extend(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; '
            f'name="files[0]"; '
            f'filename="{os.path.basename(file_path)}"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode("utf-8")
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
        ).encode("utf-8")
    )

    req = urllib.request.Request(
        url,
        data=bytes(body),
        method=method,
        headers={
            "Content-Type":
                f"multipart/form-data; "
                f"boundary={boundary}",

            "User-Agent":
                "AION2-Schedule-Bot"
        }
    )

    with urllib.request.urlopen(
        req,
        timeout=60
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
# HAUPTPROGRAMM
# ============================================================

def main():
    if not WEBHOOK_URL:
        raise RuntimeError(
            "AION_SCHEDULE_WEBHOOK fehlt."
        )

    data = load_data()
    state = load_state()

    embeds = build_embeds(
        data
    )

    payload = {
        "embeds":
            embeds,

        "attachments": [
            {
                "id":
                    0,

                "filename":
                    RIFT_CARD_FILE
            }
        ]
    }

    message_id = state.get(
        "message_id"
    )

    if message_id:

        edit_url = (
            f"{WEBHOOK_URL}"
            f"/messages/{message_id}"
        )

        webhook_request_with_file(
            edit_url,
            payload,
            RIFT_CARD_FILE,
            method="PATCH"
        )

        print(
            "Bestehende Veranstaltungs-"
            "Nachricht aktualisiert."
        )

    else:

        create_url = (
            f"{WEBHOOK_URL}"
            f"?wait=true"
        )

        result = (
            webhook_request_with_file(
                create_url,
                payload,
                RIFT_CARD_FILE,
                method="POST"
            )
        )

        save_state(
            {
                "message_id":
                    result["id"]
            }
        )

        print(
            "Neue Veranstaltungs-"
            "Nachricht erstellt."
        )


if __name__ == "__main__":
    main()
