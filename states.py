import sys

IS_WINDOWS = sys.platform == "win32"

from enum import Enum, auto

# --------------------------------------------------------------------------
# states implementation
# --------------------------------------------------------------------------
class State(Enum):
    IDLE = auto()
    PRESS_KEY2 = auto()
    WAIT_FOR_KEY2 = auto()
    PRESS_KEY1 = auto()
    WAIT_FOR_TIMER = auto()
    WAIT_FOR_KEY1 = auto()