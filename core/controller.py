import asyncio
import threading
from PySide6.QtCore import QObject, Signal, QTimer
from core.pinger import AsyncPinger
from core.statistics import get_all_stats
from core.ranker import ServerRanker
from core.lesta_api import LestaAPI

class MonitorController(QObject):
    data_updated = Signal(dict)
    online_updated = Signal(dict)
    best_server_updated = Signal(str, dict, float)

    def __init__(self, hosts_info):
        super().__init__()
        self.hosts_info = hosts_info  # [(name, address), ...]
        self.pinger = None
        self.running = False
        self.update_timer = None
        self.online_timer = None
        self.loop = None
        self.thread = None
        self.smoothing_window = 20

    def start_monitoring(self, interval_ms=500):
        if self.running:
            return
        self.running = True
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, args=(interval_ms,))
        self.thread.daemon = True
        self.thread.start()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_data)
        self.update_timer.start(2000)

        self.online_timer = QTimer()
        self.online_timer.timeout.connect(self._update_online)
        self.online_timer.start(30000)
        self._update_online()

    def _run_loop(self, interval_ms):
        asyncio.set_event_loop(self.loop)
        addresses = [addr for _, addr in self.hosts_info]
        self.pinger = AsyncPinger(addresses, interval=interval_ms/1000.0, timeout=1.0, max_history=500)
        self.pinger.start()
        self.loop.run_forever()

    def stop_monitoring(self):
        self.running = False
        if self.update_timer:
            self.update_timer.stop()
        if self.online_timer:
            self.online_timer.stop()
        if self.pinger:
            self.pinger.stop()
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=1)

    def _update_data(self):
        if not self.pinger:
            return
        data = {}
        for name, addr in self.hosts_info:
            pings = self.pinger.get_latest_rtts(addr)
            if len(pings) >= 5:
                stats = get_all_stats(pings, window=self.smoothing_window)
            else:
                stats = {'avg': float('inf'), 'loss': 100, 'count': len(pings)}
            data[addr] = {'name': name, 'pings': pings, 'stats': stats}
        self.data_updated.emit(data)

        best_addr, best_stats, best_score = ServerRanker.get_best_server(
            {addr: {'pings': data[addr]['pings']} for addr in data.keys()}
        )
        if best_addr and best_score > 0:
            best_name = data[best_addr]['name']
            self.best_server_updated.emit(best_name, best_stats, best_score)

    def _update_online(self):
        online = LestaAPI.get_online()
        if online:
            self.online_updated.emit(online)
