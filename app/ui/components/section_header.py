"""Section header: title, optional caption and a right-aligned actions slot."""

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.ui.theme import Spacing


class SectionHeader(QWidget):
    """Section title with optional caption and a right-aligned actions slot."""

    def __init__(self, title: str, caption: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        self.title = QLabel(title)
        self.title.setObjectName("sectionTitle")
        self.caption = QLabel(caption)
        self.caption.setObjectName("muted")
        self.caption.setVisible(bool(caption))

        self.actions = QHBoxLayout()
        self.actions.setContentsMargins(0, 0, 0, 0)
        self.actions.setSpacing(Spacing.SM)

        layout.addWidget(self.title)
        layout.addWidget(self.caption)
        layout.addStretch()
        layout.addLayout(self.actions)

    def set_caption(self, text: str) -> None:
        self.caption.setText(text)
        self.caption.setVisible(bool(text))

    def add_action(self, widget: QWidget) -> None:
        self.actions.addWidget(widget)
