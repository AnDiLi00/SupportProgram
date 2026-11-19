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
from unittest import case

IS_WINDOWS = sys.platform == "win32"

import random
import threading
import time

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

if IS_WINDOWS:
    import keyboard

from gui import VolumeBar, Spin
from meters import Meter
from states import State

# --------------------------------------------------------------------------
# key 
# --------------------------------------------------------------------------
def press_key(name: str, log):
    if IS_WINDOWS:
        keyboard.press_and_release(name)
    else:
        log(f"[simulated] key press: {name}")

MODIFIER_KEYS = (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta, Qt.Key_AltGr)

def key_event_to_name(event):
    if event.key() in MODIFIER_KEYS or event.key() == Qt.Key_unknown:
        return None
    parts = []
    mods = event.modifiers()
    if mods & Qt.ControlModifier:
        parts.append("ctrl")
    if mods & Qt.AltModifier:
        parts.append("alt")
    if mods & Qt.ShiftModifier:
        parts.append("shift")
    key = QKeySequence(event.key()).toString().lower()
    if not key:
        return None
    parts.append(key)
    return "+".join(parts)

# --------------------------------------------------------------------------
# bridge for cross-thread communication 
# --------------------------------------------------------------------------
class Bridge(QObject):
    toggle_requested = Signal()
    key_captured = Signal(str, str)  # (target, key name)
    sequence_done = Signal()
    log = Signal(str)

