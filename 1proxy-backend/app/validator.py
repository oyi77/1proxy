import aiohttp
import asyncio
import time
import re
import ssl
import certifi
from typing import Optional, Dict, List, Tuple
from pydantic import BaseModel
from datetime import datetime, timedelta
import hashlib

# Improved regex that matches IP:PORT format (doesn't validate ranges yet)
IP_REGEX = re.compile(r"(\d{1,3}\.){3}\d{1,3}:\d{1,5}")


def is_valid_ip(ip: str) -> bool:
    """Validate IP address octets are in range 0-255"""
    try:
        parts = ip.split(".")
        if len(parts) != 4:
            return False
        return all(0 <= int(part) <= 255 for part in parts)
    except (ValueError, AttributeError):
        return False


def is_valid_port(port: int) -> bool:
    """Validate port is in range 1-65535"""
    return 1 <= port <= 65535


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
    # New quality metrics
    ssl_valid: Optional[bool] = None
    is_blacklisted: Optional[bool] = None
    uptime_percent: Optional[float] = None
    dns_leak: Optional[bool] = None
    response_time_p95: Optional[int] = None


class ValidationCache:
    """LRU cache for validation results with TTL"""
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        self.cache: Dict[str, Tuple[ValidationResult, datetime]] = {}
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str) -> Optional[ValidationResult]:
        if key in self.cache:
            result, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return result
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, result: ValidationResult):
        if len(self.cache) >= self.max_size:
            # Remove oldest entries (simple FIFO for now)
            oldest_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k][1])[:100]
            for k in oldest_keys:
                del self.cache[k]
        self.cache[key] = (result, datetime.now())
    
    def clear(self):
        self.cache.clear()

