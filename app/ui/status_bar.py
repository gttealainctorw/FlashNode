"""Bottom status bar: current activity on the left, versions on the right."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from app.ui.components import Badge, ProgressBar, StatusDot
from app.ui.theme import Sizes, Spacing


class StatusBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(Sizes.STATUSBAR)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.XXL, 0, Spacing.XXL, 0)
        layout.setSpacing(Spacing.SM)

        self.dot = StatusDot("neutral")
        self.activity = QLabel("Ready")
        self.activity.setObjectName("secondary")

        self.progress = ProgressBar("primary")
        self.progress.setFixedWidth(140)
        self.progress.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("muted")
        self.progress_label.setVisible(False)

        self.update_badge = Badge("", "primary")
        self.update_badge.setVisible(False)

        self.versions = QLabel("")
        self.versions.setObjectName("caption")

        layout.addWidget(self.dot)
        layout.addWidget(self.activity)
        layout.addSpacing(Spacing.XS)
        layout.addWidget(self.progress)
        layout.addWidget(self.progress_label)
        layout.addStretch()
        layout.addWidget(self.update_badge)
        layout.addWidget(self.versions)

    def set_activity(self, text: str, tone: str = "neutral") -> None:
        self.activity.setText(text)
        self.dot.set_tone(tone)

    def set_progress(self, value: int | None) -> None:
        """Show an overall progress bar; pass None to hide it."""
        visible = value is not None
        self.progress.setVisible(visible)
        self.progress_label.setVisible(visible)
        if visible:
            self.progress.animate_to(value)
            self.progress_label.setText(f"{int(value)}%")
        else:
            self.progress.reset_value()

    def set_versions(self, app_version: str, firmware_label: str = "") -> None:
        parts = []
        if firmware_label:
            parts.append(firmware_label)
        parts.append(f"FlashNode v{app_version}")
        self.versions.setText("  ·  ".join(parts))

    def set_update_available(self, version: str | None) -> None:
        self.update_badge.setVisible(bool(version))
        if version:
            self.update_badge.setText(f"Update available: v{version}")
