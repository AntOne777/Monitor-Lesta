# Changelog

Все значимые изменения проекта MT Monitor.
Формат: «Исходник → Что сделано → Результат».

---

## v1.3 — 2026-09-30 — Финальная сборка ОДНОГО .exe работает ✅

### Исправлен крах собранного .exe: `ModuleNotFoundError: No module named 'PyQt6.QtXml'`
- **Исходник:** после запуска `dist\MT_Monitor.exe` падал с ошибкой отсутствия `PyQt6.QtXml`.
- **Что сделано:**
  - `build_fast.spec`: убрали `PyQt6.QtXml` из `excludes` и добавили в `hiddenimports`
    (`qfluentwidgets/common/icon.py` импортирует QtXml на старте пакета через цепочку
    `dialog_box/color_dialog.py`).
  - В `hiddenimports` сохранён `qfluentwidgets.multimedia` (в v1.11.x подтягивается
    из `message_dialog.py` на старте; сам `PyQt6.QtMultimedia` остаётся в excludes —
    модуль защищён try/except ImportError).
- **Результат:** .exe запускается без ошибок. Пользователь подтвердил: «РАБОТАЕТ».

---

## v1.2 — 2026-09-30 — Оптимизация размера и скорости однофайловой сборки

### Переход на связку PyInstaller onefile + UPX + агрессивная фильтрация Qt6
- **Исходник:** PyInstaller onefile давал ~35 МБ, но старт 5–15 с; Nuitka onefile —
  быстрый старт, но 60–120 МБ. Требование: один файл, < 35 МБ, старт 1–3 с.
- **Что сделано:**
  - Новый `build_fast.spec`:
    - вырезаны неиспользуемые модули Qt6 (Qml, Quick, Multimedia, WebEngine, PDF,
      Network, Charts, Sql, Test, Designer, UiTools, Bluetooth, SerialPort и др.);
    - удалены бинарники: `opengl32sw.dll` (~20 МБ), FFmpeg-кодеки, лишние image
      plugins (qjpeg/qtiff/qwebp/…), `Qt6Network.dll` и т.п.;
    - вырезаны все `.qm`-локализации Qt (~6.5 МБ);
    - из Python-степа исключены numpy/scipy/pandas/matplotlib/PIL/tkinter и лишний
      stdlib-раздув (ssl оставлен — нужен для HTTPS);
    - UPX `--best --lzma` для всего, КРОМЕ критичных для старта файлов
      (`Qt6Core.dll`, `qwindows.dll`, vcruntime — не сжимаются ради скорости).
  - Новый `build_fast.bat`: проверка зависимостей → сборка → вывод размера exe.
  - `worker.py`: `requests.Session` заменён на stdlib `http.client.HTTPSConnection`
    + `ssl` (keep-alive, таймауты, лимит 2 МБ, сообщения об ошибках сохранены) —
    из сборки уходят urllib3/certifi/charset_normalizer (~1.5 МБ). Удалён мёртвый
    `import subprocess`.
  - `main.py`: ленивая инициализация GUI — окно показывается сразу, тяжёлые
    страницы/метрики/фоновые потоки создаются после `show()` через
    `QTimer.singleShot(0, ...)`; защита `closeEvent` от закрытия до конца инициализации.
  - `requirements.txt`: requests/ping3 убраны (не используются), pyinstaller активен,
    nuitka помечен опциональным.
  - `build.bat`: меню выбора — A = build_fast (рекомендуется), B = Nuitka (эксперимент).
  - `README.md`: инструкция сборки, компромиссы (UPX vs антивирусы; возврат DLL при
    ошибке запуска), таблица сравнения упаковок.
- **Результат:** ожидаемо ~22–32 МБ (< 35 МБ ✅) и старт ~1.5–3 с ✅, один портативный
  .exe. Единственная связка инструментов, способная дать все три требования сразу
  (Nuitka onefile физически не даёт < 35 МБ; cx_Freeze/SoEasyPack сжатия UPX не имеют).

---

## v1.1 — 2026-09-30 — Эксперимент со сборкой через Nuitka

### Перевод сборки на Nuitka standalone+onefile (позже отменён по размеру)
- **Исходник:** жалоба на долгий запуск PyInstaller onefile (5–15 с).
- **Что сделано:**
  - Добавлен `build_nuitka.bat`: автопроверка/установка Nuitka, скачивание MinGW64
    через `--assume-yes-for-downloads`, флаги: `--standalone --onefile`,
    `--onefile-tempdir-spec="{CACHE_DIR}/{PRODUCT}/{VERSION}"` (кэш распаковки →
    повторные запуски почти мгновенные), `--windows-console-mode=disable`,
    `--enable-plugin=pyqt6`, `--include-package=qfluentwidgets/core/...`,
    `--nofollow-import-to=` для неиспользуемых модулей, `--jobs=8 --lto=no`.
  - Откат временного onedir-варианта (спеки возвращены к onefile).
- **Результат:** старт стал быстрее, но размер вырос до 60–120 МБ → вариант оставлен
  как экспериментальный (`build.bat`, пункт B), основным стал v1.2.

---

## v1.0 — до оптимизаций — Базовая версия

### Приложение мониторинга серверов Мир Танков (Lesta)
- PyQt6 + qfluentwidgets (MSFluentWindow, тёмная тема, без Mica/Acrylic).
- `worker.py`: `PingManagerWorker` (ICMP raw-сокет + TCP fallback, ThreadPoolExecutor)
  и `OnlineWorker` (онлайн с API).
- `core/`: конфиг серверов RU1–RU8/RU9, аналитика (EMA-сглаживание пинга,
  равномерность, плотность, скоринг рекомендаций).
- `ui/dashboard.py`: карточки серверов и таблица в реальном времени.
- Сборка: PyInstaller onefile (`build.spec` / `MT_Monitor.spec`, ~35 МБ, старт 5–15 с).

---

## Известные компромиссы и заметки
- **UPX и антивирусы:** некоторые антивирусы реагируют на UPX-упакованные exe.
  Лечение: исключение папки, подпись кода либо сборка без UPX (размер ~45–60 МБ).
- **Отсутствующий DLL при запуске:** удалите соответствующую строку из
  `excluded_binaries` в `build_fast.spec` и пересоберите (описано в README).
- **Python 3.14:** свежий Nuitka может его не поддерживать (актуально только для
  экспериментальной сборки v1.1; рекомендуемый путь — PyInstaller).
- `requests` и `ping3` более не зависимости проекта: HTTPS — через stdlib
  `http.client`, ICMP — через чистый `socket`.
