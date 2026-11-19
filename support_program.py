"""
support program
=============
target platform : windows
ui testing      : linux (audio level and devices are simulated, vkey presses are only logged)

install (windows):  pip install pyside6 pycaw comtypes keyboard
install (linux):    pip install pyside6
run:                python support_program.py
"""
import math
import random
import sys
import threading
import time

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
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

IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    import comtypes
    import keyboard
    from ctypes import POINTER, cast
    from comtypes import CLSCTX_ALL
    from pycaw.api.mmdeviceapi import IMMDeviceEnumerator
    from pycaw.constants import CLSID_MMDeviceEnumerator, DEVICE_STATE, EDataFlow
    from pycaw.pycaw import AudioUtilities, IAudioMeterInformation


# --------------------------------------------------------------------------
# Level meters
# --------------------------------------------------------------------------
class WindowsMeter:
    def __init__(self):
        self.meter = None
        self.device_id = None
        self._last_retry = 0.0
        self._connect()

    @staticmethod
    def _enumerator():
        return comtypes.CoCreateInstance(
            CLSID_MMDeviceEnumerator,
            IMMDeviceEnumerator,
            comtypes.CLSCTX_INPROC_SERVER,
        )

    @classmethod
    def list_devices(cls):
        names = {}
        try:
            for d in AudioUtilities.GetAllDevices():
                names[d.id] = d.FriendlyName
        except Exception:
            pass
        result = []
        coll = cls._enumerator().EnumAudioEndpoints(
            EDataFlow.eRender.value, DEVICE_STATE.ACTIVE.value
        )
        for i in range(coll.GetCount()):
            dev = coll.Item(i)
            dev_id = dev.GetId()
            result.append((dev_id, names.get(dev_id, dev_id)))
        return result

    def select(self, device_id):
        self.device_id = device_id
        self._connect()

    def _connect(self):
        if self.device_id is None:
            dev = AudioUtilities.GetSpeakers()
            if hasattr(dev, "_dev"):  # newer pycaw versions wrap the COM object
                dev = dev._dev
        else:
            dev = self._enumerator().GetDevice(self.device_id)
        iface = dev.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
        self.meter = cast(iface, POINTER(IAudioMeterInformation))

    def level(self) -> int:
        try:
            return int(round(self.meter.GetPeakValue() * 100))
        except Exception:
            # device removed/changed -> try to reconnect (at most once a second)
            now = time.monotonic()
            if now - self._last_retry > 1.0:
                self._last_retry = now
                try:
                    self._connect()
                except Exception:
                    pass
            return 0


class SimulatedMeter:
    def __init__(self):
        self.device_id = None
        self._t0 = time.monotonic()

    @staticmethod
    def list_devices():
        return [("sim1", "simulated speakers"), ("sim2", "simulated headphones")]

    def select(self, device_id):
        self.device_id = device_id

    def level(self) -> int:
        t = time.monotonic() - self._t0
        phase = 0.0 if self.device_id != "sim2" else 1.5
        v = 50 + 50 * math.sin(t * 1.2 + phase) + random.uniform(-5, 5)
        return max(0, min(100, int(v)))


# --------------------------------------------------------------------------
# Keys
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
# Thread -> GUI signals
# --------------------------------------------------------------------------
class LevelBar(QProgressBar):
    def __init__(self):
        super().__init__()
        self.threshold = 0

    def set_threshold(self, value):
        self.threshold = value
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        w = self.width()
        x = 1 + round(self.threshold / 100.0 * (w - 2))
        x = max(1, min(w - 2, x))
        p = QPainter(self)
        pen = QPen(QColor("#ff3030"))
        pen.setWidth(2)
        p.setPen(pen)
        p.drawLine(x, 1, x, self.height() - 2)
        p.end()

class Bridge(QObject):
    toggle_requested = Signal()
    key_captured = Signal(str, str)  # (target, key name)
    sequence_done = Signal()
    log = Signal(str)


