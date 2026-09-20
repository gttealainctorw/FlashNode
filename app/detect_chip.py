"""Chip identification through the bundled esptool helper.

The helper reports the chip with a ``@@CHIP <name>`` marker taken directly from
esptool's ``ESPLoader.CHIP_NAME``; the name is matched *exactly* against the
table in ``app.chips``. As a fallback, the two lines esptool itself prints
("Detecting chip type... X" / "Connected to X on PORT:") are parsed with
anchored patterns. Anything else yields an explicit failure instead of a guess.
"""

import re
from dataclasses import dataclass

from app import chips, toolchain
from app.config import CHIP_DETECT_TIMEOUT_S
from app.esptool_helper import MARKER_CHIP

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_DETECTING_RE = re.compile(r"^Detecting chip type\.\.\.\s+(\S+)\s*$")
_CONNECTED_RE = re.compile(r"^Connected to (\S+) on \S+:?\s*$")

# Error kinds reported to the UI and what they mean (kept short: shown in a badge/tooltip)
ERROR_LABELS = {
    "PORT_BUSY": "Port busy",
    "PORT": "Port not found",
    "NO_RESPONSE": "No response",
    "UNKNOWN_CHIP": "Unknown chip",
    "SERIAL": "Serial error",
    "TIMEOUT": "Timed out",
    "FATAL": "Failed",
    "INTERNAL": "Tool error",
    "LAUNCH": "Tool missing",
}


@dataclass(frozen=True)
class DetectionResult:
    chip: str | None            # internal chip id ("esp32c3") or None
    error: str | None = None    # one of ERROR_LABELS' keys when chip is None
    detail: str = ""            # diagnostic text for the console

    @property
    def ok(self) -> bool:
        return self.chip is not None

    @property
    def error_label(self) -> str:
        return ERROR_LABELS.get(self.error or "", "Failed")


def clean_line(line: str) -> str:
    return _ANSI_RE.sub("", line).strip()


def parse_chip_name(output: str) -> str | None:
    """Return esptool's chip name from helper output, or None when absent."""
    lines = [clean_line(line) for line in output.splitlines()]
    for line in lines:
        if line.startswith(MARKER_CHIP + " "):
            return line[len(MARKER_CHIP):].strip()
    for line in lines:
        match = _DETECTING_RE.match(line) or _CONNECTED_RE.match(line)
        if match:
            return match.group(1)
    return None


def classify(output: str, result: toolchain.HelperResult | None = None) -> DetectionResult:
    """Turn helper output (and its exit status) into a DetectionResult."""
    name = parse_chip_name(output)
    if name is not None:
        chip = chips.chip_from_esptool_name(name)
        if chip is not None:
            return DetectionResult(chip.id)
        return DetectionResult(None, "UNKNOWN_CHIP", f"esptool reported unrecognised chip '{name}'")

    if result is not None and result.error_kind:
        return DetectionResult(None, result.error_kind, result.error_message)
    if result is not None and result.returncode != 0:
        return DetectionResult(None, "FATAL", f"helper exited with code {result.returncode}")
    return DetectionResult(None, "UNKNOWN_CHIP", "no chip identification in output")


def detect_chip(port: str, timeout: float = CHIP_DETECT_TIMEOUT_S) -> DetectionResult:
    """Identify the chip on ``port``. Never raises."""
    lines: list[str] = []
    try:
        result = toolchain.run_helper(["chip-id", "--port", port], lines.append, timeout=timeout)
    except Exception as exc:  # defensive: a bug here must not kill the scan thread
        return DetectionResult(None, "INTERNAL", str(exc))
    return classify("\n".join(lines), result)
