"""Subprocess entry point that runs esptool in-process and reports structured events.

The application never shells out to a system Python or a system esptool: it
runs *this* module in a child process (the frozen executable re-launches itself
with ``--esptool``, the source tree uses ``sys.executable``). esptool is
imported here, so it ships inside the packaged application.

Besides esptool's normal output, the helper prints marker lines the parent can
parse deterministically:

    @@CHIP <esptool chip name>       (chip-id mode)
    @@PROGRESS <0-100>               (write-flash progress)
    @@ERROR <KIND> <message>         (KIND: PORT_BUSY, PORT, NO_RESPONSE, UNKNOWN_CHIP, SERIAL,
                                      FATAL, INTERNAL)

Modes::

    esptool_helper version
    esptool_helper chip-id --port COM3
    esptool_helper run <esptool arguments...>

This module intentionally has no dependency on the rest of the ``app`` package.
"""

import sys
import traceback

MARKER_CHIP = "@@CHIP"
MARKER_PROGRESS = "@@PROGRESS"
MARKER_ERROR = "@@ERROR"

EXIT_OK = 0
EXIT_SERIAL = 1
EXIT_FATAL = 2
EXIT_INTERNAL = 3
EXIT_USAGE = 64


def _emit(line: str) -> None:
    print(line, flush=True)


def _single_line(message: str) -> str:
    return " | ".join(part.strip() for part in str(message).splitlines() if part.strip())


def _classify_fatal(message: str) -> str:
    """Map esptool FatalError messages (stable strings in esptool 5.x) to a kind."""
    if message.startswith("Could not open"):
        # esptool appends pyserial's error, which embeds the OS exception repr. The exception
        # *type* is language-independent (the OS text is localized, e.g. "Acceso denegado."):
        # PermissionError -> another program holds the port; FileNotFoundError -> port is gone.
        if ("PermissionError(" in message or "Access is denied" in message
                or "Permission denied" in message):
            return "PORT_BUSY"
        return "PORT"
    if message.startswith("Failed to connect"):
        return "NO_RESPONSE"
    if "Failed to autodetect chip type" in message:
        return "UNKNOWN_CHIP"
    return "FATAL"


def _install_marker_logger() -> None:
    """Emit @@PROGRESS markers from esptool's own progress-bar hook."""
    from esptool.logger import EsptoolLogger, log

    class MarkerLogger(EsptoolLogger):
        _last_pct = -1

        def __new__(cls):
            # EsptoolLogger.__new__ would hand back the existing singleton (whose class
            # would then be used by set_logger); only this class object matters here.
            return object.__new__(cls)

        def progress_bar(self, cur_iter, total_iters, prefix="", suffix="", bar_length=30):
            super().progress_bar(cur_iter, total_iters, prefix, suffix, bar_length)
            if total_iters <= 0 or not prefix.startswith("Writing at"):
                return
            pct = int(100 * cur_iter // total_iters)
            if pct != MarkerLogger._last_pct:
                MarkerLogger._last_pct = pct
                _emit(f"{MARKER_PROGRESS} {pct}")

    # Never use ANSI/overwriting output: the parent reads whole lines from a pipe.
    log.set_verbosity("verbose")
    log.set_logger(MarkerLogger())


def _run_chip_id(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] != "--port":
        _emit(f"{MARKER_ERROR} INTERNAL usage: chip-id --port <port>")
        return EXIT_USAGE
    port = argv[1]

    from esptool.cmds import detect_chip

    esp = detect_chip(port)
    _emit(f"{MARKER_CHIP} {esp.CHIP_NAME}")
    try:
        # Same as the CLI's default `--after hard-reset`: leave the board running its app.
        esp.hard_reset()
    except Exception as exc:  # a failed reset must not invalidate the detection
        _emit(f"Warning: could not reset {port} after detection: {_single_line(exc)}")
    finally:
        esp._port.close()
    return EXIT_OK


def _run_esptool(argv: list[str]) -> int:
    import esptool

    _install_marker_logger()
    esptool.main(argv)
    return EXIT_OK


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(line_buffering=True)

    if not argv:
        _emit(f"{MARKER_ERROR} INTERNAL usage: version | chip-id --port <port> | run <esptool args>")
        return EXIT_USAGE

    mode, rest = argv[0], argv[1:]
    try:
        if mode == "version":
            import esptool
            _emit(f"esptool {esptool.__version__}")
            return EXIT_OK
        if mode == "chip-id":
            return _run_chip_id(rest)
        if mode == "run":
            return _run_esptool(rest)
        _emit(f"{MARKER_ERROR} INTERNAL unknown mode: {mode}")
        return EXIT_USAGE

    except SystemExit as exc:
        # click usage errors; esptool.main() already swallowed exit code 0
        code = exc.code if isinstance(exc.code, int) else EXIT_USAGE
        _emit(f"{MARKER_ERROR} FATAL esptool exited with code {code}")
        return code or EXIT_USAGE
    except Exception as exc:
        kind = "INTERNAL"
        try:
            import serial
            from esptool import FatalError

            if isinstance(exc, FatalError):
                kind = _classify_fatal(str(exc))
            elif isinstance(exc, serial.SerialException):
                kind = "SERIAL"
        except ImportError:
            pass

        if kind == "INTERNAL":
            traceback.print_exc()
        _emit(f"{MARKER_ERROR} {kind} {_single_line(exc)}")
        return {"SERIAL": EXIT_SERIAL, "INTERNAL": EXIT_INTERNAL}.get(kind, EXIT_FATAL)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
