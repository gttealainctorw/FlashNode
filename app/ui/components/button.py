"""Buttons."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton

from app.ui import icons
from app.ui.theme import Colors, Sizes

from ._style import set_style_property

_ICON_COLORS = {
    "primary": Colors.TEXT_ON_PRIMARY,
    "secondary": Colors.TEXT_SECONDARY,
    "ghost": Colors.TEXT_SECONDARY,
    "danger": Colors.ERROR,
}


class Button(QPushButton):
    """A push button with a visual variant and an optional line icon.

    variant: "primary" | "secondary" | "ghost" | "danger"
    size:    "sm" | "md" | "lg"
    """

    def __init__(self, text: str = "", icon: str | None = None,
                 variant: str = "secondary", size: str = "md", parent=None):
        super().__init__(text, parent)
        self._icon_name = icon
        self._variant = variant
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setProperty("variant", variant)
        self.setProperty("size", size)
        if icon:
            self.setIconSize(QSize(Sizes.ICON, Sizes.ICON))
            self._apply_icon()

    def _apply_icon(self) -> None:
        if not self._icon_name:
            self.setIcon(QIcon())
            return
        color = _ICON_COLORS.get(self._variant, Colors.TEXT_SECONDARY)
        self.setIcon(icons.icon(self._icon_name, color, Sizes.ICON))

    def set_variant(self, variant: str) -> None:
        self._variant = variant
        set_style_property(self, "variant", variant)
        self._apply_icon()

    def set_icon_name(self, name: str | None) -> None:
        self._icon_name = name
        self._apply_icon()


class LinkButton(QPushButton):
    """Text-only action styled as a link ("Select all", "Clear")."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setFlat(True)
