import random

from enum import Enum, auto

from PySide6.QtCore import QTimer

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
# state machine implementation (mixin: the host class must be a QObject)
# --------------------------------------------------------------------------
class StateMachine:
    def __init__(self):
        self.state = State.IDLE
        self.state_settings = Settings()
        self.pending = []

        self.timer1 = QTimer(self)
        self.timer1.setSingleShot(True)
        self.timer1.timeout.connect(self.onTimer1)
        self.timer2 = QTimer(self)
        self.timer2.setSingleShot(True)
        self.timer2.timeout.connect(self.onTimer2)

        self.timer_lure = QTimer(self)
        self.timer_lure.setSingleShot(True)
        self.timer_lure.timeout.connect(self.onTimerLure)
        self.lure = False

    def start(self, settings: Settings):
        if self.state == State.IDLE:
            self.state_settings = settings
            self.setState(State.CHECK_FISHING_LURE)

    def stop(self):
        if self.state != State.IDLE:
            self.setState(State.IDLE)

    def onFishDetected(self):
        if self.state == State.WAIT_FOR_FISH:
            self.setState(State.WAIT_FOR_DELAY)

    def setState(self, new_state: State):
        if new_state == self.state:
            return

        previous_state, self.state = self.state, new_state
        self.pending.append((new_state, previous_state))
        self.onSetState()

        while self.pending:
            new, previous = self.pending.pop(0)
            self.onStateChange(new, previous)

    @staticmethod
    def randomMs(a: int, b: int) -> int:
        lo, hi = sorted((a, b))
        return int(random.uniform(lo, hi))

    def onSetState(self):
        s = self.state_settings
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
                self.timer_lure.stop()
                self.timer_lure.start(self.randomMs(s.wait_lure_duration_min, s.wait_lure_duration_max))
                self.lure = True
                self.setState(State.WAIT_FOR_LURE)
            case State.WAIT_FOR_LURE:
                self.timer1.stop()
                self.timer1.start(self.randomMs(s.wait_lure_min, s.wait_lure_max))
            case State.CAST_FISHING_POLE:
                self.setState(State.WAIT_FOR_POLE)
            case State.WAIT_FOR_POLE:
                self.timer1.stop()
                self.timer1.start(self.randomMs(s.wait_fish_min, s.wait_fish_max))
                self.timer2.stop()
                self.timer2.start(self.randomMs(s.wait_fish_duration_min, s.wait_fish_duration_max))
            case State.WAIT_FOR_FISH:
                pass
            case State.WAIT_FOR_DELAY:
                self.timer2.stop()
                self.timer1.stop()
                self.timer1.start(self.randomMs(s.wait_delay_min, s.wait_delay_max))
            case State.REEL_FISH_IN:
                self.setState(State.WAIT_FOR_REEL)
            case State.WAIT_FOR_REEL:
                # the same "casting / reel in time" setting is used for the reel
                self.timer1.stop()
                self.timer1.start(self.randomMs(s.wait_fish_min, s.wait_fish_max))

    def onTimer1(self):
        match self.state:
            case State.WAIT_FOR_LURE:
                self.setState(State.CAST_FISHING_POLE)
            case State.WAIT_FOR_POLE:
                self.setState(State.WAIT_FOR_FISH)
            case State.WAIT_FOR_DELAY:
                self.setState(State.REEL_FISH_IN)
            case State.WAIT_FOR_REEL:
                self.setState(State.CHECK_FISHING_LURE)

    def onTimer2(self):
        if self.state in (State.WAIT_FOR_POLE, State.WAIT_FOR_FISH):
            self.setState(State.WAIT_FOR_DELAY)

    def onTimerLure(self):
        self.lure = False

    def onStateChange(self, new_state: State, previous_state: State):
        raise NotImplementedError()
