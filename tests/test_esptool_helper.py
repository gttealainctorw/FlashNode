"""The helper process: marker protocol, error classification, real esptool invocation."""

import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

from tests.helpers import ROOT  # noqa: F401

from app import esptool_helper, toolchain

PORT_MISSING = "Could not open COM7, the port is busy or doesn't exist.\n(FileNotFoundError(2))"
PORT_BUSY = "Could not open COM7, the port is busy or doesn't exist.\n(PermissionError(13, 'Access is denied.'))"
# Real message captured on a Spanish Windows with COM3 held by another process (hardware run)
PORT_BUSY_ES = ("Could not open COM3, the port is busy or doesn't exist.\n"
                "(could not open port 'COM3': PermissionError(13, 'Acceso denegado.', None, 5))\n")


class MarkerLoggerTest(unittest.TestCase):
    def test_progress_markers_from_esptool_logger(self):
        """Installing the marker logger makes esptool's own progress_bar emit @@PROGRESS."""
        from esptool.logger import log

        original_class = log.__class__
        buffer = io.StringIO()
        try:
            esptool_helper._install_marker_logger()
            with redirect_stdout(buffer):
                total = 1000
                for sent in (0, 100, 105, 500, 1000):
                    log.progress_bar(sent, total, prefix="Writing at 0x00010000 ",
                                     suffix=f" {sent}/{total} bytes...")
                log.progress_bar(3, 10, prefix="Reading from 0x0 ", suffix="")   # not a write: no marker
        finally:
            log.__class__ = original_class

        markers = [line for line in buffer.getvalue().splitlines() if line.startswith("@@PROGRESS")]
        self.assertEqual(markers, ["@@PROGRESS 0", "@@PROGRESS 10", "@@PROGRESS 50", "@@PROGRESS 100"])
        # Human-readable progress lines are still printed (one per call, no ANSI overwriting)
        self.assertIn("Writing at 0x00010000 [", buffer.getvalue())
        self.assertNotIn("\x1b[", buffer.getvalue())

    def test_classify_fatal_messages(self):
        c = esptool_helper._classify_fatal
        self.assertEqual(c(PORT_MISSING), "PORT")
        self.assertEqual(c(PORT_BUSY), "PORT_BUSY")
        self.assertEqual(c(PORT_BUSY_ES), "PORT_BUSY")
        self.assertEqual(c("Failed to connect to ESP32: No serial data received."), "NO_RESPONSE")
        self.assertEqual(c("Unexpected chip magic value 0x1. Failed to autodetect chip type."), "UNKNOWN_CHIP")
        self.assertEqual(c("Packet content transfer stopped"), "FATAL")

    def test_usage_errors(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.assertEqual(esptool_helper.main([]), esptool_helper.EXIT_USAGE)
            self.assertEqual(esptool_helper.main(["bogus"]), esptool_helper.EXIT_USAGE)
            self.assertEqual(esptool_helper.main(["chip-id"]), esptool_helper.EXIT_USAGE)
        self.assertEqual(buffer.getvalue().count("@@ERROR INTERNAL"), 3)


class HelperProcessTest(unittest.TestCase):
    """Runs the real helper as a subprocess exactly like the application does."""

    def test_version_mode(self):
        lines = []
        result = toolchain.run_helper(["version"], lines.append, timeout=60)
        self.assertTrue(result.ok, result)
        self.assertTrue(any(line.startswith("esptool ") for line in lines), lines)

    def test_chip_id_missing_port_reports_port_error(self):
        lines = []
        result = toolchain.run_helper(["chip-id", "--port", "COM253"], lines.append, timeout=60)
        self.assertFalse(result.ok)
        self.assertEqual(result.returncode, esptool_helper.EXIT_FATAL)
        self.assertEqual(result.error_kind, "PORT")
        self.assertIn("COM253", result.error_message)

    def test_run_mode_uses_new_command_names(self):
        """`erase-flash` reaches esptool (it fails on the port, not on the command)."""
        lines = []
        result = toolchain.run_helper(["run", "--chip", "esp32", "--port", "COM253", "erase-flash"],
                                      lines.append, timeout=60)
        self.assertEqual(result.error_kind, "PORT")
        self.assertTrue(any(line.startswith("esptool v") for line in lines), lines)
        self.assertFalse(any("Deprecated" in line for line in lines), lines)

    def test_timeout_kills_the_child(self):
        # Use a plain Python sleep through the same launch path to simulate a hung helper.
        cmd = [sys.executable, "-c", "import time; print('x', flush=True); time.sleep(30)"]
        with mock.patch.object(toolchain, "helper_command", return_value=cmd):
            result = toolchain.run_helper(["version"], timeout=1.5)
        self.assertEqual(result.error_kind, "TIMEOUT")
        self.assertEqual(toolchain.active_count(), 0)

    def test_launch_failure_is_reported_not_raised(self):
        with mock.patch.object(toolchain, "helper_command", return_value=["definitely-not-a-program.exe"]):
            result = toolchain.run_helper(["version"])
        self.assertEqual(result.error_kind, "LAUNCH")
        self.assertIn("helper", result.error_message)

    def test_terminate_all_kills_running_helpers(self):
        cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
        proc = subprocess.Popen(cmd, **toolchain._popen_kwargs())
        with toolchain._active_lock:
            toolchain._active.add(proc)
        toolchain.terminate_all()
        proc.wait(timeout=5)
        proc.stdout.close()
        with toolchain._active_lock:
            toolchain._active.discard(proc)
        self.assertNotEqual(proc.returncode, None)


if __name__ == "__main__":
    unittest.main()
