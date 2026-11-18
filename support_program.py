"""
Support Program for Windows (PySide6)
=========================================

Installation:
    pip install PySide6

View the interface only (e.g. on Linux, no keys are sent):
    python support_program.py --layout-test
"""

import ctypes
import random
import string
import sys
import time
from ctypes import wintypes

IS_WINDOWS = sys.platform == "win32"
LAYOUT_TEST = "--layout-test" in sys.argv

if not IS_WINDOWS and not LAYOUT_TEST:
    sys.exit(
        "This program only runs on Windows.\n"
        "To view the layout only: python key_press_simulator.py --layout-test"
    )

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# Windows API: key press via SendInput (scan code mode, also works in many
# programs/games that ignore virtual key codes)
# ---------------------------------------------------------------------------
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

VK_SHIFT = 0x10
VK_CTRL = 0x11
VK_ALT = 0x12

ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


if IS_WINDOWS:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    user32.SendInput.restype = wintypes.UINT
    user32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
    user32.MapVirtualKeyW.restype = wintypes.UINT
    user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
    user32.GetAsyncKeyState.restype = ctypes.c_short
else:
    user32 = None


def send_key(vk: int, extended: bool, down: bool) -> None:
    if user32 is None:
        return

    scan = user32.MapVirtualKeyW(vk, 0)
    flags = KEYEVENTF_SCANCODE
    if extended:
        flags |= KEYEVENTF_EXTENDEDKEY
    if not down:
        flags |= KEYEVENTF_KEYUP
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = 0
    inp.ki.wScan = scan
    inp.ki.dwFlags = flags
    inp.ki.time = 0
    inp.ki.dwExtraInfo = 0
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def is_key_down(vk: int) -> bool:
    if user32 is None:
        return False

    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def mods_down():
    return (is_key_down(VK_CTRL), is_key_down(VK_SHIFT), is_key_down(VK_ALT))


def format_combo(name: str, ctrl: bool, shift: bool, alt: bool) -> str:
    parts = []
    if ctrl:
        parts.append("Ctrl")
    if shift:
        parts.append("Shift")
    if alt:
        parts.append("Alt")
    parts.append(name)
    return "+".join(parts)


# ---------------------------------------------------------------------------
# Key tables
#   KEYS:       display name -> (virtual key code, extended key?)
#   QT_TO_NAME: Qt key code -> display name (for "Record key")
#   VK_TO_NAME: virtual key code -> display name (only used on Windows, so that
#               e.g. Shift+1 is recognized as "1")
# ---------------------------------------------------------------------------
KEYS = {}
for _c in string.ascii_uppercase + string.digits:
    KEYS[_c] = (ord(_c), False)
for _i in range(1, 13):
    KEYS[f"F{_i}"] = (0x6F + _i, False)
KEYS.update(
    {
        "Space": (0x20, False),
        "Enter": (0x0D, False),
        "Tab": (0x09, False),
        "Esc": (0x1B, False),
        "Backspace": (0x08, False),
        "Up Arrow": (0x26, True),
        "Down Arrow": (0x28, True),
        "Left Arrow": (0x25, True),
        "Right Arrow": (0x27, True),
        "Insert": (0x2D, True),
        "Delete": (0x2E, True),
        "Home": (0x24, True),
        "End": (0x23, True),
        "Page Up": (0x21, True),
        "Page Down": (0x22, True),
    }
)

VK_TO_NAME = {vk: name for name, (vk, _ext) in KEYS.items()}


def build_qt_map() -> dict:
    k = Qt.Key
    m = {
        int(k.Key_Space): "Space",
        int(k.Key_Return): "Enter",
        int(k.Key_Enter): "Enter",
        int(k.Key_Tab): "Tab",
        int(k.Key_Escape): "Esc",
        int(k.Key_Backspace): "Backspace",
        int(k.Key_Up): "Up Arrow",
        int(k.Key_Down): "Down Arrow",
        int(k.Key_Left): "Left Arrow",
        int(k.Key_Right): "Right Arrow",
        int(k.Key_Insert): "Insert",
        int(k.Key_Delete): "Delete",
        int(k.Key_Home): "Home",
        int(k.Key_End): "End",
        int(k.Key_PageUp): "Page Up",
        int(k.Key_PageDown): "Page Down",
    }
    for i, c in enumerate(string.ascii_uppercase):
        m[int(k.Key_A) + i] = c
    for i, c in enumerate(string.digits):
        m[int(k.Key_0) + i] = c
    for i in range(1, 13):
        m[int(k.Key_F1) + i - 1] = f"F{i}"
    return m


