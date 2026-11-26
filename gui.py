import sys
import threading
import time

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import keyboard

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from meters import Meter
from settings import Settings

# --------------------------------------------------------------------------
# key event helper (used on non-windows, where keyboard.read_hotkey is not used)
# --------------------------------------------------------------------------
def key_event_to_name(event):
    key = event.key()
    if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
        return None  # modifier alone: keep waiting for the real key
    mods = event.modifiers()
    parts = []
    if mods & Qt.ControlModifier:
        parts.append("ctrl")
    if mods & Qt.AltModifier:
        parts.append("alt")
    if mods & Qt.ShiftModifier:
        parts.append("shift")
    parts.append(QKeySequence(key).toString().lower())
    return "+".join(parts)

# --------------------------------------------------------------------------
# bridge for cross-thread communication 
# --------------------------------------------------------------------------
class Bridge(QObject):
    onStartKey = Signal()
    onKeyCaptured = Signal(str, str)  # (target, key name)

# --------------------------------------------------------------------------
# volume bar implementation
# --------------------------------------------------------------------------
class VolumeBar(QProgressBar):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(
            "QProgressBar { border: 1px solid #555; border-radius: 3px; text-align: center; background: #222; }"
            "QProgressBar::chunk { background-color: #3a3; }"
        )
        self.threshold = 0

    def setThreshold(self, value: int):
        self.threshold = value
        self.update()

    def paintEvent(self, event: QPaintEvent):
        super().paintEvent(event)
        span = abs(Settings.THRESHOLD_MAX - Settings.THRESHOLD_MIN)
        w = self.width()
        x = 1 + round(self.threshold / span * (w - 2))
        x = max(1, min(w - 2, x))
        p = QPainter(self)
        pen = QPen(QColor("#ff3030"))
        pen.setWidth(2)
        p.setPen(pen)
        p.drawLine(x, 1, x, self.height() - 2)
        p.end()

# --------------------------------------------------------------------------
# spin implementation
# --------------------------------------------------------------------------
class Spin(QSpinBox):
    def __init__(self, value: int, min: int, max: int, step: int):
        super().__init__()
        self.setRange(min, max)
        self.setSingleStep(step)
        self.setValue(value)

