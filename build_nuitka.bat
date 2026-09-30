@echo off
setlocal
chcp 65001 >nul
title MT Monitor - Nuitka Onefile Build

cd /d "%~dp0"

echo ===================================================
echo   MT Monitor: сборка ОДНОГО .exe через Nuitka
echo   (portable onefile, быстрый старт)
echo ===================================================
echo.

REM ------------------------------------------------------------
REM 1. Ищем Python и проверяем/ставим зависимости
REM ------------------------------------------------------------
where python >nul 2>nul
if %errorlevel%==0 (set "PY=python") else (where py >nul 2>nul && set "PY=py -3")

"%PY%" --version >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] Python не найден в PATH. Установите Python 3.10+ и повторите.
    pause & exit /b 1
)

echo [1/4] Проверка зависимостей...
"%PY%" -m pip show nuitka >nul 2>nul || (
    echo       Установка Nuitka...
    "%PY%" -m pip install -U nuitka ordered-set zstandard
)
"%PY%" -c "import PyQt6, qfluentwidgets" >nul 2>nul || (
    echo       Установка библиотек проекта из requirements.txt...
    "%PY%" -m pip install -r requirements.txt
)

REM ------------------------------------------------------------
REM 2. Проверяем C-компилятор. Если его нет — ускоренный кэш
REM    скачивания MinGW64 отключён, Nuitka сама скачает GCC
REM    при сборке (флаг --assume-yes-for-downloads).
REM ------------------------------------------------------------
echo [2/4] Компилятор: Nuitka скачает MinGW64/GCC автоматически ^(если нужен^)...

REM ------------------------------------------------------------
REM 3. Сборка одного файла
REM    Флаги:
REM      --standalone                 автономная сборка (все DLL внутри)
REM      --onefile                    упаковать всё в один .exe
REM      --windows-console-mode=disable  без окна консоли (GUI-приложение)
REM      --enable-plugin=pyqt6        плагин PyQt6 (Qt hooks, DLL, плагины платформ)
REM      --include-package=qfluentwidgets  ресурсы/иконки Fluent-виджетов
REM      --include-package=core,ui,worker  локальные модули проекта
REM      --nofollow-import-to=...     исключить тяжёлые неиспользуемые модули Qt
REM      --assume-yes-for-downloads   авто-скачивание компилятора без вопросов
REM      --onefile-tempdir-spec=...   распаковка в кэш: повторные запуски быстрее
REM      --lto=no + jobs=8            ускорение компиляции без потери скорости старта
REM ------------------------------------------------------------
echo [3/4] Сборка. ПЕРВЫЙ запуск ДОЛГИЙ (скачивание компилятора + компиляция C),
echo        это нормально. Дальнейшие пересборки идут быстрее (кэш .nuitka-cache).
echo.

"%PY%" -m nuitka ^
    main.py ^
    --standalone ^
    --onefile ^
    --onefile-tempdir-spec="{CACHE_DIR}/{PRODUCT}/{VERSION}" ^
    --windows-console-mode=disable ^
    --enable-plugin=pyqt6 ^
    --include-package=qfluentwidgets ^
    --include-package=core ^
    --include-package=ui ^
    --include-module=worker ^
    --nofollow-import-to=PyQt6.QtWebEngineCore ^
    --nofollow-import-to=PyQt6.QtWebEngineWidgets ^
    --nofollow-import-to=PyQt6.QtQml ^
    --nofollow-import-to=PyQt6.QtQuick ^
    --nofollow-import-to=PyQt6.QtQuickWidgets ^
    --nofollow-import-to=PyQt6.QtMultimedia ^
    --nofollow-import-to=PyQt6.QtMultimediaWidgets ^
    --nofollow-import-to=PyQt6.QtBluetooth ^
    --nofollow-import-to=PyQt6.QtPositioning ^
    --nofollow-import-to=PyQt6.QtNfc ^
    --nofollow-import-to=PyQt6.QtSensors ^
    --nofollow-import-to=PyQt6.QtSerialPort ^
    --nofollow-import-to=PyQt6.QtTest ^
    --nofollow-import-to=PyQt6.QtDesigner ^
    --nofollow-import-to=PyQt6.QtHelp ^
    --nofollow-import-to=tkinter ^
    --nofollow-import-to=numpy ^
    --nofollow-import-to=scipy ^
    --nofollow-import-to=pandas ^
    --nofollow-import-to=matplotlib ^
    --nofollow-import-to=PIL ^
    --nofollow-import-to=unittest ^
    --nofollow-import-to=pydoc ^
    --assume-yes-for-downloads ^
    --jobs=8 ^
    --lto=no ^
    --remove-all-comments-from-code ^
    --python-flag=no_asserts ^
    --python-flag=-O ^
    --output-dir=dist ^
    --output-filename=MT_Monitor.exe ^
    --windows-icon-from-ico=ico.ico

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Сборка не удалась. См. текст ошибки выше.
    echo   Частые причины: антивирус блокирует скачанный gcc^(Nuitka^),
    echo   либо не хватает памяти при компиляции. Попробуйте закрыть лишние
    echo   программы и запустить build_nuitka.bat снова.
    pause & exit /b 1
)

REM ------------------------------------------------------------
REM 4. Результат
REM ------------------------------------------------------------
echo.
echo ===================================================
echo   Готово! Один портативный файл:
echo       dist\MT_Monitor.exe
echo   Можно кидать на флешку и запускать где угодно.
echo ===================================================
pause
endlocal
