"""Background workers (run inside QThreads) that wrap the blocking backend calls.

Workers never touch widgets: every result crosses to the UI thread through
signals (queued connections), including those emitted from the flash pool
threads.

Connect these signals to methods of QObjects that live in the UI thread (the
controller, the window). PySide6 gives plain callables (lambdas, functions) the
*sender's* thread affinity, so signals emitted from the pool threads would be
queued to the busy worker thread and never delivered.
"""

from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QObject, Signal

from app.config import FLASH_MAX_PARALLEL
from app.detect_chip import detect_chip
from app.flasher import flash

# Status strings understood by the device row (see app/ui/device_list.py)
STATUS_QUEUED = "Queued"
STATUS_CONNECTING = "Connecting"
STATUS_ERASING = "Erasing"
STATUS_WRITING = "Writing"          # connected for the write, before the first percentage
STATUS_DONE = "Done"
STATUS_ERROR = "Error"


class DetectWorker(QObject):
    """Identify the chip on each port (one at a time)."""

    detected = Signal(str, str)            # port, chip id
    failed = Signal(str, str, str)         # port, error kind, detail
    finished = Signal()

    def __init__(self, ports):
        super().__init__()
        self.ports = ports

    def run(self):
        for port in self.ports:
            try:
                result = detect_chip(port)
            except Exception as exc:   # detect_chip() should never raise; report if it does
                self.failed.emit(port, "INTERNAL", str(exc))
                continue
            if result.ok:
                self.detected.emit(port, result.chip)
            else:
                self.failed.emit(port, result.error or "FATAL", result.detail)
        self.finished.emit()


class FlashWorker(QObject):
    """Flash the given ports, up to FLASH_MAX_PARALLEL at a time."""

    progress_device = Signal(str, int)   # port, percent
    status_device = Signal(str, str)     # port, status text
    progress = Signal(int)
    log = Signal(str)
    finished = Signal()

    def __init__(self, ports):
        super().__init__()
        self.ports = ports

    def run(self):
        if not self.ports:
            self.finished.emit()
            return

        def flash_one(port):
            def log_handler(text):
                if "[PROGRESS]" in text:
                    try:
                        pct = int(text.split("[PROGRESS]")[1].strip())
                    except ValueError:
                        return
                    self.progress_device.emit(port, pct)
                    self.status_device.emit(port, f"Flashing {pct}%")
                    return

                if text.startswith("[DL]"):
                    # Firmware download progress: reflect it in the device status only.
                    try:
                        pct = int(text.split("[DL]")[1].strip().split("%")[0])
                    except ValueError:
                        return
                    self.status_device.emit(port, f"Downloading {pct}%")
                    return

                if text.startswith("Writing at"):
                    return   # already represented by the progress bar

                if text.startswith("[INFO] Erasing flash"):
                    self.status_device.emit(port, STATUS_ERASING)
                elif text.startswith("[INFO] Writing firmware"):
                    self.status_device.emit(port, STATUS_WRITING)

                # Everything else the backend says goes to the console, tagged by port.
                self.log.emit(f"[{port}] {text}")

            try:
                self.status_device.emit(port, STATUS_CONNECTING)
                success = flash(port, log_handler)
            except Exception as exc:   # flash() reports its own errors; this is a safety net
                self.log.emit(f"[{port}] [FATAL ERROR] {exc}")
                success = False

            if success:
                self.progress_device.emit(port, 100)
                self.status_device.emit(port, STATUS_DONE)
                self.log.emit(f"[{port}] [OK] Flash completed")
            else:
                self.status_device.emit(port, STATUS_ERROR)
                self.log.emit(f"[{port}] [ERROR] Flash failed")

        with ThreadPoolExecutor(max_workers=FLASH_MAX_PARALLEL) as executor:
            executor.map(flash_one, self.ports)

        self.finished.emit()
