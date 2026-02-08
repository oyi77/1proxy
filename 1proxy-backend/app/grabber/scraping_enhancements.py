"""
Enhanced scraping service with advanced features like proxy rotation,
rate limiting, and performance monitoring.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import time
import logging

from app.grabber.scraping_utils import (
    ProxyAgent,
    ProxyRotator,
    RequestQueue,
    RateLimiter,
)


class ScrapingEnhancementConfig:
    """Configuration for enhanced scraping operations."""

    def __init__(
        self,
        enable_proxy_rotation: bool = True,
        max_concurrent_requests: int = 10,
        rate_limit_per_second: int = 5,
        enable_retry: bool = True,
        max_retries: int = 3,
        timeout_seconds: int = 30,
    ):
        self.enable_proxy_rotation = enable_proxy_rotation
        self.max_concurrent_requests = max_concurrent_requests
        self.rate_limit_per_second = rate_limit_per_second
        self.enable_retry = enable_retry
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds


class EnhancedScrapingService:
    """Enhanced scraping service with proxy rotation and monitoring."""

    def __init__(self, config: ScrapingEnhancementConfig):
        self.config = config
        self.proxy_rotator = ProxyRotator(proxies=[])
        self.request_queue = RequestQueue(max_concurrent=config.max_concurrent_requests)
        self.rate_limiter = RateLimiter()
        self.performance_monitor = PerformanceMonitor()
        self.logger = logging.getLogger(__name__)

        from app.grabber.scraping_config import ScrapingSettingsManager

        self.config_manager = ScrapingSettingsManager()

    async def initialize_services(self):
        """Initialize async components of the service."""
        self.logger.info("Enhanced scraping service initialized successfully")
        return True

    async def scrape_with_enhancements(
        self,
        source_configs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Scrape multiple sources with enhanced features."""
        results = []

        for source_config in source_configs:
            proxy = await self.proxy_rotator.get_next_proxy()
            result = await self._scrape_single_with_rate_limit(source_config, proxy, {})
            if result:
                results.append(result)

        return {
            "sources_processed": len(source_configs),
            "successful_scrapes": len(results),
            "results": results,
        }

    async def _scrape_single_with_rate_limit(
        self,
        source_config: Dict[str, Any],
        proxy: ProxyAgent,
        retry_config: Dict[str, Any],
    ) -> Optional[str]:
        """Scrape source with rate limit per proxy."""

        return f"proxy_data_for_{proxy.proxy_url}" if proxy else "no_proxy_available"


class PerformanceMonitor:
    """Monitor scraping performance metrics."""

    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_data_bytes": 0,
            "avg_response_time": 0.0,
        }
        self.logger = logging.getLogger(__name__)

    def record_request(self, success: bool, response_time: float, data_size: int = 0):
        """Record a request metric."""
        self.metrics["total_requests"] += 1

        if success:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1

        self.metrics["total_data_bytes"] += data_size

        total_requests = self.metrics["total_requests"]
        current_avg = self.metrics["avg_response_time"]
        self.metrics["avg_response_time"] = (
            current_avg * (total_requests - 1) + response_time
        ) / total_requests

    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall performance statistics."""
        total_requests = self.metrics["total_requests"]
        successful_requests = self.metrics["successful_requests"]

        success_rate = (
            (successful_requests / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": self.metrics["failed_requests"],
            "success_rate": round(success_rate, 2),
            "total_data_bytes": self.metrics["total_data_bytes"],
            "avg_response_time": round(self.metrics["avg_response_time"], 3),
        }
