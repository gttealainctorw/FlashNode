# Firmware cache

FlashNode does not ship firmware. When a chip family is flashed for the first
time, the official MicroPython generic image is downloaded from
<https://micropython.org/download/> and cached:

* running from source: this `firmware/` directory
* packaged application: `%LOCALAPPDATA%\FlashNode\firmware\`

The images are **not** committed to the repository (`firmware/*.bin` is
ignored). The pinned builds, their URLs and SHA-256 checksums are:

| Chip | File | SHA-256 |
|------|------|---------|
| ESP32 | `ESP32_GENERIC-20241025-v1.24.0.bin` | `648e655fdaa8c31ece4e8f2a5c7815b015a7bca1c8db56246287799164ad9bff` |
| ESP32-C3 | `ESP32_GENERIC_C3-20241025-v1.24.0.bin` | `48dc337687608c4f98398a0bf1242142bf5282738ba8256aaf517993cf40c27c` |
| ESP32-S2 | `ESP32_GENERIC_S2-20241025-v1.24.0.bin` | not downloaded during validation |
| ESP32-S3 | `ESP32_GENERIC_S3-20241025-v1.24.0.bin` | not downloaded during validation |

URLs are defined in `app/firmware.py`; flash offsets in `app/chips.py`.
MicroPython is distributed under the MIT License.
