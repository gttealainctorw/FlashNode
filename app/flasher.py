"""Serial port enumeration and the flashing sequence (detect → firmware → erase → write).

All esptool work goes through the bundled helper (``app.toolchain``); progress
reaches the caller as ``[PROGRESS] <pct>`` lines, exactly as before.
"""

import serial.tools.list_ports

from app import chips, toolchain
from app.detect_chip import detect_chip
from app.esptool_helper import MARKER_CHIP, MARKER_ERROR, MARKER_PROGRESS
from app.firmware import download_fw


def detect_ports():
    ports = serial.tools.list_ports.comports()
    detected = []

    for p in ports:
        detected.append({
            "device": p.device,
            "description": p.description,
            "hwid": p.hwid
        })

    return detected


def _forward(log_cb):
    """Translate helper marker lines into the log protocol; pass everything else through."""
    def handler(line: str) -> None:
        if line.startswith(MARKER_PROGRESS + " "):
            log_cb(f"[PROGRESS] {line.split(' ', 1)[1].strip()}")
        elif line.startswith(MARKER_ERROR + " "):
            kind, _, message = line[len(MARKER_ERROR):].strip().partition(" ")
            log_cb(f"[ERROR] {message.strip() or kind}")
        elif line.startswith(MARKER_CHIP + " "):
            return
        else:
            log_cb(line)
    return handler


def _run(args: list[str], log_cb) -> toolchain.HelperResult:
    return toolchain.run_helper(["run", *args], _forward(log_cb))


def flash(port, log_cb):
    try:
        log_cb(f"[START] Flashing {port}...")

        # STEP 1: Detect chip
        log_cb(f"[INFO] Detecting chip on {port}...")
        detection = detect_chip(port)
        if not detection.ok:
            log_cb(f"[ERROR] Could not detect chip on {port}: {detection.error_label}. {detection.detail}".rstrip())
            return False

        chip = detection.chip
        info = chips.CHIPS[chip]
        log_cb(f"[OK] Chip detected: {chip}")

        if not info.flashable:
            log_cb(f"[ERROR] {info.label} is not supported by FlashNode (no MicroPython image configured).")
            return False

        # STEP 2: Download firmware
        fw = download_fw(chip, log_cb)
        if not fw:
            log_cb(f"[ERROR] Firmware unavailable for {chip}.")
            return False

        # STEP 3: Erase flash
        log_cb(f"[INFO] Erasing flash on {port}...")
        erase = _run(["--chip", chip, "--port", port, "erase-flash"], log_cb)
        if not erase.ok:
            log_cb(f"[ERROR] Erase failed: {erase.error_message}".rstrip(": "))
            return False

        log_cb("[OK] Flash erased.")

        # STEP 4: Write firmware
        offset = f"{info.firmware_offset:#x}"

        log_cb("[INFO] Writing firmware...")
        log_cb(f"[DEBUG] esptool write-flash --chip {chip} --port {port} -z {offset} {fw}")

        write = _run(["--chip", chip, "--port", port, "write-flash", "-z", offset, str(fw)], log_cb)
        if not write.ok:
            log_cb(f"[ERROR] Flash write failed: {write.error_message}".rstrip(": "))
            return False

        log_cb(f"[✓] {port} flashed successfully ({chip})")
        return True

    except Exception as e:
        log_cb(f"[FATAL ERROR] {str(e)}")
        return False
