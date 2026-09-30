@echo off
chcp 65001 >nul
REM ============================================================
REM  MT Monitor — ОДИН .exe, минимальный размер, быстрый старт.
REM  Рекомендуется: build_fast.bat (PyInstaller onefile + UPX best,
REM               фильтрованная Qt6 → < 35 МБ, старт 1–3 с).
REM  build_nuitka.bat оставлен как экспериментальный вариант
REM  (старт самый быстрый, но размер 60–120 МБ — требование <35 МБ нарушает).
REM ============================================================
set "PATH=%LOCALAPPDATA%\Programs\Python\Python314;%LOCALAPPDATA%\Programs\Python\Python314\Scripts;%PATH%"

echo ===================================================
echo   A (рекомендуется): PyInstaller onefile + UPX
echo      ^< 35 MB, старт 1-3 c
echo   B (эксперимент):  Nuitka onefile
echo      старт ~1-2 c, но размер 60-120 MB
echo ===================================================
choice /C AB /N /M "A = PyInstaller+UPX, B = Nuitka:"
if errorlevel 2 goto nuitka
if errorlevel 1 goto pyi

:pyi
call build_fast.bat
goto end

:nuitka
call build_nuitka.bat
goto end

:end