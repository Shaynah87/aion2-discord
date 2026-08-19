import os
import json
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


WEBHOOK_URL = os.environ.get("AION_SCHEDULE_WEBHOOK")

DATA_FILE = "schedule_data.json"
STATE_FILE = "schedule_message.json"


# ------------------------------------------------------------
# DATEIEN
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# ALLGEMEINE ZEITFUNKTIONEN
# ------------------------------------------------------------

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

    return weekdays[dt.weekday()]


def format_day_time(
    dt,
    now
):
    if dt.date() == now.date():
        return (
            f"Heute · "
            f"{dt.strftime('%H:%M')} Uhr"
        )

    tomorrow = (
        now + timedelta(days=1)
    ).date()

    if dt.date() == tomorrow:
        return (
            f"Morgen · "
            f"{dt.strftime('%H:%M')} Uhr"
        )

    return (
        f"{german_weekday(dt)} · "
        f"{dt.strftime('%H:%M')} Uhr"
    )


def format_time_range(
    start,
    end
):
    return (
        f"{start.strftime('%H:%M')} – "
        f"{end.strftime('%H:%M')} Uhr"
    )


# ------------------------------------------------------------
# DAILY RESET
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# WEEKLY RESET
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# SPACETIME RIFT
# ------------------------------------------------------------

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
        hours=rift_data["interval_hours"]
    )

    duration = timedelta(
        minutes=rift_data[
            "duration_minutes"
        ]
    )

    entry_duration = timedelta(
        minutes=rift_data[
            "entry_minutes"
        ]
    )

    # Genügend Termine von gestern bis morgen erzeugen.
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
    active_entry_end = None

    next_start = None
    following_start = None


    # Prüfen, ob aktuell ein Rift aktiv ist.
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

            active_entry_end = (
                start_time +
                entry_duration
            )

            break


    # Nächsten und übernächsten Start suchen.
    future_starts = [
        start_time
        for start_time in starts
        if start_time > now
    ]

    future_starts.sort()

    if future_starts:
        next_start = future_starts[0]

    if len(future_starts) > 1:
        following_start = future_starts[1]


    return {
        "active_start":
            active_start,

        "active_end":
            active_end,

        "active_entry_end":
            active_entry_end,

        "next_start":
            next_start,

        "following_start":
            following_start,

        "duration":
            duration,

        "entry_duration":
            entry_duration
    }


# ------------------------------------------------------------
# SHUGO GAMES
# ------------------------------------------------------------

