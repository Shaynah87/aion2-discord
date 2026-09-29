
    
  
import os
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageFilter,
    ImageChops,
)


# ============================================================
# LAUNCH – DATEIEN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

EARLY_ACCESS_OUTPUT = BASE_DIR / "early_access_card.png"
GLOBAL_LAUNCH_OUTPUT = BASE_DIR / "global_launch_card.png"

# ============================================================
# KARTENFORMAT
# ============================================================

CARD_WIDTH = 1200
FULL_HEIGHT = 535
COMPACT_HEIGHT = 220


# ============================================================
# COUNTDOWN
# ============================================================

COUNTDOWN_DAYS_SIZE = 54
COUNTDOWN_NOCH_SIZE = 17
COUNTDOWN_NOCH_DAYS_GAP = 10

# Launch-Zeit (Europe/Berlin).
# Early Access und Global Launch nutzen 15:00 als Countdown-Ziel.
LAUNCH_HOUR = 15
LAUNCH_MINUTE = 0


# ============================================================
# GLOBAL – POSITION DES OBEREN BLOCKS
#
# GLOBAL bleibt exakt auf der bisherigen Position.
# ============================================================

GLOBAL_VISIBLE_TOP = 60


# ============================================================
# GLOBAL – GOLDENE TITELKANTE
# ============================================================

GLOBAL_GOLD_OUTLINE = (
    225,
    198,
    143,
    215,
)


# ============================================================
# EARLY ACCESS
# ============================================================

EARLY_TITLE_SIZE = 96
EARLY_TITLE_BOLD = True
EARLY_TITLE_TARGET_WIDTH = 625

EARLY_DATE_SIZE = 36
EARLY_NOCH_SIZE = COUNTDOWN_NOCH_SIZE
EARLY_COUNTDOWN_SIZE = COUNTDOWN_DAYS_SIZE


# ------------------------------------------------------------
# EARLY – ABSTÄNDE
# ------------------------------------------------------------

EARLY_GAP_TITLE_DIVIDER = 28
EARLY_GAP_DIVIDER_DATE = 28


# ============================================================
# EARLY – TITEL
# ============================================================

EARLY_TITLE_SHADOW_OFFSET_X = 2
EARLY_TITLE_SHADOW_OFFSET_Y = 4
EARLY_TITLE_SHADOW_BLUR = 3.2

EARLY_TITLE_SHADOW = (
    4,
    8,
    13,
    195,
)

EARLY_TITLE_GLOW_BLUR = 3.2

EARLY_TITLE_GLOW = (
    250,
    235,
    202,
    40,
)


# ------------------------------------------------------------
# EARLY – WEISSE LESEKANTE
#
# Nur EARLY ACCESS.
# ------------------------------------------------------------

EARLY_READABILITY_OUTLINE = (
    255,
    255,
    255,
    115,
)

