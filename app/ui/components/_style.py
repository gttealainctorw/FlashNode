"""Small helpers shared by the components."""

from PySide6.QtWidgets import QWidget


def set_style_property(widget: QWidget, name: str, value) -> None:
    """Set a dynamic property used by the stylesheet and re-apply the style.

    Qt only re-evaluates `[prop="value"]` selectors after unpolish/polish, so
    every state change that should be reflected visually goes through here.
    """
    if widget.property(name) == value:
        return
    widget.setProperty(name, value)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()