def next_shugo_starts(
    shugo_data,
    timezone
):
    now = datetime.now(timezone)

    candidates = []

    # Heute und morgen prüfen.
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

    next_start = candidates[0]
    following_start = candidates[1]

    return (
        next_start,
        following_start
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


# ------------------------------------------------------------
# "ALS NÄCHSTES"
# ------------------------------------------------------------

def find_next_event(
    rift_next,
    shugo_next,
    daily_reset,
    weekly_reset
):
    events = [
        (
            rift_next,
            "🌀",
            "Spacetime Rift"
        ),

        (
            shugo_next,
            "🐹",
            "Shugo Games"
        ),

        (
            daily_reset,
            "🔄",
            "Daily Reset"
        ),

        (
            weekly_reset,
            "🔄",
            "Weekly Reset"
        )
    ]

    events.sort(
        key=lambda item: item[0]
    )

    return events[0]


# ------------------------------------------------------------
# DISCORD EMBEDS
# ------------------------------------------------------------

def build_embeds(data):
    timezone = ZoneInfo(
        data["timezone"]
    )

    now = datetime.now(timezone)

    rift_data = data["rift"]
    shugo_data = data["shugo_games"]


    # --------------------------------------------------------
    # RIFT BERECHNEN
    # --------------------------------------------------------

    rift_times = build_rift_times(
        rift_data,
        timezone
    )

    rift_next = rift_times[
        "next_start"
    ]

    rift_following = rift_times[
        "following_start"
    ]


    # --------------------------------------------------------
    # SHUGO BERECHNEN
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

    daily_reset = next_daily_reset(
        data["resets"]["daily"],
        timezone
    )

    weekly_reset = next_weekly_reset(
        data["resets"]["weekly_day"],
        data["resets"]["weekly_time"],
        timezone
    )


    # --------------------------------------------------------
    # GLOBAL NÄCHSTES EVENT
    # --------------------------------------------------------

    (
        next_event_time,
        next_event_icon,
        next_event_name
    ) = find_next_event(
        rift_next,
        shugo_next,
        daily_reset,
        weekly_reset
    )


    # ========================================================
    # EMBED 1
    # ALS NÄCHSTES
    # ========================================================

    next_embed = {
        "title": "⚡ ALS NÄCHSTES",

        "description": (
            f"{next_event_icon} "
            f"**{next_event_name}**\n"
            f"{format_day_time(
                next_event_time,
                now
            )}"
        ),

        "color": 10181046
    }


    # ========================================================
    # EMBED 2
    # SPACETIME RIFT
    # ========================================================

    if rift_times["active_start"]:

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

        entry_end = (
            rift_times[
                "active_entry_end"
            ]
        )

        if now < entry_end:
            rift_status = (
                "🟢 **RIFT AKTIV**\n"
                f"{format_time_range(
                    active_start,
                    active_end
                )}\n"
                f"⚠️ Eintritt nur bis "
                f"{entry_end.strftime('%H:%M')} Uhr"
            )

        else:
            rift_status = (
                "🟢 **RIFT AKTIV**\n"
                f"{format_time_range(
                    active_start,
                    active_end
                )}\n"
                "🔒 Eintritt bereits geschlossen"
            )

    else:
        next_end = (
            rift_next +
            timedelta(
                minutes=rift_data[
                    "duration_minutes"
                ]
            )
        )

        next_entry_end = (
            rift_next +
            timedelta(
                minutes=rift_data[
                    "entry_minutes"
                ]
            )
        )

        rift_status = (
            "🔮 **NÄCHSTER RIFT**\n"
            f"{format_time_range(
                rift_next,
                next_end
            )}\n"
            f"⚠️ Eintritt nur bis "
            f"{next_entry_end.strftime('%H:%M')} Uhr"
        )


    following_end = (
        rift_following +
        timedelta(
            minutes=rift_data[
                "duration_minutes"
            ]
        )
    )

    rift_embed = {
        "title": "🌀 SPACETIME RIFT",

        "description": (
            f"{rift_status}\n\n"
            f"**Danach**\n"
            f"{format_time_range(
                rift_following,
                following_end
            )}\n\n"
            f"Alle "
            f"{rift_data['interval_hours']} Stunden "
            f"· Aufenthalt bis zu "
            f"{rift_data['duration_minutes'] // 60} Stunde\n"
            f"⚠️ Eintritt nur in den ersten "
            f"{rift_data['entry_minutes']} Minuten"
        ),

        "color": 5793266
    }


    # ========================================================
    # EMBED 3
    # SHUGO GAMES
    # ========================================================

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
        "title": "🐹 SHUGO GAMES",

        "description": (
            "Alle 30 Minuten · Starts um "
            "**:15** und **:45**"
        ),

        "fields": [
            {
                "name": (
                    f"🟣 KOMMEND · "
                    f"{shugo_next.strftime('%H:%M')} Uhr"
                ),

                "value": next_games,

                "inline": True
            },

            {
                "name": (
                    f"⚪ DANACH · "
                    f"{shugo_following.strftime('%H:%M')} Uhr"
                ),

                "value": following_games,

                "inline": True
            }
        ],

        "color": 14058735
    }


    # ========================================================
    # EMBED 4
    # RESETS
    # ========================================================

    reset_embed = {
        "title": "🔄 RESETS",

        "fields": [
            {
                "name": "Daily Reset",

                "value": (
                    f"**{data['resets']['daily']} Uhr**"
                ),

                "inline": True
            },

            {
                "name": "Weekly Reset",

                "value": (
                    f"**{german_weekday(
                        weekly_reset
                    )} · "
                    f"{data['resets']['weekly_time']} Uhr**"
                ),

                "inline": True
            }
        ],

        "color": 6724044
    }


    return [
        next_embed,
        rift_embed,
        shugo_embed,
        reset_embed
    ]


# ------------------------------------------------------------
# DISCORD
# ------------------------------------------------------------

def webhook_request(
    url,
    payload,
    method="POST"
):
    request_data = json.dumps(
        payload
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=request_data,
        method=method,
        headers={
            "Content-Type":
                "application/json",

            "User-Agent":
                "AION2-Schedule-Bot"
        }
    )

    with urllib.request.urlopen(
        req,
        timeout=30
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


# ------------------------------------------------------------
# HAUPTPROGRAMM
# ------------------------------------------------------------

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

    message_id = state.get(
        "message_id"
    )


    # --------------------------------------------------------
    # VORHANDENE NACHRICHT BEARBEITEN
    # --------------------------------------------------------

    if message_id:

        edit_url = (
            f"{WEBHOOK_URL}"
            f"/messages/{message_id}"
        )

        webhook_request(
            edit_url,
            {
                "embeds": embeds
            },
            method="PATCH"
        )

        print(
            "Bestehende Veranstaltungs-"
            "Nachricht aktualisiert."
        )


    # --------------------------------------------------------
    # NEUE NACHRICHT ERSTELLEN
    # --------------------------------------------------------

    else:

        create_url = (
            f"{WEBHOOK_URL}"
            f"?wait=true"
        )

        result = webhook_request(
            create_url,
            {
                "embeds": embeds
            },
            method="POST"
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
