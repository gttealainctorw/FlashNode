"""Badges and status indicators."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from ._style import set_style_property


class Badge(QLabel):
    """Small pill label with a semantic tone (neutral, primary, success, warning, error, info)."""

    def __init__(self, text: str = "", tone: str = "neutral", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setProperty("tone", tone)

    def set_tone(self, tone: str) -> None:
        set_style_property(self, "tone", tone)

    def set_content(self, text: str, tone: str | None = None) -> None:
        self.setText(text)
        if tone is not None:
            self.set_tone(tone)


class StatusDot(QLabel):
    """8px colored dot used next to a status text."""

    def __init__(self, tone: str = "neutral", parent=None):
        super().__init__(parent)
        self.setProperty("tone", tone)

    def set_tone(self, tone: str) -> None:
        set_style_property(self, "tone", tone)
