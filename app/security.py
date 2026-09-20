import sys
import os


def check():
    """Basic integrity check — ensures the app isn't renamed/repackaged."""
    exe_name = os.path.basename(sys.argv[0]).lower()
    # Allow running as main.py during development OR as FlashNode.exe
    if exe_name not in ("main.py", "flashnode.exe", "flashnode"):
        print(f"[WARN] Unexpected executable name: {exe_name}")
        # Exit only in production (not during dev)
        if getattr(sys, "frozen", False):
            sys.exit(1)
