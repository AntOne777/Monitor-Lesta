"""
worker.py — Background QThread workers for ping and online monitoring.

Architecture:
  PingWorker  — one thread per server, pings at configurable intervals.
  OnlineWorker — single thread, fetches online player count from the API.
"""
from __future__ import annotations

import concurrent.futures
import http.client
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import threading
import time
from typing import Optional
from urllib.parse import urlparse
from PyQt6.QtCore import QThread, pyqtSignal

from core.config import AppSettings, ServerInfo, ONLINE_API_URL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_dns_cache: dict[str, tuple[float, Optional[str]]] = {}
_DNS_TTL_S = 300.0  # перевыводим DNS каждые 5 минут


def _resolve_host(host: str) -> Optional[str]:
    """Resolve domain to IP with short-lived cache; None on failure.

    Если хост уже является IP-адресом — возвращаем его как есть
    (обратная совместимость со старым config.py).
    """
    now = time.monotonic()
    cached = _dns_cache.get(host)
    if cached and (now - cached[0]) < _DNS_TTL_S and cached[1] is not None:
        return cached[1]
    try:
        import ipaddress
        ipaddress.ip_address(host)
        ip = host                      # это уже IP — резолвить не нужно
    except ValueError:
        try:
            ip = socket.gethostbyname(host)
        except OSError:
            ip = None
    _dns_cache[host] = (now, ip)
    return ip


# Порты для TCP-fallback в порядке приоритета.
# ВАЖНО: у некоторых игровых шлюзов (например login.p1.tanki.su) порт 443
# закрыт/фильтруется — тогда пинг по 443 всегда даёт прочерк, хотя сервер жив.
# Поэтому пробуем несколько портов и берём первый успешный замер.
_TCP_PROBE_PORTS = (80, 443, 20012, 20021)


def _ping_tcp(host: str, ports=_TCP_PROBE_PORTS, timeout_s: float = 2.0) -> Optional[float]:
    """Fallback: TCP connect latency (ms). Пробует несколько портов."""
    try:
        ip = _resolve_host(host)
        if ip is None:
            return None
    except OSError:
        return None

    for port in ports:
        try:
            t0 = time.perf_counter()
            with socket.create_connection((ip, port), timeout=timeout_s):
                pass
            return (time.perf_counter() - t0) * 1000.0
        except (OSError, socket.timeout):
            continue
    return None


# Паттерны собираются из байтов в ЯВНО указанных кодировках — это надёжнее,
# чем хардкод байтовых литералов (cp866 и cp1251 дают разные байты для кириллицы).
def _alts(word: str):
    out = []
    for enc in ("cp866", "cp1251", "utf-8"):
        out.append(word.encode(enc))
        out.append(word.upper().encode(enc))
    return b"|".join(re.escape(a) for a in out)

_TIME_WORD = _alts("время")
# ASCII-вариант «time=Nms» ловится всегда; русский «время=N...» не привязывается
# к байтам суффикса «мс» (они зависят от кодировки) — берём только число.
_NUM_PAT = re.compile(
    rb"(?:time\s*[=<]\s*(\d+(?:[.,]\d+)?)\s*m?s" +
    rb"|" + rb"(?:" + _TIME_WORD + rb")\s*[=<]\s*(\d+(?:[.,]\d+)?)" + rb")",
    re.IGNORECASE)
_LT1_PAT = re.compile(
    rb"(?:time\s*<\s*1\s*m?s|(?:" + _TIME_WORD + rb")\s*<)", re.IGNORECASE)


