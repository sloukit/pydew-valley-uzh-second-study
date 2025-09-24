import os
import sys
from typing import Final, Tuple, Dict, List, Union, TypeAlias

import pygame  # noqa
import pytmx  # type: ignore [import-untyped]

from src.enums import Map
from src.import_checks import *  # noqa: F403

Coordinate: TypeAlias = tuple[int | float, int | float]
SoundDict: TypeAlias = dict[str, pygame.mixer.Sound]
MapDict: TypeAlias = dict[str, pytmx.TiledMap]
AniFrames: TypeAlias = dict[str, list[pygame.Surface]]
GogglesStatus: TypeAlias = bool | None
NecklaceStatus: TypeAlias = bool | None
HatStatus: TypeAlias = bool | None
HornStatus: TypeAlias = bool | None
OutgroupSkinStatus: TypeAlias = bool | None

SCREEN_WIDTH: Final[int] = 1280
SCREEN_HEIGHT: Final[int] = 720
VOLCANO_SIZE: Final[int] = 500
TILE_SIZE: Final[int] = 16
CHAR_TILE_SIZE: Final[int] = 48
SCALE_FACTOR: Final[int] = 4
SCALED_TILE_SIZE: Final[int] = TILE_SIZE * SCALE_FACTOR

RANDOM_SEED: Final[int] = 123456789

# may possibly change, not marked as final
GAME_MAP: TypeAlias = Map.NEW_FARM

ENABLE_NPCS: Final[bool] = True
TEST_ANIMALS: Final[bool] = True

GAME_LANGUAGE: Final[str] = os.environ.get("GAME_LANGUAGE", "en")


DEBUG_MODE_VERSION: Final[bool] = False
# True  => virtual game time
# False => real world time
USE_GAME_TIME: Final[bool] = False
# number of seconds per in game minute (reference - in Stardew Valley each minute is 0.7 seconds)
# change to e.g. 0.1 for debug to speed-up day/night cycle
SECONDS_PER_GAME_MINUTE: Final[float] = 0.7
# should be 1.0 - increase x10 for debug to speed-up round end
WORLD_TIME_MULTIPLIER: Final[float] = 1.0
# USE_SERVER = False
# changes a few lines later, not marked as final
USE_SERVER = True

# position is normally only logged after movement and when the character stands still
# this is the minimum accumulated moving time to trigger logging for this scenario, to reduce server load
POS_MIN_LOG_INTERVAL: Final[float] = 1
# if a player moves for a long time continuously, we log the position during movement
POS_MOVE_LOG_INTERVAL: Final[float] = 15
# tool log interval after n accumulative uses of all tools and seeds, the statistics are sent to the server
TOOLS_LOG_INTERVAL: Final[float] = 5

IS_WEB = sys.platform in ("emscripten", "wasm")
# for now, in web mode, do not use dummy server (which requires `requests` module not available via pygbag)
if not IS_WEB:
    # If we're running locally, set this via environment variable:
    if os.getenv("USE_SERVER") == "true":
        USE_SERVER = True
    else:
        USE_SERVER = False


# NOTE(larsbutler): Don't change this line at all.
# WEB_SERVER_URL is populated during build,
# and build scripts expect this value exactly
# so we can populate it with the actual server URL
# at deploy time.
WEB_SERVER_URL: Final[str] = "WEB_SERVER_URL_PLACEHOLDER"
if IS_WEB:
    # For the web distribution, this should be replaced during
    # build time.
    SERVER_URL = WEB_SERVER_URL
else:
    SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.0:8888")
    # SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8001")

SETUP_PATHFINDING = any((ENABLE_NPCS, TEST_ANIMALS))

EMOTE_SIZE: Final[int] = 48

SAM_BORDER_SIZE: Final[Tuple[int, int]] = (
    122,
    131,
)  # absolute size of the border around self-assessment manikins

SIA_BORDER_SIZE: Final[Tuple[int, int]] = (
    122,
    131,
)

GROW_SPEED: Final[Dict[str, float]] = {
    "corn": 1.40,
    "tomato": 1.40,
    "beetroot": 1.40,
    "carrot": 1.40,
    "eggplant": 1.40,
    "pumpkin": 1.40,
    "parsnip": 1.40,
}

