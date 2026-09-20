"""Progress bar with smooth value changes and semantic tones."""

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import QProgressBar

from ._style import set_style_property


class ProgressBar(QProgressBar):
    """Thin, text-less progress bar. tone: "primary" | "success" | "warning" | "error" | "neutral"."""

    def __init__(self, tone: str = "primary", parent=None):
        super().__init__(parent)
        self.setRange(0, 100)
        self.setValue(0)
        self.setTextVisible(False)
        self.setProperty("tone", tone)

        self._anim = QPropertyAnimation(self, b"value", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_tone(self, tone: str) -> None:
        set_style_property(self, "tone", tone)

    def set_indeterminate(self) -> None:
        """Busy state without a known percentage (Qt animates the chunk)."""
        if self.maximum() != 0:
            self._anim.stop()
            self.setRange(0, 0)

    def set_determinate(self) -> None:
        if self.maximum() == 0:
            self.setRange(0, 100)
            self.setValue(0)

    def animate_to(self, value: int) -> None:
        """Move to `value` smoothly (jumps backwards instantly, e.g. on reset)."""
        value = max(self.minimum(), min(self.maximum(), int(value)))
        self._anim.stop()
        if value < self.value():
            self.setValue(value)
            return
        self._anim.setStartValue(self.value())
        self._anim.setEndValue(value)
        self._anim.start()

    def reset_value(self) -> None:
        self._anim.stop()
        self.setValue(0)
