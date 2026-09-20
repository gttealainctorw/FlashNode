"""Clean release build: PyInstaller (one-folder) + Inno Setup installer + SHA-256 sums.

    py -3.13 tools\\build_release.py            # full pipeline
    py -3.13 tools\\build_release.py --no-installer

Artifacts:
    dist\\FlashNode\\                    the application folder (what the installer packages)
    release\\FlashNode_Setup_<ver>.exe  the installer
    release\\SHA256SUMS.txt             hashes of the release artifacts
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISCC_CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Inno Setup 6" / "ISCC.exe",
]


def run(cmd: list[str]) -> None:
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def find_iscc() -> Path | None:
    on_path = shutil.which("ISCC")
    if on_path:
        return Path(on_path)
    return next((p for p in ISCC_CANDIDATES if p.is_file()), None)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    version = json.loads((ROOT / "version.json").read_text(encoding="utf-8"))["version"]
    with_installer = "--no-installer" not in sys.argv

    # Clean only what this pipeline produces (older, hand-made files in dist/ are left alone)
    shutil.rmtree(ROOT / "build", ignore_errors=True)
    shutil.rmtree(ROOT / "dist" / "FlashNode", ignore_errors=True)
    (ROOT / "dist" / "FlashNode.exe").unlink(missing_ok=True)
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "FlashNode.spec"])

    app_dir = ROOT / "dist" / "FlashNode"
    exe = app_dir / "FlashNode.exe"
    if not exe.is_file():
        print("build failed: missing", exe)
        return 1

    artifacts = []
    if with_installer:
        iscc = find_iscc()
        if iscc is None:
            print("Inno Setup (ISCC.exe) not found; skipping the installer. Install Inno Setup 6 or pass --no-installer.")
            return 2
        run([str(iscc), "/Qp", str(ROOT / "installer.iss")])
        installer = ROOT / "release" / f"FlashNode_Setup_{version}.exe"
        if not installer.is_file():
            print("installer build failed: missing", installer)
            return 1
        artifacts.append(installer)

    release = ROOT / "release"
    release.mkdir(exist_ok=True)
    lines = [f"{sha256(p)}  {p.name}" for p in artifacts]
    lines.append(f"{sha256(exe)}  dist/FlashNode/FlashNode.exe")
    (release / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    size_mb = sum(p.stat().st_size for p in app_dir.rglob("*") if p.is_file()) / 1e6
    print(f"\nFlashNode {version} built {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}")
    print(f"  application folder: {app_dir}  ({size_mb:.0f} MB)")
    for p in artifacts:
        print(f"  {p.relative_to(ROOT)}  ({p.stat().st_size / 1e6:.1f} MB)")
    print("\n".join("  " + line for line in lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
