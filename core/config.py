"""
core/config.py — Server list, application settings and shared constants.

ВАЖНО (исправлено в v1.1.1):
    Раньше здесь были захардкожены IP-адреса серверов. Это ошибка:
    Lesta Games использует балансировщики нагрузки, и IP у login-хостов
    со временем МЕНЯЕТСЯ. Именно так RU1 перестал пинговаться — старый IP
    более не принадлежит серверу. Теперь во всех пунктах SERVERS указаны
    ДОМЕНЫ (login.pN.tanki.su) — worker.py сам резолвит их через DNS перед
    каждым замером, поэтому адреса всегда актуальны.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

APP_NAME = "MT Monitor"
APP_VERSION = "1.1.1"
APP_AUTHOR = "MT Monitor Team"

# ---------------------------------------------------------------------------
# Server definitions
# ---------------------------------------------------------------------------

@dataclass
class ServerInfo:
    name: str          # e.g. "RU1"
    host: str          # ДОМЕН (не IP!) — резолвится динамически через DNS
    location: str      # Human-readable city name
    port: int = 443    # TCP port for latency check fallback

SERVERS: List[ServerInfo] = [
    ServerInfo("RU1", "login.p1.tanki.su", "Москва"),
    ServerInfo("RU2", "login.p2.tanki.su", "Москва"),
    ServerInfo("RU3", "login.p3.tanki.su", "Москва (временный)"),
    ServerInfo("RU4", "login.p4.tanki.su", "Екатеринбург"),
    ServerInfo("RU5", "login.p5.tanki.su", "Москва (временный)"),
    ServerInfo("RU6", "login.p6.tanki.su", "Москва"),
    ServerInfo("RU8", "login.p8.tanki.su", "Красноярск"),
    ServerInfo("RU9", "login.p9.tanki.su", "Хабаровск"),
]

ONLINE_API_URL = "https://straniks.ru/pub/api/v2/wot_online.php?online=all"

# ---------------------------------------------------------------------------
# Application settings (runtime-mutable)
# ---------------------------------------------------------------------------

@dataclass
class AppSettings:
    """Mutable settings controlled via Settings screen."""
    smoothing_window: int = 20       # EMA window N  →  A = 2/(N+1)
    ping_interval_ms: int = 500      # How often to ping (ms)
    history_size: int = 200          # Max raw ping samples to keep per server
    online_interval_ms: int = 30_000 # Online API refresh interval

# Singleton instance used app-wide
settings = AppSettings()
