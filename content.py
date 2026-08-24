import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo


# ============================================================
# DATEIEN / EINSTELLUNGEN
# ============================================================

DATA_FILE = "content_data.json"
MESSAGE_FILE = "content_message.json"

WEBHOOK_URL = os.environ.get("CONTENT_WEBHOOK")


# ============================================================
# DATEN LADEN
# ============================================================

def load_json(filename, default=None):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return default if default is not None else {}


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


# ============================================================
# ZEIT / COUNTDOWN
# ============================================================

def get_now(timezone_name):
    timezone = ZoneInfo(timezone_name)
    return datetime.now(timezone)


def parse_date(date_string, timezone_name):
    timezone = ZoneInfo(timezone_name)

    return datetime.strptime(
        date_string,
        "%Y-%m-%d"
    ).replace(tzinfo=timezone)


def get_milestone_status(milestone, now, timezone_name):
    target = parse_date(
        milestone["date"],
        timezone_name
    )

    difference = target.date() - now.date()
    days = difference.days

    if days > 1:
        return {
            "state": "countdown",
            "text": f"Noch {days} Tage"
        }

    if days == 1:
        return {
            "state": "countdown",
            "text": "Noch 1 Tag"
        }

    if days == 0:
        return {
            "state": "today",
            "text": "HEUTE"
        }

    return {
        "state": "started",
        "text": "GESTARTET"
    }


# ============================================================
# CONTENT AUFBEREITEN
# ============================================================

def build_content_state(data):
    timezone_name = data.get(
        "timezone",
        "Europe/Berlin"
    )

    now = get_now(timezone_name)

    result = {
        "updated_at": now.isoformat(),
        "milestones": [],
        "active_content": None
    }

    for milestone in data.get("milestones", []):
        status = get_milestone_status(
            milestone,
            now,
            timezone_name
        )

        result["milestones"].append({
            "key": milestone["key"],
            "title": milestone["title"],
            "date": milestone["date"],
            "date_display": milestone["date_display"],
            "background": milestone.get("background"),
            "state": status["state"],
            "status_text": status["text"]
        })

    active_phases = []

    for phase in data.get("content_phases", []):
        if not phase.get("enabled", False):
            continue

        start = parse_date(
            phase["start_date"],
            timezone_name
        )

        if start.date() <= now.date():
            active_phases.append(
                (
                    start,
                    phase
                )
            )

    if active_phases:
        active_phases.sort(
            key=lambda item: item[0]
        )

        result["active_content"] = active_phases[-1][1]

    return result


# ============================================================
# TESTAUSGABE
# ============================================================

def print_status(content_state):
    print("")
    print("========================================")
    print("AION 2 CONTENT")
    print("========================================")

    for milestone in content_state["milestones"]:
        print("")
        print(milestone["title"])
        print(milestone["date_display"])
        print(milestone["status_text"])

    active_content = content_state.get(
        "active_content"
    )

    if active_content:
        print("")
        print("----------------------------------------")
        print("AKTUELLER CONTENT")
        print(active_content.get("title", ""))
        print("----------------------------------------")

    print("")
    print("========================================")


# ============================================================
# HAUPTPROGRAMM
# ============================================================

def main():
    data = load_json(
        DATA_FILE,
        {}
    )

    if not data:
        raise RuntimeError(
            "content_data.json ist leer oder fehlt."
        )

    content_state = build_content_state(
        data
    )

    print_status(
        content_state
    )

    # Discord-Ausgabe kommt im nächsten Schritt.
    #
    # Erst legen wir gemeinsam das Design der beiden Karten
    # EARLY ACCESS und GLOBAL LAUNCH fest.
    #
    # Danach bekommt dieser Teil:
    # - Bildgenerierung
    # - Discord Webhook
    # - bestehende Nachricht bearbeiten
    # - automatische kompakte Darstellung nach dem Start
    # - spätere Seasons / Chapters


if __name__ == "__main__":
    main()
