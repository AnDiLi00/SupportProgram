"""
support program
=============
target platform : windows
ui testing      : linux (audio level and devices are simulated, vkey presses are only logged)

install (windows):  pip install pyside6 pycaw comtypes keyboard
install (linux):    pip install pyside6
run:                python support_program.py
"""
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from gui import MainWindow
from settings import Settings
from states import State, StateMachine

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import keyboard

# --------------------------------------------------------------------------
# main implementation
# --------------------------------------------------------------------------
class Main(MainWindow, StateMachine):
    def __init__(self):
        MainWindow.__init__(self)
        self.initStateMachine()
        self.setWindowTitle("support program")
        self.setMinimumWidth(500)

        self.level_timer = QTimer(self)
        self.level_timer.timeout.connect(self.pollLevel)
        self.level_timer.start(Settings.LEVEL_POLL_MS)

        self.refreshDevices()
        self.onStartKeyChange()

    def pollLevel(self):
        level = self.meter.level()
        self.volume_bar.setValue(level)
        if self.state == State.WAIT_FOR_FISH and level >= self.settings.volume_threshold:
            self.appendLog(f"fish detected (level {level})")
            self.onFishDetected()

    def pressKey(self, key: str):
        if not key:
            self.appendLog("press key: no key configured")
            return
        if self.state == State.IDLE:
            return
        if IS_WINDOWS and any(keyboard.is_pressed(m) for m in ("ctrl", "alt", "shift")):
            QTimer.singleShot(Settings.PRESS_RETRY_MS, lambda: self.pressKey(key))
            return
        duration = self.randomMs(self.settings.pressed_duration_min, self.settings.pressed_duration_max)
        self.appendLog(f"press key: {key} ({duration} ms)")
        if IS_WINDOWS:
            try:
                keyboard.press(key)
            except Exception as e:
                self.appendLog(f"press key: could not press key '{key}': {e}")
                return
            # always release, even if stopped in the meantime, so the key is never stuck
            QTimer.singleShot(duration, lambda: self.releaseKey(key))

    def releaseKey(self, key: str):
        try:
            keyboard.release(key)
        except Exception as e:
            self.appendLog(f"press key: could not release key '{key}': {e}")

    # from MainWindow
    def onStartKey(self):
        if self.state == State.IDLE:
            self.storeSettings()
            self.changeActiveFlag(False, False)
            self.btn_start.setText("stop")
            self.start(self.settings)
        else:
            self.stop()
            self.btn_start.setText("start")
            self.changeActiveFlag(True, False)

    # from StateMachine
    def onStateChange(self, new_state: State, previous_state: State):
        match new_state:
            case State.IDLE:
                self.appendLog("state: idle")
            case State.CHECK_FISHING_LURE:
                self.appendLog("state: checking fishing lure")
            case State.APPLY_FISHING_LURE:
                self.appendLog("state: applying fishing lure")
                self.pressKey(self.settings.key_lure)
            case State.WAIT_FOR_LURE:
                self.appendLog("state: waiting for fishing lure")
            case State.CAST_FISHING_POLE:
                self.appendLog("state: casting fishing pole")
                self.pressKey(self.settings.key_fishing)
            case State.WAIT_FOR_POLE:
                self.appendLog("state: waiting for fishing pole")
            case State.WAIT_FOR_FISH:
                self.appendLog("state: waiting for fish")
            case State.WAIT_FOR_DELAY:
                self.appendLog("state: waiting for delay")
            case State.REEL_FISH_IN:
                self.appendLog("state: reeling fish in")
                self.pressKey(self.settings.key_fishing)
            case State.WAIT_FOR_REEL:
                self.appendLog("state: waiting for reel")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Main()
    window.show()
    sys.exit(app.exec())
