"""Values that are reasonable to tune without touching the code that uses them."""

import os

# Device scanning
SCAN_INTERVAL_MS = 2000            # how often serial ports are enumerated
RESCAN_AFTER_FLASH_MS = 1500       # delay before the first scan after a flash job
CHIP_DETECT_TIMEOUT_S = 20         # max time for one chip identification attempt
UNKNOWN_CHIP_RETRY_S = 20          # re-try identifying a port that failed, after this long

# Flashing
FLASH_MAX_PARALLEL = 3             # devices flashed concurrently

# Console
CONSOLE_MAX_LINES = 5000           # bounded log buffer (oldest lines are dropped)

# Updates. Set to the raw URL of a JSON document like {"version": "1.2.0"}.
# Empty (the default) disables the check. Can also be provided at runtime through
# the FLASHNODE_UPDATE_URL environment variable. Only https:// URLs are accepted.
UPDATE_MANIFEST_URL = os.environ.get("FLASHNODE_UPDATE_URL", "")
UPDATE_TIMEOUT_S = 5
