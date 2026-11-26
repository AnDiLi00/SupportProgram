import sys

IS_WINDOWS = sys.platform == "win32"

import random

from PySide6.QtCore import QTimer

from enum import Enum, auto
from settings import Settings

# --------------------------------------------------------------------------
# state implementation
# --------------------------------------------------------------------------
class State(Enum):
    IDLE = auto()
    CHECK_FISHING_LURE = auto()
    APPLY_FISHING_LURE = auto()
    WAIT_FOR_LURE = auto()
    CAST_FISHING_POLE = auto()
    WAIT_FOR_POLE = auto()
    WAIT_FOR_FISH = auto()
    WAIT_FOR_DELAY = auto()
    REEL_FISH_IN = auto()
    WAIT_FOR_REEL = auto()

# --------------------------------------------------------------------------
# state machine implementation
# --------------------------------------------------------------------------
class StateMachine:
    def __init__(self):
        self.state = State.IDLE
        self.settings = Settings()
        self.pending = []
        
        self.timer1 = QTimer(self)
        self.timer1.setSingleShot(True)
        self.timer1.timeout.connect(self.onTimer)
        self.timer2 = QTimer(self)
        self.timer2.setSingleShot(True)
        self.timer2.timeout.connect(self.onTimer)

        self.timer_lure = QTimer(self)
        self.timer_lure.setSingleShot(True)
        self.timer_lure.timeout.connect(self.onTimer)
        self.lure = False

    def start(self, settings: Settings): 
        if self.state == State.IDLE:
            self.settings = settings
            self.setState(State.CHECK_FISHING_LURE)

    def stop(self): 
        if self.state != State.IDLE:
            self.setState(State.IDLE)

    def getState(self) -> State:
        return self.state

    def setState(self, new_state: State):
        if new_state == self.state:
            return

        previous_state, self.state = self.state, new_state
        self.pending.append((new_state, previous_state))
        self.onSetState()

        while self.pending:
            new, previous = self.pending.pop(0)
            self.onStateChange(new, previous)

    def onSetState(self):
        match self.state:
            case State.IDLE:
                self.timer1.stop()
                self.timer2.stop()
            case State.CHECK_FISHING_LURE:
                if not self.lure:
                    self.setState(State.APPLY_FISHING_LURE)
                else:
                    self.setState(State.CAST_FISHING_POLE)
            case State.APPLY_FISHING_LURE:
                lo_lure, hi_lure = sorted((self.settings.wait_lure_duration_min, self.settings.wait_lure_duration_max))
                self.timer_lure.stop()
                self.timer_lure.start(int(random.uniform(lo_lure, hi_lure)))
                self.lure = True
                self.setState(State.WAIT_FOR_LURE)
            case State.WAIT_FOR_LURE:
                lo1, hi1 = sorted((self.settings.wait_lure_min, self.settings.wait_lure_max))
                self.timer1.stop()
                self.timer1.start(int(random.uniform(lo1, hi1)))
            case State.CAST_FISHING_POLE:
                self.setState(State.WAIT_FOR_POLE)
            case State.WAIT_FOR_POLE:
                lo1, hi1 = sorted((self.settings.wait_cast_min, self.settings.wait_cast_max))
                self.timer1.stop()
                self.timer1.start(int(random.uniform(lo1, hi1)))
                lo2, hi2 = sorted((self.settings.wait_fish_min, self.settings.wait_fish_max))
                self.timer2.stop()
                self.timer2.start(int(random.uniform(lo2, hi2)))
            case State.WAIT_FOR_FISH:
                pass
            case State.WAIT_FOR_DELAY:
                lo1, hi1 = sorted((self.settings.wait_delay_min, self.settings.wait_delay_max))
                self.timer1.stop()
                self.timer1.start(int(random.uniform(lo1, hi1)))
            case State.REEL_FISH_IN:
                self.setState(State.WAIT_FOR_REEL)
            case State.WAIT_FOR_REEL:
                lo1, hi1 = sorted((self.settings.wait_reel_min, self.settings.wait_reel_max))
                self.timer1.stop()
                self.timer1.start(int(random.uniform(lo1, hi1)))
            
    def onTimer(self):
        match self.state:
            case State.IDLE:
                pass
            case State.CHECK_FISHING_LURE:
                pass
            case State.APPLY_FISHING_LURE:
                pass
            case State.WAIT_FOR_LURE:
                match self.sender():
                    case self.timer1:
                        self.setState(State.CAST_FISHING_POLE)
            case State.CAST_FISHING_POLE:
                pass
            case State.WAIT_FOR_POLE:
                match self.sender():
                    case self.timer1:
                        self.setState(State.WAIT_FOR_FISH)
            case State.WAIT_FOR_FISH:
                match self.sender():
                    case self.timer2:
                        self.setState(State.WAIT_FOR_DELAY)
            case State.WAIT_FOR_DELAY:
                match self.sender():
                    case self.timer1:
                        self.setState(State.REEL_FISH_IN)
            case State.REEL_FISH_IN:
                pass
            case State.WAIT_FOR_REEL:
                match self.sender():
                    case self.timer1:
                        self.setState(State.CHECK_FISHING_LURE)

        if self.sender() == self.timer_lure:
            self.timer_lure.stop()
            self.lure = False

    def onStateChange(self, new_state: State, previous_state: State):
        raise NotImplementedError()