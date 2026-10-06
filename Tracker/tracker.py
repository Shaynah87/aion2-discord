
    
  

import os
import json
import urllib.request
import urllib.error
import time
import uuid
from io import BytesIO
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


WEBHOOK_URL = os.environ.get("TRACKER_WEBHOOK")

BASE_DIR = Path(__file__).resolve().parent

DATA_FILE = BASE_DIR / "tracker_data.json"
STATE_FILE = BASE_DIR / "tracker_message.json"


# ============================================================
# NETZWERK / RETRY
# ============================================================

MAX_NETWORK_ATTEMPTS = 3
RETRY_DELAYS = (5, 15)



# ============================================================
# ANZEIGENAMEN
# ============================================================

DISPLAY_NAMES = {
    "overview_card": "ÜBERSICHT",
    "rift": "Spacetime Rift",
    "rift_card": "SPACETIME RIFT",
    "shugo": "Shugofesta",
    "shugo_card": "SHUGOFESTA",
    "daily_reset": "Täglicher Reset",
    "weekly_reset": "Wöchentlicher Reset",
    "reset_card": "RESETS",
    "daily_card": "TÄGLICH",
    "weekly_card": "WÖCHENTLICH",
}


# ============================================================
# HINTERGRUNDBILDER
# ============================================================

OVERVIEW_BACKGROUND_URL = (
    "https://raw.githubusercontent.com/"
    "Shaynah87/aion2-discord/main/Tracker/event_overview.png"
)

RIFT_BACKGROUND_URL = (
    "https://raw.githubusercontent.com/"
    "Shaynah87/aion2-discord/main/Tracker/spacetime_rift.png"
)

SHUGO_BACKGROUND_URL = (
    "https://raw.githubusercontent.com/"
    "Shaynah87/aion2-discord/main/Tracker/shugo_games.png"
)

RESET_BACKGROUND_URL = (
    "https://raw.githubusercontent.com/"
    "Shaynah87/aion2-discord/main/Tracker/resets.png"
)


# ============================================================
# AUSGABEDATEIEN
# ============================================================

OVERVIEW_CARD_FILE = BASE_DIR / "event_overview_card.png"
RIFT_CARD_FILE = BASE_DIR / "spacetime_rift_card.png"
SHUGO_CARD_FILE = BASE_DIR / "shugo_games_card.png"
RESET_CARD_FILE = BASE_DIR / "resets_card.png"


# ============================================================
# GEMEINSAMES VISUELLES RASTER
#
# 20 px = gehört optisch zusammen
# 56 px = neuer eigenständiger Abschnitt
# ============================================================

CLOSE_GAP = 20
SECTION_GAP = 56

ACTIVE_EVENT_GAP = 34
NEXT_ENTRY_GAP = 18



# ============================================================
# ÜBERSICHT
# ============================================================

MAX_OVERVIEW_EVENTS = 5
RESET_OVERVIEW_LEAD_HOURS = 3


# ============================================================
# EVENT-FARBEN
# ============================================================

RIFT_COLOR = (255, 78, 88, 255)
SHUGO_COLOR = (229, 177, 62, 255)
RESET_COLOR = (64, 145, 255, 255)


# ============================================================
# DATEIEN
# ============================================================

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    try:

