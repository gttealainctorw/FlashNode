"""The chip table must agree with the esptool that is actually installed."""

import unittest

from tests.helpers import ROOT  # noqa: F401  (sets sys.path)

from app import chips


class ChipTableTest(unittest.TestCase):
    def test_table_matches_installed_esptool(self):
        from esptool.targets import CHIP_DEFS

        for chip_id, cls in CHIP_DEFS.items():
            with self.subTest(chip=chip_id):
                self.assertIn(chip_id, chips.CHIPS, f"esptool knows {chip_id!r}; add it to app/chips.py")
                self.assertEqual(chips.CHIPS[chip_id].esptool_name, cls.CHIP_NAME)

    def test_lookup_is_exact(self):
        self.assertEqual(chips.chip_from_esptool_name("ESP32-S3").id, "esp32s3")
        self.assertEqual(chips.chip_from_esptool_name("  ESP32-C3 ").id, "esp32c3")
        self.assertIsNone(chips.chip_from_esptool_name("esp32-s3"))      # case matters
        self.assertIsNone(chips.chip_from_esptool_name("ESP32-S3X"))
        self.assertIsNone(chips.chip_from_esptool_name("ESP32-C"))
        self.assertIsNone(chips.chip_from_esptool_name(""))

    def test_flashable_set_matches_firmware_urls(self):
        from app.firmware import FIRMWARE_URLS

        flashable = {c.id for c in chips.CHIPS.values() if c.flashable}
        self.assertEqual(flashable, set(FIRMWARE_URLS))

    def test_labels(self):
        self.assertEqual(chips.chip_label("esp32c6"), "ESP32-C6")
        self.assertEqual(chips.chip_label(None), "")
        self.assertEqual(chips.chip_label("something"), "SOMETHING")


if __name__ == "__main__":
    unittest.main()
