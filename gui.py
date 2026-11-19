import sys

IS_WINDOWS = sys.platform == "win32"

from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QProgressBar, QSpinBox

# --------------------------------------------------------------------------
# volume bar implementation
# --------------------------------------------------------------------------
class VolumeBar(QProgressBar):
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

# --------------------------------------------------------------------------
# spin implementation
# --------------------------------------------------------------------------
class Spin(QSpinBox):
    def __init__(self, value, min, max, step, suffix):
        super().__init__()
        self.setRange(min, max)
        self.setSingleStep(step)
        self.setSuffix(suffix)
        self.setValue(value)