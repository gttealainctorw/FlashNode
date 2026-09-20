"""Known Espressif chips: identity, esptool naming and flash layout.

``esptool_name`` values are the ``CHIP_NAME`` constants esptool itself reports
(``esptool.targets.CHIP_DEFS``); detection matches them exactly. Chips without a
``firmware_offset`` are recognised but cannot be flashed by this application.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Chip:
    id: str                 # internal id, also the esptool --chip argument
    esptool_name: str       # exact name printed/returned by esptool
    label: str              # what the UI shows
    firmware_offset: int | None = None   # MicroPython image offset, None = not flashable here

    @property
    def flashable(self) -> bool:
        return self.firmware_offset is not None


CHIPS: dict[str, Chip] = {
    c.id: c
    for c in (
        Chip("esp32", "ESP32", "ESP32", 0x1000),
        Chip("esp32s2", "ESP32-S2", "ESP32-S2", 0x0),
        Chip("esp32s3", "ESP32-S3", "ESP32-S3", 0x0),
        Chip("esp32c3", "ESP32-C3", "ESP32-C3", 0x0),
        Chip("esp32c2", "ESP32-C2", "ESP32-C2"),
        Chip("esp32c5", "ESP32-C5", "ESP32-C5"),
        Chip("esp32c6", "ESP32-C6", "ESP32-C6"),
        Chip("esp32c61", "ESP32-C61", "ESP32-C61"),
        Chip("esp32h2", "ESP32-H2", "ESP32-H2"),
        Chip("esp32h21", "ESP32-H21", "ESP32-H21"),
        Chip("esp32h4", "ESP32-H4", "ESP32-H4"),
        Chip("esp32p4", "ESP32-P4", "ESP32-P4"),
        Chip("esp32s31", "ESP32-S31", "ESP32-S31"),
        Chip("esp32e22", "ESP32-E22", "ESP32-E22"),
        Chip("esp8266", "ESP8266", "ESP8266"),
    )
}

BY_ESPTOOL_NAME: dict[str, Chip] = {c.esptool_name: c for c in CHIPS.values()}


def chip_from_esptool_name(name: str) -> Chip | None:
    """Exact (case-sensitive) lookup of an esptool chip name; None when unknown."""
    return BY_ESPTOOL_NAME.get(name.strip())


def chip_label(chip_id: str | None) -> str:
    if not chip_id:
        return ""
    chip = CHIPS.get(chip_id)
    return chip.label if chip else chip_id.upper()
