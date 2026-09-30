@echo off
chcp 65001 >nul
REM ============================================================
REM  MT Monitor — ОДИН .exe, минимальный размер (<35 МБ), быстрый старт.
REM  PyInstaller onefile + UPX (--best --lzma) + агрессивная фильтрация Qt6.
REM  Требуется Windows. upx.exe уже лежит в папке проекта.
REM ============================================================
set "PATH=%LOCALAPPDATA%\Programs\Python\Python314;%LOCALAPPDATA%\Programs\Python\Python314\Scripts;%PATH%"

where python >nul 2>nul || (echo [ERROR] Python not found in PATH & pause & exit /b 1)

echo [1/3] Checking dependencies...
python -c "import PyInstaller" 2>nul || pip install --upgrade pyinstaller
python -c "import PyQt6, qfluentwidgets, requests" 2>nul ^
  || pip install PyQt6 PyQt6-Qt6 PyQt6-Fluent-Widgets requests

if not exist upx.exe (
    echo [WARN] upx.exe not found next to this script.
    echo        Download UPX from https://github.com/upx/upx/releases
    echo        and put upx.exe into the project folder for max compression.
)

echo [2/3] Building dist\MT_Monitor.exe  (onefile, UPX best)...
pyinstaller build_fast.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] Build failed. See messages above.
    pause & exit /b 1
)

echo [3/3] Done!
for %%F in ("dist\MT_Monitor.exe") do echo   File: %%~fF   Size: %%~zF bytes
echo   Один портативный .exe — можно кидать на флешку.
pause