def _ping_system_command(host: str, timeout_s: float = 2.0) -> Optional[float]:
    """
    RTT через системный ping.exe — тот же метод, который гарантированно
    работает у пользователя в cmd (PingSucceeded=True, RTT=10 ms).

    Исправления по итогам внешнего код-ревью:
      * НЕ используем text=True: он декодирует вывод в cp1251, тогда как
        ping.exe печатает в OEM-кодировке (cp866/cp1251/oem) — кириллица
        превращалась в крякозябры и регулярка «время=Nмс» не срабатывала.
        Читаем БАЙТЫ и ищем паттерны сразу в нескольких кодировках.
      * Убран читерский «return 1.0»: если reply есть, но число не
        распознано — честно возвращаем None и идём в TCP-фолбэк.
    """
    target = _resolve_host(host) or host
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", str(int(timeout_s * 1000)), target],
            capture_output=True,
            timeout=timeout_s + 1.5,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        out = result.stdout or b""

        # Собираем варианты декодирования → utf-8 байты (для RU-локали:
        # cp866/cp1251 дают корректное «время=10мс», затем матчимся).
        blobs = [out]
        for enc in ("cp866", "cp1251", "utf-8"):
            try:
                blobs.append(out.decode(enc, errors="ignore").encode("utf-8"))
            except Exception:
                continue
        blob = b"\n".join(blobs)

        # Собираем ВСЕ ответы (ping -n 1 выдаёт одну строку «время=Nмс»,
        # но при увеличении -n берём медиану для устойчивости к выбросам).
        vals = []
        for m in _NUM_PAT.finditer(blob):
            g = next(x for x in m.groups() if x)
            try:
                v = float(g.replace(b",", b"."))
            except ValueError:
                continue
            if 0 < v < 10000:
                vals.append(v)

        # "время<..." / "time<1ms" — очень быстрый ответ (<1 мс)
        if not vals and _LT1_PAT.search(blob):
            return 0.5

        if vals:
            vals.sort()
            return vals[len(vals) // 2]   # медиана

        # Reply мог прийти без распознанного числа — НЕ выдумываем значение:
        # возвращаем None, решение за TCP-фолбэком.
        return None

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def measure_ping(server: ServerInfo, timeout_s: float = 2.0) -> Optional[float]:
    """
    Порядок замеров:
      1) Системный ping.exe (ICMP) — надёжный, тот же что в cmd.
      2) Fallback: TCP connect latency (несколько портов).
    """
    host = server.host

    # 1) Системный ping.exe
    result = _ping_system_command(host, timeout_s)
    if result is not None:
        return result

    # 2) Fallback: TCP connect (сначала настроенный порт сервера, затем типовые)
    ports = tuple([server.port] + [p for p in _TCP_PROBE_PORTS if p != server.port])
    return _ping_tcp(host, ports, timeout_s)


# ---------------------------------------------------------------------------
# PingWorker
# ---------------------------------------------------------------------------

class PingManagerWorker(QThread):
    """
    Manages pinging of all servers concurrently using a ThreadPoolExecutor.
    Emits `ping_result(server_name, ping_ms_or_None)` on each measurement.
    """

    ping_result = pyqtSignal(str, object)   # (server_name, float | None)
    error_occurred = pyqtSignal(str, str)   # (server_name, error_message)

    def __init__(self, servers: list[ServerInfo], app_settings: AppSettings, parent=None):
        super().__init__(parent)
        self.servers = servers
        self.app_settings = app_settings
        self._stop_event = threading.Event()
        self._executor = None

    def run(self) -> None:
        interval_s = self.app_settings.ping_interval_ms / 1000.0
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(self.servers))

        while not self._stop_event.is_set():
            t_start = time.perf_counter()

            futures = {
                self._executor.submit(measure_ping, srv, interval_s * 0.8): srv
                for srv in self.servers
            }

            for future in concurrent.futures.as_completed(futures):
                if self._stop_event.is_set():
                    break
                srv = futures[future]
                try:
                    ping_ms = future.result()
                    self.ping_result.emit(srv.name, ping_ms)
                except Exception as exc:  # noqa: BLE001
                    self.error_occurred.emit(srv.name, str(exc))
                    self.ping_result.emit(srv.name, None)

            if not self._stop_event.is_set():
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                sleep_ms = max(0, self.app_settings.ping_interval_ms - elapsed_ms)
                self._stop_event.wait(sleep_ms / 1000.0)

    def stop(self) -> None:
        self._stop_event.set()
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)


# ---------------------------------------------------------------------------
# OnlineWorker
# ---------------------------------------------------------------------------

