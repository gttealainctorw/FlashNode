"""Top bar: application identity on the left, connection summary on the right."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from app.ui import icons
from app.ui.components import StatusDot
from app.ui.theme import Sizes, Spacing


class TopBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(Sizes.TOPBAR)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.XXL, 0, Spacing.XXL, 0)
        layout.setSpacing(Spacing.MD)

        self.logo = QLabel()
        self.logo.setObjectName("appLogo")
        self.logo.setPixmap(icons.logo_pixmap(28))
        self.logo.setFixedSize(28, 28)

        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(0)
        self.name = QLabel("FlashNode")
        self.name.setObjectName("appName")
        self.tagline = QLabel("ESP32 MicroPython deployment")
        self.tagline.setObjectName("appTagline")
        titles.addWidget(self.name)
        titles.addWidget(self.tagline)

        self.dot = StatusDot("neutral")
        self.connection = QLabel("No devices connected")
        self.connection.setObjectName("secondary")

        layout.addWidget(self.logo)
        layout.addLayout(titles)
        layout.addStretch()
        layout.addWidget(self.dot)
        layout.addSpacing(Spacing.XS)
        layout.addWidget(self.connection)

    def set_connected_count(self, count: int) -> None:
        if count <= 0:
            self.dot.set_tone("neutral")
            self.connection.setText("No devices connected")
        else:
            self.dot.set_tone("success")
            noun = "device" if count == 1 else "devices"
            self.connection.setText(f"{count} {noun} connected")
