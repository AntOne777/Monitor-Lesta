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

### Build .exe
`ash
pip install pyinstaller
pyinstaller build.spec
`
Output: dist/MT Monitor.exe

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