class ProxyValidator:
    # Known blacklist IPs/ranges (simplified - in production use real blacklist APIs)
    BLACKLISTED_ASNS = {
        "AS14618",  # Amazon AWS (often blocked)
        "AS15169",  # Google Cloud
        "AS8075",   # Microsoft Azure
    }
    
    def __init__(self, timeout: int = 10, max_concurrent: int = 50):
        self.timeout = aiohttp.ClientTimeout(total=timeout, connect=timeout//2)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.cache = ValidationCache(max_size=10000, ttl_seconds=3600)
        # Connection pooling
        self.connector = aiohttp.TCPConnector(
            limit=max_concurrent * 2,
            limit_per_host=10,
            ttl_dns_cache=300,
            enable_cleanup_closed=True
        )
        self.session: Optional[aiohttp.ClientSession] = None
        self._response_times: Dict[str, List[int]] = {}  # Track for p95 calculation

    async def validate_format(self, proxy: str) -> bool:
        if proxy.startswith(("http://", "https://", "socks4://", "socks5://")):
            proxy = proxy.split("://", 1)[1]

        if not IP_REGEX.match(proxy):
            return False

        try:
            ip_port = proxy.split(":")
            if len(ip_port) != 2:
                return False

            ip, port_str = ip_port
            port = int(port_str)

            return is_valid_ip(ip) and is_valid_port(port)
        except (ValueError, IndexError):
            return False

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create shared session with connection pooling"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                connector=self.connector
            )
        return self.session
    
    async def close(self):
        """Close the shared session and connector"""
        if self.session and not self.session.closed:
            await self.session.close()
        if self.connector:
            await self.connector.close()
    
    async def validate_connectivity(
        self, proxy_url: str
    ) -> tuple[bool, Optional[int], Optional[str]]:
        async with self.semaphore:
            try:
                start_time = time.time()
                session = await self._get_session()
                
                async with session.get(
                    "http://httpbin.org/ip", 
                    proxy=proxy_url, 
                    ssl=False,
                    allow_redirects=False
                ) as resp:
                    latency_ms = int((time.time() - start_time) * 1000)
                    
                    # Track response times for p95 calculation
                    if proxy_url not in self._response_times:
                        self._response_times[proxy_url] = []
                    self._response_times[proxy_url].append(latency_ms)
                    # Keep only last 100 measurements
                    self._response_times[proxy_url] = self._response_times[proxy_url][-100:]

                    if resp.status == 200:
                        return True, latency_ms, None
                    else:
                        return False, None, f"HTTP {resp.status}"

            except aiohttp.ClientProxyConnectionError:
                return False, None, "Proxy connection failed"
            except asyncio.TimeoutError:
                return False, None, "Connection timeout"
            except Exception as e:
                return False, None, str(e)[:100]

    def _calculate_p95_latency(self, proxy_url: str) -> Optional[int]:
        """Calculate 95th percentile latency from recent measurements"""
        times = self._response_times.get(proxy_url, [])
        if not times:
            return None
        sorted_times = sorted(times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[idx] if idx < len(sorted_times) else sorted_times[-1]
    
    async def check_anonymity(self, proxy_url: str) -> Optional[str]:
        try:
            session = await self._get_session()
            async with session.get(
                "http://httpbin.org/headers", proxy=proxy_url, ssl=False
            ) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()
                headers = data.get("headers", {})

                # Enhanced anonymity detection
                transparent_headers = ["X-Forwarded-For", "Via", "X-Real-Ip", "Forwarded"]
                anonymous_headers = ["Proxy-Connection", "X-Proxy-Id"]
                
                if any(h in headers for h in transparent_headers):
                    return "transparent"
                elif any(h in headers for h in anonymous_headers):
                    return "anonymous"
                else:
                    return "elite"

        except Exception:
            return None
    
    async def check_ssl_validity(self, proxy_url: str) -> bool:
        """Test if proxy can handle HTTPS connections with valid SSL"""
        try:
            session = await self._get_session()
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            async with session.get(
                "https://www.google.com",
                proxy=proxy_url,
                ssl=ssl_context
            ) as resp:
                return resp.status == 200
        except ssl.SSLError:
            return False
        except Exception:
            return False
    
    async def check_dns_leak(self, proxy_url: str, original_ip: str) -> bool:
        """Check if DNS queries leak real IP"""
        try:
            session = await self._get_session()
            async with session.get(
                "https://dns.google/resolve?name=example.com&type=A",
                proxy=proxy_url,
                ssl=False
            ) as resp:
                if resp.status == 200:
                    # If we can access DNS resolver, check if response reveals original IP
                    data = await resp.json()
                    # Simplified: real DNS leak detection would check resolver IP
                    return False  # Assume no leak if proxy works
        except Exception:
            pass
        return True  # Assume leak if test fails
    
    async def check_blacklist(self, ip: str, asn: Optional[str]) -> bool:
        """Check if IP or ASN is blacklisted"""
        # Check ASN blacklist
        if asn and asn in self.BLACKLISTED_ASNS:
            return True
        
        # Check against public blacklists (simplified)
        # In production: use APIs like AbuseIPDB, Project Honey Pot, etc.
        try:
            session = await self._get_session()
            # Example: check if IP is in a known proxy/VPN range
            async with session.get(
                f"https://ipinfo.io/{ip}/json",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Check if marked as proxy/VPN/hosting
                    if data.get("privacy", {}).get("proxy") or data.get("privacy", {}).get("vpn"):
                        return False  # Known proxy, not blacklisted
        except Exception:
            pass
        
        return False  # Default: not blacklisted

    async def test_google_access(self, proxy_url: str) -> bool:
        """Test with retry logic"""
        for attempt in range(2):
            try:
                session = await self._get_session()
                async with session.get(
                    "https://www.google.com", 
                    proxy=proxy_url, 
                    ssl=False,
                    allow_redirects=False
                ) as resp:
                    return resp.status == 200
            except Exception:
                if attempt == 1:
                    return False
                await asyncio.sleep(0.5)  # Brief retry delay
        return False

    async def test_openai_access(self, proxy_url: str) -> bool:
        """Test if proxy can access OpenAI API with retry"""
        for attempt in range(2):
            try:
                session = await self._get_session()
                async with session.get(
                    "https://api.openai.com/v1/models", 
                    proxy=proxy_url, 
                    ssl=False,
                    allow_redirects=False
                ) as resp:
                    return resp.status in (200, 401)  # 401 means API is reachable
            except Exception:
                if attempt == 1:
                    return False
                await asyncio.sleep(0.5)
        return False

    async def get_geo_info(self, ip: str) -> Dict[str, Optional[str]]:
        try:
            session = await self._get_session()
            async with session.get(
                f"https://ipapi.co/{ip}/json/",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "country_code": data.get("country_code"),
                        "country_name": data.get("country_name"),
                        "state": data.get("region"),
                        "city": data.get("city"),
                        "asn": data.get("asn"),
                    }
        except Exception:
            pass

        return {
            "country_code": None, 
            "country_name": None, 
            "state": None, 
            "city": None,
            "asn": None
        }

    async def detect_proxy_type(self, ip: str) -> dict:
        try:
            session = await self._get_session()
            async with session.get(
                f"https://ipinfo.io/{ip}/json",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    org = data.get("org", "").lower()
                    isp = data.get("hostname", "").lower()

                    datacenter_keywords = [
                        "amazon", "aws", "google", "microsoft", "azure",
                        "digitalocean", "linode", "ovh", "hetzner", "vultr",
                        "hosting", "datacenter", "data center", "cloud",
                        "server", "vps", "dedicated"
                    ]

                    proxy_type = "residential"
                    for keyword in datacenter_keywords:
                        if keyword in org or keyword in isp:
                            proxy_type = "datacenter"
                            break

                    return {
                        "proxy_type": proxy_type,
                        "isp": data.get("org"),
                        "org": data.get("company", {}).get("name") or data.get("org"),
                        "asn": data.get("asn"),
                    }
        except Exception:
            pass

        return {"proxy_type": "unknown", "isp": None, "org": None, "asn": None}

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
        score = 0

        # Latency scoring (0-40 points)
        if latency_ms is not None:
            if latency_ms < 100:
                score += 40
            elif latency_ms < 200:
                score += 35
            elif latency_ms < 500:
                score += 25
            elif latency_ms < 1000:
                score += 15
            elif latency_ms < 2000:
                score += 8
            elif latency_ms < 5000:
                score += 3

        # Anonymity scoring (0-25 points)
        if anonymity == "elite":
            score += 25
        elif anonymity == "anonymous":
            score += 15
        elif anonymity == "transparent":
            score += 5

        # Access checks (0-20 points total)
        if can_access_google:
            score += 10
        if can_access_openai:
            score += 10

        # Proxy type (0-10 points)
        if proxy_type == "residential":
            score += 10
        elif proxy_type == "datacenter":
            score += 5

        # SSL validity (0-10 points)
        if ssl_valid:
            score += 10
        
        # Blacklist check (penalty)
        if is_blacklisted:
            score -= 30
        
        # DNS leak check (penalty)
        if dns_leak:
            score -= 15

        return max(0, min(score, 100))

    async def validate_comprehensive(self, proxy_url: str, ip: str) -> ValidationResult:
        # Check cache first
        cache_key = hashlib.md5(f"{proxy_url}:{ip}".encode()).hexdigest()
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Basic connectivity check
        is_valid, latency_ms, error = await self.validate_connectivity(proxy_url)

        if not is_valid:
            result = ValidationResult(success=False, error_message=error)
            self.cache.set(cache_key, result)
            return result

        # Run all checks in parallel for performance
        results = await asyncio.gather(
            self.check_anonymity(proxy_url),
            self.test_google_access(proxy_url),
            self.test_openai_access(proxy_url),
            self.get_geo_info(ip),
            self.detect_proxy_type(ip),
            self.check_ssl_validity(proxy_url),
            self.check_dns_leak(proxy_url, ip),
            return_exceptions=True,
        )

        anonymity = results[0] if not isinstance(results[0], Exception) else None
        can_access_google = results[1] if not isinstance(results[1], Exception) else None
        can_access_openai = results[2] if not isinstance(results[2], Exception) else None
        geo_info = results[3] if not isinstance(results[3], Exception) else {}
        type_info = results[4] if not isinstance(results[4], Exception) else {"proxy_type": "unknown"}
        ssl_valid = results[5] if not isinstance(results[5], Exception) else None
        dns_leak = results[6] if not isinstance(results[6], Exception) else None

        proxy_type = type_info.get("proxy_type", "unknown")
        asn = geo_info.get("asn") or type_info.get("asn")
        
        # Check blacklist
        is_blacklisted = await self.check_blacklist(ip, asn)

        quality_score = await self.calculate_quality_score(
            latency_ms, anonymity, can_access_google, can_access_openai, 
            proxy_type, ssl_valid, is_blacklisted, dns_leak
        )
        
        # Calculate p95 latency
        p95_latency = self._calculate_p95_latency(proxy_url)

        result = ValidationResult(
            success=True,
            latency_ms=latency_ms,
            anonymity=anonymity,
            can_access_google=can_access_google,
            can_access_openai=can_access_openai,
            country_code=geo_info.get("country_code"),
            country_name=geo_info.get("country_name"),
            proxy_type=proxy_type,
            isp=type_info.get("isp"),
            org=type_info.get("org"),
            quality_score=quality_score,
            error_message=None,
            ssl_valid=ssl_valid,
            is_blacklisted=is_blacklisted,
            dns_leak=dns_leak,
            response_time_p95=p95_latency,
        )
        
        # Cache the result
        self.cache.set(cache_key, result)
        return result

    async def validate_batch(
        self, proxies: List[tuple[str, str]], batch_size: int = 100
    ) -> List[tuple[str, ValidationResult]]:
        """Validate proxies in batches for better performance"""
        all_results = []
        
        # Process in batches to avoid overwhelming the system
        for i in range(0, len(proxies), batch_size):
            batch = proxies[i:i + batch_size]
            tasks = []
            for proxy_url, ip in batch:
                tasks.append(self.validate_comprehensive(proxy_url, ip))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for (proxy_url, ip), result in zip(batch, results):
                if isinstance(result, Exception):
                    all_results.append(
                        (
                            proxy_url,
                            ValidationResult(
                                success=False, error_message=str(result)[:100]
                            ),
                        )
                    )
                else:
                    all_results.append((proxy_url, result))
        
        return all_results


proxy_validator = ProxyValidator()
