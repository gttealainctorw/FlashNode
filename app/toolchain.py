"""Launch the bundled esptool helper as a child process and stream its output.

In the source tree the helper is run with the current interpreter; in the
frozen build the executable re-launches itself with ``--esptool`` (see
``main.py``). Either way no system-wide Python or esptool is required.
"""

import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from app import esptool_helper
from app.paths import FROZEN

HELPER_FLAG = "--esptool"

_active: set[subprocess.Popen] = set()
_active_lock = threading.Lock()


@dataclass
class HelperResult:
    returncode: int
    error_kind: str | None = None       # PORT_BUSY, PORT, NO_RESPONSE, UNKNOWN_CHIP, SERIAL, FATAL, INTERNAL, TIMEOUT, LAUNCH
    error_message: str = ""
    markers: dict[str, str] = field(default_factory=dict)   # last value seen for @@CHIP etc.

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and self.error_kind is None


def helper_command(args: list[str]) -> list[str]:
    """Argument vector that runs the esptool helper in a child process."""
    if FROZEN:
        return [sys.executable, HELPER_FLAG, *args]
    helper = Path(esptool_helper.__file__).resolve()
    return [sys.executable, str(helper), *args]


def _popen_kwargs() -> dict:
    kwargs = dict(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                  text=True, encoding="utf-8", errors="replace", bufsize=1)
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def run_helper(args: list[str], on_line: Callable[[str], None] | None = None,
               timeout: float | None = None) -> HelperResult:
    """Run the helper, forwarding each output line to ``on_line``.

    Marker lines (``@@…``) are interpreted and *also* forwarded, so callers can
    keep their own logging. ``timeout`` (seconds) kills the child when exceeded;
    flashing callers pass None because a slow write is not an error.
    """
    result = HelperResult(returncode=-1)
    try:
        proc = subprocess.Popen(helper_command(args), **_popen_kwargs())
    except OSError as exc:
        result.error_kind = "LAUNCH"
        result.error_message = f"Could not start the esptool helper: {exc}"
        return result

    with _active_lock:
        _active.add(proc)

    timer = None
    timed_out = threading.Event()
    if timeout:
        def _kill():
            timed_out.set()
            proc.kill()
        timer = threading.Timer(timeout, _kill)
        timer.daemon = True
        timer.start()

    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip("\r\n")
            if not line.strip():
                continue
            _interpret_marker(line, result)
            if on_line:
                on_line(line)
        proc.wait()
    finally:
        if timer:
            timer.cancel()
        if proc.stdout is not None:
            proc.stdout.close()
        with _active_lock:
            _active.discard(proc)

    result.returncode = proc.returncode
    if timed_out.is_set():
        result.error_kind = "TIMEOUT"
        result.error_message = f"No result after {timeout:.0f} seconds"
    elif result.returncode != 0 and result.error_kind is None:
        result.error_kind = "FATAL"
        result.error_message = f"esptool helper exited with code {result.returncode}"
    return result


def _interpret_marker(line: str, result: HelperResult) -> None:
    if not line.startswith("@@"):
        return
    marker, _, payload = line.partition(" ")
    if marker == esptool_helper.MARKER_ERROR:
        kind, _, message = payload.partition(" ")
        result.error_kind = kind or "FATAL"
        result.error_message = message.strip()
    else:
        result.markers[marker] = payload.strip()


def terminate_all() -> None:
    """Kill every running helper (used on application shutdown)."""
    with _active_lock:
        procs = list(_active)
    for proc in procs:
        try:
            proc.kill()
        except OSError:
            pass


def active_count() -> int:
    with _active_lock:
        return len(_active)
