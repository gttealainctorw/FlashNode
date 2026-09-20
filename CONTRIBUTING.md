# Contributing to FlashNode

Thanks for your interest! Bug reports, feature ideas, documentation fixes,
hardware test reports and code are all welcome.

## Reporting a bug or a hardware result

Open a GitHub Issue and include:

* FlashNode version (status bar, bottom right) and whether you used the
  installer or ran from source;
* the board and chip (as shown in the device list), the USB-serial adapter
  (CH340, CP210x, native USB…) and the Windows version;
* what you did, what happened, and the relevant lines from FlashNode's console
  (it contains esptool's full output).

Results from boards that are **not yet physically validated** (ESP32-S2, S3,
C3) are especially useful, including successful ones.

## Making a change

1. Fork the repository and create a branch for your change.
2. Set up the environment:

   ```
   py -3.13 -m pip install -r requirements.txt
   py -3.13 -m app.main
   ```

3. Make your change. Keep the UI free of business logic (it lives in
   `app/controller.py`, `app/flasher.py` and friends) and connect worker
   signals only to methods of QObjects in the UI thread (see `app/workers.py`).
4. Run the tests — they need no hardware:

   ```
   py -3.13 -m unittest discover -s tests -t . -v
   ```

   Add or update tests for behaviour you change; esptool output fixtures live
   in `tests/fixtures/`.
5. Commit with a clear message and open a pull request describing what you
   changed and how you tested it (and on which hardware, if any).

## Adding support for a chip

Add the MicroPython image URL in `app/firmware.py` and the flash offset in
`app/chips.py`; `tests/test_chips.py` checks that the chip table stays in sync
with the bundled esptool. Please only mark a chip as validated after flashing a
real board.

## Contact

Questions, proposals and collaboration ideas: **carlosaalain@gmail.com**.
