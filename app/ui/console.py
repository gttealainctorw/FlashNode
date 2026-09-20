"""Console panel: a timestamped, color-coded log of backend messages."""

import html
import re
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextOption
from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

from app.config import CONSOLE_MAX_LINES
from app.ui.components import Button, SectionHeader
from app.ui.theme import Colors, Spacing, mono_font

# Level tag (as emitted by the backend in square brackets) -> (display label, color)
_LEVELS = {
    "OK": ("OK", Colors.SUCCESS),
    "✓": ("OK", Colors.SUCCESS),
    "ERROR": ("ERROR", Colors.ERROR),
    "FATAL ERROR": ("FATAL", Colors.ERROR),
    "WARN": ("WARN", Colors.WARNING),
    "WARNING": ("WARN", Colors.WARNING),
    "INFO": ("INFO", Colors.TEXT_SECONDARY),
    "START": ("START", Colors.PRIMARY),
    "UPDATE": ("UPDATE", Colors.PRIMARY),
    "DEBUG": ("DEBUG", Colors.TEXT_MUTED),
    "DL": ("DL", Colors.TEXT_MUTED),
    "LOG": ("", Colors.TEXT_MUTED),
}

_TAG_RE = re.compile(r"^\[([^\]]+)\]\s*")
_RAW_ERROR_RE = re.compile(r"\b(error|fatal|failed|exception|timed out)\b", re.IGNORECASE)


def parse_line(text: str) -> tuple[str | None, str, str, str]:
    """Split a backend line into (source, level label, color, message).

    Handles `[INFO] msg`, `[COM3] [ERROR] msg`, and raw tool output.
    """
    source = None
    level = None
    rest = text.strip()

    while True:
        match = _TAG_RE.match(rest)
        if not match:
            break
        tag = match.group(1).strip()
        key = tag.upper()
        if key in _LEVELS and level is None:
            level = key
        elif key not in _LEVELS and source is None:
            source = tag
        rest = rest[match.end():]

    if level is None:
        level = "ERROR" if _RAW_ERROR_RE.search(rest) else "LOG"

    label, color = _LEVELS[level]
    return source, label, color, rest


class ConsoleView(QPlainTextEdit):
    """Read-only monospace log. `append(text)` is the only entry point.

    The buffer is bounded (CONSOLE_MAX_LINES). The view follows new output only
    while the user is already at the bottom, so reading history is not disturbed.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(mono_font())
        self.setMaximumBlockCount(CONSOLE_MAX_LINES)
        self.setPlaceholderText("Activity will appear here.")
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setMinimumHeight(96)

    def append(self, text: str) -> None:
        if not text or not text.strip():
            return
        source, label, color, message = parse_line(text)
        stamp = datetime.now().strftime("%H:%M:%S")

        parts = [f'<span style="color:{Colors.TEXT_MUTED}">{stamp}</span>']
        if label:
            parts.append(f'<span style="color:{color}; font-weight:600">{html.escape(label):<6}</span>'
                         .replace(" ", "&nbsp;"))
        else:
            parts.append("&nbsp;" * 6)
        source_cell = html.escape(source or "").ljust(6).replace(" ", "&nbsp;")
        parts.append(f'<span style="color:{Colors.TEXT_SECONDARY}">{source_cell}</span>')
        text_color = color if label in ("ERROR", "FATAL", "OK") else Colors.TEXT
        parts.append(f'<span style="color:{text_color}">{html.escape(message)}</span>')

        scrollbar = self.verticalScrollBar()
        follow = scrollbar.value() >= scrollbar.maximum() - 4
        self.appendHtml("&nbsp;&nbsp;".join(parts))
        if follow:
            scrollbar.setValue(scrollbar.maximum())


class ConsolePanel(QWidget):
    """Console with a header and a Clear action."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        self.header = SectionHeader("Console")
        self.clear_btn = Button("Clear", icon="trash", variant="ghost", size="sm")
        self.clear_btn.setToolTip("Clear the console")
        self.header.add_action(self.clear_btn)

        self.view = ConsoleView()
        self.clear_btn.clicked.connect(self.view.clear)

        layout.addWidget(self.header)
        layout.addWidget(self.view, 1)

    # Convenience passthroughs used by the controller
    def append(self, text: str) -> None:
        self.view.append(text)

    def clear(self) -> None:
        self.view.clear()
