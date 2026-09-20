"""Empty state placeholder: icon, title, description and an optional action."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.ui import icons
from app.ui.theme import Colors, Spacing


class EmptyState(QWidget):
    def __init__(self, icon: str, title: str, description: str = "",
                 action: QWidget | None = None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XXL, Spacing.XXXL, Spacing.XXL, Spacing.XXXL)
        layout.setSpacing(Spacing.SM)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon = QLabel()
        self.icon.setPixmap(icons.pixmap(icon, Colors.TEXT_MUTED, 36, stroke_width=1.25))
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title = QLabel(title)
        self.title.setObjectName("sectionTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.description = QLabel(description)
        self.description.setObjectName("secondary")
        self.description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description.setWordWrap(True)
        self.description.setFixedWidth(400)
        self.description.setVisible(bool(description))

        layout.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(Spacing.XS)
        layout.addWidget(self.title, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.description, 0, Qt.AlignmentFlag.AlignHCenter)
        if action is not None:
            layout.addSpacing(Spacing.SM)
            layout.addWidget(action, 0, Qt.AlignmentFlag.AlignHCenter)

    def set_text(self, title: str, description: str = "") -> None:
        self.title.setText(title)
        self.description.setText(description)
        self.description.setVisible(bool(description))
