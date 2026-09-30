# -*- mode: python ; coding: utf-8 -*-
"""
build.spec — Оптимизированная сборка MT Monitor с минимальным весом.
Сборка: pyinstaller build.spec
"""

import sys
from pathlib import Path

block_cipher = None

# Сбор ресурсов и подмодулей qfluentwidgets (шрифты, qss, иконки)
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
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ---------------------------------------------------------------------------
# Фильтрация тяжелых и ненужных файлов для минимизации размера
# ---------------------------------------------------------------------------
excluded_binaries = {
    # Графика и тяжелые движки
    "opengl32sw.dll",   # Софтверный рендерер OpenGL (~19.7 МБ) — не нужен в Win 10/11
    "Qt6Pdf.dll",       # Движок рендеринга PDF (~4.5 МБ)
    "qpdf.dll",
    "Qt6Multimedia.dll",
    "Qt6MultimediaWidgets.dll",
    # FFmpeg кодеки, подтягиваемые мультимедией
    "avcodec-61.dll",
    "avformat-61.dll",
    "swscale-8.dll",
    "swresample-5.dll",
    "avutil-59.dll",
    # Лишние форматы картинок (программе нужны только PNG и ICO)
    "qtiff.dll",
    "qwebp.dll",
    "qjpeg.dll",
    "qgif.dll",
    "qtga.dll",
    "qicns.dll",
    "qwbmp.dll",
    # Лишние интерфейсы win32
    "win32ui.pyd",
}

# Исключаем бинарники
a.binaries = [x for x in a.binaries if Path(x[0]).name not in excluded_binaries]

# Исключаем все 96 файлов локализаций Qt (.qm) — экономия ~6.5 МБ
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
    upx_dir=".",        # Берем upx.exe прямо из папки проекта
    upx_exclude=[
        "vcruntime140.dll",
        "msvcp140.dll",
        "qwindows.dll",
    ],
    runtime_tmpdir=None,
    console=False,      # Оконный режим (без консоли)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)
