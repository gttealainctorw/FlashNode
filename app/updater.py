"""Optional update check against a remote JSON manifest ({"version": "x.y.z"}).

The manifest URL comes from ``app.config.UPDATE_MANIFEST_URL`` (or the
FLASHNODE_UPDATE_URL environment variable). When it is empty the check is
disabled. Nothing is ever downloaded or executed: the user is only told that a
newer version exists.
"""

import json
import re

import requests

from app.config import UPDATE_MANIFEST_URL, UPDATE_TIMEOUT_S
from app.paths import resource_path

LOCAL_VERSION_FILE = resource_path("version.json")

_VERSION_RE = re.compile(r"^\d+(?:\.\d+){0,3}$")


def get_local_version():
    try:
        with open(LOCAL_VERSION_FILE, encoding="utf-8") as f:
            return json.load(f)["version"]
    except Exception:
        return "0.0.0"


def parse_version(text) -> tuple[int, ...] | None:
    """'1.2.0' -> (1, 2, 0); None when the text is not a plain dotted version."""
    if not isinstance(text, str) or not _VERSION_RE.match(text.strip()):
        return None
    return tuple(int(part) for part in text.strip().split("."))


def is_newer(remote: str, local: str) -> bool:
    r, l = parse_version(remote), parse_version(local)
    if r is None or l is None:
        return False
    width = max(len(r), len(l))
    return r + (0,) * (width - len(r)) > l + (0,) * (width - len(l))


def update_check_enabled() -> bool:
    return UPDATE_MANIFEST_URL.startswith("https://")


def check_update(url: str | None = None):
    """Returns (has_update: bool, remote_version: str | None).

    Never raises; any network or content problem simply means "no update".
    """
    url = UPDATE_MANIFEST_URL if url is None else url
    if not url.startswith("https://"):
        return False, None
    try:
        r = requests.get(url, timeout=UPDATE_TIMEOUT_S)
        r.raise_for_status()
        payload = r.json()
        remote = payload.get("version") if isinstance(payload, dict) else None
        if parse_version(remote) is None:
            return False, None
        return is_newer(remote, get_local_version()), remote
    except Exception:
        return False, None