QT_TO_NAME = build_qt_map()

DEFAULT_KEY = "Ö"
DEFAULT_HOTKEY = "F12"
DEFAULT_INTERVAL_MS = 1000
DEFAULT_VARIANCE_MS = 500
MAX_MS = 86_400_000    # 24 hours
MIN_INTERVAL_MS = 100  # smallest selectable interval
MIN_DELAY_MS = 50      # smallest actual delay (including variance)
HOLD_MS = 50           # how long the key is held down
HOLD_VARIANCE_MS = 25


# ---------------------------------------------------------------------------
# Dialog for recording a key (also remembers Ctrl/Shift/Alt)
#   validator(name, ctrl, shift, alt) -> error text or None
# ---------------------------------------------------------------------------
class CaptureDialog(QDialog):
    def __init__(self, title: str, validator, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.name = None
        self.ctrl = self.shift = self.alt = False
        self.validator = validator

        layout = QVBoxLayout(self)
        self.label = QLabel("Press the desired key now\n(also with Ctrl / Shift / Alt) …")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setMinimumSize(340, 80)
        layout.addWidget(self.label)

        cancel = QPushButton("Cancel")
        cancel.setFocusPolicy(Qt.NoFocus)
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel)

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        name = None
        if IS_WINDOWS:
            name = VK_TO_NAME.get(event.nativeVirtualKey())
        if name is None:
            name = QT_TO_NAME.get(int(event.key()))
        if name is None:
            self.label.setText("This key is not supported.\nPlease press another key.")
            return
        mods = event.modifiers()
        ctrl = bool(mods & Qt.ControlModifier)
        shift = bool(mods & Qt.ShiftModifier)
        alt = bool(mods & Qt.AltModifier)
        error = self.validator(name, ctrl, shift, alt)
        if error:
            self.label.setText(f"{error}\nPlease press another key.")
            return
        self.name, self.ctrl, self.shift, self.alt = name, ctrl, shift, alt
        self.accept()


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Support Program" + ("" if IS_WINDOWS else " (Layout Test)"))

        self.running = False
        self.count = 0
        self.next_time = 0.0
        self.pressed = []
        self.cur_sequence = []
        self.interval = DEFAULT_INTERVAL_MS
        self.variance = DEFAULT_VARIANCE_MS
        self.hotkey_was_down = False

        self.fire_timer = QTimer(self, singleShot=True)
        self.fire_timer.timeout.connect(self._fire)
        self.release_timer = QTimer(self, singleShot=True)
        self.release_timer.timeout.connect(self._release_key)
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(100)
        self.tick_timer.timeout.connect(self._tick)
        self.hotkey_timer = QTimer(self)
        self.hotkey_timer.setInterval(50)
        self.hotkey_timer.timeout.connect(self._poll_hotkey)

        self._build_ui()
        self._on_hotkey_changed()
        self.hotkey_timer.start()

    # ------------------------------------------------------------------ UI
    def _make_mod_row(self, grid, row: int, label: str):
        grid.addWidget(QLabel(label), row, 0)
        layout = QHBoxLayout()
        boxes = (QCheckBox("Ctrl"), QCheckBox("Shift"), QCheckBox("Alt"))
        for cb in boxes:
            layout.addWidget(cb)
        layout.addStretch(1)
        grid.addLayout(layout, row, 1, 1, 2)
        return boxes

    def _build_ui(self):
        grid = QGridLayout(self)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setVerticalSpacing(10)
        grid.setHorizontalSpacing(12)

        # --- simulated key ---
        grid.addWidget(QLabel("Key:"), 0, 0)
        self.key_box = QComboBox()
        self.key_box.addItems(list(KEYS))
        self.key_box.setCurrentText(DEFAULT_KEY)
        grid.addWidget(self.key_box, 0, 1)
        self.capture_btn = QPushButton("Record key")
        self.capture_btn.clicked.connect(self.capture_key)
        grid.addWidget(self.capture_btn, 0, 2)

        self.ctrl_check, self.shift_check, self.alt_check = self._make_mod_row(grid, 1, "Modifiers:")

        # --- timing ---
        grid.addWidget(QLabel("Interval:"), 2, 0)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(MIN_INTERVAL_MS, MAX_MS)
        self.interval_spin.setSingleStep(100)
        self.interval_spin.setSuffix(" ms")
        self.interval_spin.setValue(DEFAULT_INTERVAL_MS)
        grid.addWidget(self.interval_spin, 2, 1)

        grid.addWidget(QLabel("Variance ±:"), 3, 0)
        self.variance_spin = QSpinBox()
        self.variance_spin.setRange(0, MAX_MS)
        self.variance_spin.setSingleStep(100)
        self.variance_spin.setSuffix(" ms")
        self.variance_spin.setValue(DEFAULT_VARIANCE_MS)
        grid.addWidget(self.variance_spin, 3, 1)

        # --- start/stop hotkey ---
        grid.addWidget(QLabel("Start/Stop hotkey:"), 4, 0)
        self.hotkey_box = QComboBox()
        self.hotkey_box.addItems(list(KEYS))
        self.hotkey_box.setCurrentText(DEFAULT_HOTKEY)
        grid.addWidget(self.hotkey_box, 4, 1)
        self.hotkey_capture_btn = QPushButton("Record hotkey")
        self.hotkey_capture_btn.clicked.connect(self.capture_hotkey)
        grid.addWidget(self.hotkey_capture_btn, 4, 2)

        self.hk_ctrl_check, self.hk_shift_check, self.hk_alt_check = self._make_mod_row(
            grid, 5, "Hotkey modifiers:"
        )
        self.hotkey_box.currentTextChanged.connect(self._on_hotkey_changed)
        for cb in (self.hk_ctrl_check, self.hk_shift_check, self.hk_alt_check):
            cb.toggled.connect(self._on_hotkey_changed)

        hint = QLabel(
            "Example: interval 5000 ms, variance 1000 ms →\n"
            "key press every 4000–6000 ms (random)."
        )
        hint.setStyleSheet("color: gray;")
        grid.addWidget(hint, 6, 0, 1, 3)

        self.toggle_btn = QPushButton("Start")
        self.toggle_btn.setMinimumHeight(40)
        self.toggle_btn.clicked.connect(self.toggle)
        grid.addWidget(self.toggle_btn, 7, 0, 1, 3)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        grid.addWidget(line, 8, 0, 1, 3)

        self.status_label = QLabel("Ready.")
        self.countdown_label = QLabel("")
        self.count_label = QLabel("Key presses: 0")
        grid.addWidget(self.status_label, 9, 0, 1, 3)
        grid.addWidget(self.countdown_label, 10, 0, 1, 3)
        grid.addWidget(self.count_label, 11, 0, 1, 3)

        grid.setColumnStretch(1, 1)
        self.setFixedSize(self.sizeHint().expandedTo(self.minimumSizeHint()))

    def _set_inputs_enabled(self, enabled: bool):
        for w in (
            self.key_box,
            self.capture_btn,
            self.ctrl_check,
            self.shift_check,
            self.alt_check,
            self.interval_spin,
            self.variance_spin,
            self.hotkey_box,
            self.hotkey_capture_btn,
            self.hk_ctrl_check,
            self.hk_shift_check,
            self.hk_alt_check,
        ):
            w.setEnabled(enabled)

    # ------------------------------------------- current settings
    def _key_mods(self):
        return (
            self.ctrl_check.isChecked(),
            self.shift_check.isChecked(),
            self.alt_check.isChecked(),
        )

    def _hotkey_mods(self):
        return (
            self.hk_ctrl_check.isChecked(),
            self.hk_shift_check.isChecked(),
            self.hk_alt_check.isChecked(),
        )

    def _key_text(self) -> str:
        return format_combo(self.key_box.currentText(), *self._key_mods())

    def _hotkey_text(self) -> str:
        return format_combo(self.hotkey_box.currentText(), *self._hotkey_mods())

    # ---------------------------------------------- recording keys
    def capture_key(self):
        if self.running:
            return

        def validator(name, ctrl, shift, alt):
            if name == self.hotkey_box.currentText() and (ctrl, shift, alt) == self._hotkey_mods():
                return "This combination is set as the Start/Stop hotkey."
            return None

        dlg = CaptureDialog("Record key", validator, self)
        if dlg.exec() == QDialog.Accepted and dlg.name:
            self.key_box.setCurrentText(dlg.name)
            self.ctrl_check.setChecked(dlg.ctrl)
            self.shift_check.setChecked(dlg.shift)
            self.alt_check.setChecked(dlg.alt)
            self.status_label.setText(f"Key “{self._key_text()}” applied.")

    def capture_hotkey(self):
        if self.running:
            return

        def validator(name, ctrl, shift, alt):
            if name == self.key_box.currentText() and (ctrl, shift, alt) == self._key_mods():
                return "This combination is already being simulated."
            return None

        dlg = CaptureDialog("Record hotkey", validator, self)
        if dlg.exec() == QDialog.Accepted and dlg.name:
            self.hotkey_box.setCurrentText(dlg.name)
            self.hk_ctrl_check.setChecked(dlg.ctrl)
            self.hk_shift_check.setChecked(dlg.shift)
            self.hk_alt_check.setChecked(dlg.alt)
            self.status_label.setText(f"Hotkey “{self._hotkey_text()}” applied.")

    def _on_hotkey_changed(self, *_):
        # Remember the state of the new key so that a hotkey that is still held
        # down (e.g. from recording) does not immediately trigger Start/Stop.
        vk = KEYS[self.hotkey_box.currentText()][0]
        self.hotkey_was_down = is_key_down(vk)

    # ------------------------------------------------------ Start / Stop
    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        name = self.key_box.currentText()
        hotkey = self.hotkey_box.currentText()
        if name not in KEYS or hotkey not in KEYS:
            QMessageBox.critical(self, "Invalid input", "Please select a valid key.")
            return
        if name == hotkey and self._key_mods() == self._hotkey_mods():
            QMessageBox.critical(
                self,
                "Invalid input",
                "The simulated key combination and the Start/Stop hotkey must not be identical.",
            )
            return

        # Press order: modifiers first, then the actual key
        ctrl, shift, alt = self._key_mods()
        sequence = []
        if ctrl:
            sequence.append((VK_CTRL, False))
        if shift:
            sequence.append((VK_SHIFT, False))
        if alt:
            sequence.append((VK_ALT, False))
        sequence.append(KEYS[name])

        self.cur_sequence = sequence
        self.interval = self.interval_spin.value()
        self.variance = self.variance_spin.value()

        self.running = True
        self.count = 0
        self.count_label.setText("Key presses: 0")
        self._set_inputs_enabled(False)
        self.toggle_btn.setText("Stop")
        low = max(MIN_DELAY_MS, self.interval - self.variance)
        high = self.interval + self.variance
        self.status_label.setText(
            f"Running – “{self._key_text()}”, every {low}–{high} ms. Stop with {self._hotkey_text()}."
        )
        self._schedule_next()
        self.tick_timer.start()
        self._tick()

    def stop(self):
        self.running = False
        self.fire_timer.stop()
        self.release_timer.stop()
        self.tick_timer.stop()
        self._release_key()
        self._set_inputs_enabled(True)
        self.toggle_btn.setText("Start")
        self.status_label.setText("Stopped.")
        self.countdown_label.setText("")

    # ------------------------------------------------------------ Sequence
    def _schedule_next(self):
        low = max(MIN_DELAY_MS, self.interval - self.variance)
        high = max(low, self.interval + self.variance)
        delay = random.randint(low, high)
        self.next_time = time.monotonic() + delay / 1000.0
        self.fire_timer.start(delay)

    def _fire(self):
        if not self.running:
            return
        self._release_key()  # safety net: never leave a key stuck
        for vk, ext in self.cur_sequence:
            send_key(vk, ext, True)
            self.pressed.append((vk, ext))
        release_delay = random.randint(HOLD_MS-HOLD_VARIANCE_MS, HOLD_MS+HOLD_VARIANCE_MS)
        self.release_timer.start(release_delay)
        self.count += 1
        self.count_label.setText(f"Key presses: {self.count}")
        self._schedule_next()

    def _release_key(self):
        # release in reverse order: the key first, then the modifiers
        for vk, ext in reversed(self.pressed):
            send_key(vk, ext, False)
        self.pressed = []

    def _tick(self):
        remaining = max(0.0, self.next_time - time.monotonic())
        self.countdown_label.setText(f"Next key press in {remaining:0.1f} s")

    # ------------------------------------------- global Start/Stop hotkey
    def _poll_hotkey(self):
        # Triggers at the moment the hotkey key is pressed while exactly the
        # configured modifiers (Ctrl/Shift/Alt) are held down.
        vk = KEYS[self.hotkey_box.currentText()][0]
        down = is_key_down(vk)
        if down and not self.hotkey_was_down and mods_down() == self._hotkey_mods():
            self.toggle()
        self.hotkey_was_down = down

    # ------------------------------------------------------------ Exit
    def closeEvent(self, event):
        if self.running:
            self.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
