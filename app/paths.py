"""Filesystem locations that differ between the source tree and the frozen build.

Two kinds of location exist:

* **bundled resources** (read-only): the project root in development, or the
  PyInstaller extraction directory (``sys._MEIPASS``) when frozen;
* **user data** (writable): the project root in development, or a per-user
  application folder when frozen, because the install directory
  (e.g. ``Program Files``) is usually not writable.
"""

import os
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))

if FROZEN:
    ROOT_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    ROOT_DIR = Path(__file__).resolve().parent.parent

APP_NAME = "FlashNode"


def resource_path(*parts: str) -> Path:
    """Absolute path to a bundled, read-only resource (e.g. ``version.json``)."""
    return ROOT_DIR.joinpath(*parts)


def user_data_dir() -> Path:
    """Writable per-user directory for caches and downloads."""
    if not FROZEN:
        return ROOT_DIR
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / APP_NAME


def firmware_dir() -> Path:
    """Where downloaded firmware images are cached."""
    return user_data_dir() / "firmware"
