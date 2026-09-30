@echo off
set "PATH=%LOCALAPPDATA%\Programs\Python\Python314;%LOCALAPPDATA%\Programs\Python\Python314\Scripts;%PATH%"
echo ===================================================
echo   Building MT Monitor (Size Optimization + UPX)
echo ===================================================
echo.
python -m PyInstaller build.spec --clean
echo.
echo ===================================================
echo   Build finished! Check dist\MT_Monitor.exe
echo ===================================================
