"""Application controller: connects the UI to the backend.

Owns the runtime state (known chips, scan timer, flashing flag) and the worker
threads. Ports are scanned every SCAN_INTERVAL_MS, unknown chips are identified
in the background, and flashing pauses the scanner until the job completes.
"""

import re
import threading
import time

from PySide6.QtCore import QObject, QThread, QTimer
from PySide6.QtWidgets import QMessageBox

from app import toolchain
from app.chips import CHIPS, chip_label
from app.config import RESCAN_AFTER_FLASH_MS, SCAN_INTERVAL_MS, UNKNOWN_CHIP_RETRY_S
from app.detect_chip import ERROR_LABELS
from app.firmware import FIRMWARE_URLS
from app.flasher import detect_ports
from app.updater import check_update, get_local_version, update_check_enabled
from app.workers import STATUS_DONE, STATUS_ERROR, STATUS_QUEUED, DetectWorker, FlashWorker

SHUTDOWN_WAIT_MS = 3000


def port_sort_key(info: dict) -> tuple:
    """Natural order for port names: COM3 < COM5 < COM11, /dev/ttyUSB0 < /dev/ttyUSB1."""
    return tuple(int(part) if part.isdigit() else part.lower()
                 for part in re.split(r"(\d+)", info["device"]))


def firmware_label() -> str:
    """Human-readable firmware description derived from the configured URLs."""
    url = FIRMWARE_URLS.get("esp32", "")
    match = re.search(r"-v(\d+\.\d+\.\d+)\.bin$", url)
    return f"MicroPython v{match.group(1)}" if match else "MicroPython"


