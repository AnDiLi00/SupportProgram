import sys

from dataclasses import dataclass

IS_WINDOWS = sys.platform == "win32"

# --------------------------------------------------------------------------
# settings implementation
# --------------------------------------------------------------------------
@dataclass
class Settings:
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
    WAIT_LURE_MIN = 0
    WAIT_LURE_MAX = 10000
    WAIT_LURE_STEP = 100

    WAIT_FISH_DURATION_MIN_DEFAULT = 30000
    WAIT_FISH_DURATION_MAX_DEFAULT = 30000
    WAIT_FISH_DURATION_MIN = 10000
    WAIT_FISH_DURATION_MAX = 40000
    WAIT_FISH_DURATION_STEP = 1000

    WAIT_FISH_MIN_DEFAULT = 500
    WAIT_FISH_MAX_DEFAULT = 1000
    WAIT_FISH_MIN = 0
    WAIT_FISH_MAX = 2000
    WAIT_FISH_STEP = 100

    WAIT_DELAY_MIN_DEFAULT = 500
    WAIT_DELAY_MAX_DEFAULT = 1000
    WAIT_DELAY_MIN = 0
    WAIT_DELAY_MAX = 2000
    WAIT_DELAY_STEP = 100

    key_lure: str
    key_fishing: str
    key_start: str
    volume_threshold: int
    wait_lure_duration_min: int
    wait_lure_duration_max: int
    wait_lure_min: int
    wait_lure_max: int
    wait_fish_duration_min: int
    wait_fish_duration_max: int
    wait_fish_min: int
    wait_fish_max: int
    wait_delay_min: int
    wait_delay_max: int

    def __post_init__(self):
        self.key_lure = self.KEY_LURE_DEFAULT
        self.key_fishing = self.KEY_FISHING_DEFAULT
        self.key_start = self.KEY_START_DEFAULT
        self.volume_threshold = self.THRESHOLD_DEFAULT
        self.wait_lure_duration_min = self.WAIT_LURE_DURATION_MIN_DEFAULT
        self.wait_lure_duration_max = self.WAIT_LURE_DURATION_MAX_DEFAULT
        self.wait_lure_min = self.WAIT_LURE_MIN_DEFAULT
        self.wait_lure_max = self.WAIT_LURE_MAX_DEFAULT
        self.wait_fish_duration_min = self.WAIT_FISH_DURATION_MIN_DEFAULT
        self.wait_fish_duration_max = self.WAIT_FISH_DURATION_MAX_DEFAULT
        self.wait_fish_min = self.WAIT_FISH_MIN_DEFAULT
        self.wait_fish_max = self.WAIT_FISH_MAX_DEFAULT
        self.wait_delay_min = self.WAIT_DELAY_MIN_DEFAULT
        self.wait_delay_max = self.WAIT_DELAY_MAX_DEFAULT
