from dataclasses import dataclass

# --------------------------------------------------------------------------
# settings implementation
# --------------------------------------------------------------------------
@dataclass
class Settings:
    LEVEL_POLL_MS = 50
    PRESS_RETRY_MS = 50

    KEY_LURE_DEFAULT = "9"
    KEY_LURE_TEXT_DEFAULT = "key_lure"
    KEY_FISHING_DEFAULT = "g"
    KEY_FISHING_TEXT_DEFAULT = "key_fishing"
    KEY_START_DEFAULT = "ctrl+alt+f"
    KEY_START_TEXT_DEFAULT = "key_start"

    THRESHOLD_DEFAULT = 38
    THRESHOLD_MIN = 0
    THRESHOLD_MAX = 100
    THRESHOLD_STEP = 1

    WAIT_LURE_DURATION_MIN_DEFAULT = 600000
    WAIT_LURE_DURATION_MAX_DEFAULT = 600000
    WAIT_LURE_DURATION_MIN = 540000
    WAIT_LURE_DURATION_MAX = 660000
    WAIT_LURE_DURATION_STEP = 1000

    WAIT_LURE_MIN_DEFAULT = 2000
    WAIT_LURE_MAX_DEFAULT = 3000
    WAIT_LURE_MIN = 100
    WAIT_LURE_MAX = 10000
    WAIT_LURE_STEP = 100

    WAIT_FISH_DURATION_MIN_DEFAULT = 30000
    WAIT_FISH_DURATION_MAX_DEFAULT = 30000
    WAIT_FISH_DURATION_MIN = 10000
    WAIT_FISH_DURATION_MAX = 40000
    WAIT_FISH_DURATION_STEP = 1000

    WAIT_FISH_MIN_DEFAULT = 500
    WAIT_FISH_MAX_DEFAULT = 1000
    WAIT_FISH_MIN = 100
    WAIT_FISH_MAX = 2000
    WAIT_FISH_STEP = 100

    WAIT_DELAY_MIN_DEFAULT = 500
    WAIT_DELAY_MAX_DEFAULT = 1000
    WAIT_DELAY_MIN = 100
    WAIT_DELAY_MAX = 2000
    WAIT_DELAY_STEP = 100

    PRESSED_DURATION_MIN_DEFAULT = 50
    PRESSED_DURATION_MAX_DEFAULT = 100
    PRESSED_DURATION_MIN = 10
    PRESSED_DURATION_MAX = 500
    PRESSED_DURATION_STEP = 10

    key_lure: str = KEY_LURE_DEFAULT
    key_fishing: str = KEY_FISHING_DEFAULT
    key_start: str = KEY_START_DEFAULT
    volume_threshold: int = THRESHOLD_DEFAULT
    wait_lure_duration_min: int = WAIT_LURE_DURATION_MIN_DEFAULT
    wait_lure_duration_max: int = WAIT_LURE_DURATION_MAX_DEFAULT
    wait_lure_min: int = WAIT_LURE_MIN_DEFAULT
    wait_lure_max: int = WAIT_LURE_MAX_DEFAULT
    wait_fish_duration_min: int = WAIT_FISH_DURATION_MIN_DEFAULT
    wait_fish_duration_max: int = WAIT_FISH_DURATION_MAX_DEFAULT
    wait_fish_min: int = WAIT_FISH_MIN_DEFAULT
    wait_fish_max: int = WAIT_FISH_MAX_DEFAULT
    wait_delay_min: int = WAIT_DELAY_MIN_DEFAULT
    wait_delay_max: int = WAIT_DELAY_MAX_DEFAULT
    pressed_duration_min: int = PRESSED_DURATION_MIN_DEFAULT
    pressed_duration_max: int = PRESSED_DURATION_MAX_DEFAULT
