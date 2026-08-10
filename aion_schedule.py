import os
import json
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


WEBHOOK_URL = os.environ.get("AION_SCHEDULE_WEBHOOK")
DATA_FILE = "schedule_data.json"
STATE_FILE = "schedule_message.json"


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_state(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def discord_timestamp(dt):
    unix = int(dt.timestamp())
    return f"<t:{unix}:t> · <t:{unix}:R>"


def next_time_today_or_tomorrow(time_string, timezone):
    hour, minute = map(int, time_string.split(":"))
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


def build_embed(data):
    timezone = ZoneInfo(data["timezone"])
    now = datetime.now(timezone)

    upcoming = []

    # Rifts
    rift_lines = []
    for rift in data.get("rifts", []):
        next_times = [
            next_time_today_or_tomorrow(t, timezone)
            for t in rift.get("times", [])
        ]

        if not next_times:
            continue

        next_rift_time = min(next_times)
        upcoming.append(
            (next_rift_time, "🌀", rift["name"])
        )

        rift_lines.append(
            f"**{rift['name']}** — {discord_timestamp(next_rift_time)}"
        )

    # Shugo Games
    shugo_lines = []
    for game in data.get("shugo_games", []):
        game_time = next_time_today_or_tomorrow(
            game["time"],
            timezone
        )

        upcoming.append(
            (game_time, "🐹", game["name"])
        )

        shugo_lines.append(
            f"**{game['name']}** — {discord_timestamp(game_time)}"
        )

    # Daily Reset
    daily_reset = next_time_today_or_tomorrow(
        data["resets"]["daily"],
        timezone
    )

    upcoming.append(
        (daily_reset, "🔄", "Daily Reset")
    )

    upcoming.sort(key=lambda x: x[0])

    next_event_time, next_event_icon, next_event_name = upcoming[0]

    fields = [
        {
            "name": "⚡ ALS NÄCHSTES",
            "value": (
                f"{next_event_icon} **{next_event_name}**\n"
                f"{discord_timestamp(next_event_time)}"
            ),
            "inline": False
        }
    ]

    if rift_lines:
        fields.append({
            "name": "🌀 SPACE RIFTS",
            "value": "\n".join(rift_lines),
            "inline": False
        })

    if shugo_lines:
        fields.append({
            "name": "🐹 SHUGO GAMES",
            "value": "\n".join(shugo_lines),
            "inline": False
        })

    fields.append({
        "name": "🔄 RESETS",
        "value": (
            f"**Daily Reset** — {discord_timestamp(daily_reset)}\n"
            f"**Weekly Reset** — {data['resets']['weekly_day']} "
            f"{data['resets']['weekly_time']}"
        ),
        "inline": False
    })

    embed = {
        "title": "AION 2 · Fahrplan",
        "description": "Alles Wichtige auf einen Blick.",
        "color": 3447003,
        "fields": fields,
        "footer": {
            "text": "Automatisch aktualisiert"
        },
        "timestamp": now.isoformat()
    }

    return embed


def webhook_request(url, payload, method="POST"):
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "AION2-Schedule-Bot"
        }
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    if not WEBHOOK_URL:
        raise RuntimeError("AION_SCHEDULE_WEBHOOK fehlt.")

    data = load_data()
    state = load_state()
    embed = build_embed(data)

    message_id = state.get("message_id")

    if message_id:
        edit_url = f"{WEBHOOK_URL}/messages/{message_id}"

        webhook_request(
            edit_url,
            {
                "embeds": [embed]
            },
            method="PATCH"
        )

        print("Bestehende Fahrplan-Nachricht aktualisiert.")

    else:
        create_url = f"{WEBHOOK_URL}?wait=true"

        result = webhook_request(
            create_url,
            {
                "embeds": [embed]
            },
            method="POST"
        )

        save_state({
            "message_id": result["id"]
        })

        print("Neue Fahrplan-Nachricht erstellt.")


if __name__ == "__main__":
    main()