class OnlineWorker(QThread):
    """
    Periodically fetches player online counts from the Straniks API.
    Emits `online_updated(data_dict)` where data_dict maps server_name -> count.
    Also emits `total_updated(total_int)`.
    """

    online_updated = pyqtSignal(dict)   # {server_name: int}
    total_updated  = pyqtSignal(int)    # total online
    fetch_error    = pyqtSignal(str)    # error message

    def __init__(self, app_settings: AppSettings, parent=None):
        super().__init__(parent)
        self.app_settings = app_settings
        self._stop_event = threading.Event()
        self._force_event = threading.Event()
        self._conn = None  # keep-alive http.client.HTTPSConnection

    def run(self) -> None:
        while not self._stop_event.is_set():
            self._fetch()
            self._force_event.clear()
            # Wait for next interval or force fetch
            interval = self.app_settings.online_interval_ms / 1000.0
            chunk = 0.2
            slept = 0.0
            while slept < interval and not self._stop_event.is_set() and not self._force_event.is_set():
                self._stop_event.wait(chunk)
                slept += chunk

    def _close_conn(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def _fetch(self) -> None:
        """HTTPS GET без requests/urllib3 — экономия ~1.5 МБ в собранном .exe."""
        url = urlparse(ONLINE_API_URL)
        host = url.netloc
        path = url.path or "/"
        if url.query:
            path += "?" + url.query
        headers = {"User-Agent": "MT-Monitor/1.0", "Accept": "application/json"}
        try:
            try:
                if self._conn is None:
                    self._conn = http.client.HTTPSConnection(
                        host, timeout=10, context=ssl.create_default_context())
                self._conn.request("GET", path, headers=headers)
                resp = self._conn.getresponse()
            except (http.client.HTTPException, OSError):
                # соединение протухло / сети нет — пересоздаём один раз
                self._close_conn()
                self._conn = http.client.HTTPSConnection(
                    host, timeout=10, context=ssl.create_default_context())
                self._conn.request("GET", path, headers=headers)
                resp = self._conn.getresponse()

            if resp.status >= 400:
                raise RuntimeError(f"HTTP {resp.status}")

            # Защита от OOM (max 2 MB)
            content_length = resp.getheader("Content-Length")
            if content_length and int(content_length) > 2 * 1024 * 1024:
                raise ValueError("Payload too large (Content-Length)")

            raw_data = b""
            while True:
                if self._stop_event.is_set():
                    return
                chunk = resp.read(8192)
                if not chunk:
                    break
                raw_data += chunk
                if len(raw_data) > 2 * 1024 * 1024:
                    raise ValueError("Payload too large (Chunking)")

            self._close_conn()
            data = json.loads(raw_data)
            self._parse(data)
        except (http.client.HTTPException, OSError) as exc:
            self._close_conn()
            if self._stop_event.is_set():
                return
            if isinstance(exc, socket.timeout) or "timed out" in str(exc).lower():
                self.fetch_error.emit("Сервис API не отвечает")
            else:
                self.fetch_error.emit("Кажется, пропал интернет")
        except Exception as exc:  # noqa: BLE001
            self._close_conn()
            self.fetch_error.emit(f"Не удалось обновить онлайн: {exc}")

    def _parse(self, data: dict | list) -> None:
        """
        Parse the Straniks API response safely without duplicating code.
        """
        online_map: dict[str, int] = {}
        total = 0
        target_servers = {"RU1", "RU2", "RU3", "RU4", "RU5", "RU6", "RU7", "RU8", "RU9"}

        def extract(items):
            nonlocal total
            for key, val in items:
                k = str(key).upper().replace("-", "").replace("_", "")
                for sv in target_servers:
                    idx = k.find(sv)
                    if idx != -1:
                        # Prevent "RU1" from matching "RU10", "RU11", etc.
                        if idx + len(sv) < len(k) and k[idx + len(sv)].isdigit():
                            continue
                        try:
                            cnt = int(val)
                            online_map[sv] = cnt
                            total += cnt
                        except (ValueError, TypeError):
                            pass

        if isinstance(data, dict):
            extract(data.items())
            if not online_map:
                for top_val in data.values():
                    if isinstance(top_val, dict):
                        extract(top_val.items())
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    name_raw = str(item.get("name", item.get("server", item.get("id", ""))))
                    count = item.get("count", item.get("online", item.get("players", 0)))
                    extract([(name_raw, count)])

        if online_map:
            self.online_updated.emit(online_map)
            self.total_updated.emit(total)

    def stop(self) -> None:
        self._stop_event.set()
        self._close_conn()

    def fetch_now(self) -> None:
        """Request immediate fetch on next worker cycle without blocking caller thread."""
        self._force_event.set()