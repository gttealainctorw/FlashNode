"""Main window: composes the top bar, device workspace, console and status bar.

The window owns no business logic. It exposes a small API (`set_devices`,
`set_device_status`, `selected_ports`, ...) and two signals
(`flash_requested`, `rescan_requested`) that the controller wires up.
"""

from typing import Callable

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QSplitter, QVBoxLayout, QWidget

from app.ui.console import ConsolePanel
from app.ui.device_list import DeviceList
from app.ui.status_bar import StatusBar
from app.ui.theme import Spacing
from app.ui.toolbar import DeviceToolbar
from app.ui.top_bar import TopBar


class MainWindow(QWidget):
    flash_requested = Signal()
    rescan_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FlashNode")
        self.setMinimumSize(760, 520)
        self.resize(1040, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.top_bar = TopBar()
        self.toolbar = DeviceToolbar()
        self.device_list = DeviceList()
        self.console = ConsolePanel()
        self.status_bar = StatusBar()

        # Workspace: toolbar above a vertical splitter (devices / console)
        workspace = QWidget()
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(Spacing.XXL, Spacing.XL, Spacing.XXL, Spacing.XL)
        workspace_layout.setSpacing(Spacing.LG)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(Spacing.SM)
        self.splitter.addWidget(self.device_list)
        self.splitter.addWidget(self.console)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.device_list.setMinimumHeight(160)
        self.console.setMinimumHeight(140)

        workspace_layout.addWidget(self.toolbar)
        workspace_layout.addWidget(self.splitter, 1)

        root.addWidget(self.top_bar)
        root.addWidget(workspace, 1)
        root.addWidget(self.status_bar)

        # Wiring between views (no business logic here)
        self.toolbar.flash_requested.connect(self.flash_requested)
        self.toolbar.rescan_requested.connect(self.rescan_requested)
        self.device_list.rescan_requested.connect(self.rescan_requested)
        self.toolbar.select_all_requested.connect(self.device_list.select_all)
        self.toolbar.clear_selection_requested.connect(self.device_list.clear_selection)
        self.device_list.selection_changed.connect(self._sync_toolbar)
        self.device_list.rows_changed.connect(self._update_tab_order)

        # Backwards-compatible aliases used by the controller
        self.log = self.console.view
        self.flash_btn = self.toolbar.flash_btn

        # Keyboard focus starts on the workspace, not on the first button
        self.device_list.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._close_handler: Callable[[], bool] | None = None
        self._positioned = False
        self._update_tab_order()

    def _update_tab_order(self) -> None:
        """Tab: toolbar actions → device rows (in order) → console."""
        chain = [self.toolbar.select_all, self.toolbar.clear_selection,
                 self.toolbar.rescan_btn, self.toolbar.flash_btn, self.device_list]
        chain += [row.checkbox for row in self.device_list.ordered_rows()]
        chain += [self.console.clear_btn, self.console.view]
        for first, second in zip(chain, chain[1:]):
            QWidget.setTabOrder(first, second)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._positioned:
            self._positioned = True
            self._center_on_screen()
        QTimer.singleShot(0, self.device_list.setFocus)

    def _center_on_screen(self) -> None:
        """First show: fit inside the available screen area and center (the OS default
        cascade position can leave part of a 1040px window off-screen)."""
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        width = min(self.width(), area.width())
        height = min(self.height(), area.height())
        self.resize(width, height)
        self.move(area.x() + (area.width() - width) // 2, area.y() + (area.height() - height) // 2)

    # -- closing ----------------------------------------------------------

    def set_close_handler(self, handler: Callable[[], bool]) -> None:
        """`handler()` runs on close and returns False to keep the window open."""
        self._close_handler = handler

    def closeEvent(self, event):
        if self._close_handler is not None and not self._close_handler():
            event.ignore()
            return
        super().closeEvent(event)

    # -- devices ----------------------------------------------------------

    def set_devices(self, ports: list[dict], chips: dict[str, str]) -> None:
        self.device_list.set_devices(ports, chips)
        self.top_bar.set_connected_count(len(ports))
        self.toolbar.set_device_count(len(ports))
        self._sync_toolbar()

    def set_device_chip(self, port: str, chip: str) -> None:
        self.device_list.set_chip(port, chip)

    def set_device_chip_error(self, port: str, label: str, detail: str = "") -> None:
        self.device_list.set_chip_error(port, label, detail)

    def set_device_status(self, port: str, text: str) -> None:
        self.device_list.set_status(port, text)

    def set_device_progress(self, port: str, value: int) -> None:
        self.device_list.set_progress(port, value)

    def selected_ports(self) -> list[str]:
        return self.device_list.selected_ports()

    def reset_job_states(self) -> None:
        self.device_list.reset_job_states()

    # -- global state -----------------------------------------------------

    def set_flashing(self, active: bool) -> None:
        self.toolbar.set_flashing(active)
        self.device_list.set_selection_enabled(not active)
        if not active:
            self._sync_toolbar()

    def set_overall_progress(self, value: int | None) -> None:
        self.status_bar.set_progress(value)

    def set_activity(self, text: str, tone: str = "neutral") -> None:
        self.status_bar.set_activity(text, tone)

    def _sync_toolbar(self) -> None:
        self.toolbar.set_selected_count(len(self.device_list.selected_ports()))
