"""AppController driving the real MainWindow with a deterministic fake backend."""

import threading
import time
import unittest
from unittest import mock

from PySide6.QtWidgets import QMessageBox

from tests.helpers import process_events, qapp, wait_until

from app import controller as controller_mod
from app import workers as workers_mod
from app.detect_chip import DetectionResult
from app.ui.main_window import MainWindow


class FakeBackend:
    """Replaces detect_ports / detect_chip / flash. Everything is controllable per port."""

    def __init__(self):
        self.ports: list[dict] = []
        self.chips: dict[str, DetectionResult] = {}
        self.outcomes: dict[str, object] = {}       # True | False | Exception
        self.flash_delay = 0.02
        self.detect_calls: list[str] = []
        self.flash_calls: list[str] = []
        self.release = threading.Event()             # when set, slow flashes may finish
        self.release.set()

    def add(self, port, description="USB Serial Device", chip="esp32"):
        self.ports.append({"device": port, "description": description, "hwid": ""})
        self.chips[port] = DetectionResult(chip) if isinstance(chip, str) else chip
        self.outcomes.setdefault(port, True)

    def remove(self, port):
        self.ports = [p for p in self.ports if p["device"] != port]

    def detect_ports(self):
        return list(self.ports)

    def detect_chip(self, port):
        self.detect_calls.append(port)
        return self.chips.get(port, DetectionResult(None, "NO_RESPONSE", "No serial data received."))

    def flash(self, port, log_cb):
        self.flash_calls.append(port)
        log_cb(f"[INFO] Erasing flash on {port}...")
        for pct in (0, 40, 100):
            time.sleep(self.flash_delay)
            log_cb(f"[PROGRESS] {pct}")
            outcome = self.outcomes.get(port, True)
            if pct == 40 and outcome is not True:
                if isinstance(outcome, Exception):
                    raise outcome
                log_cb("[ERROR] Flash write failed")
                return False
        self.release.wait(10)
        return True


class ControllerTestCase(unittest.TestCase):
    def setUp(self):
        qapp()
        self.backend = FakeBackend()
        self.patches = [
            mock.patch.object(controller_mod, "detect_ports", side_effect=self.backend.detect_ports),
            mock.patch.object(workers_mod, "detect_chip", side_effect=self.backend.detect_chip),
            mock.patch.object(workers_mod, "flash", side_effect=self.backend.flash),
            mock.patch.object(controller_mod, "update_check_enabled", return_value=False),
        ]
        for p in self.patches:
            p.start()
        self.win = MainWindow()
        self.ctl = controller_mod.AppController(self.win)
        self.ctl.timer.setInterval(100)     # fast scans in tests

    def tearDown(self):
        self.backend.release.set()
        self.ctl.shutdown()
        process_events(100)          # deliver signals already queued for the window
        self.win.close()
        self.win.deleteLater()
        process_events(50)
        for p in self.patches:
            p.stop()

    # helpers
    def rows(self):
        return self.win.device_list.rows

    def status_of(self, port):
        return self.rows()[port].status_text.text()

    def wait_idle(self):
        self.assertTrue(wait_until(lambda: not self.ctl._threads, 10000), "worker threads still alive")


