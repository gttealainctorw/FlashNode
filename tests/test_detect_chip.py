"""Deterministic chip identification from helper/esptool output."""

import unittest
from unittest import mock

from tests.helpers import fixture

from app import detect_chip, toolchain


def helper_result_from(text: str, returncode: int) -> toolchain.HelperResult:
    """Interpret marker lines the way toolchain.run_helper does."""
    result = toolchain.HelperResult(returncode=returncode)
    for line in text.splitlines():
        toolchain._interpret_marker(line, result)
    return result


class ParseChipNameTest(unittest.TestCase):
    def test_marker_fixtures(self):
        expected = {
            "chip_id_esp32.txt": "esp32",
            "chip_id_esp32s2.txt": "esp32s2",
            "chip_id_esp32s3.txt": "esp32s3",
            "chip_id_esp32c3.txt": "esp32c3",
            "chip_id_esp32c6.txt": "esp32c6",
            "ansi.txt": "esp32c3",
        }
        for name, chip in expected.items():
            with self.subTest(fixture=name):
                result = detect_chip.classify(fixture(name))
                self.assertTrue(result.ok)
                self.assertEqual(result.chip, chip)

    def test_cli_style_lines_are_parsed_exactly(self):
        self.assertEqual(detect_chip.classify(fixture("cli_connected_esp32s3.txt")).chip, "esp32s3")
        self.assertEqual(detect_chip.classify(fixture("cli_connected_esp32.txt")).chip, "esp32")

    def test_s3_never_becomes_s2_and_c3_never_becomes_generic(self):
        self.assertEqual(detect_chip.classify("Detecting chip type... ESP32-S3\n").chip, "esp32s3")
        self.assertEqual(detect_chip.classify("Detecting chip type... ESP32-C3\n").chip, "esp32c3")
        self.assertEqual(detect_chip.classify("Detecting chip type... ESP32-C6\n").chip, "esp32c6")
        # The marker wins over any later mention of another chip name
        self.assertEqual(detect_chip.classify("@@CHIP ESP32\nESP32-C3 mentioned later\n").chip, "esp32")

    def test_unknown_or_malformed_output_is_not_guessed(self):
        for name in ("malformed.txt", "empty.txt"):
            with self.subTest(fixture=name):
                result = detect_chip.classify(fixture(name))
                self.assertFalse(result.ok)
                self.assertIsNone(result.chip)
                self.assertEqual(result.error, "UNKNOWN_CHIP")

    def test_unrecognised_marker_name(self):
        result = detect_chip.classify("@@CHIP ESP32-XYZ\n")
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "UNKNOWN_CHIP")
        self.assertIn("ESP32-XYZ", result.detail)

    def test_error_markers_are_classified(self):
        cases = {
            "port_busy.txt": "PORT_BUSY",
            "no_response.txt": "NO_RESPONSE",
            "unknown_chip.txt": "UNKNOWN_CHIP",
        }
        for name, kind in cases.items():
            with self.subTest(fixture=name):
                text = fixture(name)
                result = detect_chip.classify(text, helper_result_from(text, 2))
                self.assertFalse(result.ok)
                self.assertEqual(result.error, kind)
                self.assertTrue(result.detail)
                self.assertIn(result.error_label, detect_chip.ERROR_LABELS.values())

    def test_timeout_and_exit_code_without_marker(self):
        timed_out = toolchain.HelperResult(returncode=-9, error_kind="TIMEOUT",
                                           error_message="No result after 20 seconds")
        self.assertEqual(detect_chip.classify("Connecting....\n", timed_out).error, "TIMEOUT")
        crashed = toolchain.HelperResult(returncode=3)
        self.assertEqual(detect_chip.classify("", crashed).error, "FATAL")


class DetectChipRunnerTest(unittest.TestCase):
    def test_uses_helper_and_never_raises(self):
        def fake_run(args, on_line=None, timeout=None):
            self.assertEqual(args, ["chip-id", "--port", "COM4"])
            for line in fixture("chip_id_esp32s2.txt").splitlines():
                on_line(line)
            return toolchain.HelperResult(returncode=0)

        with mock.patch.object(toolchain, "run_helper", side_effect=fake_run):
            self.assertEqual(detect_chip.detect_chip("COM4").chip, "esp32s2")

        with mock.patch.object(toolchain, "run_helper", side_effect=RuntimeError("boom")):
            result = detect_chip.detect_chip("COM4")
            self.assertFalse(result.ok)
            self.assertEqual(result.error, "INTERNAL")

    def test_real_helper_on_missing_port(self):
        """Integration: runs the real esptool helper process (no hardware needed)."""
        result = detect_chip.detect_chip("COM254", timeout=30)
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "PORT")
        self.assertIn("COM254", result.detail)
        self.assertEqual(toolchain.active_count(), 0)


if __name__ == "__main__":
    unittest.main()
