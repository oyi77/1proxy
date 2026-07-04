import aiohttp
import asyncio
import time
import re
from typing import Optional, Dict, List
from pydantic import BaseModel

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

class ProxyValidator:
    def __init__(self, timeout: int = 10, max_concurrent: int = 20):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.semaphore = asyncio.Semaphore(max_concurrent)

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

    async def validate_connectivity(
        self, proxy_url: str
    ) -> tuple[bool, Optional[int], Optional[str]]:
        async with self.semaphore:
            try:
                start_time = time.time()

                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(
                        "http://httpbin.org/ip", proxy=proxy_url, ssl=False
                    ) as resp:
                        latency_ms = int((time.time() - start_time) * 1000)

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

    async def check_anonymity(self, proxy_url: str) -> Optional[str]:
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    "http://httpbin.org/headers", proxy=proxy_url, ssl=False
                ) as resp:
                    if resp.status != 200:
                        return None

                    data = await resp.json()
                    headers = data.get("headers", {})

                    if "X-Forwarded-For" in headers or "Via" in headers:
                        return "transparent"
                    elif "Proxy-Connection" in headers or "X-Real-Ip" in headers:
                        return "anonymous"
                    else:
                        return "elite"

        except Exception:
            return None

    async def test_google_access(self, proxy_url: str) -> bool:
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    "https://www.google.com", proxy=proxy_url, ssl=False
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def test_openai_access(self, proxy_url: str) -> bool:
        """Test if proxy can access OpenAI API"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    "https://api.openai.com/v1/models", proxy=proxy_url, ssl=False
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def get_geo_info(self, ip: str) -> Dict[str, Optional[str]]:
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"https://ipapi.co/{ip}/json/") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "country_code": data.get("country_code"),
                            "country_name": data.get("country_name"),
                            "state": data.get("region"),
                            "city": data.get("city"),
                        }
        except Exception:
            pass

        return {"country_code": None, "country_name": None, "state": None, "city": None}

    async def detect_proxy_type(self, ip: str) -> dict:
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"https://ipinfo.io/{ip}/json") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        org = data.get("org", "").lower()
                        isp = data.get("hostname", "").lower()

                        datacenter_keywords = [
                            "amazon",
                            "aws",
                            "google",
                            "microsoft",
                            "azure",
                            "digitalocean",
                            "linode",
                            "ovh",
                            "hetzner",
                            "hosting",
                            "datacenter",
                            "data center",
                            "cloud",
                        ]

                        proxy_type = "residential"
                        for keyword in datacenter_keywords:
                            if keyword in org or keyword in isp:
                                proxy_type = "datacenter"
                                break

                        return {
                            "proxy_type": proxy_type,
                            "isp": data.get("org"),
                            "org": data.get("company", {}).get("name")
                            or data.get("org"),
                        }
        except Exception:
            pass

        return {"proxy_type": "unknown", "isp": None, "org": None}

    async def calculate_quality_score(
        self,
        latency_ms: Optional[int],
        anonymity: Optional[str],
        can_access_google: Optional[bool],
        can_access_openai: Optional[bool],
        proxy_type: Optional[str],
    ) -> int:
        score = 0

        if latency_ms is not None:
            if latency_ms < 200:
                score += 40
            elif latency_ms < 500:
                score += 30
            elif latency_ms < 1000:
                score += 20
            elif latency_ms < 2000:
                score += 10

        if anonymity == "elite":
            score += 30
        elif anonymity == "anonymous":
            score += 20
        elif anonymity == "transparent":
            score += 5

        if can_access_google:
            score += 10

        if can_access_openai:
            score += 10

        if proxy_type == "residential":
            score += 15
        elif proxy_type == "datacenter":
            score += 5

        return min(score, 100)

    async def validate_comprehensive(self, proxy_url: str, ip: str) -> ValidationResult:
        is_valid, latency_ms, error = await self.validate_connectivity(proxy_url)

        if not is_valid:
            return ValidationResult(success=False, error_message=error)

        results = await asyncio.gather(
            self.check_anonymity(proxy_url),
            self.test_google_access(proxy_url),
            self.test_openai_access(proxy_url),
            self.get_geo_info(ip),
            self.detect_proxy_type(ip),
            return_exceptions=True,
        )

        anonymity = results[0] if not isinstance(results[0], Exception) else None
        can_access_google = (
            results[1] if not isinstance(results[1], Exception) else None
        )
        can_access_openai = (
            results[2] if not isinstance(results[2], Exception) else None
        )
        geo_info = results[3] if not isinstance(results[3], Exception) else {}
        type_info = (
            results[4]
            if not isinstance(results[4], Exception)
            else {"proxy_type": "unknown"}
        )

        proxy_type = type_info.get("proxy_type", "unknown")

        quality_score = await self.calculate_quality_score(
            latency_ms, anonymity, can_access_google, can_access_openai, proxy_type
        )

        return ValidationResult(
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
        )

    async def validate_batch(
        self, proxies: List[tuple[str, str]]
    ) -> List[tuple[str, ValidationResult]]:
        tasks = []
        for proxy_url, ip in proxies:
            tasks.append(self.validate_comprehensive(proxy_url, ip))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = []
        for (proxy_url, ip), result in zip(proxies, results):
            if isinstance(result, Exception):
                output.append(
                    (
                        proxy_url,
                        ValidationResult(
                            success=False, error_message=str(result)[:100]
                        ),
                    )
                )
            else:
                output.append((proxy_url, result))

        return output


proxy_validator = ProxyValidator()
