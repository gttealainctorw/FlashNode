# FlashNode 1.0.0

First public release.

FlashNode is an open-source Windows desktop application that detects ESP32
boards over USB, identifies the chip, and erases, writes, verifies and resets
MicroPython firmware — with the flashing toolchain (esptool 5.2) bundled, so no
Python or esptool installation is needed to use it.

## Highlights

* Automatic device scanning and **exact chip identification** through esptool
  (`ESP32`, `ESP32-C3`, …); unknown and unsupported chips are shown as such and
  are never flashed with the wrong image.
* One-click job per board: **erase → write → verify → reset**, up to three
  boards in parallel, with per-device and overall progress taken from esptool's
  own write loop.
* Console with timestamps, severity and port column keeping esptool's full
  output; short, actionable error reasons in the device list (*Port busy*,
  *Port not found*, *No response*, *Unknown chip*, *Unsupported*).
* Safe lifecycle: the scanner pauses during a job, failed identifications are
  not retried every two seconds, and closing during a flash asks for
  confirmation and terminates the helper processes.
* Native **Windows installer** (per-user by default, no administrator rights;
  all-users install available), one-folder packaging that starts in about two
  seconds, clean in-place upgrades and uninstall.
* Dark, keyboard-navigable interface built with PySide6 / Qt 6.

## Verified hardware

* **ESP32-D0WD-V3** (revision v3.1, 4 MB flash) on a **CH340** USB-to-serial
  adapter.

ESP32-S2, ESP32-S3 and ESP32-C3 are supported by the same code path but were
**not physically validated** for this release.

## MicroPython validation

The official `ESP32_GENERIC-20241025-v1.24.0` image was flashed at offset
0x1000 four times during validation (from the source tree, from the packaged
application and from the installed application). Each time the flash was fully
erased (a marker file placed on the MicroPython filesystem beforehand was gone
afterwards), esptool verified the written data, the board was reset and booted
into the MicroPython v1.24.0 REPL.

## Packaging and installer

* `FlashNode_Setup_1.0.0.exe` (Inno Setup 6): installs to the per-user
  Programs folder by default; upgrades replace the previous version in place
  and remove stale runtime files; uninstall removes the application, shortcuts
  and registry entry and leaves the small firmware cache in
  `%LOCALAPPDATA%\FlashNode`.
* Application version comes from `version.json` and is embedded in the
  executable's version resource and the installer.
* Firmware images are downloaded from micropython.org on first use and cached.
* The installer and executable are **not code-signed**.

## Reliability validation

Real-hardware checks: port held by another program (identification reports
*Port busy*; a flash attempt fails before erasing), missing firmware file
(clear esptool error, board recoverable), application closed at 20 % of a
write (confirmation dialog, helper terminated, port released, board recovered
by flashing again), repeated flashing, no leftover processes after closing.

## Testing

71 automated tests (unittest, no hardware required) covering chip
identification against real esptool output, the flashing sequence, workers,
the controller driving the real window, UI state machines, the updater and
the real esptool helper process. Visual QA at several window sizes and 150 %
display scaling.

## Known limitations

* Only ESP32 (D0WD-V3) was physically validated; multi-board jobs were
  validated in simulation only (one board was available).
* Writes run at esptool's default 115200 baud (~100 s for the 1.7 MB image).
* Unsigned executable and installer: SmartScreen may warn on first run.
* The optional update check is disabled until a manifest URL is configured.

## Feedback

Suggestions, bug reports, test results from other boards and collaboration
proposals: **carlosaalain@gmail.com** or GitHub Issues.