# --------------------------------------------------------------------------
# main window implementation
# --------------------------------------------------------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.capture_target = None
        self.startbutton_handle = None
        self.meter = Meter()
        self.bridge = Bridge()
        self.bridge.onStartKey.connect(self.onStartKey)
        self.bridge.onKeyCaptured.connect(self.onKeyCaptured)
        self.createUI()

    def createUI(self):
        self.setFocusPolicy(Qt.StrongFocus)
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
        self.device_list.currentIndexChanged.connect(self.onDeviceChange)
        grid_devices.addWidget(self.device_list, 1, 0)

        self.btn_refresh = QPushButton("refresh")
        self.btn_refresh.clicked.connect(self.refreshDevices)
        grid_devices.addWidget(self.btn_refresh, 1, 1)

        lbl_level = QLabel("level")
        lbl_level.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_devices.addWidget(lbl_level, 2, 0, 1, 2)

        self.volume_bar = VolumeBar()
        self.volume_bar.setRange(Settings.THRESHOLD_MIN, Settings.THRESHOLD_MAX)
        self.volume_bar.setFormat("%v")
        self.volume_bar.setThreshold(Settings.THRESHOLD_DEFAULT)
        grid_devices.addWidget(self.volume_bar, 3, 0, 1, 2)

        lbl_threshold = QLabel("threshold")
        lbl_threshold.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_devices.addWidget(lbl_threshold, 4, 0, 1, 2)

        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(Settings.THRESHOLD_MIN, Settings.THRESHOLD_MAX)
        self.threshold_slider.setValue(Settings.THRESHOLD_DEFAULT)
        grid_devices.addWidget(self.threshold_slider, 5, 0)

        self.threshold_spin = Spin(Settings.THRESHOLD_DEFAULT, Settings.THRESHOLD_MIN, Settings.THRESHOLD_MAX, Settings.THRESHOLD_STEP)
        grid_devices.addWidget(self.threshold_spin, 5, 1)

        self.threshold_slider.valueChanged.connect(self.threshold_spin.setValue)
        self.threshold_spin.valueChanged.connect(self.threshold_slider.setValue)
        self.threshold_spin.valueChanged.connect(self.volume_bar.setThreshold)

        layout.addWidget(box_devices)

        # keys
        box_keys = QGroupBox("keys [modifiers like ctrl+alt+shift are supported]")
        grid_keys = QGridLayout(box_keys)

        key_lure_lbl = QLabel("lure key")
        key_lure_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_keys.addWidget(key_lure_lbl, 0, 0)
        self.key_lure = QLineEdit(Settings.KEY_LURE_DEFAULT)
        grid_keys.addWidget(self.key_lure, 0, 1)
        self.key_lure_btn = QPushButton("record")
        self.key_lure_btn.clicked.connect(lambda: self.captureKey(Settings.KEY_LURE_TEXT_DEFAULT))
        grid_keys.addWidget(self.key_lure_btn, 0, 2)

        key_fishing_lbl = QLabel("fishing key")
        key_fishing_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_keys.addWidget(key_fishing_lbl, 1, 0)
        self.key_fishing = QLineEdit(Settings.KEY_FISHING_DEFAULT)
        grid_keys.addWidget(self.key_fishing, 1, 1)
        self.key_fishing_btn = QPushButton("record")
        self.key_fishing_btn.clicked.connect(lambda: self.captureKey(Settings.KEY_FISHING_TEXT_DEFAULT))
        grid_keys.addWidget(self.key_fishing_btn, 1, 2)

        key_start_lbl = QLabel("start / stop fishing")
        key_start_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_keys.addWidget(key_start_lbl, 2, 0)
        self.key_start = QLineEdit(Settings.KEY_START_DEFAULT)
        grid_keys.addWidget(self.key_start, 2, 1)
        self.key_start_btn = QPushButton("record")
        self.key_start_btn.clicked.connect(lambda: self.captureKey(Settings.KEY_START_TEXT_DEFAULT))
        grid_keys.addWidget(self.key_start_btn, 2, 2)
        self.key_start.editingFinished.connect(self.onStartKeyChange)

        layout.addWidget(box_keys)

        # timing
        box_time = QGroupBox("timing [ms]")
        grid_time = QGridLayout(box_time)

        lure_duration_lbl = QLabel("lure duration")
        lure_duration_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lure_duration_lbl, 0, 0)
        lure_duration_min_lbl = QLabel("min")
        lure_duration_min_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lure_duration_min_lbl, 0, 1)
        self.lure_duration_min = Spin(Settings.WAIT_LURE_DURATION_MIN_DEFAULT, Settings.WAIT_LURE_DURATION_MIN, Settings.WAIT_LURE_DURATION_MAX, Settings.WAIT_LURE_DURATION_STEP)
        grid_time.addWidget(self.lure_duration_min, 0, 2)
        lure_duration_max_lbl = QLabel("max")
        lure_duration_max_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lure_duration_max_lbl, 0, 3)
        self.lure_duration_max = Spin(Settings.WAIT_LURE_DURATION_MAX_DEFAULT, Settings.WAIT_LURE_DURATION_MIN, Settings.WAIT_LURE_DURATION_MAX, Settings.WAIT_LURE_DURATION_STEP)
        grid_time.addWidget(self.lure_duration_max, 0, 4)

        lure_cast_lbl = QLabel("lure cast time")
        lure_cast_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lure_cast_lbl, 1, 0)
        lure_cast_min_lbl = QLabel("min")
        lure_cast_min_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lure_cast_min_lbl, 1, 1)
        self.lure_cast_min = Spin(Settings.WAIT_LURE_MIN_DEFAULT, Settings.WAIT_LURE_MIN, Settings.WAIT_LURE_MAX, Settings.WAIT_LURE_STEP)
        grid_time.addWidget(self.lure_cast_min, 1, 2)
        lure_cast_max_lbl = QLabel("max")
        lure_cast_max_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lure_cast_max_lbl, 1, 3)
        self.lure_cast_max = Spin(Settings.WAIT_LURE_MAX_DEFAULT, Settings.WAIT_LURE_MIN, Settings.WAIT_LURE_MAX, Settings.WAIT_LURE_STEP)
        grid_time.addWidget(self.lure_cast_max, 1, 4)

        fishing_duration_lbl = QLabel("fishing duration")
        fishing_duration_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(fishing_duration_lbl, 2, 0)
        fishing_duration_min_lbl = QLabel("min")
        fishing_duration_min_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(fishing_duration_min_lbl, 2, 1)
        self.fishing_duration_min = Spin(Settings.WAIT_FISH_DURATION_MIN_DEFAULT, Settings.WAIT_FISH_DURATION_MIN, Settings.WAIT_FISH_DURATION_MAX, Settings.WAIT_FISH_DURATION_STEP)
        grid_time.addWidget(self.fishing_duration_min, 2, 2)
        fishing_duration_max_lbl = QLabel("max")
        fishing_duration_max_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(fishing_duration_max_lbl, 2, 3)
        self.fishing_duration_max = Spin(Settings.WAIT_FISH_DURATION_MAX_DEFAULT, Settings.WAIT_FISH_DURATION_MIN, Settings.WAIT_FISH_DURATION_MAX, Settings.WAIT_FISH_DURATION_STEP)
        grid_time.addWidget(self.fishing_duration_max, 2, 4)

        fishing_lbl = QLabel("casting / reel in time")
        fishing_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(fishing_lbl, 3, 0)
        fishing_min_lbl = QLabel("min")
        fishing_min_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(fishing_min_lbl, 3, 1)
        self.fishing_min = Spin(Settings.WAIT_FISH_MIN_DEFAULT, Settings.WAIT_FISH_MIN, Settings.WAIT_FISH_MAX, Settings.WAIT_FISH_STEP)
        grid_time.addWidget(self.fishing_min, 3, 2)
        fishing_max_lbl = QLabel("max")
        fishing_max_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(fishing_max_lbl, 3, 3)
        self.fishing_max = Spin(Settings.WAIT_FISH_MAX_DEFAULT, Settings.WAIT_FISH_MIN, Settings.WAIT_FISH_MAX, Settings.WAIT_FISH_STEP)
        grid_time.addWidget(self.fishing_max, 3, 4)

        delay_lbl = QLabel("response delay")
        delay_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(delay_lbl, 4, 0)
        delay_min_lbl = QLabel("min")
        delay_min_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(delay_min_lbl, 4, 1)
        self.delay_min = Spin(Settings.WAIT_DELAY_MIN_DEFAULT, Settings.WAIT_DELAY_MIN, Settings.WAIT_DELAY_MAX, Settings.WAIT_DELAY_STEP)
        grid_time.addWidget(self.delay_min, 4, 2)
        delay_max_lbl = QLabel("max")
        delay_max_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(delay_max_lbl, 4, 3)
        self.delay_max = Spin(Settings.WAIT_DELAY_MAX_DEFAULT, Settings.WAIT_DELAY_MIN, Settings.WAIT_DELAY_MAX, Settings.WAIT_DELAY_STEP)
        grid_time.addWidget(self.delay_max, 4, 4)

        layout.addWidget(box_time)

        # control
        self.btn_start = QPushButton("start")
        self.btn_start.clicked.connect(self.onStartKey)
        
        layout.addWidget(self.btn_start)

        # log
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(110)

        layout.addWidget(self.log_view, 1)

    def onDeviceChange(self):
        dev_id = self.device_list.currentData()
        try:
            self.meter.select(dev_id)
            self.appendLog(f"observing: {self.device_list.currentText()}")
        except Exception as e:
            self.appendLog(f"could not open device: {e}")

    def refreshDevices(self):
        previous = self.device_list.currentData()
        self.device_list.blockSignals(True)
        self.device_list.clear()
        self.device_list.addItem("default output device", None)
        try:
            for dev_id, name in self.meter.listDevices():
                self.device_list.addItem(name, dev_id)
        except Exception as e:
            self.appendLog(f"could not list output devices: {e}")
        idx = self.device_list.findData(previous)
        self.device_list.setCurrentIndex(idx if idx >= 0 else 0)
        self.device_list.blockSignals(False)
        self.onDeviceChange()

    def changeActiveFlag(self, enabled: bool, change_start: bool):  
        self.device_list.setEnabled(enabled)
        self.btn_refresh.setEnabled(enabled)
        self.threshold_slider.setEnabled(enabled)
        self.threshold_spin.setEnabled(enabled)
        self.key_lure.setEnabled(enabled)
        self.key_lure_btn.setEnabled(enabled)
        self.key_fishing.setEnabled(enabled)
        self.key_fishing_btn.setEnabled(enabled)
        self.key_start.setEnabled(enabled)
        self.key_start_btn.setEnabled(enabled)
        self.lure_duration_min.setEnabled(enabled)
        self.lure_duration_max.setEnabled(enabled)
        self.lure_cast_min.setEnabled(enabled)
        self.lure_cast_max.setEnabled(enabled)
        self.fishing_duration_min.setEnabled(enabled)
        self.fishing_duration_max.setEnabled(enabled)
        self.fishing_min.setEnabled(enabled)
        self.fishing_max.setEnabled(enabled)
        self.delay_min.setEnabled(enabled)
        self.delay_max.setEnabled(enabled)
        if change_start:
            self.btn_start.setEnabled(enabled)

    def captureKey(self, target: str):
        match target:
            case Settings.KEY_LURE_TEXT_DEFAULT:
                self.key_lure_btn.setText("press a key")
            case Settings.KEY_FISHING_TEXT_DEFAULT:
                self.key_fishing_btn.setText("press a key")
            case Settings.KEY_START_TEXT_DEFAULT:
                self.key_start_btn.setText("press a key")
        self.changeActiveFlag(False, True)

        if IS_WINDOWS:
            # the old start hotkey must not fire while a key is being recorded
            self.removeStartHotkey()

            def worker():
                name = keyboard.read_hotkey(suppress=False)
                self.bridge.onKeyCaptured.emit(target, name)

            threading.Thread(target=worker, daemon=True).start()
        else:
            self.capture_target = target
            self.setFocus()

    def keyPressEvent(self, event):
        if self.capture_target is not None:
            name = key_event_to_name(event)
            if name:
                target, self.capture_target = self.capture_target, None
                self.bridge.onKeyCaptured.emit(target, name)
            return
        super().keyPressEvent(event)

    def onKeyCaptured(self, target: str, name: str):
        match target:
            case Settings.KEY_LURE_TEXT_DEFAULT:
                self.key_lure.setText(name)
                self.key_lure_btn.setText("record")
            case Settings.KEY_FISHING_TEXT_DEFAULT:
                self.key_fishing.setText(name)
                self.key_fishing_btn.setText("record")
            case Settings.KEY_START_TEXT_DEFAULT:
                self.key_start.setText(name)
                self.key_start_btn.setText("record")
        self.changeActiveFlag(True, True)
        # setText does not emit editingFinished, and the hotkey was removed while recording
        self.onStartKeyChange()

    def removeStartHotkey(self):
        if self.startbutton_handle is not None:
            try:
                keyboard.remove_hotkey(self.startbutton_handle)
            except Exception:
                pass
            self.startbutton_handle = None

    def onStartKeyChange(self):
        if not IS_WINDOWS:
            return
        self.removeStartHotkey()
        key = self.key_start.text().strip().lower()
        if not key:
            return
        try:
            self.startbutton_handle = keyboard.add_hotkey(key, lambda: self.bridge.onStartKey.emit())
        except Exception as e:
            self.appendLog(f"invalid start key: {e}")
    
    def onStartKey(self):
        raise NotImplementedError()

    def storeSettings(self):
        self.settings.key_lure = self.key_lure.text().strip().lower()
        self.settings.key_fishing = self.key_fishing.text().strip().lower()
        self.settings.key_start = self.key_start.text().strip().lower()
        self.settings.volume_threshold = self.threshold_spin.value()
        self.settings.wait_lure_duration_min = self.lure_duration_min.value()
        self.settings.wait_lure_duration_max = self.lure_duration_max.value()
        self.settings.wait_lure_min = self.lure_cast_min.value()
        self.settings.wait_lure_max = self.lure_cast_max.value()
        self.settings.wait_fish_duration_min = self.fishing_duration_min.value()
        self.settings.wait_fish_duration_max = self.fishing_duration_max.value()
        self.settings.wait_fish_min = self.fishing_min.value()
        self.settings.wait_fish_max = self.fishing_max.value()
        self.settings.wait_delay_min = self.delay_min.value()
        self.settings.wait_delay_max = self.delay_max.value()

    def appendLog(self, text):
        self.log_view.appendPlainText(f"{time.strftime('%H:%M:%S')}  {text}")
