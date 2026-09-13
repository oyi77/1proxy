"""Carved verbatim out of ``app/validator.py`` — statements moved, no logic changed."""

from .validator import (
    Any,
    BaseModel,
    Optional,
    ProxyValidationConfig,
)

from . import validator as _facade

class ValidationResult(BaseModel):
    success: bool
    latency_ms: _facade.Optional[int] = None
    anonymity: _facade.Optional[str] = None
    can_access_google: _facade.Optional[bool] = None
    can_access_openai: _facade.Optional[bool] = None
    country_code: _facade.Optional[str] = None
    country_name: _facade.Optional[str] = None
    proxy_type: _facade.Optional[str] = None
    isp: _facade.Optional[str] = None
    org: _facade.Optional[str] = None
    quality_score: _facade.Optional[int] = None
    error_message: _facade.Optional[str] = None
    ssl_valid: _facade.Optional[bool] = None
    is_blacklisted: _facade.Optional[bool] = None
    dns_leak: _facade.Optional[bool] = None
    response_time_p95: _facade.Optional[int] = None
def get_default_config() -> ProxyValidationConfig:
    return _facade.get_validator_config()
class LRUCache:
    """Thread-safe LRU cache with TTL"""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: _facade.OrderedDict[str, _facade.Tuple[_facade.Any, float]] = _facade.OrderedDict()
        self._lock = _facade.asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                return None
            value, expiry = self._cache[key]
            if _facade.time.time() > expiry:
                del self._cache[key]
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        async with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)  # Remove LRU
            
            expiry = _facade.time.time() + (ttl or self.default_ttl)
            self._cache[key] = (value, expiry)
    
    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()
