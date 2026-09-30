# -*- mode: python ; coding: utf-8 -*-
"""
build_fast.spec — РЕКОМЕНДУЕМЫЙ вариант для задачи «ОДИН .exe, < 35 МБ, старт 1–3 с».

Почему PyInstaller onefile + UPX, а не Nuitka:
  * Nuitka --onefile физически не может дать < 35 МБ: нативная компиляция
    растягивает код, а UPX к артефактам Nuitka не применяется (итог 60–120 МБ).
  * Только PyInstaller onefile + UPX (--best) реально сжимает Qt6 DLL до уровня
    ~20–30 МБ за счёт фильтрации бинарников ниже.
  * Скорость старта обеспечивается двумя вещами:
      1) в main.py тяжёлые страницы/потоки создаются лениво (QTimer.singleShot),
         окно показывается сразу;
      2) отсечены все лишние модули → архив маленький → распаковка быстрая.

Сборка:  pyinstaller build_fast.spec --clean
Результат: dist\MT_Monitor.exe  (один портативный файл)
"""

import sys
from pathlib import Path

block_cipher = None

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# qfluentwidgets тянет данные (qss, иконки, шрифты) через динамические импорты
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
        "PyQt6.QtSvg",       # нужен qfluentwidgets (отрисовка иконок)
        "core.config",
        "core.analytics",
        "worker",
        "ui.dashboard",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # --- PyQt5 на всякий случай (в проекте PyQt6) ---
        "PyQt5",
        # --- Модули Qt6, которые программа НЕ использует ---
        "PyQt6.QtMultimedia", "PyQt6.QtMultimediaWidgets",
        "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtWebChannel", "PyQt6.QtWebSockets",
        "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.QtQuickWidgets",
        "PyQt6.QtBluetooth", "PyQt6.QtPositioning", "PyQt6.QtNfc",
        "PyQt6.QtSensors", "PyQt6.QtSerialPort", "PyQt6.QtSql",
        "PyQt6.QtTest", "PyQt6.QtCharts", "PyQt6.QtDataVis",
        "PyQt6.QtNetwork",   # HTTP идёт через stdlib http.client — Qt6Network.dll не нужен
        "PyQt6.QtPdf", "PyQt6.QtPdfWidgets",
        "PyQt6.QtDesigner", "PyQt6.QtUiTools",
        "PyQt6.QtXml", "PyQt6.QtDBus",
        # --- Тяжёлые Python-библиотеки, которых нет в коде ---
        "numpy", "scipy", "pandas", "matplotlib", "PIL",
        "tkinter", "unittest", "pydoc", "setuptools", "pip",
        # --- stdlib-раздувители. ВНИМАНИЕ: ssl НЕ исключаем — HTTPS к API
        #     идёт через stdlib http.client + ssl (requests удалён из проекта). ---
        "xmlrpc", "http.server", "logging.handlers",
        "py_compile", "argparse", "gettext", "difflib",
        "pdb", "profile", "pickletools", "doctest", "turtle",
        "lib2to3", "distutils", "venv", "zipapp",
    ],
    noarchive=False,
)

# ---------------------------------------------------------------------------
# Фильтрация бинарников: вырезаем всё, что не нужно для одного окна виджетов.
# Это главный источник экономии размера (Qt6 по умолчанию тянет >100 МБ).
# ---------------------------------------------------------------------------
excluded_binaries = {
    # Софтверный OpenGL-рендерер (~19.7 МБ) — на Win10/11 есть аппаратный
    "opengl32sw.dll",
    # PDF-движок
    "Qt6Pdf.dll", "qpdf.dll",
    # Multimedia + FFmpeg-кодеки
    "Qt6Multimedia.dll", "Qt6MultimediaWidgets.dll",
    "avcodec-61.dll", "avformat-61.dll", "avutil-59.dll",
    "swscale-8.dll", "swresample-5.dll",
    # Network / QML / Quick
    "Qt6Network.dll", "Qt6Qml.dll", "Qt6QmlModels.dll", "Qt6QmlWorkerScript.dll",
    "Qt6Quick.dll", "Qt6QuickControls2.dll", "Qt6QuickTemplates2.dll",
    "Qt6QuickShapes.dll", "Qt6ShaderTools.dll",
    # Лишние image plugins (программе нужны только PNG и ICO)
    "qjpeg.dll", "qtiff.dll", "qwebp.dll", "qgif.dll",
    "qtga.dll", "qicns.dll", "qwbmp.dll",
    # Лишние platform input contexts
    "qimcompose.dll", "qtvirtualkeyboardplugin.dll",
    # Прочее
    "Qt6Charts.dll", "Qt6DataVisualization.dll", "Qt6Sql.dll",
    "Qt6Test.dll", "Qt6WebChannel.dll", "Qt6WebSockets.dll",
    "Qt6RemoteObjects.dll", "win32ui.pyd",
}

a.binaries = [x for x in a.binaries if Path(x[0]).name not in excluded_binaries]

# Все .qm локализации Qt (~6.5 МБ) — программе нужен только ru/en из qfluentwidgets
a.datas = [x for x in a.datas if not x[0].endswith(".qm")]

# Отсекаем лишние подмодули qfluentwidgets (gallery/components демо и т.п.)
hiddenimports = [h for h in hiddenimports if ".gallery" not in h and ".demo" not in h]

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
    upx_dir=".",             # upx.exe лежит в корне проекта
    upx_exclude=[
        # Не сжимаем то, что ломается при UPX или критично для старта:
        "vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll",
        "qwindows.dll",     # платформенный плагин Qt — оставляем несжатым
        "Qt6Core.dll",      # самый горячий при старте DLL — без UPX ради скорости
    ],
    upx_opts=["--best", "--lzma"],   # максимальное сжатие остальных DLL/pyd
    runtime_tmpdir=None,
    console=False,          # GUI без консоли
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="ico.ico",         # иконка лежит в корне проекта
)
