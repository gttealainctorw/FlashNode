# FlashNode

**FlashNode is an open-source Windows desktop application for detecting ESP32
boards and flashing MicroPython firmware onto them.** Plug in a board, tick it,
press *Flash*: FlashNode identifies the chip, erases the flash, writes and
verifies the firmware image, and resets the board — with clear progress and
error reporting, and without installing Python or esptool yourself.

[![Latest release](https://img.shields.io/github/v/release/gttealainctorw/FlashNode?label=download&color=4F8CFF)](https://github.com/gttealainctorw/FlashNode/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE.txt)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11%20x64-lightgrey)

## What is FlashNode?

Putting MicroPython on an ESP32 normally means installing Python, installing
`esptool`, finding the right image and offset for your chip, and typing the
right commands — and repeating that for every board. FlashNode wraps that
workflow in a small desktop application:

1. **Detect** the boards connected over USB (serial ports are scanned every two seconds).
2. **Identify** the exact chip family with esptool (`ESP32`, `ESP32-C3`, …).
3. **Erase** the flash memory.
4. **Write** the matching official MicroPython image (up to three boards in parallel).
5. **Verify** the written data (esptool hash check).
6. **Reset** the board into the new firmware.
7. **Rescan** and flash again, as many boards as you like.

Progress is shown per device and for the whole job; every esptool message is
kept in a console so failures are diagnosable. FlashNode bundles the flashing
toolchain (esptool 5.2), so the packaged application has **no runtime
dependencies**: no Python installation, no pip, no manual esptool setup.

It is aimed at makers, educators and small teams who need to (re)flash ESP32
boards with MicroPython quickly and reliably — for example preparing a batch of
boards for a workshop.

## Features

* Automatic serial-port scanning and exact chip identification (no guessing:
  unknown or unsupported chips are shown as such and are never flashed with the
  wrong image).
* One-click flashing of the official MicroPython generic build for the chip,
  downloaded once and cached.
* Erase → write → verify → reset in one job; per-device and overall progress;
  final success/failure summary.
* Multiple boards in one job (three in parallel).
* Clear error categories: *Port busy*, *Port not found*, *No response*,
  *Unknown chip*, *Unsupported*, plus esptool's full diagnostic in the console.
* Safe lifecycle: closing during a flash asks for confirmation and terminates
  the helper processes; an interrupted board can simply be flashed again.
* Dark, keyboard-navigable interface (PySide6 / Qt 6); native Windows installer.

## Download

**Recommended:** download the Windows installer from the latest GitHub Release:

**<https://github.com/gttealainctorw/FlashNode/releases/latest>** → `FlashNode_Setup_1.0.0.exe`

A `SHA256SUMS.txt` file is attached to each release so you can verify the
download (`Get-FileHash FlashNode_Setup_1.0.0.exe -Algorithm SHA256` in
PowerShell).

You do **not** need Python, esptool or any other tool to use the installed
application.

## Installation

### Windows installer

1. Open the [latest release](https://github.com/gttealainctorw/FlashNode/releases/latest).
2. Download `FlashNode_Setup_1.0.0.exe`.
3. Run the installer. By default it installs for the current user only, so
   **no administrator rights are needed**; administrators can choose
   *Install for all users* instead.
4. Follow the wizard (optionally tick *Create a desktop shortcut*).
5. Launch **FlashNode** from the Start Menu.

Requirements: Windows 10 or 11, 64-bit, and the USB driver of your board
(CH340, CP210x, FTDI…; boards with a native USB connection need no driver).
Internet access is needed the first time a chip family is flashed, to download
the MicroPython image; later flashes work offline.

The installer and executable are not code-signed, so Windows SmartScreen may
show *"Windows protected your PC"* on first run — choose *More info → Run
anyway*. Upgrading is done by running the newer installer over the old
version; uninstalling is done from *Settings → Apps*.

### From source

See [Build From Source](#build-from-source).

## How to Use

1. Connect the ESP32 board(s) over USB.
2. Open FlashNode. Within two seconds each serial port appears in the device
   list and is identified; **Ready** means the chip is supported and can be flashed.
3. Tick the boards you want (or *Select all*).
4. Press **Flash N devices**.
5. Watch the row: *Connecting → Erasing → Writing → Flashing n % → Done*.
   The console shows esptool's own output, the status bar the overall progress.
6. When the job finishes the board is reset into MicroPython automatically.
   Connect a serial terminal at 115200 baud to reach the REPL (`>>>`).

What to expect:

* **Detection** takes about a second per board. *Port busy* means another
  program (serial monitor, IDE) has the port open — close it and press *Rescan*.
* **Erasing** takes a few seconds; the bar is indeterminate during this phase.
* **Writing** shows a percentage taken from esptool's write loop. A 4 MB ESP32
  at 115200 baud takes about two minutes for the 1.7 MB image.
* **Verification** happens inside esptool (*Hash of data verified* in the console).
* **Reset**: esptool resets the board through the RTS line; the port stays
  available on most boards.
* **Errors** turn the row red with a short reason; the console keeps the full
  esptool message. A board interrupted mid-write is recoverable — flash it again.

## Supported Hardware

| Chip | Firmware written | Status in 1.0.0 |
|------|------------------|-----------------|
| ESP32 | MicroPython v1.24.0 `ESP32_GENERIC` @ 0x1000 | **Physically validated** (ESP32-D0WD-V3, CH340 USB-serial adapter) |
| ESP32-S2 | MicroPython v1.24.0 `ESP32_GENERIC_S2` @ 0x0 | Supported by the code path, **not physically validated** |
| ESP32-S3 | MicroPython v1.24.0 `ESP32_GENERIC_S3` @ 0x0 | Supported by the code path, **not physically validated** |
| ESP32-C3 | MicroPython v1.24.0 `ESP32_GENERIC_C3` @ 0x0 | Supported by the code path, **not physically validated** |

Physical validation for this release was completed on **ESP32-D0WD-V3**
hardware (4 MB flash) through a **CH340** USB-to-serial interface: detection,
full erase + write of MicroPython v1.24.0, verification, reset and boot into
the REPL, repeated flashing, port-busy handling and recovery after an
interrupted write — from the source tree, from the packaged application and
from the installed application. Other ESP32 variants may work through the same
esptool workflow, but they were not physically validated for this release;
reports from owners of such boards are very welcome (see *Feedback and Contact*).

**Detected but not flashable** (shown as *Unsupported*, nothing is written):
ESP32-C2, C5, C6, C61, H2, H21, H4, P4, S31, E22 and ESP8266 — no MicroPython
image is configured for them yet. Adding one is a URL in `app/firmware.py` and
an offset in `app/chips.py`.

## Build From Source

Requirements: Python **3.13**, Windows. Tested with Python 3.13.12, PySide6
6.11.0, esptool 5.2.0, pyserial 3.5, requests 2.33.1, PyInstaller 6.19.0 and
Inno Setup 6.

```
git clone https://github.com/gttealainctorw/FlashNode.git
cd FlashNode
py -3.13 -m pip install -r requirements.txt
py -3.13 -m app.main
```

Release build (one-folder PyInstaller bundle + Inno Setup installer + checksums):

```
py -3.13 -m pip install -r requirements-build.txt
py -3.13 tools\build_release.py
```

Output: `dist\FlashNode\` (the application folder) and
`release\FlashNode_Setup_<version>.exe` + `release\SHA256SUMS.txt`. Inno Setup 6
must be installed (`ISCC.exe` is looked up in the usual locations); pass
`--no-installer` to build only the application folder. The version is taken
from `version.json` and written into the executable's version resource, which
the installer reads — edit `version.json` only.

## Development

```
app/
├── main.py            entry point; also dispatches the `--esptool` helper mode
├── controller.py      UI ↔ backend: scanning, identification, flash jobs, shutdown
├── workers.py         QThread workers wrapping the blocking backend calls
├── flasher.py         detect_ports() and flash(): detect → firmware → erase → write
├── detect_chip.py     deterministic chip identification (exact esptool names)
├── chips.py           chip table: esptool names, labels, flash offsets
├── esptool_helper.py  child-process entry point running esptool in-process
├── toolchain.py       launches the helper (sys.executable / frozen self-launch)
├── firmware.py        firmware download & cache
├── updater.py         optional version check (HTTPS manifest, validated; off by default)
├── paths.py           bundled-resource vs. user-data locations (dev / frozen)
├── config.py          tunables: scan interval, console size, update URL…
└── ui/                theme (design tokens → stylesheet), icons, components, views
tests/                 unittest suite + esptool output fixtures
tools/build_release.py release pipeline
FlashNode.spec         PyInstaller configuration
installer.iss          Inno Setup script
```

How esptool is run: FlashNode never calls a system-wide Python or esptool.
Every operation runs in a child process executing `app/esptool_helper.py` —
with the current interpreter from source, or as `FlashNode.exe --esptool …`
when packaged (the executable re-launches itself). The helper imports esptool,
reports write progress through esptool's own logger hook (`@@PROGRESS n`),
identifies chips through `detect_chip()` (`@@CHIP <name>`) and classifies
failures (`@@ERROR <kind> <message>`). Worker signals must be connected to
methods of QObjects living in the UI thread (see the note in `workers.py`).

`FlashNode.exe --esptool self-test > selftest.txt` checks that the bundled
helper can be started from an installed copy.

## Testing

```
py -3.13 -m unittest discover -s tests -t . -v
```

71 tests, no extra dependencies, no hardware needed: chip identification
against real esptool output fixtures, the flashing sequence over a replayed
helper, workers, the controller driving the real window with a fake backend,
UI state machines, the updater, and the real helper process (which runs the
bundled esptool without a board). Hardware validation is a separate, manual
layer (see *Supported Hardware* and `RELEASE_NOTES.md`).

## Open Source

FlashNode is open-source software released under the **MIT License** (see
[LICENSE.txt](LICENSE.txt)). The complete source code is public in this
repository: anyone can read exactly how boards are detected and flashed, build
the application themselves, adapt it, and contribute improvements. The
packaged installer on the Releases page is built from this source with the
scripts in the repository.

## Contributing

Contributions of every kind are welcome:

* bug reports and feature suggestions (GitHub Issues),
* testing on ESP32 variants that have not been physically validated
  (ESP32-S2, S3, C3) and on other USB-serial adapters,
* support for more chips (firmware URL + offset),
* documentation, UI/UX and accessibility improvements,
* automated tests.

Simple workflow: **fork → create a branch → make your change → run the tests
(`py -3.13 -m unittest discover -s tests -t .`) → commit → open a pull
request.** Please keep pull requests focused and describe what you tested (and
on which hardware, if any). See [CONTRIBUTING.md](CONTRIBUTING.md).

## Feedback and Contact

Suggestions, feedback, bug reports, ideas for improvement, results from other
boards and collaboration proposals are all welcome — FlashNode is meant to grow
with its users.

* GitHub Issues: <https://github.com/gttealainctorw/FlashNode/issues>
* Email: **carlosaalain@gmail.com**

## License

MIT License — see [LICENSE.txt](LICENSE.txt). MicroPython firmware images are
downloaded from micropython.org and are distributed under their own MIT License;
esptool is licensed under GPL-2.0-or-later and is bundled unmodified.

## Known Limitations

* Only ESP32 (D0WD-V3) was physically validated; ESP32-S2/S3/C3 share the code
  path but were not tested on hardware. Multi-board jobs were validated in
  simulation only (one board was available).
* Writes run at esptool's default 115200 baud (~100 s for the 1.7 MB ESP32 image).
* Unsigned executable and installer (SmartScreen warning on first run).
* The optional update check is disabled until a manifest URL is configured in
  `app/config.py`.
* Windows only; the code uses PySide6 and pyserial, which are cross-platform,
  but packaging and testing were done on Windows.
