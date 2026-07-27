"""
Optimized Proxy Validator - High-performance validation with two-phase approach.

Key optimizations:
1. Two-phase validation: Fast connectivity check first, comprehensive only for working proxies
2. Cached external API responses (geo, proxy type, ASN)
3. Configurable concurrency with semaphores
4. Fast timeouts and reduced retries
5. Priority-based validation (high-quality proxies first)
5. Batch processing with backpressure
"""

import aiohttp
import asyncio
import time
import re
import ssl
import certifi
import hashlib
from typing import Optional, Dict, List, Tuple, Any
from pydantic import BaseModel
from datetime import datetime
import logging
from collections import OrderedDict
from dataclasses import dataclass, field

from app.validation_config import get_validator_config

logger = logging.getLogger(__name__)

# Improved regex for IP:PORT
IP_REGEX = re.compile(r"(\d{1,3}\.){3}\d{1,3}:\d{1,5}")



class ValidationResult(BaseModel):
    success: bool
    latency_ms: Optional[int] = None
    anonymity: Optional[str] = None
    can_access_google: Optional[bool] = None
    can_access_openai: Optional[bool] = None
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    proxy_type: Optional[str] = None
    isp: Optional[str] = None
    org: Optional[str] = None
    quality_score: Optional[int] = None
    error_message: Optional[str] = None
    ssl_valid: Optional[bool] = None
    is_blacklisted: Optional[bool] = None
    dns_leak: Optional[bool] = None
    response_time_p95: Optional[int] = None


# Import config class from validation_config
from app.validation_config import ValidationConfig as ProxyValidationConfig

# Get default config
def get_default_config() -> ProxyValidationConfig:
    return get_validator_config()

class LRUCache:
    """Thread-safe LRU cache with TTL"""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                return None
            value, expiry = self._cache[key]
            if time.time() > expiry:
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
            
            expiry = time.time() + (ttl or self.default_ttl)
            self._cache[key] = (value, expiry)
    
    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()


