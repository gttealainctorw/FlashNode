"""Workers: signal contracts, exception safety, thread completion."""

import threading
import unittest
from unittest import mock

from PySide6.QtCore import QObject, QThread

from tests.helpers import qapp, wait_until

from app import workers
from app.detect_chip import DetectionResult


class Recorder(QObject):
    """QObject receiver living in the UI thread. Only *bound methods of a QObject*
    receive signals emitted from the flash pool threads (see app/workers.py)."""

    def __init__(self):
        super().__init__()
        self.events: list[tuple] = []
        self.finished = False

    def detected(self, *args):
        self.events.append(("detected", *args))

    def failed(self, *args):
        self.events.append(("failed", *args))

    def status(self, *args):
        self.events.append(("status", *args))

    def progress(self, *args):
        self.events.append(("progress", *args))

    def log(self, *args):
        self.events.append(("log", *args))


class WorkerHarness:
    """Run a worker in a QThread the way the controller does and collect its signals."""

    def __init__(self, worker):
        qapp()
        self.worker = worker
        self.thread = QThread()
        self.recorder = Recorder()
        self.events = self.recorder.events
        worker.moveToThread(self.thread)
        self.thread.started.connect(worker.run)
        worker.finished.connect(self._on_finished)

    def record(self, signal, name):
        signal.connect(getattr(self.recorder, name))

    def _on_finished(self):
        self.recorder.finished = True
        self.thread.quit()

    @property
    def finished(self):
        return self.recorder.finished

    def run(self, timeout_ms=10000):
        self.thread.start()
        assert wait_until(lambda: self.finished, timeout_ms), "worker did not finish"
        assert self.thread.wait(5000), "thread did not stop"
        return self.events


class DetectWorkerTest(unittest.TestCase):
    def test_reports_success_and_failure_per_port(self):
        results = {
            "COM3": DetectionResult("esp32"),
            "COM4": DetectionResult(None, "NO_RESPONSE", "No serial data received."),
        }
        with mock.patch.object(workers, "detect_chip", side_effect=lambda p: results[p]):
            h = WorkerHarness(workers.DetectWorker(["COM3", "COM4"]))
            h.record(h.worker.detected, "detected")
            h.record(h.worker.failed, "failed")
            events = h.run()
        self.assertEqual(events, [("detected", "COM3", "esp32"),
                                  ("failed", "COM4", "NO_RESPONSE", "No serial data received.")])

    def test_exception_in_detection_is_reported_and_does_not_stop_the_loop(self):
        def boom(port):
            if port == "COM3":
                raise RuntimeError("driver crashed")
            return DetectionResult("esp32c3")

        with mock.patch.object(workers, "detect_chip", side_effect=boom):
            h = WorkerHarness(workers.DetectWorker(["COM3", "COM5"]))
            h.record(h.worker.detected, "detected")
            h.record(h.worker.failed, "failed")
            events = h.run()
        self.assertEqual(events[0][:3], ("failed", "COM3", "INTERNAL"))
        self.assertEqual(events[1], ("detected", "COM5", "esp32c3"))


class FlashWorkerTest(unittest.TestCase):
    def fake_flash(self, outcomes):
        """outcomes: port -> True | False | Exception; replays a realistic log stream."""
        def flash(port, log_cb):
            log_cb(f"[START] Flashing {port}...")
            log_cb(f"[INFO] Detecting chip on {port}...")
            log_cb("[OK] Chip detected: esp32")
            log_cb("[DL] 50% (5/10 bytes)")
            log_cb(f"[INFO] Erasing flash on {port}...")
            log_cb("[OK] Flash erased.")
            log_cb("[INFO] Writing firmware...")
            log_cb("Writing at 0x00001000 [   ]   0.0% 0/10 bytes...")
            for pct in (0, 40, 100):
                log_cb(f"[PROGRESS] {pct}")
                outcome = outcomes[port]
                if outcome is not True and pct == 40:
                    if isinstance(outcome, Exception):
                        raise outcome
                    log_cb("[ERROR] Flash write failed: boom")
                    return False
            return True
        return flash

    def run_job(self, outcomes):
        with mock.patch.object(workers, "flash", side_effect=self.fake_flash(outcomes)):
            h = WorkerHarness(workers.FlashWorker(list(outcomes)))
            h.record(h.worker.status_device, "status")
            h.record(h.worker.progress_device, "progress")
            h.record(h.worker.log, "log")
            return h.run()

    def test_success_sequence(self):
        events = self.run_job({"COM3": True})
        statuses = [e[2] for e in events if e[0] == "status"]
        self.assertEqual(statuses[0], workers.STATUS_CONNECTING)
        self.assertIn("Downloading 50%", statuses)
        self.assertIn(workers.STATUS_ERASING, statuses)
        self.assertIn(workers.STATUS_WRITING, statuses)
        self.assertIn("Flashing 40%", statuses)
        self.assertEqual(statuses[-1], workers.STATUS_DONE)
        progress = [e[2] for e in events if e[0] == "progress"]
        self.assertEqual(progress, [0, 40, 100, 100])
        logs = [e[1] for e in events if e[0] == "log"]
        self.assertIn("[COM3] [OK] Flash completed", logs)
        self.assertTrue(all(l.startswith("[COM3]") for l in logs), logs)
        self.assertFalse(any("Writing at" in l for l in logs))
        self.assertFalse(any("[PROGRESS]" in l or "[DL]" in l for l in logs))

    def test_failure_and_exception_end_in_error_not_stuck(self):
        events = self.run_job({"COM3": False, "COM4": RuntimeError("worker bug")})
        final = {}
        for e in events:
            if e[0] == "status":
                final[e[1]] = e[2]
        self.assertEqual(final, {"COM3": workers.STATUS_ERROR, "COM4": workers.STATUS_ERROR})
        logs = [e[1] for e in events if e[0] == "log"]
        self.assertIn("[COM3] [ERROR] Flash failed", logs)
        self.assertIn("[COM4] [ERROR] Flash failed", logs)
        self.assertTrue(any("[FATAL ERROR] worker bug" in l for l in logs), logs)

    def test_parallelism_is_bounded(self):
        active = []
        peak = [0]
        lock = threading.Lock()

        def slow_flash(port, log_cb):
            import time
            with lock:
                active.append(port)
                peak[0] = max(peak[0], len(active))
            time.sleep(0.15)
            with lock:
                active.remove(port)
            return True

        with mock.patch.object(workers, "flash", side_effect=slow_flash):
            h = WorkerHarness(workers.FlashWorker([f"COM{i}" for i in range(6)]))
            h.run()
        self.assertLessEqual(peak[0], workers.FLASH_MAX_PARALLEL)
        self.assertGreaterEqual(peak[0], 2)

    def test_empty_job_finishes_immediately(self):
        h = WorkerHarness(workers.FlashWorker([]))
        self.assertEqual(h.run(), [])


if __name__ == "__main__":
    unittest.main()