# --------------------------------------------------------------------------
# main window
# --------------------------------------------------------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("support program")
        self.setMinimumWidth(500)

        self.meter = Meter()
        self.bridge = Bridge()
        self.bridge.toggle_requested.connect(self.__on_toggle)
        self.bridge.key_captured.connect(self.__on_key_captured)
        self.bridge.log.connect(self.__append_log)

        self.state = State.IDLE
        self.press_key2 = True
        self.capture_target = None
        self.toggle_hotkey_handle = None

        self.__build_ui()
        self.__refresh_devices()
        self.__register_toggle_hotkey()

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(10)
        self.poll_timer.timeout.connect(self.__poll)
        self.poll_timer.start()

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.__timer)

        self.timer_key2 = QTimer(self)
        self.timer_key2.setSingleShot(True)
        self.timer_key2.timeout.connect(self.__timer_key2)

        if not IS_WINDOWS:
            self.__append_log("test mode (non-windows): devices and audio level are simulated, key presses are only logged, global hotkey is disabled.")

    def keyPressEvent(self, event):
        if self.capture_target is not None:
            name = key_event_to_name(event)
            if name:
                target, self.capture_target = self.capture_target, None
                self.bridge.key_captured.emit(target, name)
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        if IS_WINDOWS:
            try:
                keyboard.unhook_all()
            except Exception:
                pass
        super().closeEvent(event)

    def __build_ui(self):
        layout = QVBoxLayout(self)

        # sound
        box_devices = QGroupBox("sound")
        grid_devices = QGridLayout(box_devices)

        lbl_device = QLabel("device")
        lbl_device.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_devices.addWidget(lbl_device, 0, 0, 1, 2)

        self.device_list = QComboBox()
        self.device_list.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.device_list.setMinimumContentsLength(30)
        self.device_list.currentIndexChanged.connect(self.__on_device_changed)
        grid_devices.addWidget(self.device_list, 1, 0)

        self.btn_refresh = QPushButton("refresh")
        self.btn_refresh.clicked.connect(self.__refresh_devices)
        grid_devices.addWidget(self.btn_refresh, 1, 1)

        lbl_level = QLabel("level")
        lbl_level.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_devices.addWidget(lbl_level, 2, 0, 1, 2)

        self.volume_bar = VolumeBar()
        self.volume_bar.setRange(0, 100)
        self.volume_bar.setFormat("%v")
        grid_devices.addWidget(self.volume_bar, 3, 0, 1, 2)

        lbl_threshold = QLabel("threshold")
        lbl_threshold.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_devices.addWidget(lbl_threshold, 4, 0, 1, 2)

        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(50)
        grid_devices.addWidget(self.threshold_slider, 5, 0)

        self.threshold_spin = Spin(50, 0, 100, 1, "%")
        grid_devices.addWidget(self.threshold_spin, 5, 1)

        self.threshold_slider.valueChanged.connect(self.threshold_spin.setValue)
        self.threshold_spin.valueChanged.connect(self.threshold_slider.setValue)
        self.threshold_spin.valueChanged.connect(self.__update_bar_style)

        layout.addWidget(box_devices)

        # keys
        box_keys = QGroupBox("keys (modifiers like ctrl+alt+shift are supported)")
        grid_keys = QGridLayout(box_keys)

        lbl_key1 = QLabel("key1")
        lbl_key1.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_keys.addWidget(lbl_key1, 0, 0)

        self.key1 = QLineEdit("g")
        grid_keys.addWidget(self.key1, 0, 1)

        self.btn_rec_key1 = QPushButton("record")
        self.btn_rec_key1.clicked.connect(lambda: self.__capture_key("key1"))
        grid_keys.addWidget(self.btn_rec_key1, 0, 2)

        lbl_key2 = QLabel("key2")
        lbl_key2.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_keys.addWidget(lbl_key2, 1, 0)

        self.key2 = QLineEdit("f")
        grid_keys.addWidget(self.key2, 1, 1)

        self.btn_rec_key2 = QPushButton("record")
        self.btn_rec_key2.clicked.connect(lambda: self.__capture_key("key2"))
        grid_keys.addWidget(self.btn_rec_key2, 1, 2)

        lbl_toggle = QLabel("start / stop")
        lbl_toggle.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_keys.addWidget(lbl_toggle, 2, 0)

        self.toggle = QLineEdit("ctrl+alt+s")
        self.toggle.editingFinished.connect(self.__register_toggle_hotkey)
        grid_keys.addWidget(self.toggle, 2, 1)

        self.btn_rec_toggle = QPushButton("record")
        self.btn_rec_toggle.clicked.connect(lambda: self.__capture_key("toggle"))
        grid_keys.addWidget(self.btn_rec_toggle, 2, 2)

        layout.addWidget(box_keys)

        # timing
        box_time = QGroupBox("timing (ms)")
        grid_time = QGridLayout(box_time)

        lbl_delay = QLabel("key press delay")
        lbl_delay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_delay, 0, 0)

        lbl_delay_min = QLabel("min")
        lbl_delay_min.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_delay_min, 0, 1)

        self.delay_min = Spin(200, 100, 1000, 10, "ms")
        grid_time.addWidget(self.delay_min, 0, 2)

        lbl_delay_max = QLabel("max")
        lbl_delay_max.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_delay_max, 0, 3)

        self.delay_max = Spin(1000, 100, 1000, 10, "ms")
        grid_time.addWidget(self.delay_max, 0, 4)

        lbl_key1_wait = QLabel("key1 wait")
        lbl_key1_wait.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_key1_wait, 1, 0)

        lbl_key1_wait_min = QLabel("min")
        lbl_key1_wait_min.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_key1_wait_min, 1, 1)

        self.key1_wait_min = Spin(28, 20, 60, 1, "s")
        grid_time.addWidget(self.key1_wait_min, 1, 2)

        lbl_key1_wait_max = QLabel("max")
        lbl_key1_wait_max.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_key1_wait_max, 1, 3)

        self.key1_wait_max = Spin(32, 20, 60, 1, "s")
        grid_time.addWidget(self.key1_wait_max, 1, 4)

        lbl_key2_wait = QLabel("key2 wait")
        lbl_key2_wait.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_key2_wait, 2, 0)

        lbl_key2_wait_min = QLabel("min")
        lbl_key2_wait_min.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_key2_wait_min, 2, 1)

        self.key2_wait_min = Spin(600, 300, 3600, 10, "s")
        grid_time.addWidget(self.key2_wait_min, 2, 2)

        lbl_key2_wait_max = QLabel("max")
        lbl_key2_wait_max.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_key2_wait_max, 2, 3)

        self.key2_wait_max = Spin(660, 300, 3600, 10, "s")
        grid_time.addWidget(self.key2_wait_max, 2, 4)

        lbl_key2_delay = QLabel("key2 delay")
        lbl_key2_delay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_key2_delay, 3, 0)

        lbl_key2_delay_min = QLabel("min")
        lbl_key2_delay_min.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_key2_delay_min, 3, 1)

        self.key2_delay_min = Spin(5, 5, 10, 1, "s")
        grid_time.addWidget(self.key2_delay_min, 3, 2)

        lbl_key2_delay_max = QLabel("max")
        lbl_key2_delay_max.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_key2_delay_max, 3, 3)

        self.key2_delay_max = Spin(6, 5, 10, 1, "s")
        grid_time.addWidget(self.key2_delay_max, 3, 4)

        layout.addWidget(box_time)

        # control
        self.btn_start = QPushButton("start")
        self.btn_start.clicked.connect(self.__on_toggle)
        
        layout.addWidget(self.btn_start)

        # log
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(110)

        layout.addWidget(self.log_view, 1)

        self.__update_bar_style()

    def __on_toggle(self):
        self.timer.stop()

        if self.state == State.IDLE:
            self.__widget_toggle(False, False)
            self.__append_log("monitoring started")
            self.btn_start.setText("stop")
            self.state = State.PRESS_KEY2
        else:
            self.__widget_toggle(True, False)
            self.__append_log("monitoring stopped")
            self.btn_start.setText("start")
            self.state = State.IDLE
            
    def __on_key_captured(self, target, name):
        if target == "key1":
            self.key1.setText(name)
            self.btn_rec_key1.setText("record")
        elif target == "key2":
            self.key2.setText(name)
            self.btn_rec_key2.setText("record")
        else:
            self.toggle.setText(name)
            self.btn_rec_toggle.setText("record")
            self.__register_toggle_hotkey()
        self.__widget_toggle(True, True)

    def __append_log(self, text):
        self.log_view.appendPlainText(f"{time.strftime('%H:%M:%S')}  {text}")

    def __update_bar_style(self):
        self.volume_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #555; border-radius: 3px;"
            " text-align: center; background: #222; }"
            "QProgressBar::chunk { background-color: #3a3; }"
        )
        self.volume_bar.set_threshold(self.threshold_spin.value())

    def __refresh_devices(self):
        previous = self.device_list.currentData()
        self.device_list.blockSignals(True)
        self.device_list.clear()
        self.device_list.addItem("Default output device", None)
        try:
            for dev_id, name in self.meter.list_devices():
                self.device_list.addItem(name, dev_id)
        except Exception as e:
            self.__append_log(f"Could not list output devices: {e}")
        idx = self.device_list.findData(previous)
        self.device_list.setCurrentIndex(idx if idx >= 0 else 0)
        self.device_list.blockSignals(False)
        self.__on_device_changed()

    def __register_toggle_hotkey(self):
        if not IS_WINDOWS:
            return
        if self.toggle_hotkey_handle is not None:
            try:
                keyboard.remove_hotkey(self.toggle_hotkey_handle)
            except Exception:
                pass
            self.toggle_hotkey_handle = None
        key = self.toggle.text().strip().lower()
        if not key:
            return
        try:
            self.toggle_hotkey_handle = keyboard.add_hotkey(key, lambda: self.bridge.toggle_requested.emit())
        except Exception as e:
            self.__append_log(f"invalid start/stop hotkey: {e}")  

    def __on_device_changed(self):
        dev_id = self.device_list.currentData()
        try:
            self.meter.select(dev_id)
            self.__append_log(f"observing: {self.device_list.currentText()}")
        except Exception as e:
            self.__append_log(f"could not open device: {e}")

    def __widget_toggle(self, enabled: bool, start_stop_enabled: bool):  
        self.device_list.setEnabled(enabled)
        self.btn_refresh.setEnabled(enabled)
        self.threshold_slider.setEnabled(enabled)
        self.threshold_spin.setEnabled(enabled)
        self.key1.setEnabled(enabled)
        self.btn_rec_key1.setEnabled(enabled)
        self.key2.setEnabled(enabled)
        self.btn_rec_key2.setEnabled(enabled)
        self.toggle.setEnabled(enabled)
        self.btn_rec_toggle.setEnabled(enabled)
        self.delay_min.setEnabled(enabled)
        self.delay_max.setEnabled(enabled)
        self.key1_wait_min.setEnabled(enabled)
        self.key1_wait_max.setEnabled(enabled)
        self.key2_wait_min.setEnabled(enabled)
        self.key2_wait_max.setEnabled(enabled)
        self.key2_delay_min.setEnabled(enabled)
        self.key2_delay_max.setEnabled(enabled)
        if start_stop_enabled:
            self.btn_start.setEnabled(enabled)

    def __capture_key(self, target: str):
        btn = {
            "key1": self.btn_rec_key1,
            "key2": self.btn_rec_key2,
            "toggle": self.btn_rec_toggle,
        }[target]
        btn.setText("press a key")
        self.__widget_toggle(False, True)

        if IS_WINDOWS:
            def worker():
                name = keyboard.read_hotkey(suppress=False)
                self.bridge.key_captured.emit(target, name)

            threading.Thread(target=worker, daemon=True).start()
        else:
            self.capture_target = target
            self.setFocus()
            
    def __poll(self):
        level = self.meter.level()
        self.volume_bar.setValue(level)

        match self.state:
            case State.IDLE:
                return
            case State.PRESS_KEY2:
                if not self.timer.isActive():
                    if self.press_key2:
                        self.__append_log(f"pressing key2: {self.key2.text().strip().lower()}")
                        press_key(self.key2.text().strip().lower(), self.__append_log)
                        lo, hi = sorted((self.key2_delay_min.value() * 1000, self.key2_delay_max.value() * 1000))
                        self.timer.start(int(random.uniform(lo, hi)))
                        self.press_key2 = False
                        self.state = State.WAIT_FOR_KEY2
                    else:
                        self.state = State.PRESS_KEY1
                return
            case State.WAIT_FOR_KEY2:
                return
            case State.PRESS_KEY1:
                if not self.timer.isActive():
                    self.__append_log(f"pressing key1 (cast): {self.key1.text().strip().lower()}")
                    press_key(self.key1.text().strip().lower(), self.__append_log)
                    lo, hi = sorted((self.key1_wait_min.value() * 1000, self.key1_wait_max.value() * 1000))
                    self.timer.start(int(random.uniform(lo, hi)))
                    self.state = State.WAIT_FOR_TIMER    
                return
            case State.WAIT_FOR_TIMER:
                if level >= self.threshold_spin.value():
                    self.__append_log(f"threshold reached")
                    self.timer.stop()
                    self.state = State.WAIT_FOR_KEY1
                return
            case State.WAIT_FOR_KEY1:
                if not self.timer.isActive():
                    lo, hi = sorted((self.delay_min.value(), self.delay_max.value()))
                    self.timer.start(int(random.uniform(lo, hi)))
                return
            
    def __timer(self):
        match self.state:
            case State.IDLE:
                return
            case State.PRESS_KEY2:
                return
            case State.WAIT_FOR_KEY2:
                lo, hi = sorted((self.key2_wait_min.value() * 1000, self.key2_wait_max.value() * 1000))
                self.timer_key2.start(int(random.uniform(lo, hi)))
                self.state = State.PRESS_KEY1
                return
            case State.PRESS_KEY1:
                return
            case State.WAIT_FOR_TIMER:
                self.state = State.WAIT_FOR_KEY1
                return
            case State.WAIT_FOR_KEY1:
                self.__append_log(f"pressing key1 (catch): {self.key1.text().strip().lower()}")
                press_key(self.key1.text().strip().lower(), self.__append_log)
                self.state = State.PRESS_KEY2 
                return
            
    def __timer_key2(self):
        self.press_key2 = True

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
    