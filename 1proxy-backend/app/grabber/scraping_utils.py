"""
Scraping Utilities

Helper functions untuk enhanced scraping dengan rate limiting,
error handling, dan performance optimization.
"""

import asyncio
import logging
import time
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ProxyAgent:
    """Proxy agent for rotation and management."""

    proxy_url: str
    success_rate: float = 1.0
    failure_count: int = 0
    last_used: Optional[datetime] = None


@dataclass
class ScrapingSession:
    """Session untuk track scraping statistics"""

    session_id: str
    start_time: float
    requests_made: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    proxies_used: List[str] = None
    avg_response_time: float = 0.0
    total_data_bytes: int = 0


@dataclass
class RequestQueue:
    """Queue untuk mengatur concurrent requests"""

    max_concurrent: int
    active_requests: Dict[str, datetime] = field(default_factory=dict)
    completed_requests: Dict[str, datetime] = field(default_factory=dict)


class RateLimiter:
    """Rate limiting per domain and IP"""

    def __init__(self):
        self.domain_requests: Dict[str, List[datetime]] = {}
        self.ip_requests: Dict[str, List[datetime]] = {}
        self.global_requests: List[datetime] = []

    def can_make_request(
        self, domain: Optional[str], ip: Optional[str]
    ) -> Tuple[bool, Optional[float]]:
        """Check if request can be made"""
        now = datetime.now()

        # Rate limiting per domain
        if domain and domain in self.domain_requests:
            recent_requests = [
                req
                for req in self.domain_requests[domain]
                if req > now - timedelta(minutes=1)
            ]
            if len(recent_requests) >= 10:  # 10 requests per minute
                return False, 60.0  # Retry after 60 seconds

        # Rate limiting per IP
        if ip and ip in self.ip_requests:
            recent_requests = [
                req for req in self.ip_requests[ip] if req > now - timedelta(minutes=5)
            ]
            if len(recent_requests) >= 50:  # 50 requests per 5 minutes
                return False, 300.0  # Retry after 5 minutes

        # Global rate limiting
        total_recent = len(
            [req for req in self.global_requests if req > now - timedelta(minutes=1)]
        )
        if total_recent >= 100:  # 100 requests per minute globally
            return False, 60.0

        return True, 0.0

    def record_request(self, domain: Optional[str], ip: Optional[str]):
        """Record successful request"""
        now = datetime.now()

        if domain:
            if domain not in self.domain_requests:
                self.domain_requests[domain] = []
            self.domain_requests[domain].append(now)

        if ip:
            if ip not in self.ip_requests:
                self.ip_requests[ip] = []
            self.ip_requests[ip].append(now)

        self.global_requests.append(now)

    def record_success(
        self,
        domain: Optional[str],
        ip: Optional[str],
        response_time: float,
        data_size: int,
    ):
        """Record successful request"""
        now = datetime.now()

        # Update session stats
        self.active_requests[str(uuid.uuid4())] = {
            "timestamp": now,
            "domain": domain,
            "ip": ip,
            "response_time": response_time,
            "data_size": data_size,
            "success": True,
        }


class ExponentialBackoff:
    """Exponential backoff dengan jitter untuk optimal retry"""

    @staticmethod
    def get_delay(
        attempt: int,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ) -> float:
        """Calculate delay dengan exponential backoff"""
        delay = base_delay * (2**attempt)

        if jitter:
            # Add random jitter (±25%) to avoid thundering herd
            jitter_factor = random.uniform(0.75, 1.25)
            delay *= jitter_factor

        return min(delay, max_delay)


class ProxyRotator:
    """Smart proxy rotation untuk load balancing"""

    def __init__(self, proxies: List[str] = None):
        self.proxies = proxies or []
        self.index = 0
        self.failure_count: Dict[str, int] = {}
        self.last_rotated = time.time()

    async def get_next_proxy(
        self, exclude: Optional[List[str]] = None
    ) -> Optional[ProxyAgent]:
        """Get next proxy dengan round-robin"""
        available_proxies = [p for p in self.proxies if not exclude or p not in exclude]

        if not available_proxies:
            return None

        proxy = available_proxies[self.index % len(available_proxies)]

        self.index = (self.index + 1) % len(available_proxies)

        return ProxyAgent(proxy_url=proxy)

    def record_failure(self, proxy: str):
        """Record proxy failure"""
        if proxy not in self.failure_count:
            self.failure_count[proxy] = 0
        self.failure_count[proxy] += 1

        # Rotate proxy setelah 5 failures
        if self.failure_count[proxy] >= 5:
            logger.warning(
                f"Proxy {proxy} memiliki {self.failure_count[proxy]} kegagalan, dirotasi"
            )
            # Move proxy ke akhir daftar
            self.proxies = [p for p in self.proxies if p != proxy]
            self.failure_count[proxy] = 0

        self.last_rotated = time.time()

    def get_stats(self) -> Dict[str, Any]:
        """Get rotation statistics"""
        return {
            "total_proxies": len(self.proxies),
            "failure_counts": dict(self.failure_count),
            "last_rotated": datetime.fromtimestamp(self.last_rotated).isoformat(),
            "rotation_count": sum(
                1 for count in self.failure_count.values() if count > 5
            ),
        }