class AppController(QObject):
    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win = win

        self.chip_cache: dict[str, str] = {}
        self.failed_ports: dict[str, float] = {}      # port -> time of the last failed identification
        self.detecting = False
        self.last_ports: set[str] | None = None       # None forces the first rebuild
        self.is_flashing = False
        self._closing = False
        self._threads: list[tuple[QThread, QObject]] = []

        # Per-job bookkeeping for the overall progress and the final summary
        self._job_ports: list[str] = []
        self._job_progress: dict[str, int] = {}
        self._job_results: dict[str, str] = {}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.auto_detect)

        win.flash_requested.connect(self.flash_selected)
        win.rescan_requested.connect(self.rescan)

    # -- lifecycle --------------------------------------------------------

    def start(self) -> None:
        self.win.status_bar.set_versions(get_local_version(), firmware_label())
        self.win.set_activity("Scanning for devices…")
        self.auto_detect()
        self.timer.start(SCAN_INTERVAL_MS)
        if update_check_enabled():
            threading.Thread(target=self._check_updates_bg, daemon=True).start()

    def _check_updates_bg(self) -> None:
        has_update, version = check_update()     # never raises
        if has_update:
            QTimer.singleShot(0, lambda: self._announce_update(version))

    def _announce_update(self, version: str) -> None:
        self.win.console.append(f"[UPDATE] Version {version} is available")
        self.win.status_bar.set_update_available(version)

    def request_close(self) -> bool:
        """Called from the window's closeEvent. Returns True when closing may proceed."""
        if self.is_flashing:
            answer = QMessageBox.question(
                self.win, "Flashing in progress",
                "A flash job is still running. Closing now will interrupt it and the "
                "affected devices will need to be flashed again.\n\nClose anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return False
        self.shutdown()
        return True

    def shutdown(self) -> None:
        """Stop scanning, kill helper processes and wait for worker threads."""
        self._closing = True
        self.timer.stop()
        toolchain.terminate_all()
        for thread, _worker in list(self._threads):
            thread.quit()
            thread.wait(SHUTDOWN_WAIT_MS)
        self._threads.clear()

    # -- threads ----------------------------------------------------------

    def _run_in_thread(self, worker: QObject) -> None:
        """Move `worker` to a fresh QThread, run it, and release both when done."""
        thread = QThread(self)
        worker.moveToThread(thread)
        entry = (thread, worker)
        self._threads.append(entry)

        def release():
            worker.deleteLater()
            if entry in self._threads:
                self._threads.remove(entry)

        worker.finished.connect(thread.quit)
        thread.finished.connect(release)
        thread.started.connect(worker.run)
        thread.start()

    # -- device discovery -------------------------------------------------

    def _rebuild_ui(self, ports: list[dict]) -> None:
        self.win.set_devices(ports, self.chip_cache)
        self._update_idle_activity(len(ports))

    def _update_idle_activity(self, count: int | None = None) -> None:
        """Status-bar text while no job runs: how many devices can be flashed."""
        if self.is_flashing:
            return
        if count is None:
            count = len(self.last_ports or ())
        if count == 0:
            self.win.set_activity("Waiting for devices", "neutral")
            return
        ready = sum(1 for chip in self.chip_cache.values()
                    if chip in CHIPS and CHIPS[chip].flashable)
        noun = "device" if count == 1 else "devices"
        if ready == count:
            self.win.set_activity(f"{count} {noun} ready to flash", "success")
        else:
            self.win.set_activity(f"{ready} of {count} {noun} ready to flash",
                                  "success" if ready else "neutral")

    def auto_detect(self) -> None:
        if self.is_flashing or self._closing:
            return

        try:
            ports = sorted(detect_ports(), key=port_sort_key)
        except Exception as exc:   # enumeration failure must not stop the scanner
            self.win.console.append(f"[WARN] Could not enumerate serial ports: {exc}")
            return
        current_ports = {p["device"] for p in ports}

        if current_ports != self.last_ports:
            self.last_ports = current_ports

            for cached in list(self.chip_cache.keys()):
                if cached not in current_ports:
                    del self.chip_cache[cached]
            for failed in list(self.failed_ports.keys()):
                if failed not in current_ports:
                    del self.failed_ports[failed]

            self._rebuild_ui(ports)

        now = time.monotonic()
        unknown_ports = [
            p["device"] for p in ports
            if p["device"] not in self.chip_cache
            and now - self.failed_ports.get(p["device"], -1e9) >= UNKNOWN_CHIP_RETRY_S
        ]

        if unknown_ports and not self.detecting:
            self.detecting = True

            worker = DetectWorker(unknown_ports)
            worker.detected.connect(self._on_chip_detected)
            worker.failed.connect(self._on_chip_failed)
            worker.finished.connect(self._on_detect_finished)
            self._run_in_thread(worker)

    def _on_chip_detected(self, port: str, chip: str) -> None:
        self.chip_cache[port] = chip
        self.failed_ports.pop(port, None)
        self.win.set_device_chip(port, chip)
        self.win.console.append(f"[{port}] [INFO] Identified as {chip_label(chip)}")
        self._update_idle_activity()

    def _on_chip_failed(self, port: str, kind: str, detail: str) -> None:
        self.failed_ports[port] = time.monotonic()
        label = ERROR_LABELS.get(kind, "Failed")
        self.win.set_device_chip_error(port, label, detail)
        message = f"[{port}] [WARN] {label}"
        if detail:
            message += f" — {detail}"
        self.win.console.append(message)
        self._update_idle_activity()

    def _on_detect_finished(self) -> None:
        self.detecting = False

    def rescan(self) -> None:
        """Manual rescan: forget known chips and failures so everything is identified again."""
        if self.is_flashing:
            return
        self.chip_cache.clear()
        self.failed_ports.clear()
        self.last_ports = None
        self.win.reset_job_states()
        self.win.console.append("[INFO] Rescanning devices…")
        self.auto_detect()

    # -- flashing ---------------------------------------------------------

    def flash_selected(self) -> None:
        if self.is_flashing:
            return
        selected = self.win.selected_ports()

        if not selected:
            QMessageBox.warning(self.win, "No selection", "Select at least one device to flash.")
            return

        self.is_flashing = True
        self.timer.stop()

        self._job_ports = list(selected)
        self._job_progress = {port: 0 for port in selected}
        self._job_results = {}

        for port in selected:
            self.win.set_device_progress(port, 0)
            self.win.set_device_status(port, STATUS_QUEUED)

        self.win.set_flashing(True)
        self.win.set_overall_progress(0)
        self._update_job_activity()
        noun = "device" if len(selected) == 1 else "devices"
        self.win.console.append(f"[START] Flashing {len(selected)} {noun}: {', '.join(selected)}")

        worker = FlashWorker(selected)
        worker.progress_device.connect(self._on_device_progress)
        worker.status_device.connect(self._on_device_status)
        worker.progress.connect(self.win.set_overall_progress)
        worker.log.connect(self.win.console.append)
        worker.finished.connect(self._on_flash_finished)
        self._run_in_thread(worker)

    def _overall_progress(self) -> int:
        """Mean progress over the job; finished devices (ok or failed) count as complete."""
        if not self._job_ports:
            return 0
        total = 0
        for port in self._job_ports:
            if port in self._job_results:
                total += 100
            else:
                total += self._job_progress.get(port, 0)
        return min(100, total // len(self._job_ports))

    def _update_job_activity(self) -> None:
        done = sum(1 for r in self._job_results.values() if r == STATUS_DONE)
        failed = sum(1 for r in self._job_results.values() if r == STATUS_ERROR)
        total = len(self._job_ports)
        parts = [f"Flashing {total} device{'s' if total != 1 else ''}…"]
        if done or failed:
            parts.append(f"{done + failed}/{total} finished")
        if failed:
            parts.append(f"{failed} failed")
        self.win.set_activity(" · ".join(parts), "error" if failed else "primary")

    def _on_device_progress(self, port: str, value: int) -> None:
        self.win.set_device_progress(port, value)
        if port in self._job_progress:
            self._job_progress[port] = max(self._job_progress[port], value)
            self.win.set_overall_progress(self._overall_progress())

    def _on_device_status(self, port: str, text: str) -> None:
        self.win.set_device_status(port, text)
        if text in (STATUS_DONE, STATUS_ERROR) and port in self._job_progress:
            self._job_results[port] = text
            self.win.set_overall_progress(self._overall_progress())
            self._update_job_activity()

    def _on_flash_finished(self) -> None:
        self.is_flashing = False

        ok = sum(1 for r in self._job_results.values() if r == STATUS_DONE)
        failed = len(self._job_ports) - ok
        if failed == 0:
            self.win.set_activity(f"Completed · {ok} flashed successfully", "success")
        else:
            self.win.set_activity(f"Completed · {ok} succeeded, {failed} failed", "error")
        self.win.console.append(f"[INFO] Job finished: {ok} succeeded, {failed} failed")

        self.win.set_overall_progress(None)
        self.win.set_flashing(False)

        if not self._closing:
            QTimer.singleShot(RESCAN_AFTER_FLASH_MS, self.auto_detect)
            self.timer.start(SCAN_INTERVAL_MS)
