"""Shared test utilities."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Qt tests never need a display
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def fixture_lines(name: str) -> list[str]:
    return [line for line in fixture(name).splitlines() if line.strip()]


_app = None


def qapp():
    """Create (once) the offscreen QApplication with the real theme applied."""
    global _app
    if _app is None:
        from PySide6.QtWidgets import QApplication

        from app.ui.theme import apply_theme

        _app = QApplication.instance() or QApplication([])
        apply_theme(_app)
    return _app


def process_events(ms: int = 0):
    """Run the event loop for `ms` milliseconds (0 = just flush pending events)."""
    from PySide6.QtCore import QEventLoop, QTimer

    app = qapp()
    if ms <= 0:
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents)
        app.sendPostedEvents()
        return
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def wait_until(predicate, timeout_ms: int = 5000, step_ms: int = 20) -> bool:
    """Pump the event loop until `predicate()` is true or the timeout expires."""
    import time

    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if predicate():
            return True
        process_events(step_ms)
    return predicate()
