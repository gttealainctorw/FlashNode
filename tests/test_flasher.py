"""flash(): the detect → firmware → erase → write sequence over a replayed helper."""

import unittest
from unittest import mock

from tests.helpers import fixture

from app import flasher, toolchain
from app.detect_chip import DetectionResult


class ReplayHelper:
    """Stands in for toolchain.run_helper: replays fixture output per helper mode."""

    def __init__(self, erase="erase_flash_success.txt", write="write_flash_success.txt"):
        self.erase, self.write = erase, write
        self.calls: list[list[str]] = []

    def __call__(self, args, on_line=None, timeout=None):
        self.calls.append(list(args))
        name = self.erase if "erase-flash" in args else self.write
        result = toolchain.HelperResult(returncode=0)
        for line in fixture(name).splitlines():
            if not line.strip():
                continue
            toolchain._interpret_marker(line, result)
            if on_line:
                on_line(line)
        if result.error_kind:
            result.returncode = 2
        return result


class FlashSequenceTest(unittest.TestCase):
    def run_flash(self, port="COM3", chip="esp32", replay=None, fw="C:/fw/esp32.bin"):
        replay = replay or ReplayHelper()
        log: list[str] = []
        with mock.patch.object(flasher, "detect_chip", return_value=DetectionResult(chip)), \
             mock.patch.object(flasher, "download_fw", return_value=fw), \
             mock.patch.object(toolchain, "run_helper", side_effect=replay):
            ok = flasher.flash(port, log.append)
        return ok, log, replay

    def test_success_emits_progress_protocol_and_uses_new_commands(self):
        ok, log, replay = self.run_flash()
        self.assertTrue(ok)
        progress = [int(l.split("[PROGRESS]")[1]) for l in log if "[PROGRESS]" in l]
        self.assertEqual(progress, [0, 9, 49, 100])
        self.assertEqual(progress, sorted(progress))            # never goes backwards
        self.assertIn("[OK] Flash erased.", log)
        self.assertTrue(any(l.startswith("[✓] COM3 flashed successfully (esp32)") for l in log))
        # helper invocations: erase then write, no shell, hyphenated commands, ESP32 offset 0x1000
        self.assertEqual(replay.calls[0], ["run", "--chip", "esp32", "--port", "COM3", "erase-flash"])
        self.assertEqual(replay.calls[1][:7], ["run", "--chip", "esp32", "--port", "COM3", "write-flash", "-z"])
        self.assertEqual(replay.calls[1][7], "0x1000")
        self.assertEqual(replay.calls[1][8], "C:/fw/esp32.bin")
        # marker lines never leak into the log
        self.assertFalse(any(l.startswith("@@") for l in log))

    def test_offsets_per_chip(self):
        for chip, offset in (("esp32", "0x1000"), ("esp32s3", "0x0"), ("esp32c3", "0x0"), ("esp32s2", "0x0")):
            with self.subTest(chip=chip):
                _, _, replay = self.run_flash(chip=chip, fw=f"{chip}.bin")
                self.assertEqual(replay.calls[1][7], offset)

    def test_write_failure_is_reported(self):
        ok, log, _ = self.run_flash(replay=ReplayHelper(write="write_flash_failure.txt"))
        self.assertFalse(ok)
        self.assertTrue(any("[ERROR] Packet content transfer stopped" in l for l in log), log)
        self.assertTrue(any(l.startswith("[ERROR] Flash write failed") for l in log), log)
        progress = [int(l.split("[PROGRESS]")[1]) for l in log if "[PROGRESS]" in l]
        self.assertEqual(progress, [0, 23])

    def test_erase_failure_stops_before_write(self):
        replay = ReplayHelper(erase="port_busy.txt")
        ok, log, replay = self.run_flash(replay=replay)
        self.assertFalse(ok)
        self.assertEqual(len(replay.calls), 1)
        self.assertTrue(any(l.startswith("[ERROR] Erase failed") for l in log), log)

    def test_detection_failure(self):
        log = []
        with mock.patch.object(flasher, "detect_chip", return_value=DetectionResult(None, "NO_RESPONSE", "No serial data received.")):
            ok = flasher.flash("COM9", log.append)
        self.assertFalse(ok)
        self.assertTrue(any("Could not detect chip on COM9: No response" in l for l in log), log)

    def test_unsupported_chip_never_reaches_esptool(self):
        replay = ReplayHelper()
        log = []
        with mock.patch.object(flasher, "detect_chip", return_value=DetectionResult("esp32c6")), \
             mock.patch.object(flasher, "download_fw") as download, \
             mock.patch.object(toolchain, "run_helper", side_effect=replay):
            ok = flasher.flash("COM5", log.append)
        self.assertFalse(ok)
        self.assertTrue(any("ESP32-C6 is not supported" in l for l in log), log)
        download.assert_not_called()
        self.assertEqual(replay.calls, [])

    def test_missing_firmware(self):
        log = []
        with mock.patch.object(flasher, "detect_chip", return_value=DetectionResult("esp32")), \
             mock.patch.object(flasher, "download_fw", return_value=None):
            ok = flasher.flash("COM3", log.append)
        self.assertFalse(ok)
        self.assertIn("[ERROR] Firmware unavailable for esp32.", log)

    def test_unexpected_exception_is_logged_not_raised(self):
        log = []
        with mock.patch.object(flasher, "detect_chip", side_effect=RuntimeError("kaboom")):
            ok = flasher.flash("COM3", log.append)
        self.assertFalse(ok)
        self.assertIn("[FATAL ERROR] kaboom", log)


if __name__ == "__main__":
    unittest.main()