class ScanningTest(ControllerTestCase):
    def test_start_discovers_devices_and_identifies_chips(self):
        self.backend.add("COM3", chip="esp32")
        self.backend.add("COM5", chip="esp32c3")
        self.ctl.start()
        self.assertEqual(sorted(self.rows()), ["COM3", "COM5"])
        self.assertTrue(wait_until(lambda: self.ctl.chip_cache == {"COM3": "esp32", "COM5": "esp32c3"}))
        self.assertEqual(self.rows()["COM3"].chip_badge.text(), "ESP32")
        self.assertEqual(self.rows()["COM5"].chip_badge.text(), "ESP32-C3")
        self.assertEqual(self.status_of("COM3"), "Ready")
        self.assertEqual(self.win.status_bar.activity.text(), "2 devices ready to flash")
        self.assertIn("2 devices connected", self.win.top_bar.connection.text())
        self.wait_idle()

    def test_no_devices_shows_empty_state(self):
        self.ctl.start()
        self.assertTrue(self.win.device_list.empty.isVisibleTo(self.win))
        self.assertEqual(self.win.status_bar.activity.text(), "Waiting for devices")
        self.assertFalse(self.win.toolbar.flash_btn.isEnabled())

    def test_device_added_and_removed_keeps_other_rows_and_selection(self):
        self.backend.add("COM3")
        self.backend.add("COM4")
        self.ctl.start()
        self.assertTrue(wait_until(lambda: "COM4" in self.ctl.chip_cache))
        self.wait_idle()
        row_com3 = self.rows()["COM3"]
        row_com3.set_selected(True)
        row_com3.set_status("Done")

        self.backend.remove("COM4")
        self.backend.add("COM7", chip="esp32s3")
        self.ctl.auto_detect()
        self.assertEqual(sorted(self.rows()), ["COM3", "COM7"])
        self.assertIs(self.rows()["COM3"], row_com3, "existing row must be reused")
        self.assertTrue(row_com3.is_selected())
        self.assertEqual(self.status_of("COM3"), "Done")
        self.assertNotIn("COM4", self.ctl.chip_cache)
        self.assertEqual(self.win.selected_ports(), ["COM3"])
        self.assertTrue(wait_until(lambda: self.ctl.chip_cache.get("COM7") == "esp32s3"))
        self.wait_idle()

    def test_failed_identification_is_shown_and_not_retried_every_scan(self):
        self.backend.add("COM9", chip=DetectionResult(None, "PORT", "Could not open COM9"))
        self.ctl.start()
        self.assertTrue(wait_until(lambda: "COM9" in self.ctl.failed_ports))
        self.wait_idle()
        self.assertEqual(self.rows()["COM9"].chip_badge.text(), "Port not found")
        self.assertEqual(self.status_of("COM9"), "Unavailable")
        self.assertEqual(self.win.status_bar.activity.text(), "0 of 1 device ready to flash")
        calls = len(self.backend.detect_calls)
        for _ in range(5):
            self.ctl.auto_detect()
            process_events(20)
        self.wait_idle()
        self.assertEqual(len(self.backend.detect_calls), calls, "no retry before UNKNOWN_CHIP_RETRY_S")
        # Manual rescan forgets the failure, resets job states and identifies again
        self.backend.chips["COM9"] = DetectionResult("esp32")
        self.rows()["COM9"].set_status("Done")
        self.ctl.rescan()
        self.assertEqual(self.rows()["COM9"].property("state"), "idle")
        self.assertTrue(wait_until(lambda: self.ctl.chip_cache.get("COM9") == "esp32"))
        self.assertEqual(self.rows()["COM9"].chip_badge.text(), "ESP32")
        self.wait_idle()

    def test_unsupported_chip_is_labelled(self):
        self.backend.add("COM6", chip="esp32c6")
        self.ctl.start()
        self.assertTrue(wait_until(lambda: self.ctl.chip_cache.get("COM6") == "esp32c6"))
        self.assertEqual(self.rows()["COM6"].chip_badge.text(), "ESP32-C6")
        self.assertEqual(self.status_of("COM6"), "Unsupported")
        self.wait_idle()

    def test_port_enumeration_failure_is_logged_and_survived(self):
        with mock.patch.object(controller_mod, "detect_ports", side_effect=OSError("wmi down")):
            self.ctl.start()
        self.assertIn("Could not enumerate", self.win.console.view.toPlainText())
        self.backend.add("COM3")
        self.ctl.auto_detect()
        self.assertIn("COM3", self.rows())
        self.wait_idle()


class SelectionTest(ControllerTestCase):
    def test_select_all_clear_and_flash_button(self):
        self.backend.add("COM3")
        self.backend.add("COM4")
        self.ctl.start()
        self.wait_idle()
        toolbar = self.win.toolbar
        self.assertFalse(toolbar.flash_btn.isEnabled())
        toolbar.select_all.click()
        self.assertEqual(self.win.selected_ports(), ["COM3", "COM4"])
        self.assertTrue(toolbar.flash_btn.isEnabled())
        self.assertEqual(toolbar.flash_btn.text(), "Flash 2 devices")
        toolbar.clear_selection.click()
        self.assertEqual(self.win.selected_ports(), [])
        self.assertFalse(toolbar.flash_btn.isEnabled())
        self.assertEqual(toolbar.flash_btn.text(), "Flash selected")

    def test_flash_without_selection_warns(self):
        self.backend.add("COM3")
        self.ctl.start()
        self.wait_idle()
        with mock.patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Ok) as warn:
            self.ctl.flash_selected()
        warn.assert_called_once()
        self.assertFalse(self.ctl.is_flashing)


