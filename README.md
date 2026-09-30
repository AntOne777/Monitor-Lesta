# MT Monitor - Мониторинг серверов Мир Танков (Lesta)

Windows 11 Fluent Design desktop application for real-time WoT Lesta server monitoring.

## Features
- Real-time ping monitoring for all 8 RU servers (ICMP + TCP fallback)
- Smoothed ping via EMA filter (Kalman-style)
- Uniformity and Density metrics
- Smart server recommendation algorithm
- Online player count from straniks.ru API
- Dark Mica/Acrylic effect (Windows 11)

## Quick Start

### Requirements
- Python 3.10+
- Windows 10/11

### Install & Run
`ash
pip install -r requirements.txt
python main.py
`

### Build .exe — ОДИН файл, < 35 МБ, старт 1–3 секунды (РЕКОМЕНДУЕТСЯ)

```bat
build_fast.bat
```

Результат: **`dist\MT_Monitor.exe`** — один портативный файл (PyInstaller onefile + UPX).
Можно кидать на флешку и запускать на любом Windows 10/11 без установки Python.

Как достигается размер < 35 МБ и быстрый старт (см. `build_fast.spec`):
- вырезаны неиспользуемые модули Qt6 (Qml/Quick/Multimedia/WebEngine/PDF/Network/Charts…),
  софтверный рендерер `opengl32sw.dll` (~20 МБ), FFmpeg-кодеки, лишние image plugins,
  все `.qm` локализации (~6.5 МБ);
- все оставшиеся DLL/EXE сжаты UPX с `--best --lzma` (`upx.exe` лежит в папке проекта);
- критичные для старта файлы (`Qt6Core.dll`, `qwindows.dll`, vcruntime) НЕ сжимаются UPX —
  это компромисс в пользу скорости запуска;
- ленивая инициализация GUI в `main.py`: окно показывается сразу, тяжёлые страницы
  и фоновые потоки создаются после `show()` через `QTimer.singleShot`.

⚠️ Компромиссы:
- Если при запуске появится ошибка отсутствующего DLL — уберите соответствующую строку
  из `excluded_binaries` в `build_fast.spec` и пересоберите.
- Антивирусы иногда подозрительно относятся к UPX-упакованным exe. Лечение:
  исключение папки, либо подпись кода, либо сборка без UPX (размер вырастет до ~45–60 МБ).

### Эксперимент: Nuitka (`build_nuitka.bat`)
Самый быстрый старт (~1–2 с, кэш распаковки), но **размер 60–120 МБ**: нативная
компиляция растягивает код, а UPX к артефактам Nuitka не применяется. Требование
«< 35 МБ» этот вариант выполнить не может — оставлен как альтернатива, если
скорость важнее размера. Первая сборка долгая (10–30 мин, скачивается MinGW64) — это нормально.

### Сравнение упаковок (для данного проекта: PyQt6 + qfluentwidgets)

| Параметр          | PyInstaller onefile (без UPX) | **PyInstaller onefile + UPX (build_fast)** | Nuitka standalone+onefile |
|-------------------|-------------------------------|--------------------------------------------|---------------------------|
| Размер .exe       | ~45–60 МБ                     | **~22–32 МБ ✅ (< 35 МБ)**                 | ~60–120 МБ ❌             |
| Время запуска     | ~4–8 с                        | **~1.5–3 с ✅** (маленький архив + ленивый GUI) | ~1–2 с ✅            |
| Сложность сборки  | низкая                        | **низкая** (тот же pyinstaller + upx.exe)  | высокая (C-компилятор, долгая первая сборка) |
| Портативность     | один файл ✅                  | **один файл ✅**                           | один файл ✅              |

Вывод: единственный инструмент, дающий одновременно «один файл + < 35 МБ + старт 1–3 с», —
**PyInstaller onefile + UPX + агрессивная фильтрация Qt** (реализовано в `build_fast.spec`).
cx_Freeze/SoEasyPack size-преимуществ не дают: внутри тот же Python+Qt без сжатия UPX.
Дополнительно: `requests` заменён на stdlib `http.client` в `worker.py` — минус ещё ~1.5 МБ
(urllib3/certifi/charset_normalizer больше не упаковываются), поведение API-запросов прежнее.

## Architecture
`
main.py           # Entry point, MSFluentWindow with Mica effect
worker.py         # PingWorker + OnlineWorker (QThread)
core/
  config.py       # Server list, AppSettings
  analytics.py    # EMA, Uniformity, Density, Scoring
ui/
  dashboard.py    # Main dashboard with cards + server table  
  settings.py     # Settings screen
  about.py        # About screen
`

## Ping Methods (No Admin Required)
1. Raw ICMP socket (Windows allows without admin in most configs)
2. TCP connect timing fallback (port 443)
3. subprocess ping fallback

## Metrics
- **Psavg** = EMA-filtered ping: Psavg(i) = Psavg(i-1)*(1-A) + A*Pi, where A = 2/(N+1)
- **Uniformity** = (Pmin/Pmax)*100 — connection stability
- **Density** = (Pmin/Pavg)*100 — intermediate equipment load

## Server Recommendation Score
Score = 0.50*(1-norm_ping) + 0.25*norm_uniformity + 0.25*norm_density