# --------------------------------------------------------------------------
# Main window
# --------------------------------------------------------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("support program")
        self.setMinimumWidth(500)

        self.meter = WindowsMeter() if IS_WINDOWS else SimulatedMeter()
        self.bridge = Bridge()
        self.bridge.toggle_requested.connect(self.toggle_monitoring)
        self.bridge.key_captured.connect(self._on_key_captured)
        self.bridge.log.connect(self._append_log)

        self.monitoring = False
        self.sequence_running = False
        self.press_key2 = False
        self.capture_target = None
        self.toggle_hotkey_handle = None

        self._build_ui()
        self._refresh_devices()
        self._register_toggle_hotkey()

        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._poll)
        self.timer.start()

        self.timer_key1 = QTimer(self)
        self.timer_key1.setSingleShot(True)
        self.timer_key1.timeout.connect(self._press_key1)

        self.timer_key1_2nd = QTimer(self)
        self.timer_key1_2nd.setSingleShot(True)
        self.timer_key1_2nd.timeout.connect(self._press_key1_2nd)

        self.timer_key2 = QTimer(self)
        self.timer_key2.setSingleShot(True)
        self.timer_key2.timeout.connect(self._press_key2)

        self.timer_key2_press = QTimer(self)
        self.timer_key2_press.setSingleShot(True)
        self.timer_key2_press.timeout.connect(self._press_key2_press)

        self.timer_key2_wait = QTimer(self)
        self.timer_key2_wait.setSingleShot(True)
        self.timer_key2_wait.timeout.connect(self._press_key2_wait)

        if not IS_WINDOWS:
            self._append_log("test mode (non-windows): devices and audio level are simulated, key presses are only logged, global hotkey is disabled.")

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
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
        self.device_list.currentIndexChanged.connect(self._on_device_changed)
        grid_devices.addWidget(self.device_list, 1, 0)

        self.btn_refresh = QPushButton("refresh")
        self.btn_refresh.clicked.connect(self._refresh_devices)
        grid_devices.addWidget(self.btn_refresh, 1, 1)

        lbl_level = QLabel("level")
        lbl_level.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_devices.addWidget(lbl_level, 2, 0, 1, 2)

        self.volume_bar = LevelBar()
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

        self.threshold_spin = self._spin(50, 0, 100, 1, "%")
        grid_devices.addWidget(self.threshold_spin, 5, 1)

        self.threshold_slider.valueChanged.connect(self.threshold_spin.setValue)
        self.threshold_spin.valueChanged.connect(self.threshold_slider.setValue)
        self.threshold_spin.valueChanged.connect(self._update_bar_style)

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
        self.btn_rec_key1.clicked.connect(lambda: self._capture_key("key1"))
        grid_keys.addWidget(self.btn_rec_key1, 0, 2)

        lbl_key2 = QLabel("key2")
        lbl_key2.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_keys.addWidget(lbl_key2, 1, 0)

        self.key2 = QLineEdit("f")
        grid_keys.addWidget(self.key2, 1, 1)

        self.btn_rec_key2 = QPushButton("record")
        self.btn_rec_key2.clicked.connect(lambda: self._capture_key("key2"))
        grid_keys.addWidget(self.btn_rec_key2, 1, 2)

        lbl_toggle = QLabel("start / stop")
        lbl_toggle.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_keys.addWidget(lbl_toggle, 2, 0)

        self.toggle = QLineEdit("ctrl+alt+s")
        self.toggle.editingFinished.connect(self._register_toggle_hotkey)
        grid_keys.addWidget(self.toggle, 2, 1)

        self.btn_rec_toggle = QPushButton("record")
        self.btn_rec_toggle.clicked.connect(lambda: self._capture_key("toggle"))
        grid_keys.addWidget(self.btn_rec_toggle, 2, 2)

        layout.addWidget(box_keys)

        # timing
        box_time = QGroupBox("timing (ms)")
        grid_time = QGridLayout(box_time)

        lbl_delay1 = QLabel("key1 delay")
        lbl_delay1.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_delay1, 0, 0)

        lbl_delaymin1 = QLabel("min")
        lbl_delaymin1.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_delaymin1, 0, 1)

        self.delay_key1_min = self._spin(25, 10, 60000, 5, "ms")
        grid_time.addWidget(self.delay_key1_min, 0, 2)

        lbl_delaymax1 = QLabel("max")
        lbl_delaymax1.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_delaymax1, 0, 3)

        self.delay_key1_max = self._spin(150, 10, 60000, 5, "ms")
        grid_time.addWidget(self.delay_key1_max, 0, 4)

        lbl_delay1_2nd = QLabel("key1 (second press) delay")
        lbl_delay1_2nd.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_delay1_2nd, 1, 0)

        lbl_delaymin1_2nd = QLabel("min")
        lbl_delaymin1_2nd.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_delaymin1_2nd, 1, 1)

        self.delay_key1_2nd_min = self._spin(500, 500, 60000, 100, "ms")
        grid_time.addWidget(self.delay_key1_2nd_min, 1, 2)

        lbl_delaymax1_2nd = QLabel("max")
        lbl_delaymax1_2nd.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_delaymax1_2nd, 1, 3)

        self.delay_key1_2nd_max = self._spin(1500, 500, 60000, 100, "ms")
        grid_time.addWidget(self.delay_key1_2nd_max, 1, 4)

        lbl_delay2 = QLabel("key2 delay")
        lbl_delay2.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_delay2, 2, 0)

        lbl_delaymin2 = QLabel("min")
        lbl_delaymin2.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_delaymin2, 2, 1)

        self.delay_key2_min = self._spin(390, 360, 2400, 10, "s")
        grid_time.addWidget(self.delay_key2_min, 2, 2)

        lbl_delaymax2 = QLabel("max")
        lbl_delaymax2.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid_time.addWidget(lbl_delaymax2, 2, 3)

        self.delay_key2_max = self._spin(660, 360, 2400, 10, "s")
        grid_time.addWidget(self.delay_key2_max, 2, 4)

        layout.addWidget(box_time)

        # Control
        self.btn_start = QPushButton("start")
        self.btn_start.clicked.connect(self.toggle_monitoring)
        
        layout.addWidget(self.btn_start)

        # Log
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(110)

        layout.addWidget(self.log_view, 1)

        self._update_bar_style()

    @staticmethod
    def _spin(value, min, max, step, suffix):
        s = QSpinBox()
        s.setRange(min, max)
        s.setSingleStep(step)
        s.setSuffix(suffix)
        s.setValue(value)
        return s

    def _update_bar_style(self):
        self.volume_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #555; border-radius: 3px;"
            " text-align: center; background: #222; }"
            "QProgressBar::chunk { background-color: #3a3; }"
        )
        self.volume_bar.set_threshold(self.threshold_spin.value())

    def _append_log(self, text):
        self.log_view.appendPlainText(f"{time.strftime('%H:%M:%S')}  {text}")

    # -------------------------------------------------------------- devices
    def _refresh_devices(self):
        previous = self.device_list.currentData()
        self.device_list.blockSignals(True)
        self.device_list.clear()
        self.device_list.addItem("Default output device", None)
        try:
            for dev_id, name in self.meter.list_devices():
                self.device_list.addItem(name, dev_id)
        except Exception as e:
            self._append_log(f"Could not list output devices: {e}")
        idx = self.device_list.findData(previous)
        self.device_list.setCurrentIndex(idx if idx >= 0 else 0)
        self.device_list.blockSignals(False)
        self._on_device_changed()

    def _on_device_changed(self, *_):
        dev_id = self.device_list.currentData()
        try:
            self.meter.select(dev_id)
            self._append_log(f"observing: {self.device_list.currentText()}")
        except Exception as e:
            self._append_log(f"could not open device: {e}")

    # -------------------------------------------------------- key selection
    def _capture_key(self, target):
        btn = {
            "key1": self.btn_rec_key1,
            "key2": self.btn_rec_key2,
            "toggle": self.btn_rec_toggle,
        }[target]
        btn.setText("Press a key...")
        btn.setEnabled(False)

        if IS_WINDOWS:
            def worker():
                name = keyboard.read_hotkey(suppress=False)
                self.bridge.key_captured.emit(target, name)

            threading.Thread(target=worker, daemon=True).start()
        else:
            self.capture_target = target
            self.setFocus()

    def keyPressEvent(self, event):
        if self.capture_target is not None:
            name = key_event_to_name(event)
            if name:
                target, self.capture_target = self.capture_target, None
                self.bridge.key_captured.emit(target, name)
            return
        super().keyPressEvent(event)

    def _on_key_captured(self, target, name):
        if target == "key1":
            self.key1.setText(name)
            self.btn_rec_key1.setText("Record")
            self.btn_rec_key1.setEnabled(True)
        elif target == "key2":
            self.key2.setText(name)
            self.btn_rec_key2.setText("Record")
            self.btn_rec_key2.setEnabled(True)
        else:
            self.toggle.setText(name)
            self.btn_rec_toggle.setText("Record")
            self.btn_rec_toggle.setEnabled(True)
            self._register_toggle_hotkey()

    def _register_toggle_hotkey(self):
        if not IS_WINDOWS:
            return
        if self.toggle_hotkey_handle is not None:
            try:
                keyboard.remove_hotkey(self.toggle_hotkey_handle)
            except Exception:
                pass
            self.toggle_hotkey_handle = None
        key = self.toggle_key.text().strip().lower()
        if not key:
            return
        try:
            self.toggle_hotkey_handle = keyboard.add_hotkey(key, lambda: self.bridge.toggle_requested.emit())
        except Exception as e:
            self._append_log(f"invalid start/stop hotkey: {e}")

    # ------------------------------------------------------------ monitoring
    def toggle_monitoring(self):
        self.monitoring = not self.monitoring

        if self.monitoring:
            self.btn_start.setText("stop")
            self._append_log("monitoring started")
            self._schedule_key2()
        else:
            self.sequence_running = False
            self.press_key2 = False
            self.timer_key1.stop()
            self.timer_key1_2nd.stop()
            self.timer_key2.stop()
            self.btn_start.setText("start")
            self._append_log("monitoring stopped")

    def _poll(self):
        level = self.meter.level()
        self.volume_bar.setValue(level)

        if not self.monitoring:
            return
        
        if not self.sequence_running and level >= self.threshold_spin.value():
            self._append_log(f"threshold reached")
            self.sequence_running = True
            self._schedule_key1()

    def _schedule_key1(self):
        lo, hi = sorted((self.delay_key1_min.value(), self.delay_key1_max.value()))
        self.timer_key1.start(int(random.uniform(lo, hi)))

    def _schedule_key1_2nd(self):
        lo, hi = sorted((self.delay_key1_2nd_min.value(), self.delay_key1_2nd_max.value()))
        self.timer_key1_2nd.start(int(random.uniform(lo, hi)))

    def _schedule_key2(self):
        lo, hi = sorted((self.delay_key2_min.value(), self.delay_key2_max.value()))
        self.timer_key2.start(int(random.uniform(lo, hi)) * 1000)

    def _schedule_key2_press(self):
        self.timer_key2_press.start(int(random.uniform(500, 700)))

    def _schedule_key2_wait(self):
        self._schedule_key2()
        self.press_key2 = False
        self.timer_key2_wait.start(int(random.uniform(2000, 2300)))

    def _press_key1(self):
        if not self.monitoring:
            return
        
        if not self.sequence_running:
            return

        if self.press_key2:
            self._schedule_key2_press()
        else:
            self._schedule_key1_2nd()
        
        key = self.key1.text().strip().lower()
        if not key:
            return
        
        try:
            press_key(key, self._append_log)
            self._append_log(f"key1 pressed: {key}")
        except Exception as e:
            self._append_log(f"key1 press error: {e}")

    def _press_key1_2nd(self):
        if not self.monitoring:
            return
        
        if not self.sequence_running:
            return

        self.sequence_running = False
        
        key = self.key1.text().strip().lower()
        if not key:
            return
        
        try:
            press_key(key, self._append_log)
            self._append_log(f"key1 2nd pressed: {key}")
        except Exception as e:
            self._append_log(f"key1 2nd press error: {e}")

    def _press_key2(self):
        if self.monitoring:
            self.press_key2 = True

    def _press_key2_press(self):
        if not self.monitoring:
            return
        
        if not self.sequence_running:
            return
        
        key = self.key2.text().strip().lower()
        if not key:
            return
        
        try:
            press_key(key, self._append_log)
            self._append_log(f"key2 pressed: {key}")
        except Exception as e:
            self._append_log(f"key2 press error: {e}")

    def _press_key2_wait(self):
        if self.monitoring:
            self.press_key2 = True

    def closeEvent(self, event):
        if IS_WINDOWS:
            try:
                keyboard.unhook_all()
            except Exception:
                pass
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
