"""UI components: device row state machine, list syncing, console, toolbar, elision."""

import unittest

from tests.helpers import process_events, qapp

from app.ui.components import ElidedLabel
from app.ui.console import ConsoleView, parse_line
from app.ui.device_list import DETECTING, DeviceList, DeviceRow, status_style
from app.ui.toolbar import DeviceToolbar


class StatusStyleTest(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(status_style("Queued"), ("warning", "queued"))
        self.assertEqual(status_style("Connecting"), ("primary", "busy"))
        self.assertEqual(status_style("Downloading 42%"), ("primary", "busy"))
        self.assertEqual(status_style("Erasing"), ("primary", "busy"))
        self.assertEqual(status_style("Writing"), ("primary", "busy"))
        self.assertEqual(status_style("Flashing"), ("primary", "flashing"))
        self.assertEqual(status_style("Flashing 73%"), ("primary", "flashing"))
        self.assertEqual(status_style("Done"), ("success", "done"))
        self.assertEqual(status_style("Error"), ("error", "error"))
        self.assertEqual(status_style("Idle"), ("neutral", "idle"))
        self.assertEqual(status_style("anything else"), ("neutral", "idle"))


class DeviceRowStateTest(unittest.TestCase):
    def setUp(self):
        qapp()

    def test_identification_states(self):
        row = DeviceRow("COM3", "USB Serial", DETECTING)
        self.assertEqual(row.chip_badge.text(), "Detecting…")
        self.assertEqual(row.status_text.text(), "Identifying…")
        self.assertFalse(row.progress.isVisibleTo(row))

        row.set_chip("esp32s3")
        self.assertEqual(row.chip_badge.text(), "ESP32-S3")
        self.assertEqual(row.chip_badge.property("tone"), "info")
        self.assertEqual(row.status_text.text(), "Ready")

        row.set_chip("esp32h2")
        self.assertEqual(row.chip_badge.property("tone"), "warning")
        self.assertEqual(row.status_text.text(), "Unsupported")

        row.set_chip_error("No response", "No serial data received.")
        self.assertEqual(row.chip_badge.text(), "No response")
        self.assertEqual(row.status_text.text(), "Unavailable")
        self.assertIsNone(row.chip)

    def test_job_lifecycle_success(self):
        row = DeviceRow("COM3", "", "esp32")
        for status, state in (("Queued", "queued"), ("Connecting", "busy"), ("Downloading 10%", "busy"),
                              ("Erasing", "busy"), ("Flashing 0%", "flashing")):
            row.set_status(status)
            self.assertEqual(row.property("state"), state, status)
            self.assertTrue(row.progress.isVisibleTo(row))
        self.assertEqual(row.progress.maximum(), 100, "flashing uses a determinate bar")
        row.set_progress(55)
        process_events(300)
        self.assertEqual(row.progress.value(), 55)
        row.set_status("Done")
        process_events(300)
        self.assertEqual(row.property("state"), "done")
        self.assertEqual(row.progress.value(), 100, "Done always shows a full bar")
        self.assertEqual(row.progress.property("tone"), "success")
        # Back to idle restores the identification-derived status, not "Done"
        row.set_status("Idle")
        self.assertEqual(row.status_text.text(), "Ready")
        self.assertFalse(row.progress.isVisibleTo(row))

    def test_busy_uses_indeterminate_bar_and_error_keeps_progress(self):
        row = DeviceRow("COM3", "", "esp32")
        row.set_status("Erasing")
        self.assertEqual(row.progress.maximum(), 0, "indeterminate")
        row.set_status("Flashing 0%")
        row.set_progress(40)
        process_events(300)
        row.set_status("Error")
        self.assertEqual(row.property("state"), "error")
        self.assertEqual(row.progress.value(), 40)
        self.assertEqual(row.progress.property("tone"), "error")

    def test_selection_toggle_and_lock(self):
        row = DeviceRow("COM3", "", "esp32")
        seen = []
        row.toggled.connect(lambda port, sel: seen.append((port, sel)))
        row.set_selected(True)
        self.assertTrue(row.is_selected())
        self.assertEqual(row.property("selected"), True)
        row.set_selection_enabled(False)
        self.assertFalse(row.checkbox.isEnabled())
        self.assertEqual(seen, [("COM3", True)])


class DeviceListSyncTest(unittest.TestCase):
    def setUp(self):
        qapp()
        self.lst = DeviceList()

    def ports(self, *names):
        return [{"device": n, "description": f"desc {n}", "hwid": ""} for n in names]

    def test_rows_are_reused_and_ordered(self):
        self.lst.set_devices(self.ports("COM3", "COM4"), {"COM3": "esp32"})
        a, b = self.lst.rows["COM3"], self.lst.rows["COM4"]
        a.set_selected(True)
        b.set_status("Error")
        self.lst.set_devices(self.ports("COM4", "COM3", "COM9"), {"COM3": "esp32", "COM4": "esp32c3"})
        self.assertIs(self.lst.rows["COM3"], a)
        self.assertIs(self.lst.rows["COM4"], b)
        self.assertTrue(a.is_selected())
        self.assertEqual(b.status_text.text(), "Error")
        self.assertEqual(b.chip_badge.text(), "ESP32-C3")
        order = [self.lst.container_layout.itemAt(i).widget().port
                 for i in range(3)]
        self.assertEqual(order, ["COM4", "COM3", "COM9"])
        self.assertEqual(self.lst.selected_ports(), ["COM3"])

    def test_removed_rows_drop_their_selection(self):
        self.lst.set_devices(self.ports("COM3", "COM4"), {})
        self.lst.select_all()
        self.lst.set_devices(self.ports("COM4"), {})
        self.assertEqual(self.lst.selected_ports(), ["COM4"])
        self.lst.set_devices([], {})
        self.assertEqual(self.lst.selected_ports(), [])
        self.assertTrue(self.lst.empty.isVisibleTo(self.lst))

    def test_selection_lock_applies_to_new_rows(self):
        self.lst.set_selection_enabled(False)
        self.lst.set_devices(self.ports("COM3"), {})
        self.assertFalse(self.lst.rows["COM3"].checkbox.isEnabled())


class ToolbarStateTest(unittest.TestCase):
    def test_texts_and_enabled_states(self):
        qapp()
        tb = DeviceToolbar()
        tb.set_device_count(0)
        self.assertFalse(tb.flash_btn.isEnabled())
        self.assertFalse(tb.select_all.isVisibleTo(tb))
        tb.set_device_count(3)
        tb.set_selected_count(0)
        self.assertEqual(tb.hint.text(), "Select devices to flash")
        tb.set_selected_count(1)
        self.assertEqual(tb.flash_btn.text(), "Flash 1 device")
        self.assertTrue(tb.flash_btn.isEnabled())
        tb.set_flashing(True)
        self.assertEqual(tb.flash_btn.text(), "Flashing…")
        self.assertFalse(tb.flash_btn.isEnabled())
        self.assertFalse(tb.rescan_btn.isEnabled())
        self.assertFalse(tb.select_all.isEnabled())
        tb.set_flashing(False)
        self.assertTrue(tb.flash_btn.isEnabled())


class ConsoleTest(unittest.TestCase):
    def test_parse_line(self):
        self.assertEqual(parse_line("[INFO] COM3 → esp32")[:2], (None, "INFO"))
        self.assertEqual(parse_line("[COM3] [ERROR] Erase failed")[0], "COM3")
        self.assertEqual(parse_line("[COM3] [ERROR] Erase failed")[1], "ERROR")
        self.assertEqual(parse_line("[COM3] [ERROR] Erase failed")[3], "Erase failed")
        self.assertEqual(parse_line("[✓] COM3 flashed")[1], "OK")
        self.assertEqual(parse_line("[FATAL ERROR] x")[1], "FATAL")
        self.assertEqual(parse_line("A fatal error occurred: timed out")[1], "ERROR")
        self.assertEqual(parse_line("Hash of data verified.")[1], "")

    def test_bounded_buffer_and_scroll_following(self):
        from app.config import CONSOLE_MAX_LINES

        qapp()
        view = ConsoleView()
        view.resize(600, 200)
        view.show()
        process_events(30)
        for i in range(CONSOLE_MAX_LINES + 500):
            view.append(f"[INFO] line {i}")
        self.assertEqual(view.document().blockCount(), CONSOLE_MAX_LINES)
        bar = view.verticalScrollBar()
        self.assertEqual(bar.value(), bar.maximum(), "follows output while at the bottom")
        bar.setValue(0)
        view.append("[INFO] while reading history")
        self.assertEqual(bar.value(), 0, "does not steal the scroll position")
        bar.setValue(bar.maximum())
        view.append("[INFO] back at bottom")
        self.assertEqual(bar.value(), bar.maximum())
        view.close()


class ElidedLabelTest(unittest.TestCase):
    def test_elides_and_restores(self):
        qapp()
        label = ElidedLabel("A very long device description that does not fit in a narrow column")
        label.resize(120, 20)
        label.show()
        process_events(30)
        shown = label.property("text") if False else super(ElidedLabel, label).text()
        self.assertTrue(shown.endswith("…"))
        self.assertEqual(label.text(), "A very long device description that does not fit in a narrow column")
        self.assertTrue(label.toolTip())
        label.resize(900, 20)
        process_events(30)
        self.assertFalse(super(ElidedLabel, label).text().endswith("…"))
        self.assertEqual(label.toolTip(), "")
        label.close()


if __name__ == "__main__":
    unittest.main()