class FlashJobTest(ControllerTestCase):
    def start_job(self, ports):
        for port in ports:
            self.rows()[port].set_selected(True)
        self.ctl.flash_selected()
        self.assertTrue(self.ctl.is_flashing)
        self.assertFalse(self.ctl.timer.isActive(), "scanner pauses during a job")
        self.assertFalse(self.win.toolbar.flash_btn.isEnabled())
        self.assertFalse(self.win.toolbar.rescan_btn.isEnabled())
        self.assertFalse(self.rows()[ports[0]].checkbox.isEnabled())

    def finish_job(self):
        self.assertTrue(wait_until(lambda: not self.ctl.is_flashing, 15000))
        self.wait_idle()
        self.assertTrue(self.ctl.timer.isActive(), "scanner resumes after the job")
        self.assertTrue(self.win.toolbar.flash_btn.isEnabled())
        self.assertFalse(self.win.status_bar.progress.isVisibleTo(self.win))

    def test_two_devices_succeed(self):
        self.backend.add("COM3")
        self.backend.add("COM4")
        self.ctl.start()
        self.wait_idle()
        self.start_job(["COM3", "COM4"])
        self.finish_job()
        self.assertEqual(self.status_of("COM3"), "Done")
        self.assertEqual(self.status_of("COM4"), "Done")
        process_events(300)          # let the progress animation settle
        self.assertEqual(self.rows()["COM3"].progress.value(), 100)
        self.assertEqual(self.win.status_bar.activity.text(), "Completed · 2 flashed successfully")
        text = self.win.console.view.toPlainText()
        self.assertIn("Job finished: 2 succeeded, 0 failed", text)
        self.assertEqual(sorted(self.backend.flash_calls), ["COM3", "COM4"])

    def test_mixed_results_and_overall_progress(self):
        self.backend.add("COM3")
        self.backend.add("COM4")
        self.backend.add("COM5")
        self.backend.outcomes["COM4"] = False
        self.backend.outcomes["COM5"] = RuntimeError("worker bug")
        self.ctl.start()
        self.wait_idle()

        overall: list[int] = []
        original = self.win.set_overall_progress

        def record(value):
            if value is not None:
                overall.append(value)
            original(value)

        self.win.set_overall_progress = record
        self.start_job(["COM3", "COM4", "COM5"])
        self.finish_job()
        self.assertEqual(self.status_of("COM3"), "Done")
        self.assertEqual(self.status_of("COM4"), "Error")
        self.assertEqual(self.status_of("COM5"), "Error")
        self.assertEqual(overall, sorted(overall), "overall progress must never go backwards")
        self.assertEqual(overall[-1], 100, "job completion means 100% even with failures")
        self.assertEqual(self.win.status_bar.activity.text(), "Completed · 1 succeeded, 2 failed")
        self.assertEqual(self.rows()["COM4"].property("state"), "error")

    def test_single_device_instant_failure(self):
        self.backend.add("COM3")
        self.backend.outcomes["COM3"] = False
        self.ctl.start()
        self.wait_idle()
        self.start_job(["COM3"])
        self.finish_job()
        self.assertEqual(self.status_of("COM3"), "Error")
        self.assertEqual(self.win.status_bar.activity.text(), "Completed · 0 succeeded, 1 failed")

    def test_flash_requests_are_ignored_while_a_job_runs(self):
        self.backend.add("COM3")
        self.backend.release.clear()
        self.ctl.start()
        self.wait_idle()
        self.start_job(["COM3"])
        self.assertTrue(wait_until(lambda: len(self.backend.flash_calls) == 1))
        self.ctl.flash_selected()
        self.ctl.rescan()
        process_events(50)
        self.assertEqual(len(self.backend.flash_calls), 1)
        self.backend.release.set()
        self.finish_job()

    def test_post_flash_rescan_picks_up_new_device(self):
        self.backend.add("COM3")
        self.ctl.start()
        self.wait_idle()
        self.start_job(["COM3"])
        self.backend.add("COM8", chip="esp32s2")
        self.finish_job()
        self.assertTrue(wait_until(lambda: "COM8" in self.rows(), 5000))
        self.assertEqual(self.status_of("COM3"), "Done", "previous result survives the rescan")
        self.wait_idle()


class ShutdownTest(ControllerTestCase):
    def test_shutdown_during_flash_stops_threads(self):
        self.backend.add("COM3")
        self.backend.release.clear()
        self.ctl.start()
        self.wait_idle()
        self.rows()["COM3"].set_selected(True)
        self.ctl.flash_selected()
        self.assertTrue(self.ctl.is_flashing)
        with mock.patch.object(controller_mod.toolchain, "terminate_all") as terminate:
            self.backend.release.set()
            self.ctl.shutdown()
        terminate.assert_called_once()
        self.assertEqual(self.ctl._threads, [])
        self.assertFalse(self.ctl.timer.isActive())

    def test_close_is_refused_when_user_keeps_flashing(self):
        self.backend.add("COM3")
        self.backend.release.clear()
        self.ctl.start()
        self.wait_idle()
        self.rows()["COM3"].set_selected(True)
        self.ctl.flash_selected()
        with mock.patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            self.assertFalse(self.ctl.request_close())
        self.assertTrue(self.ctl.is_flashing)
        self.backend.release.set()
        self.assertTrue(wait_until(lambda: not self.ctl.is_flashing, 10000))
        self.assertTrue(self.ctl.request_close())


if __name__ == "__main__":
    unittest.main()
