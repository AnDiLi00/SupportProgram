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

import random
import threading
import time

from PySide6.QtWidgets import QApplication

from gui import MainWindow
from states import State, StateMachine

IS_WINDOWS = sys.platform == "win32"

# --------------------------------------------------------------------------
# main implementation
# --------------------------------------------------------------------------
class Main(MainWindow, StateMachine):
    def __init__(self):
        self.setWindowTitle("amd program")
        self.setMinimumWidth(500)
        super().__init__()

    # from MainWindow
    def onStartKey(self):
        if self.state == State.IDLE:
            self.storeSettings
            self.start(self.settings)
        else:
            self.stop()

    # from StateMachine
    def onStateChange(self, new_state: State, previous_state: State):
        match new_state:
            case State.IDLE:
                self.appendLog("state: idle")
            case State.CHECK_FISHING_LURE:
                self.appendLog("state: checking fishing lure")
            case State.APPLY_FISHING_LURE:
                self.appendLog("state: applying fishing lure")
            case State.WAIT_FOR_LURE:
                self.appendLog("state: waiting for fishing lure")
            case State.CAST_FISHING_POLE:
                self.appendLog("state: casting fishing pole")
            case State.WAIT_FOR_POLE:
                self.appendLog("state: waiting for fishing pole")
            case State.WAIT_FOR_FISH:
                self.appendLog("state: waiting for fish")
            case State.WAIT_FOR_DELAY:
                self.appendLog("state: waiting for delay")
            case State.REEL_FISH_IN:
                self.appendLog("state: reeling fish in")
            case State.WAIT_FOR_REEL:
                self.appendLog("state: waiting for reel")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Main()
    window.show()
    sys.exit(app.exec())