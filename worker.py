"""
worker.py — Background QThread workers for ping and online monitoring.

Architecture:
  PingWorker  — one thread per server, pings at configurable intervals.
  OnlineWorker — single thread, fetches online player count from the API.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import socket
import subprocess
import sys
import threading
import time
from typing import Optional

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from core.config import AppSettings, ServerInfo, ONLINE_API_URL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_host(host: str) -> Optional[str]:
    """Resolve domain to IP; return IP string or None on failure."""
    try:
        return socket.gethostbyname(host)
    except OSError:
        return None


def _ping_socket(host: str, timeout_s: float = 1.0) -> Optional[float]:
    """
    Measure round-trip via raw ICMP echo using socket (requires no admin on some OSes).
    Falls back gracefully. Returns ms or None.
    """
    import struct, select, time as _time

    # Build ICMP echo packet
    ICMP_ECHO_REQUEST = 8
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        sock.settimeout(timeout_s)
    except OSError:
        # Raw socket not available (no admin) — return None to use TCP fallback
        return None

    try:
        ip = _resolve_host(host)
        if ip is None:
            return None

        # Build ICMP packet using network byte order (!)
        packet_id = threading.get_ident() & 0xFFFF
        header = struct.pack("!bbHHh", ICMP_ECHO_REQUEST, 0, 0, packet_id, 1)
        payload = b"abcdefghijklmnop"
        checksum = _icmp_checksum(header + payload)
        header = struct.pack("!bbHHh", ICMP_ECHO_REQUEST, 0, checksum, packet_id, 1)
        packet = header + payload

        t0 = _time.perf_counter()
        sock.sendto(packet, (ip, 0))
        ready = select.select([sock], [], [], timeout_s)
        if ready[0]:
            _ = sock.recv(1024)
            return (_time.perf_counter() - t0) * 1000.0
    except OSError:
        pass
    finally:
        sock.close()

    return None


def _icmp_checksum(data: bytes) -> int:
    s = 0
    for i in range(0, len(data) - 1, 2):
        s += (data[i] << 8) + data[i + 1]
    if len(data) % 2:
        s += data[-1] << 8
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return ~s & 0xFFFF


def _ping_tcp(host: str, port: int = 443, timeout_s: float = 2.0) -> Optional[float]:
    """Fallback: measure TCP connect latency (ms)."""
    try:
        ip = _resolve_host(host)
        if ip is None:
            return None
        t0 = time.perf_counter()
        with socket.create_connection((ip, port), timeout=timeout_s):
            pass
        return (time.perf_counter() - t0) * 1000.0
    except (OSError, socket.timeout):
        return None


def measure_ping(server: ServerInfo, timeout_s: float = 2.0) -> Optional[float]:
    """
    Try ICMP ping first; fall back to TCP connect if ICMP fails.
    Resolves domain hosts before pinging.
    """
    host = server.host

    # Try socket ICMP
    result = _ping_socket(host, timeout_s)
    if result is not None:
        return result

    # Fallback: TCP connect
    return _ping_tcp(host, server.port, timeout_s)


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
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "MT-Monitor/1.0"})

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

    def _fetch(self) -> None:
        try:
            with self._session.get(ONLINE_API_URL, timeout=10, stream=True, verify=True) as resp:
                resp.raise_for_status()
                
                # Protect against OOM (max 2 MB)
                content_length = resp.headers.get('Content-Length')
                if content_length and int(content_length) > 2 * 1024 * 1024:
                    raise ValueError("Payload too large (Content-Length)")
                
                raw_data = b""
                for chunk in resp.iter_content(chunk_size=8192):
                    if self._stop_event.is_set():
                        return
                    raw_data += chunk
                    if len(raw_data) > 2 * 1024 * 1024:
                        raise ValueError("Payload too large (Chunking)")
                        
                data = json.loads(raw_data)
                self._parse(data)
        except requests.ConnectionError:
            self.fetch_error.emit("Кажется, пропал интернет")
        except requests.Timeout:
            self.fetch_error.emit("Сервис API не отвечает")
        except requests.HTTPError as exc:
            self.fetch_error.emit(f"Ошибка API: {exc}")
        except Exception as exc:  # noqa: BLE001
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
        self._session.close()

    def fetch_now(self) -> None:
        """Request immediate fetch on next worker cycle without blocking caller thread."""
        self._force_event.set()
