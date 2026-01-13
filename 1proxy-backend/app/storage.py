from typing import List, Dict, Optional
from app.models import Proxy
from datetime import datetime
import asyncio


class InMemoryStorage:
    def __init__(self):
        self._proxies: Dict[str, Proxy] = {}
        self._lock = asyncio.Lock()

    async def add_proxies(self, proxies: List[Proxy]) -> int:
        async with self._lock:
            added = 0
            for proxy in proxies:
                key = f"{proxy.ip}:{proxy.port}:{proxy.protocol}"
                if key not in self._proxies:
                    self._proxies[key] = proxy
                    added += 1
            return added

    async def get_all_proxies(
        self, protocol: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Proxy]:
        async with self._lock:
            proxies = list(self._proxies.values())

            if protocol:
                proxies = [p for p in proxies if p.protocol == protocol]

            return proxies[offset : offset + limit]

    async def get_count(self, protocol: Optional[str] = None) -> int:
        async with self._lock:
            if protocol:
                return len(
                    [p for p in self._proxies.values() if p.protocol == protocol]
                )
            return len(self._proxies)

    async def clear(self):
        async with self._lock:
            self._proxies.clear()


storage = InMemoryStorage()
