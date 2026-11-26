import math
import random
import sys
import time

from settings import Settings

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import comtypes
    from comtypes import CLSCTX_ALL
    from ctypes import POINTER, cast
    from pycaw.api.mmdeviceapi import IMMDeviceEnumerator
    from pycaw.constants import CLSID_MMDeviceEnumerator, DEVICE_STATE, EDataFlow
    from pycaw.pycaw import AudioUtilities, IAudioMeterInformation

# --------------------------------------------------------------------------
# meter implementation
# --------------------------------------------------------------------------
class Meter:
    def __init__(self):
        if IS_WINDOWS:
            self.implemented = WindowsMeter()
        else:
            self.implemented = SimulatedMeter()

    def listDevices(self):
        return self.implemented.listDevices()

    def select(self, device_id):
        self.implemented.select(device_id)

    def level(self):
        return self.implemented.level()

# --------------------------------------------------------------------------
# base meter implementation
# --------------------------------------------------------------------------
class BaseMeter:
    def listDevices(self):
        raise NotImplementedError()

    def select(self, device_id):
        raise NotImplementedError()

    def level(self) -> int:
        raise NotImplementedError()

# --------------------------------------------------------------------------
# simulated meter implementation
# --------------------------------------------------------------------------
class SimulatedMeter(BaseMeter):
    def __init__(self):
        self.device_id = None
        self.time_created = time.monotonic()

    def listDevices(self):
        return [("sim1", "simulated speakers"), ("sim2", "simulated headphones")]

    def select(self, device_id):
        self.device_id = device_id

    def level(self) -> int:
        time_elapsed = time.monotonic() - self.time_created

        half_range = abs(Settings.THRESHOLD_MAX - Settings.THRESHOLD_MIN) / 2
        phase = 0.0 if self.device_id != "sim2" else 1.5
        value = half_range + half_range * math.sin(time_elapsed * 1.2 + phase) + random.uniform(-5, 5)
        return max(Settings.THRESHOLD_MIN, min(Settings.THRESHOLD_MAX, int(value)))

# --------------------------------------------------------------------------
# windows meter implementation
# --------------------------------------------------------------------------
class WindowsMeter(BaseMeter):
    def __init__(self):
        self.device_id = None
        self.meter = None
        self.last_retry = 0.0
        try:
            self.connect()
        except Exception:
            pass

    def listDevices(self):
        names = {}
        try:
            for device in AudioUtilities.GetAllDevices():
                names[device.id] = device.FriendlyName
        except Exception:
            pass
        result = []
        collection = self.enumerator().EnumAudioEndpoints(EDataFlow.eRender.value, DEVICE_STATE.ACTIVE.value)
        for item in range(collection.GetCount()):
            device = collection.Item(item)
            device_id = device.GetId()
            result.append((device_id, names.get(device_id, device_id)))
        return result

    def select(self, device_id):
        self.device_id = device_id
        self.connect()

    def level(self) -> int:
        try:
            return int(round(self.meter.GetPeakValue() * 100))
        except Exception:
            now = time.monotonic()
            if now - self.last_retry > 1.0:
                self.last_retry = now
                try:
                    self.connect()
                except Exception:
                    pass
            return 0

    def connect(self):
        if self.device_id is None:
            dev = AudioUtilities.GetSpeakers()
            if hasattr(dev, "_dev"):
                dev = dev._dev
        else:
            dev = self.enumerator().GetDevice(self.device_id)
        iface = dev.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
        self.meter = cast(iface, POINTER(IAudioMeterInformation))

    def enumerator(self):
        return comtypes.CoCreateInstance(CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, comtypes.CLSCTX_INPROC_SERVER)
