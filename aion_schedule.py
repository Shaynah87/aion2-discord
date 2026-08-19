import os
import json
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


WEBHOOK_URL = os.environ.get("AION_SCHEDULE_WEBHOOK")

DATA_FILE = "schedule_data.json"
STATE_FILE = "schedule_message.json"


# ------------------------------------------------------------
# DATEIEN LADEN / SPEICHERN
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
# NÄCHSTE TÄGLICHE UHRZEIT
# ------------------------------------------------------------

def next_time_today_or_tomorrow(
    time_string,
    timezone
):
    hour, minute = map(
        int,
        time_string.split(":")
    )

    now = datetime.now(timezone)

    candidate = now.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0
    )

    if candidate <= now:
        candidate += timedelta(days=1)

    return candidate


# ------------------------------------------------------------
# NÄCHSTER WOCHENTERMIN
# ------------------------------------------------------------

def next_weekly_time(
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

    target_weekday = weekdays[day_name]

    hour, minute = map(
        int,
        time_string.split(":")
    )

    now = datetime.now(timezone)

    days_ahead = (
        target_weekday - now.weekday()
    ) % 7

    candidate = (
        now + timedelta(days=days_ahead)
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
# DEUTSCHE WOCHENTAGE
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# UHRZEIT FÜR "ALS NÄCHSTES"
# ------------------------------------------------------------

def format_next_event_time(
    dt,
    now
):
    if dt.date() == now.date():
        return (
            f"Heute · "
            f"{dt.strftime('%H:%M')} Uhr"
        )

    if dt.date() == (
        now + timedelta(days=1)
    ).date():
        return (
            f"Morgen · "
            f"{dt.strftime('%H:%M')} Uhr"
        )

    return (
        f"{german_weekday(dt)} · "
        f"{dt.strftime('%H:%M')} Uhr"
    )


# ------------------------------------------------------------
# EMBED ERSTELLEN
# ------------------------------------------------------------

def build_embed(data):
    timezone = ZoneInfo(
        data["timezone"]
    )

    now = datetime.now(timezone)

    upcoming = []

    # --------------------------------------------------------
    # SPACE RIFTS
    # --------------------------------------------------------

    rift_lines = []

    for rift in data.get(
        "rifts",
        []
    ):
        rift_times = rift.get(
            "times",
            []
        )

        if not rift_times:
            continue

        for time_string in rift_times:
            next_rift_time = (
                next_time_today_or_tomorrow(
                    time_string,
                    timezone
                )
            )

            upcoming.append(
                (
                    next_rift_time,
                    "🌀",
                    rift["name"]
                )
            )

        formatted_times = " / ".join(
            rift_times
        )

        rift_lines.append(
            f"**{rift['name']}** · "
            f"{formatted_times}"
        )


    # --------------------------------------------------------
    # SHUGO GAMES
    # --------------------------------------------------------

    shugo_lines = []

    for game in data.get(
        "shugo_games",
        []
    ):
        game_time = (
            next_time_today_or_tomorrow(
                game["time"],
                timezone
            )
        )

        upcoming.append(
            (
                game_time,
                "🐹",
                game["name"]
            )
        )

        shugo_lines.append(
            f"**{game['name']}** · "
            f"{game['time']}"
        )


    # --------------------------------------------------------
    # DAILY RESET
    # --------------------------------------------------------

    daily_reset = (
        next_time_today_or_tomorrow(
            data["resets"]["daily"],
            timezone
        )
    )

    upcoming.append(
        (
            daily_reset,
            "🔄",
            "Daily Reset"
        )
    )


    # --------------------------------------------------------
    # WEEKLY RESET
    # --------------------------------------------------------

    weekly_reset = (
        next_weekly_time(
            data["resets"]["weekly_day"],
            data["resets"]["weekly_time"],
            timezone
        )
    )

    upcoming.append(
        (
            weekly_reset,
            "🔄",
            "Weekly Reset"
        )
    )


    # --------------------------------------------------------
    # NÄCHSTES EREIGNIS
    # --------------------------------------------------------

    upcoming.sort(
        key=lambda item: item[0]
    )

    (
        next_event_time,
        next_event_icon,
        next_event_name
    ) = upcoming[0]


    # --------------------------------------------------------
    # FELDER
    # --------------------------------------------------------

    fields = [
        {
            "name": "⚡ ALS NÄCHSTES",
            "value": (
                f"{next_event_icon} "
                f"**{next_event_name}** — "
                f"{format_next_event_time(
                    next_event_time,
                    now
                )}"
            ),
            "inline": False
        }
    ]


    # --------------------------------------------------------
    # RIFTS
    # --------------------------------------------------------

    if rift_lines:
        fields.append(
            {
                "name": "🌀 SPACE RIFTS",
                "value": "\n".join(
                    rift_lines
                ),
                "inline": False
            }
        )


    # --------------------------------------------------------
    # SHUGO
    # --------------------------------------------------------

    if shugo_lines:
        fields.append(
            {
                "name": "🐹 SHUGO GAMES",
                "value": "\n".join(
                    shugo_lines
                ),
                "inline": False
            }
        )


    # --------------------------------------------------------
    # RESETS
    # --------------------------------------------------------

    fields.append(
        {
            "name": "🔄 RESETS",
            "value": (
                f"**Daily Reset** · "
                f"{data['resets']['daily']}\n"
                f"**Weekly Reset** · "
                f"{german_weekday(weekly_reset)} "
                f"{data['resets']['weekly_time']}"
            ),
            "inline": False
        }
    )


    # --------------------------------------------------------
    # EMBED
    # --------------------------------------------------------

    embed = {
        "title": "AION 2 · Veranstaltungszentrale",

        "description": (
            "Alle regelmäßigen Zeiten "
            "auf einen Blick."
        ),

        "color": 10181046,

        "fields": fields,

        "footer": {
            "text": "Automatisch aktualisiert"
        }
    }

    return embed


# ------------------------------------------------------------
# DISCORD WEBHOOK
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

        response_data = response.read()

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

    embed = build_embed(data)

    message_id = state.get(
        "message_id"
    )


    # --------------------------------------------------------
    # BESTEHENDE NACHRICHT AKTUALISIEREN
    # --------------------------------------------------------

    if message_id:
        edit_url = (
            f"{WEBHOOK_URL}"
            f"/messages/{message_id}"
        )

        webhook_request(
            edit_url,
            {
                "embeds": [
                    embed
                ]
            },
            method="PATCH"
        )

        print(
            "Bestehende Fahrplan-Nachricht "
            "aktualisiert."
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
                "embeds": [
                    embed
                ]
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
            "Neue Fahrplan-Nachricht "
            "erstellt."
        )


if __name__ == "__main__":
    main()
