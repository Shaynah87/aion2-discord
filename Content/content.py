"""AION 2 Content: bestehende Discord-Nachrichten aktualisieren."""
import json
import os
import importlib.util
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "content_data.json"
MESSAGE_STATE_FILE = BASE_DIR / "content_message.json"
LAUNCH_FILE = BASE_DIR / "Launch" / "launch.py"
WEBHOOK_URL = os.environ.get("CONTENT_WEBHOOK")


def load_json(filename, default=None):
    try:
        with open(filename, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {} if default is None else default


def load_launch_module():
    if not LAUNCH_FILE.exists():
        raise RuntimeError(f"Launch-Modul fehlt: {LAUNCH_FILE}")
    spec = importlib.util.spec_from_file_location("nyerk24_launch", LAUNCH_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Launch-Modul konnte nicht geladen werden.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LAUNCH = load_launch_module()


def load_message_state():

    state = load_json(
        MESSAGE_STATE_FILE,
        {},
    )

    if not isinstance(state, dict):

        return {}

    return state


def save_message_state(state):

    with open(
        MESSAGE_STATE_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            state,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")


def webhook_wait_url():

    if not WEBHOOK_URL:

        raise RuntimeError(
            "GitHub Secret CONTENT_WEBHOOK fehlt."
        )

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


def discord_message_url(message_id):

    if not WEBHOOK_URL:

        raise RuntimeError(
            "GitHub Secret CONTENT_WEBHOOK fehlt."
        )

    base_url = WEBHOOK_URL.split(
        "?",
        1,
    )[0]

    return (
        f"{base_url}/messages/{message_id}"
    )


def build_discord_image_payload(
    discord_filename,
):

    return {
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


def post_discord_image(
    image_file,
    discord_filename,
):

    payload = build_discord_image_payload(
        discord_filename
    )

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

    return str(message_id)


def patch_discord_image(
    message_id,
    image_file,
    discord_filename,
):

    payload = build_discord_image_payload(
        discord_filename
    )

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
            discord_message_url(
                message_id
            ),
            data={
                "payload_json":
                    json.dumps(payload)
            },
            files=files,
            timeout=30,
        )

    if response.status_code == 404:

        return False

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

    return True


def update_or_create_discord_image(
    state,
    state_key,
    image_file,
    discord_filename,
    label,
):

    message_id = state.get(
        state_key
    )

    if message_id:

        print(
            f"{label} wird aktualisiert ..."
        )

        updated = patch_discord_image(
            message_id,
            image_file,
            discord_filename,
        )

        if updated:

            print(
                f"{label} aktualisiert. "
                f"Message-ID: {message_id}"
            )

            return False

        print(
            f"{label}: gespeicherte "
            "Discord-Nachricht wurde nicht "
            "gefunden. Sie wird neu erstellt."
        )

    else:

        print(
            f"{label}: noch keine "
            "Message-ID gespeichert. "
            "Nachricht wird erstellt ..."
        )

    new_message_id = post_discord_image(
        image_file,
        discord_filename,
    )

    state[state_key] = new_message_id

    print(
        f"{label} erstellt. "
        f"Message-ID: {new_message_id}"
    )

    return True



def update_one_milestone(milestone):
    filename = LAUNCH.save_milestone_card(milestone)
    state = load_message_state()
    key = milestone["key"]
    changed = update_or_create_discord_image(
        state=state,
        state_key=f"{key}_message_id",
        image_file=filename,
        discord_filename=f"{key}.png",
        label=milestone["title"],
    )
    if changed:
        save_message_state(state)


def should_update(milestone, mode, now, timezone_name):
    target = LAUNCH.parse_launch_datetime(milestone["date"], timezone_name)
    remaining = (target - now).total_seconds()
    # Normaler Content-Job bleibt unabhängig vom Countdown aktiv.
    if mode == "daily":
        return True
    # Ein verspäteter Lauf darf das endgültige GESTARTET nicht verpassen.
    # Nach dem Start übernimmt der reguläre tägliche Content-Job.
    if remaining <= 0:
        return mode == "minute" and remaining > -120
    if mode == "quarter":
        return 3600 < remaining <= 86400
    if mode == "minute":
        return remaining <= 3600
    raise ValueError(f"Unbekannter CONTENT_MODE: {mode}")


def main():
    data = load_json(DATA_FILE)
    if not data:
        raise RuntimeError("content_data.json ist leer oder fehlt.")
    mode = os.environ.get("CONTENT_MODE", "daily").strip().lower()
    if mode not in ("daily", "quarter", "minute"):
        raise ValueError(f"Ungültiger CONTENT_MODE: {mode}")
    timezone_name = data.get("timezone", "Europe/Berlin")
    now = datetime.now(ZoneInfo(timezone_name))
    content_state = LAUNCH.build_content_state(data)
    milestones = {m["key"]: m for m in content_state["milestones"]}
    for key in ("early_access", "global_launch"):
        if key not in milestones:
            raise RuntimeError(f"Milestone fehlt in content_data.json: {key}")
    for key in ("early_access", "global_launch"):
        milestone = milestones[key]
        if should_update(milestone, mode, now, timezone_name):
            print(f"{mode}: {milestone['title']} – {milestone['status_text']}")
            update_one_milestone(milestone)
        else:
            print(f"{mode}: {milestone['title']} – außerhalb des Zeitfensters")


if __name__ == "__main__":
    main()
