"""Device toolbar: section title, selection helpers and the main actions."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.ui.components import Badge, Button, LinkButton
from app.ui.theme import Spacing


class DeviceToolbar(QWidget):
    flash_requested = Signal()
    rescan_requested = Signal()
    select_all_requested = Signal()
    clear_selection_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        self.title = QLabel("Devices")
        self.title.setObjectName("pageTitle")
        self.count = Badge("0", "neutral")

        self.select_all = LinkButton("Select all")
        self.clear_selection = LinkButton("Clear")
        self.select_all.clicked.connect(self.select_all_requested)
        self.clear_selection.clicked.connect(self.clear_selection_requested)

        self.hint = QLabel("")
        self.hint.setObjectName("muted")

        self.rescan_btn = Button("Rescan", icon="refresh", variant="secondary", size="lg")
        self.rescan_btn.setToolTip("Re-detect connected devices")
        self.rescan_btn.clicked.connect(self.rescan_requested)

        self.flash_btn = Button("Flash selected", icon="bolt", variant="primary", size="lg")
        self.flash_btn.setToolTip("Write MicroPython to every selected device")
        self.flash_btn.clicked.connect(self.flash_requested)
        self.flash_btn.setEnabled(False)

        layout.addWidget(self.title)
        layout.addWidget(self.count)
        layout.addSpacing(Spacing.SM)
        layout.addWidget(self.select_all)
        layout.addWidget(self.clear_selection)
        layout.addStretch()
        layout.addWidget(self.hint)
        layout.addSpacing(Spacing.XS)
        layout.addWidget(self.rescan_btn)
        layout.addWidget(self.flash_btn)

        self._device_count = 0
        self._selected = 0
        self._flashing = False
        self._refresh()

    # -- state ------------------------------------------------------------

    def set_device_count(self, count: int) -> None:
        self._device_count = count
        self._refresh()

    def set_selected_count(self, count: int) -> None:
        self._selected = count
        self._refresh()

    def set_flashing(self, active: bool) -> None:
        self._flashing = active
        self._refresh()

    def _refresh(self) -> None:
        self.count.setText(str(self._device_count))
        self.count.set_tone("primary" if self._device_count else "neutral")

        has_devices = self._device_count > 0
        self.select_all.setVisible(has_devices)
        self.clear_selection.setVisible(has_devices)
        self.select_all.setEnabled(not self._flashing and self._selected < self._device_count)
        self.clear_selection.setEnabled(not self._flashing and self._selected > 0)
        self.rescan_btn.setEnabled(not self._flashing)

        if self._flashing:
            self.flash_btn.setText("Flashing…")
            self.flash_btn.setEnabled(False)
            self.hint.setText("")
        elif self._selected > 0:
            noun = "device" if self._selected == 1 else "devices"
            self.flash_btn.setText(f"Flash {self._selected} {noun}")
            self.flash_btn.setEnabled(True)
            self.hint.setText("")
        else:
            self.flash_btn.setText("Flash selected")
            self.flash_btn.setEnabled(False)
            self.hint.setText("Select devices to flash" if has_devices else "")
