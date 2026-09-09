import asyncio
from icmplib import async_ping
from typing import Optional, List
import time

class AsyncPinger:
    def __init__(self, hosts: List[str], interval: float = 0.5, timeout: float = 1.0, max_history: int = 500):
        self.hosts = hosts
        self.interval = interval
        self.timeout = timeout
        self.max_history = max_history
        self.history = {host: [] for host in hosts}
        self.running = False
        self._task = None

    async def _ping_one(self, host: str) -> Optional[float]:
        try:
            result = await async_ping(host, count=1, timeout=self.timeout, privileged=False)
            if result.packets_received > 0:
                return result.rtt_avg * 1000
            else:
                return None
        except Exception:
            return None

    async def _ping_cycle(self):
        while self.running:
            tasks = [self._ping_one(host) for host in self.hosts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            now = time.time()
            for host, rtt in zip(self.hosts, results):
                if isinstance(rtt, Exception) or rtt is None:
                    self.history[host].append((now, None))
                else:
                    self.history[host].append((now, rtt))
                if len(self.history[host]) > self.max_history:
                    self.history[host].pop(0)
            await asyncio.sleep(self.interval)

    def start(self):
        if self.running:
            return
        self.running = True
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._ping_cycle())

    def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()

    def get_latest_rtts(self, host: str, count: int = None) -> List[Optional[float]]:
        hist = self.history.get(host, [])
        if not hist:
            return []
        rtts = [rtt for _, rtt in hist]
        if count is not None:
            return rtts[-count:]
        return rtts