BASE_ALLOWED_CROPS: Final[List[str]] = [
    "wood",
    "apple",
    "blackberry",
    "blueberry",
    "raspberry",
    "orange",
    "peach",
    "pear",
]

# Overlays
OVERLAY_POSITIONS: Final[Dict[str, Tuple[Union[int, float], Union[int, float]]]] = {
    "tool": (86, 150),
    "seed": (47, 141),
    "money": (115, 205),
    "box_info_label": (15, SCREEN_HEIGHT - 100),
    "box_info": (150, 90),
    "clock": (SCREEN_WIDTH - 10, 10),
    "FPS": (SCREEN_WIDTH - 10, SCREEN_HEIGHT - 5),
    "display_error": (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2),
    "dead_npcs_box": (15, SCREEN_HEIGHT - 60),
}
BLUR_FACTOR: Final[int] = 4 # blur overlay in groups.py; removed _ prefix since there is no getter/setter

APPLE_POS: Final[Dict[str, List[Tuple[int, int]]]]  = {
    "small": [(18, 17), (30, 37), (12, 50), (30, 45), (20, 30), (30, 10)],
    "default": [(12, 12), (46, 10), (40, 34), (3, 42), (65, 55), (32, 59)],
    "bush": [(10, 10), (8, 37), (25, 25), (40, 13), (33, 40)],
}

VOLCANO_POS: Final[Tuple[int, int]] = (640, 0)
CHARS_PER_LINE: Final[int] = 45
TB_SIZE: Final[Tuple[int, int]] = (491, 376)
GVT_TB_SIZE: Final[Tuple[int, int]] = (607, 276)

# tutorial and intro text box position
TUTORIAL_TB_LEFT: Final[int] = SCREEN_WIDTH - TB_SIZE[0]
TUTORIAL_TB_TOP: Final[int] = SCREEN_HEIGHT / 1.5 - TB_SIZE[1]

HEALTH_DECAY_VALUE: Final[float] = 0.01
BATH_STATUS_TIMEOUT: Final[int] = 30

DEFAULT_ANIMATION_NAME: Final[str] = "intro"

EMOTES_LIST: Final[List[str]] = [
    "furious_ani",
    "love_ani",
    "sad_ani",
    "smile_ani",
    "wink_ani",
]

TOMATO_OR_CORN_LIST: Final[List[str]] = [
    "tomato",
    "corn",
]

# Clamp delta time to prevent extreme movement during lag spikes
# Maximum of 1/12 second (~83ms) to maintain reasonable collision detection
# Used in player.py
# Changing the divisor with the minimum supported FPS will result in different tolerated lag spikes
MAX_DT: Final[float] = 1.0 / 12.0


# health related
# =================
MAX_HP: Final[int] = 100

# interval at which to determine sickness
# changing this is untested and may break the game, leave it at 300s / 5min if possible
SICK_INTERVAL: Final[int] = 60 * 5
RECOVERY_INTERVAL: Final[int] = 60 * 5

MIN_GOGGLE_TIME: Final[int] = 240  # time per each SICK INTERVAL for goggles to be effective

# regular sickness
SICK_DURATION: Final[int] = 240  # duration of sickness
SICK_DECLINE: Final[int] = 120  # decline time of sickness
SICK_INCLINE: Final[int] = SICK_DURATION - SICK_DECLINE  # incline time of sickness
SICK_MIN_HP: Final[int] = 10  # min hp to go to

# sickness after bath
BSICK_DURATION: Final[int] = 60  # duration of sickness
BSICK_DECLINE: Final[int] = 30  # decline time of sickness
BSICK_INCLINE: Final[int] = SICK_DURATION - SICK_DECLINE  # incline time of sickness
BSICK_MIN_HP: Final[int] = 50  # min hp to go to


# db logging terms
PLAYER_HP_STR: Final[str] = "player_hp"
PLAYER_IS_SICK_STR: Final[str] = "player_is_sick"
PLAYER_IS_BSICK_STR: Final[str] = "player_is_bath_sick"
PLAYER_HP_STATE_STR: Final[str] = "player_hp_state"
