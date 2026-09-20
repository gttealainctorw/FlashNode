# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build for FlashNode.

    python -m PyInstaller FlashNode.spec

Produces a one-folder application in dist/FlashNode/ (FlashNode.exe + _internal/)
that bundles Python, PySide6, pyserial, requests and esptool. The executable
doubles as the esptool helper process (it re-launches itself with ``--esptool``),
so end users need no separate Python or esptool installation. The folder is
what installer.iss packages; users never see it.

One-folder was chosen over one-file after measuring startup on the same machine:
~1.6-2.2 s versus ~12-14 s for one-file (archive extraction + antivirus scan).

The version comes from version.json (single source of truth) and is written
into the executable's Windows version resource.
"""

import json
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

APP_VERSION = json.load(open(os.path.join(SPECPATH, "version.json"), encoding="utf-8"))["version"]

# --- Windows version resource --------------------------------------------------
_parts = [int(p) for p in APP_VERSION.split(".")][:4]
_parts += [0] * (4 - len(_parts))
_version_file = os.path.join(SPECPATH, "build", "version_info.txt")
os.makedirs(os.path.dirname(_version_file), exist_ok=True)
with open(_version_file, "w", encoding="utf-8") as _f:
    _f.write(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={tuple(_parts)}, prodvers={tuple(_parts)}, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'FlashNode'),
      StringStruct('FileDescription', 'FlashNode - ESP32 MicroPython deployment'),
      StringStruct('FileVersion', '{APP_VERSION}'),
      StringStruct('InternalName', 'FlashNode'),
      StringStruct('LegalCopyright', 'Copyright (c) 2025 FlashNode. MIT License.'),
      StringStruct('OriginalFilename', 'FlashNode.exe'),
      StringStruct('ProductName', 'FlashNode'),
      StringStruct('ProductVersion', '{APP_VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""")

# --- Packages that must never end up in the bundle ------------------------------
# They are not used by FlashNode; they get pulled in only through *optional* imports
# of rich/pygments (IPython/Jupyter integration, image formatter) when they happen
# to be installed on the build machine. Excluding them keeps the build reproducible
# and roughly halves its size.
EXCLUDES = [
    "IPython", "ipykernel", "jupyter_client", "jupyter_core", "comm", "traitlets",
    "jedi", "parso", "prompt_toolkit", "stack_data", "asttokens", "executing", "pure_eval",
    "matplotlib", "matplotlib_inline", "numpy", "scipy", "pandas", "PIL",
    "tkinter", "_tkinter", "zmq", "tornado", "debugpy", "psutil", "nest_asyncio",
    # Qt modules a QtWidgets application does not use
    "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtOpenGL",
    "PySide6.QtPdf", "PySide6.QtMultimedia", "PySide6.QtWebEngineCore",
]

a = Analysis(
    ["app\\main.py"],
    pathex=[],                      # the spec directory (project root) is added automatically
    binaries=[],
    datas=[
        ("assets", "assets"),
        ("version.json", "."),      # read by app.updater
        *collect_data_files("esptool"),   # flasher stubs: esptool/targets/stub_flasher/**/*.json
    ],
    hiddenimports=collect_submodules("esptool"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)

# Qt binaries that only serve QtQuick/OpenGL/PDF/network features this app has no use for.
_DROP_BINARIES = (
    "opengl32sw.dll", "d3dcompiler_47.dll",
    "Qt6Quick.dll", "Qt6Qml.dll", "Qt6QmlModels.dll", "Qt6QmlMeta.dll", "Qt6QmlWorkerScript.dll",
    "Qt6OpenGL.dll", "Qt6Pdf.dll", "Qt6Network.dll",
    "qpdf.dll", "qnetworklistmanager.dll", "qschannelbackend.dll", "qcertonlybackend.dll",
    "qopensslbackend.dll",
)
a.binaries = [b for b in a.binaries if os.path.basename(b[0]) not in _DROP_BINARIES]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FlashNode",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                      # UPX is unreliable with Qt binaries; keep the build deterministic
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
    version=_version_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="FlashNode",
)