class PerformanceMonitor:
    """Monitor scraping performance"""

    def __init__(self):
        self.session_stats: List[ScrapingSession] = []
        self.start_time = time.time()

    def start_session(self) -> ScrapingSession:
        """Start new scraping session"""
        session = ScrapingSession(
            session_id=f"session_{int(time.time())}", start_time=time.time()
        )
        self.session_stats.append(session)
        return session

    def end_session(self, session: ScrapingSession):
        """End scraping session"""
        session.end_time = time.time()
        session.duration = session.end_time - session.start_time
        session.success_rate = (
            (session.successful_requests / max(session.requests_made, 1)) * 100
            if session.requests_made > 0
            else 0
        )
        session.avg_response_time = (
            session.avg_response_time / max(session.requests_made, 1)
            if session.requests_made > 0
            else 0
        )

        # Calculate performance metrics
        self.session_stats.remove(session)
        return session

    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall performance statistics"""
        if not self.session_stats:
            return {}

        total_sessions = len(self.session_stats)
        total_requests = sum(s.requests_made for s in self.session_stats)
        total_successful = sum(s.successful_requests for s in self.session_stats)
        total_data_bytes = sum(s.total_data_bytes for s in self.session_stats)
        avg_duration = (
            sum(s.duration for s in self.session_stats) / max(total_sessions, 1)
            if total_sessions > 0
            else 0
        )

        return {
            "total_sessions": total_sessions,
            "total_requests": total_requests,
            "total_successful": total_successful,
            "success_rate": (total_successful / max(total_requests, 1)) * 100
            if total_requests > 0
            else 0,
            "total_data_bytes": total_data_bytes,
            "avg_session_duration": avg_duration,
            "requests_per_second": total_requests / max(avg_duration, 1)
            if avg_duration > 0
            else 0,
            "bytes_per_second": total_data_bytes / max(avg_duration, 1)
            if avg_duration > 0
            else 0,
        }


# Helper functions
def calculate_proxy_score(
    latency: int, can_access_google: bool, proxy_type: str, country_code: str
) -> int:
    """Calculate proxy quality score (0-100)"""
    score = 0

    # Latency scoring (40 points max)
    if latency <= 200:
        score += 40  # Perfect
    elif latency <= 500:
        score += 30
    elif latency <= 1000:
        score += 20
    elif latency <= 2000:
        score += 10

    # Anonymity scoring (30 points max)
    if proxy_type == "elite":
        score += 30
    elif proxy_type == "anonymous":
        score += 20
    elif proxy_type == "transparent":
        score += 0  # No points for transparent

    # Google access scoring (15 points)
    if can_access_google:
        score += 15

    # Residential bonus (15 points)
    if country_code and country_code != "US":
        score += 15  # Assume non-US is residential

    return min(score, 100)


def extract_domain(url: str) -> str:
    """Extract domain dari URL"""
    try:
        return urlparse(url).netloc
    except:
        return "unknown"


def validate_url(url: str) -> bool:
    """Validate URL format"""
    try:
        result = urlparse(url)
        return bool(result.scheme and result.netloc)
    except:
        return False


def clean_text(text: str) -> str:
    """Clean text dari HTML tags dan noise"""
    import re

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Remove multiple whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove URLs yang tidak relevan
    text = re.sub(r"https?://[^\s]+", "", text)

    return text.strip()


def format_bytes(bytes_size: int) -> str:
    """Format bytes size untuk human readable"""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024:
            return f"{bytes_size} {unit}"
        bytes_size /= 1024
        if bytes_size < 1024:
            return f"{bytes_size} {unit}"
        bytes_size /= 1024
        if bytes_size < 1024:
            return f"{bytes_size} {unit}"
        else:
            return f"{bytes_size:.1f} {unit}"


def generate_session_id() -> str:
    """Generate unique session ID"""
    import uuid

    return str(uuid.uuid4())


# Constants
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_BATCH_SIZE = 100

# Rate limiting constants
DOMAIN_RATE_LIMIT = 10  # requests per minute per domain
IP_RATE_LIMIT = 50  # requests per 5 minutes per IP
GLOBAL_RATE_LIMIT = 100  # requests per minute globally

# Quality thresholds
MIN_QUALITY_SCORE = 30
SUCCESS_RATE_THRESHOLD = 0.3  # 30% success rate untuk proxy rotation
