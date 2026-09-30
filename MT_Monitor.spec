# -*- mode: python ; coding: utf-8 -*-
"""
MT_Monitor.spec — Оптимизированная сборка MT Monitor с минимальным весом.
Сборка: pyinstaller MT_Monitor.spec
"""

import sys
from pathlib import Path

block_cipher = None

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("qfluentwidgets")
hiddenimports = collect_submodules("qfluentwidgets")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=datas + [
        ("assets", "assets"),
    ],
    hiddenimports=hiddenimports + [
        "PyQt6.QtSvg",
        "core.config",
        "core.analytics",
        "worker",
        "ui.dashboard",
        "ui.settings",
        "ui.about",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt5",
        "PyQt6.QtMultimedia",
        "PyQt6.QtMultimediaWidgets",
        "PyQt6.QtQml",
        "PyQt6.QtQuick",
        "PyQt6.QtBluetooth",
        "PyQt6.QtPositioning",
        "PyQt6.QtNfc",
        "PyQt6.QtSensors",
        "PyQt6.QtSerialPort",
        "numpy",
        "scipy",
        "pandas",
        "matplotlib",
        "PIL",
        "tkinter",
        "unittest",
        "pydoc",
        "email",
        "html",
        "http.server",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

excluded_binaries = {
    "opengl32sw.dll",
    "Qt6Pdf.dll",
    "qpdf.dll",
    "Qt6Multimedia.dll",
    "Qt6MultimediaWidgets.dll",
    "Qt6Xml.dll",
    "avcodec-61.dll",
    "avformat-61.dll",
    "swscale-8.dll",
    "swresample-5.dll",
    "avutil-59.dll",
    "qtiff.dll",
    "qwebp.dll",
    "qjpeg.dll",
    "qgif.dll",
    "qtga.dll",
    "qicns.dll",
    "qwbmp.dll",
    "win32ui.pyd",
    "pythoncom314.dll",
}

a.binaries = [x for x in a.binaries if Path(x[0]).name not in excluded_binaries]
a.datas = [x for x in a.datas if not x[0].endswith(".qm")]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MT_Monitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_dir=".",
    upx_exclude=[
        "vcruntime140.dll",
        "msvcp140.dll",
        "qwindows.dll",
    ],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)