class OptimizedProxyValidator:
    """
    High-performance proxy validator with two-phase validation:
    
    Phase 1 (Fast): Basic connectivity + latency (< 5s)
    Phase 2 (Comprehensive): Anonymity, geo, access checks - only for passing proxies
    """
    
    # Known blacklisted ASNs (simplified - use real API in production)
    BLACKLISTED_ASNS = {
        "AS12345", "AS666",  # Example malicious ASNs
    }
    
    DATACENTER_KEYWORDS = [
        "amazon", "aws", "google", "microsoft", "azure",
        "digitalocean", "linode", "ovh", "hetzner", "vultr",
        "hosting", "datacenter", "data center", "cloud",
        "server", "vps", "dedicated"
    ]
    
    def __init__(
        self,
        timeout: int = 10,
        max_concurrent: int = 50,
        config: Optional[ProxyValidationConfig] = None,
    ):
        # Handle backward compatibility - if config not provided but old params given
        if config is None:
            config = get_default_config()
            config.max_concurrent_validations = max_concurrent
            config.connectivity_timeout = timeout
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.connector: Optional[aiohttp.TCPConnector] = None
        self.semaphore: Optional[asyncio.Semaphore] = None
        
        # Caches for external API responses
        self._geo_cache = LRUCache(max_size=5000, default_ttl=self.config.geo_cache_ttl)
        self._proxy_type_cache = LRUCache(max_size=5000, default_ttl=self.config.proxy_type_cache_ttl)
        self._validation_cache = LRUCache(max_size=10000, default_ttl=300)  # 5 min for validation results
        
        # Response time tracking for p95
        self._response_times: Dict[str, List[int]] = {}
        self._response_times_lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            "validations_total": 0,
            "validations_fast_pass": 0,
            "validations_comprehensive": 0,
            "validations_failed": 0,
            "cache_hits": 0,
            "external_api_calls": 0,
        }
    
    async def _ensure_session(self) -> None:
        """Lazily create session and connector when event loop is available"""
        if self.session is None:
            if self.connector is None:
                self.connector = aiohttp.TCPConnector(
                    limit=self.config.max_concurrent_validations * 2,
                    limit_per_host=self.config.max_concurrent_per_host,
                    ttl_dns_cache=300,
                    enable_cleanup_closed=True,
                    force_close=False,
                )
            if self.semaphore is None:
                self.semaphore = asyncio.Semaphore(self.config.max_concurrent_validations)
            
            # Default timeout for all requests
            timeout = aiohttp.ClientTimeout(
                total=self.config.connectivity_timeout,
                connect=2.0,
                sock_read=self.config.connectivity_timeout,
                sock_connect=2.0,
            )
            
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (compatible; 1proxy/1.0)"},
            )
    
    async def close(self) -> None:
        """Close session and connector"""
        if self.session and not self.session.closed:
            await self.session.close()
        if self.connector:
            await self.connector.close()
    
    # ===== PHASE 1: FAST CONNECTIVITY CHECK =====
    
    async def validate_connectivity_fast(self, proxy_url: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Ultra-fast connectivity check with minimal overhead.
        Returns (success, latency_ms, error_message)
        """
        await self._ensure_session()
        
        # Single attempt, no retry for fast check
        try:
            start = time.perf_counter()
            async with self.semaphore:
                async with self.session.get(
                    "http://httpbin.org/ip",
                    proxy=proxy_url,
                    ssl=False,
                    allow_redirects=False,
                    timeout=aiohttp.ClientTimeout(
                        total=self.config.connectivity_timeout,
                        connect=1.5,
                        sock_read=self.config.connectivity_timeout,
                    )
                ) as resp:
                    latency_ms = int((time.perf_counter() - start) * 1000)
                    
                    if resp.status == 200:
                        # Track latency
                        await self._record_latency(proxy_url, latency_ms)
                        return True, latency_ms, None
                    return False, None, f"HTTP {resp.status}"
                    
        except asyncio.TimeoutError:
            return False, None, "Timeout"
        except aiohttp.ClientProxyConnectionError:
            return False, None, "Proxy connection failed"
        except aiohttp.ClientConnectorError as e:
            return False, None, f"Connector error: {type(e).__name__}"
        except Exception as e:
            return False, None, f"{type(e).__name__}: {str(e)[:50]}"
    
    async def _record_latency(self, proxy_url: str, latency_ms: int) -> None:
        """Record latency for p95 calculation"""
        async with self._response_times_lock:
            if proxy_url not in self._response_times:
                self._response_times[proxy_url] = []
            times = self._response_times[proxy_url]
            times.append(latency_ms)
            # Keep only last 50 measurements (reduced from 100)
            if len(times) > 50:
                times[:] = times[-50:]
    
    def _calculate_p95_latency(self, proxy_url: str) -> Optional[int]:
        """Calculate 95th percentile latency"""
        times = self._response_times.get(proxy_url, [])
        if not times:
            return None
        sorted_times = sorted(times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]
    
    # ===== PHASE 2: COMPREHENSIVE CHECKS (with caching) =====
    
    async def check_anonymity_fast(self, proxy_url: str) -> Optional[str]:
        """Fast anonymity check - single request, no retries"""
        try:
            async with self.semaphore:
                async with self.session.get(
                    "http://httpbin.org/headers",
                    proxy=proxy_url,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=5.0)
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    headers = data.get("headers", {})
                    
                    # Check for transparency indicators
                    transparent_indicators = [
                        "X-Forwarded-For", "X-Real-Ip", "Forwarded",
                        "X-Proxy-Id", "Proxy-Connection"
                    ]
                    
                    for h in transparent_indicators:
                        if h in headers:
                            return "transparent"
                    
                    # Check for anonymity indicators
                    if "Via" not in headers and "X-Forwarded-For" not in headers:
                        return "elite"
                    return "anonymous"
        except Exception:
            return None
    
    async def test_google_access_fast(self, proxy_url: str) -> Optional[bool]:
        """Fast Google access check - single request, no redirects"""
        try:
            async with self.semaphore:
                async with self.session.get(
                    "https://www.google.com",
                    proxy=proxy_url,
                    ssl=False,
                    allow_redirects=False,
                    timeout=aiohttp.ClientTimeout(total=5.0)
                ) as resp:
                    self._stats["external_api_calls"] += 1
                    return resp.status == 200
        except Exception:
            return None
    
    async def test_openai_access_fast(self, proxy_url: str) -> Optional[bool]:
        """Fast OpenAI API access check"""
        try:
            async with self.semaphore:
                async with self.session.get(
                    "https://api.openai.com/v1/models",
                    proxy=proxy_url,
                    ssl=False,
                    allow_redirects=False,
                    timeout=aiohttp.ClientTimeout(total=5.0)
                ) as resp:
                    self._stats["external_api_calls"] += 1
                    return resp.status in (200, 401)  # 401 = reachable but needs auth
        except Exception:
            return None
    
    async def get_geo_info_cached(self, ip: str) -> Dict[str, Optional[str]]:
        """Get geo info with caching"""
        # Check cache first
        cached = await self._geo_cache.get(f"geo:{ip}")
        if cached is not None:
            self._stats["cache_hits"] += 1
            return cached
        
        self._stats["external_api_calls"] += 1
        
        try:
            async with self.semaphore:
                async with self.session.get(
                    f"https://ipapi.co/{ip}/json/",
                    timeout=aiohttp.ClientTimeout(total=self.config.external_api_timeout)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = {
                            "country_code": data.get("country_code"),
                            "country_name": data.get("country_name"),
                            "state": data.get("region"),
                            "city": data.get("city"),
                            "asn": data.get("asn"),
                        }
                        await self._geo_cache.set(f"geo:{ip}", result)
                        return result
        except Exception:
            pass
        
        return {"country_code": None, "country_name": None, "state": None, "city": None, "asn": None}
    
    async def detect_proxy_type_cached(self, ip: str) -> Dict[str, Optional[str]]:
        """Detect proxy type with caching"""
        cached = await self._proxy_type_cache.get(f"type:{ip}")
        if cached is not None:
            self._stats["cache_hits"] += 1
            return cached
        
        self._stats["external_api_calls"] += 1
        
        try:
            async with self.semaphore:
                async with self.session.get(
                    f"https://ipinfo.io/{ip}/json",
                    timeout=aiohttp.ClientTimeout(total=self.config.external_api_timeout)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        org = (data.get("org") or "").lower()
                        hostname = (data.get("hostname") or "").lower()
                        
                        proxy_type = "residential"
                        for keyword in self.DATACENTER_KEYWORDS:
                            if keyword in org or keyword in hostname:
                                proxy_type = "datacenter"
                                break
                        
                        result = {
                            "proxy_type": proxy_type,
                            "isp": data.get("org"),
                            "org": data.get("company", {}).get("name") or data.get("org"),
                            "asn": data.get("asn"),
                        }
                        await self._proxy_type_cache.set(f"type:{ip}", result)
                        return result
        except Exception:
            pass
        
        return {"proxy_type": "unknown", "isp": None, "org": None, "asn": None}

    async def get_ip_intel_cached(self, ip: str) -> Dict[str, Optional[object]]:
        """Get IP intelligence from ipquery.io — replaces geo + proxy-type lookups.
        Returns location, ISP, risk data in one call. Falls back to empty on failure.
        """
        cached = await self._geo_cache.get(f"ipq:{ip}")
        if cached is not None:
            self._stats["cache_hits"] += 1
            return cached

        self._stats["external_api_calls"] += 1

        try:
            url = self.config.ip_query_url.format(ip=ip)
            async with self.semaphore:
                async with self.session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.config.external_api_timeout)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        risk = data.get("risk", {})
                        isp = data.get("isp", {})
                        loc = data.get("location", {})

                        # Determine proxy type: ipquery returns is_datacenter bool
                        proxy_type = "residential"
                        if risk.get("is_datacenter"):
                            proxy_type = "datacenter"
                        if risk.get("is_proxy") or risk.get("is_vpn"):
                            proxy_type = "proxy"
                        if risk.get("is_tor"):
                            proxy_type = "tor"

                        result: Dict[str, Optional[object]] = {
                            "country_code": loc.get("country_code"),
                            "country_name": loc.get("country"),
                            "state": loc.get("state"),
                            "city": loc.get("city"),
                            "asn": isp.get("asn"),
                            "isp": isp.get("isp") or isp.get("org"),
                            "org": isp.get("org"),
                            "proxy_type": proxy_type,
                            "is_proxy": risk.get("is_proxy"),
                            "is_vpn": risk.get("is_vpn"),
                            "is_tor": risk.get("is_tor"),
                            "is_datacenter": risk.get("is_datacenter"),
                            "is_mobile": risk.get("is_mobile"),
                            "risk_score": risk.get("risk_score"),
                        }
                        await self._geo_cache.set(f"ipq:{ip}", result)
                        return result
        except Exception:
            pass

        return {"country_code": None, "country_name": None, "state": None,
                "city": None, "asn": None, "isp": None, "org": None,
                "proxy_type": "unknown", "is_proxy": None, "is_vpn": None,
                "is_tor": None, "is_datacenter": None, "is_mobile": None,
                "risk_score": None}
    
    async def check_ssl_validity_fast(self, proxy_url: str) -> Optional[bool]:
        """Fast SSL check"""
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            async with self.semaphore:
                async with self.session.get(
                    "https://www.google.com",
                    proxy=proxy_url,
                    ssl=ssl_context,
                    timeout=aiohttp.ClientTimeout(total=5.0)
                ) as resp:
                    return resp.status == 200
        except ssl.SSLError:
            return False
        except Exception:
            return None
    
    async def check_dns_leak_fast(self, proxy_url: str, original_ip: str) -> Optional[bool]:
        """Fast DNS leak check"""
        try:
            async with self.semaphore:
                async with self.session.get(
                    "https://dns.google/resolve?name=example.com&type=A",
                    proxy=proxy_url,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=3.0)
                ) as resp:
                    if resp.status == 200:
                        # Simplified: if proxy works, assume no leak
                        return False
        except Exception:
            pass
        return None
    
    async def check_blacklist_fast(self, ip: str, asn: Optional[str]) -> bool:
        """Fast blacklist check"""
        if asn and asn in self.BLACKLISTED_ASNS:
            return True
        # Could add IP range checks here
        return False
    
    async def calculate_quality_score(
        self,
        latency_ms: Optional[int],
        anonymity: Optional[str],
        can_access_google: Optional[bool],
        can_access_openai: Optional[bool],
        proxy_type: Optional[str],
        ssl_valid: Optional[bool] = None,
        is_blacklisted: Optional[bool] = None,
        dns_leak: Optional[bool] = None,
    ) -> int:
        """Calculate quality score (0-100)"""
        score = 0
        
        # Latency scoring (0-40 points) - optimized thresholds
        if latency_ms is not None:
            if latency_ms < 80:
                score += 40
            elif latency_ms < 150:
                score += 35
            elif latency_ms < 300:
                score += 25
            elif latency_ms < 600:
                score += 18
            elif latency_ms < 1200:
                score += 10
            elif latency_ms < 3000:
                score += 5
        
        # Anonymity (0-25)
        if anonymity == "elite":
            score += 25
        elif anonymity == "anonymous":
            score += 15
        elif anonymity == "transparent":
            score += 5
        
        # Access checks (0-20)
        if can_access_google:
            score += 10
        if can_access_openai:
            score += 10
        
        # Proxy type (0-10)
        if proxy_type == "residential":
            score += 10
        elif proxy_type == "datacenter":
            score += 5
        
        # SSL (0-10)
        if ssl_valid:
            score += 10
        
        # Penalties
        if is_blacklisted:
            score -= 30
        if dns_leak:
            score -= 15
        
        return max(0, min(score, 100))
    
    # ===== MAIN VALIDATION METHODS =====
    
    async def validate_phase1(self, proxy_url: str, ip: str) -> ValidationResult:
        """
        Phase 1: Fast connectivity + basic quality estimation.
        Takes ~1-5 seconds per proxy.
        """
        cache_key = hashlib.md5(f"{proxy_url}:{ip}:phase1".encode()).hexdigest()
        cached = await self._validation_cache.get(cache_key)
        if cached:
            self._stats["cache_hits"] += 1
            return cached
        
        self._stats["validations_total"] += 1
        
        # Fast connectivity check
        is_valid, latency_ms, error = await self.validate_connectivity_fast(proxy_url)
        
        if not is_valid:
            self._stats["validations_failed"] += 1
            result = ValidationResult(success=False, error_message=error)
            await self._validation_cache.set(cache_key, result, ttl=60)  # Cache failures for 1 min
            return result
        
        # Fast fail for very slow proxies
        if latency_ms and latency_ms > self.config.fast_fail_latency_ms:
            self._stats["validations_failed"] += 1
            result = ValidationResult(
                success=False, 
                error_message=f"Latency too high: {latency_ms}ms"
            )
            await self._validation_cache.set(cache_key, result, ttl=60)
            return result
        
        self._stats["validations_fast_pass"] += 1
        
        # Quick quality estimate without external calls
        # Score based only on latency (max 40 points)
        quick_score = 0
        if latency_ms < 80:
            quick_score = 40
        elif latency_ms < 150:
            quick_score = 35
        elif latency_ms < 300:
            quick_score = 25
        elif latency_ms < 600:
            quick_score = 18
        elif latency_ms < 1200:
            quick_score = 10
        elif latency_ms < 3000:
            quick_score = 5
        
        result = ValidationResult(
            success=True,
            latency_ms=latency_ms,
            quality_score=quick_score,
            error_message=None,
        )
        await self._validation_cache.set(cache_key, result, ttl=300)
        return result
    
    async def validate_phase2(
        self, 
        proxy_url: str, 
        ip: str, 
        phase1_result: ValidationResult
    ) -> ValidationResult:
        """
        Phase 2: Comprehensive validation for proxies that passed Phase 1.
        Only runs if Phase 1 quality score meets threshold.
        """
        cache_key = hashlib.md5(f"{proxy_url}:{ip}:phase2".encode()).hexdigest()
        cached = await self._validation_cache.get(cache_key)
        if cached:
            self._stats["cache_hits"] += 1
            return cached
        
        # Skip comprehensive if quality too low (unless forced)
        if (phase1_result.quality_score or 0) < self.config.min_quality_for_comprehensive:
            # Return phase1 result with slightly boosted score
            return phase1_result
        
        self._stats["validations_comprehensive"] += 1
        
        # Primary: single ipquery.io call for geo + proxy type + risk
        ipq = await self.get_ip_intel_cached(ip)
        geo_info = {
            "country_code": ipq.get("country_code"),
            "country_name": ipq.get("country_name"),
            "state": ipq.get("state"),
            "city": ipq.get("city"),
            "asn": ipq.get("asn"),
        }
        proxy_type = ipq.get("proxy_type", "unknown")
        risk_score = ipq.get("risk_score")
        is_proxy = ipq.get("is_proxy")
        is_vpn = ipq.get("is_vpn")
        is_tor = ipq.get("is_tor")
        isp = ipq.get("isp")
        org = ipq.get("org")

        # Fallback: if ipquery returned nothing useful, try old services
        if proxy_type == "unknown":
            old_geo, old_type = await asyncio.gather(
                self.get_geo_info_cached(ip),
                self.detect_proxy_type_cached(ip),
                return_exceptions=True,
            )
            if not isinstance(old_geo, Exception) and old_geo.get("country_code"):
                geo_info = old_geo
                if not isinstance(old_type, Exception):
                    proxy_type = old_type.get("proxy_type", "unknown")
                    isp = old_type.get("isp") or isp
                    org = old_type.get("org") or org

        # Run remaining checks in parallel
        results = await asyncio.gather(
            self.check_anonymity_fast(proxy_url),
            self.test_google_access_fast(proxy_url),
            self.test_openai_access_fast(proxy_url),
            self.check_ssl_validity_fast(proxy_url),
            self.check_dns_leak_fast(proxy_url, ip),
            return_exceptions=True,
        )
        
        anonymity = results[0] if not isinstance(results[0], Exception) else None
        can_access_google = results[1] if not isinstance(results[1], Exception) else None
        can_access_openai = results[2] if not isinstance(results[2], Exception) else None
        ssl_valid = results[3] if not isinstance(results[3], Exception) else None
        dns_leak = results[4] if not isinstance(results[4], Exception) else None

        asn = geo_info.get("asn")

        is_blacklisted = await self.check_blacklist_fast(ip, asn)

        quality_score = await self.calculate_quality_score(
            phase1_result.latency_ms, anonymity, can_access_google,
            can_access_openai, proxy_type, ssl_valid, is_blacklisted, dns_leak
        )

        # Risk penalty from ipquery.io (risk_score 0-100, higher = riskier)
        if risk_score is not None and risk_score > 50:
            quality_score = max(0, quality_score - max(0, (risk_score - 50) // 5))
        # Penalty for known proxy/VPN IPs (free proxies often recycled)
        if is_proxy or is_vpn:
            quality_score = max(0, quality_score - 5)
        
        p95_latency = self._calculate_p95_latency(proxy_url)
        
        result = ValidationResult(
            success=True,
            latency_ms=phase1_result.latency_ms,
            anonymity=anonymity,
            can_access_google=can_access_google,
            can_access_openai=can_access_openai,
            country_code=geo_info.get("country_code"),
            country_name=geo_info.get("country_name"),
            proxy_type=proxy_type,
            isp=isp,
            org=org,
            quality_score=quality_score,
            error_message=None,
            ssl_valid=ssl_valid,
            is_blacklisted=is_blacklisted,
            dns_leak=dns_leak,
            response_time_p95=p95_latency,
        )
        
        await self._validation_cache.set(cache_key, result, ttl=600)  # Cache for 10 min
        return result
    
    async def validate_comprehensive(self, proxy_url: str, ip: str) -> ValidationResult:
        """
        Full two-phase validation.
        Use this for on-demand validation.
        """
        # Phase 1
        phase1 = await self.validate_phase1(proxy_url, ip)
        
        if not phase1.success:
            return phase1
        
        # Phase 2
        return await self.validate_phase2(proxy_url, ip, phase1)
    
    async def validate_batch_optimized(
        self, 
        proxies: List[Tuple[str, str]], 
        batch_size: Optional[int] = None,
        run_phase2: bool = True,
    ) -> List[Tuple[str, ValidationResult]]:
        """
        Optimized batch validation with configurable phases.
        
        Args:
            proxies: List of (proxy_url, ip) tuples
            batch_size: Override default batch size
            run_phase2: Whether to run comprehensive phase 2 checks
            
        Returns:
            List of (proxy_url, ValidationResult) tuples
        """
        batch_size = batch_size or self.config.validation_batch_size
        all_results = []
        
        # Sort by priority if enabled (revalidate working proxies first)
        if self.config.prioritize_high_quality:
            # We can't easily sort without knowing quality first, 
            # but we could prioritize by IP reputation if available
            pass
        
        for i in range(0, len(proxies), batch_size):
            batch = proxies[i:i + batch_size]
            
            # Phase 1: Fast connectivity for all
            phase1_tasks = [
                self.validate_phase1(proxy_url, ip) 
                for proxy_url, ip in batch
            ]
            phase1_results = await asyncio.gather(*phase1_tasks, return_exceptions=True)
            
            # Collect phase 2 candidates
            phase2_tasks = []
            phase2_indices = []
            
            for idx, (phase1_result, (proxy_url, ip)) in enumerate(zip(phase1_results, batch)):
                if isinstance(phase1_result, Exception):
                    all_results.append((
                        proxy_url,
                        ValidationResult(success=False, error_message=str(phase1_result)[:100])
                    ))
                elif not phase1_result.success:
                    all_results.append((proxy_url, phase1_result))
                elif run_phase2:
                    phase2_tasks.append(self.validate_phase2(proxy_url, ip, phase1_result))
                    phase2_indices.append(idx)
                else:
                    all_results.append((proxy_url, phase1_result))
            
            # Run Phase 2 for qualified proxies
            if phase2_tasks:
                phase2_results = await asyncio.gather(*phase2_tasks, return_exceptions=True)
                
                # Merge results
                for idx, phase2_result in zip(phase2_indices, phase2_results):
                    proxy_url, _ = batch[idx]
                    if isinstance(phase2_result, Exception):
                        all_results.append((
                            proxy_url,
                            ValidationResult(success=False, error_message=str(phase2_result)[:100])
                        ))
                    else:
                        all_results.append((proxy_url, phase2_result))
            
            # Small delay between batches to prevent overwhelming
            if i + batch_size < len(proxies):
                await asyncio.sleep(0.1)
        
        return all_results
    
    # Backward compatibility alias
    async def validate_batch(
        self, 
        proxies: List[Tuple[str, str]], 
        batch_size: Optional[int] = None
    ) -> List[Tuple[str, ValidationResult]]:
        """Alias for validate_batch_optimized for backward compatibility"""
        return await self.validate_batch_optimized(proxies, batch_size, run_phase2=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            **self._stats,
            "cache_sizes": {
                "geo": len(self._geo_cache._cache),
                "proxy_type": len(self._proxy_type_cache._cache),
                "validation": len(self._validation_cache._cache),
            },
            "tracked_proxies": len(self._response_times),
        }
    
    async def clear_caches(self) -> None:
        """Clear all caches"""
        await self._geo_cache.clear()
        await self._proxy_type_cache.clear()
        await self._validation_cache.clear()
        self._response_times.clear()


# Global instance
optimized_validator = OptimizedProxyValidator()

# Backward compatibility
proxy_validator = optimized_validator

# Backward compatibility for tests
ProxyValidator = OptimizedProxyValidator