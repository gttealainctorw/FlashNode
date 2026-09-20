import requests
import os

from app.paths import firmware_dir

# MicroPython stable firmware URLs
FIRMWARE_URLS = {
    "esp32":    "https://micropython.org/resources/firmware/ESP32_GENERIC-20241025-v1.24.0.bin",
    "esp32c3":  "https://micropython.org/resources/firmware/ESP32_GENERIC_C3-20241025-v1.24.0.bin",
    "esp32s2":  "https://micropython.org/resources/firmware/ESP32_GENERIC_S2-20241025-v1.24.0.bin",
    "esp32s3":  "https://micropython.org/resources/firmware/ESP32_GENERIC_S3-20241025-v1.24.0.bin",
}



def get_fw_path(chip):
    """Cache location for a chip's image (project ./firmware in development,
    the per-user data folder when packaged, so it works from Program Files)."""
    directory = firmware_dir()
    os.makedirs(directory, exist_ok=True)
    return os.path.join(str(directory), f"{chip}.bin")


def download_fw(chip, log_cb=None):
    """Download firmware for the given chip. Returns path or None on failure."""
    if chip not in FIRMWARE_URLS:
        if log_cb:
            log_cb(f"[ERROR] No firmware URL for chip: {chip}")
        return None

    path = get_fw_path(chip)
    if os.path.exists(path):
        if log_cb:
            log_cb(f"[INFO] Using cached firmware: {path}")
        return path

    url = FIRMWARE_URLS[chip]
    if log_cb:
        log_cb(f"[INFO] Downloading firmware for {chip}...")
        log_cb(f"[INFO] URL: {url}")

    try:
        r = requests.get(url, timeout=60, stream=True)
        r.raise_for_status()

        total = int(r.headers.get("content-length", 0))
        downloaded = 0

        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if log_cb and total:
                    pct = int(downloaded / total * 100)
                    log_cb(f"[DL] {pct}% ({downloaded}/{total} bytes)")

        if log_cb:
            log_cb(f"[OK] Firmware saved to {path}")
        return path

    except requests.RequestException as e:
        if log_cb:
            log_cb(f"[ERROR] Download failed: {e}")
        # Clean up partial file
        if os.path.exists(path):
            os.remove(path)
        return None
