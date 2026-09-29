
    
  
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

