"""Device list: one selectable row per serial port with chip, status and progress.

Row state machine (``state`` property, styled in theme.py)::

    idle      discovered; status tells whether it can be flashed
              ("Identifying…", "Ready", "Unsupported", "Unavailable")
    queued    part of a job, waiting for a flash slot
    busy      connecting / downloading firmware / erasing (indeterminate bar)
    flashing  writing, with a percentage
    done      job finished successfully
    error     job failed (row keeps the last progress)

Selection is allowed in idle/done/error and disabled for every row while a job
runs, because the job is global.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from app import chips
from app.ui.components import (
    Badge, Button, Checkbox, ElidedLabel, EmptyState, ProgressBar, StatusDot,
    set_style_property,
)
from app.ui.theme import Sizes, Spacing

DETECTING = "detecting..."   # sentinel used by the controller before the chip is known

# Status text -> (tone, state)
_FIXED_STATUS = {
    "queued": ("warning", "queued"),
    "connecting": ("primary", "busy"),
    "erasing": ("primary", "busy"),
    "writing": ("primary", "busy"),
    "done": ("success", "done"),
    "error": ("error", "error"),
}


def status_style(text: str) -> tuple[str, str]:
    """Map a controller status string to (tone, row state)."""
    t = text.strip().lower()
    if t in _FIXED_STATUS:
        return _FIXED_STATUS[t]
    if t.startswith("downloading"):
        return "primary", "busy"
    if t.startswith("flashing"):
        return "primary", "flashing"
    return "neutral", "idle"


class DeviceRow(QFrame):
    """A single device. Click anywhere on the row to toggle selection."""

    toggled = Signal(str, bool)   # port, selected

    def __init__(self, port: str, description: str, chip: str | None, parent=None):
        super().__init__(parent)
        self.port = port
        self.chip: str | None = None
        self._idle_status: tuple[str, str] = ("Identifying…", "neutral")
        self.setFixedHeight(Sizes.ROW)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("selected", False)
        self.setProperty("state", "idle")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, 0, Spacing.LG, 0)
        layout.setSpacing(Spacing.LG)

        self.checkbox = Checkbox()
        self.checkbox.setToolTip("Include this device in the next flash job")
        self.checkbox.toggled.connect(self._on_checkbox_toggled)

        identity = QVBoxLayout()
        identity.setContentsMargins(0, 0, 0, 0)
        identity.setSpacing(1)
        self.port_label = QLabel(port)
        self.port_label.setObjectName("port")
        self.description_label = ElidedLabel(description or "Serial device")
        self.description_label.setObjectName("description")
        identity.addWidget(self.port_label)
        identity.addWidget(self.description_label)

        self.chip_badge = Badge("", "neutral")
        self.chip_badge.setFixedWidth(104)

        self.progress = ProgressBar("primary")
        self.progress.setFixedWidth(160)
        self.progress.setVisible(False)
        # Keep the column reserved while hidden so idle and active rows align
        policy = self.progress.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self.progress.setSizePolicy(policy)

        status = QHBoxLayout()
        status.setContentsMargins(0, 0, 0, 0)
        status.setSpacing(Spacing.SM)
        self.status_dot = StatusDot("neutral")
        self.status_text = QLabel("")
        self.status_text.setObjectName("statusText")
        self.status_text.setProperty("tone", "neutral")
        self.status_text.setFixedWidth(112)
        status.addWidget(self.status_dot)
        status.addWidget(self.status_text)

        layout.addWidget(self.checkbox)
        layout.addLayout(identity, 1)
        layout.addWidget(self.chip_badge)
        layout.addWidget(self.progress)
        layout.addLayout(status)

        self.set_chip(chip)

    # -- selection --------------------------------------------------------

    def is_selected(self) -> bool:
        return self.checkbox.isChecked()

    def set_selected(self, selected: bool) -> None:
        self.checkbox.setChecked(selected)

    def set_selection_enabled(self, enabled: bool) -> None:
        self.checkbox.setEnabled(enabled)
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.checkbox.isEnabled():
            self.checkbox.toggle()
            event.accept()
            return
        super().mousePressEvent(event)

    def _on_checkbox_toggled(self, checked: bool) -> None:
        set_style_property(self, "selected", checked)
        self.toggled.emit(self.port, checked)

    # -- device identity --------------------------------------------------

    def set_description(self, description: str) -> None:
        self.description_label.setText(description or "Serial device")

    def set_chip(self, chip: str | None) -> None:
        """Chip identified (or DETECTING/None while unknown)."""
        self.chip = chip if chip and chip != DETECTING else None
        if self.chip is None:
            self.chip_badge.set_content("Detecting…", "neutral")
            self.chip_badge.setToolTip("Identifying the chip with esptool")
            self._set_idle_status("Identifying…", "neutral")
            return

        info = chips.CHIPS.get(self.chip)
        label = chips.chip_label(self.chip)
        if info is not None and info.flashable:
            self.chip_badge.set_content(label, "info")
            self.chip_badge.setToolTip("")
            self._set_idle_status("Ready", "neutral")
        else:
            self.chip_badge.set_content(label, "warning")
            self.chip_badge.setToolTip("No MicroPython image is configured for this chip")
            self._set_idle_status("Unsupported", "warning")

    def set_chip_error(self, label: str, detail: str = "") -> None:
        """Identification failed (port busy, no response, unknown chip…)."""
        self.chip = None
        self.chip_badge.set_content(label, "warning")
        self.chip_badge.setToolTip(detail or label)
        self._set_idle_status("Unavailable", "warning")

    def _set_idle_status(self, text: str, tone: str) -> None:
        """Remember the idle status; show it now unless a job state is active."""
        self._idle_status = (text, tone)
        if self.property("state") == "idle":
            self._apply_status(text, tone, "idle")

    # -- job state --------------------------------------------------------

    def set_status(self, text: str) -> None:
        tone, state = status_style(text)
        if state == "idle":
            text, tone = self._idle_status
        self._apply_status(text, tone, state)

    def _apply_status(self, text: str, tone: str, state: str) -> None:
        self.status_text.setText(text)
        set_style_property(self.status_text, "tone", tone)
        self.status_dot.set_tone(tone)
        set_style_property(self, "state", state)

        bar = self.progress
        bar.setVisible(state != "idle")
        if state == "idle":
            bar.set_determinate()
            bar.reset_value()
        elif state == "queued":
            bar.set_tone("neutral")
            bar.set_determinate()
            bar.reset_value()
        elif state == "busy":
            bar.set_tone("primary")
            bar.set_indeterminate()
        elif state == "flashing":
            bar.set_tone("primary")
            bar.set_determinate()
        elif state == "done":
            bar.set_tone("success")
            bar.set_determinate()
            bar.animate_to(100)
        elif state == "error":
            bar.set_tone("error")
            bar.set_determinate()

    def set_progress(self, value: int) -> None:
        self.progress.set_determinate()
        self.progress.animate_to(value)


class DeviceList(QWidget):
    """Scrollable list of DeviceRow widgets with an empty state."""

    selection_changed = Signal()
    rescan_requested = Signal()
    rows_changed = Signal()        # rows added/removed/reordered (tab order must be rebuilt)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: dict[str, DeviceRow] = {}
        self._selection_enabled = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # only the checkboxes take keyboard focus

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, Spacing.XS, 0)
        self.container_layout.setSpacing(Spacing.SM)
        self.container_layout.addStretch()
        self.scroll.setWidget(self.container)

        rescan = Button("Rescan now", icon="refresh", variant="secondary")
        rescan.clicked.connect(self.rescan_requested)
        self.empty = EmptyState(
            "cpu",
            "No devices detected",
            "Connect an ESP32 board over USB. FlashNode scans for new serial ports "
            "every two seconds. If a board is plugged in but missing, check the "
            "cable, install its USB driver, or close other programs using the port.",
            action=rescan,
        )

        outer.addWidget(self.scroll)
        outer.addWidget(self.empty)
        self._update_empty_state()

    # -- population -------------------------------------------------------

    def set_devices(self, ports: list[dict], chips_known: dict[str, str]) -> None:
        """Sync rows with `ports` (list of {device, description, hwid}).

        Existing rows are kept (with their selection and job state); new ports
        get new rows; vanished ports are removed.
        """
        wanted = [info["device"] for info in ports]
        for port in list(self.rows):
            if port not in wanted:
                row = self.rows.pop(port)
                self.container_layout.removeWidget(row)
                row.deleteLater()

        for index, info in enumerate(ports):
            port = info["device"]
            row = self.rows.get(port)
            if row is None:
                row = DeviceRow(port, info.get("description", ""), chips_known.get(port, DETECTING))
                row.set_selection_enabled(self._selection_enabled)
                row.toggled.connect(self._on_row_toggled)
                self.rows[port] = row
            else:
                row.set_description(info.get("description", ""))
                known = chips_known.get(port)
                if known != row.chip:
                    row.set_chip(known or DETECTING)
            # (Re)insert in port order; cheap, keeps widgets alive
            self.container_layout.removeWidget(row)
            self.container_layout.insertWidget(index, row)

        self._update_empty_state()
        self.rows_changed.emit()
        self.selection_changed.emit()

    def ordered_rows(self) -> list[DeviceRow]:
        """Rows in display order."""
        rows = []
        for i in range(self.container_layout.count()):
            widget = self.container_layout.itemAt(i).widget()
            if isinstance(widget, DeviceRow):
                rows.append(widget)
        return rows

    def _update_empty_state(self) -> None:
        has_rows = bool(self.rows)
        self.scroll.setVisible(has_rows)
        self.empty.setVisible(not has_rows)

    # -- per-device updates ----------------------------------------------

    def set_chip(self, port: str, chip: str) -> None:
        if port in self.rows:
            self.rows[port].set_chip(chip)

    def set_chip_error(self, port: str, label: str, detail: str = "") -> None:
        if port in self.rows:
            self.rows[port].set_chip_error(label, detail)

    def set_status(self, port: str, text: str) -> None:
        if port in self.rows:
            self.rows[port].set_status(text)

    def set_progress(self, port: str, value: int) -> None:
        if port in self.rows:
            self.rows[port].set_progress(value)

    def reset_job_states(self) -> None:
        """Return every row to its idle status (used by a manual rescan)."""
        for row in self.rows.values():
            row.set_status("Idle")

    # -- selection --------------------------------------------------------

    def selected_ports(self) -> list[str]:
        return [port for port, row in self.rows.items() if row.is_selected()]

    def select_all(self) -> None:
        for row in self.rows.values():
            row.set_selected(True)

    def clear_selection(self) -> None:
        for row in self.rows.values():
            row.set_selected(False)

    def set_selection_enabled(self, enabled: bool) -> None:
        self._selection_enabled = enabled
        for row in self.rows.values():
            row.set_selection_enabled(enabled)

    def _on_row_toggled(self, _port: str, _selected: bool) -> None:
        self.selection_changed.emit()
