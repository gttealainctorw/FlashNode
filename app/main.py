"""FlashNode entry point.

Development:  python -m app.main   (run from the project root)
Packaged:     FlashNode.exe

The packaged executable also serves as the esptool helper process: when it is
launched with ``--esptool …`` it runs ``app.esptool_helper`` and exits without
touching Qt (see ``app.toolchain``).
"""

import os
import sys

# Running as a plain script (``python app/main.py``) puts app/ on sys.path
# instead of the project root; add the root so the ``app`` package resolves.
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not getattr(sys, "frozen", False) and _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

HELPER_FLAG = "--esptool"


def _run_helper_mode() -> None:
    from app.esptool_helper import main as helper_main

    if sys.argv[2:3] == ["self-test"]:
        sys.exit(_self_test())
    sys.exit(helper_main(sys.argv[2:]))


def _self_test() -> int:
    """`FlashNode --esptool self-test`: prove the bundled esptool helper can be spawned."""
    import time

    from app import toolchain

    started = time.perf_counter()
    lines: list[str] = []
    result = toolchain.run_helper(["version"], lines.append, timeout=60)
    elapsed = time.perf_counter() - started
    print(f"helper command: {' '.join(toolchain.helper_command(['version']))}")
    print(f"helper output:  {' | '.join(lines) or '(none)'}")
    print(f"helper status:  rc={result.returncode} error={result.error_kind} in {elapsed:.2f}s")
    return 0 if result.ok and any(l.startswith("esptool ") for l in lines) else 1


def run():
    if len(sys.argv) > 1 and sys.argv[1] == HELPER_FLAG:
        _run_helper_mode()
        return

    from PySide6.QtWidgets import QApplication

    from app.controller import AppController
    from app.security import check
    from app.ui.icons import app_icon
    from app.ui.main_window import MainWindow
    from app.ui.theme import apply_theme

    check()

    if sys.platform == "win32":
        # Give the process its own taskbar identity so the window icon is used
        # instead of the Python interpreter's when running from source.
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FlashNode.App")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("FlashNode")
    app.setApplicationDisplayName("FlashNode")
    apply_theme(app)
    app.setWindowIcon(app_icon())

    win = MainWindow()
    controller = AppController(win, parent=app)
    win.set_close_handler(controller.request_close)
    controller.start()

    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
