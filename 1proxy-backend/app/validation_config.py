"""
Validation Performance Configuration

Tune these settings based on your deployment environment:
- Local development: Lower concurrency, higher timeouts
- Production (Railway/Cloud): Higher concurrency, lower timeouts
- High-volume scraping: Aggressive settings
"""

from pydantic import BaseModel
from typing import Optional


class ValidationConfig(BaseModel):
    """Configuration for proxy validation performance"""
    
    # Concurrency settings
    max_concurrent_validations: int = 30
    max_concurrent_per_host: int = 5
    
    # Timeout settings (seconds)
    connectivity_timeout: float = 5.0
    comprehensive_timeout: float = 15.0
    external_api_timeout: float = 3.0
    
    # Retry settings
    connectivity_retries: int = 1
    comprehensive_retries: int = 0
    
    # Cache TTL (seconds)
    geo_cache_ttl: int = 3600      # 1 hour
    proxy_type_cache_ttl: int = 3600  # 1 hour
    validation_cache_ttl: int = 300   # 5 minutes
    
    # Batch processing
    validation_batch_size: int = 20
    validation_interval_seconds: int = 30
    
    # Quality thresholds
    min_quality_for_comprehensive: int = 30
    fast_fail_latency_ms: int = 3000
    
    # Prioritization
    prioritize_high_quality: bool = True
    revalidation_hours: int = 24
    
    # SQLite-specific
    db_semaphore_limit: int = 3  # Max concurrent DB operations
    
    # External API endpoints (can be overridden for testing)
    connectivity_test_url: str = "http://httpbin.org/ip"
    anonymity_test_url: str = "http://httpbin.org/headers"
    google_test_url: str = "https://www.google.com"
    openai_test_url: str = "https://api.openai.com/v1/models"
    ssl_test_url: str = "https://www.google.com"
    dns_leak_test_url: str = "https://dns.google/resolve?name=example.com&type=A"
    geo_api_url: str = "https://ipapi.co/{ip}/json/"
    proxy_type_api_url: str = "https://ipinfo.io/{ip}/json"


# Production-optimized configs
PRODUCTION_CONFIG = ValidationConfig(
    max_concurrent_validations=30,
    max_concurrent_per_host=5,
    connectivity_timeout=5.0,
    comprehensive_timeout=15.0,
    external_api_timeout=3.0,
    validation_batch_size=20,
    validation_interval_seconds=30,
    min_quality_for_comprehensive=30,
    fast_fail_latency_ms=3000,
)

# High-throughput config for dedicated validation servers
HIGH_THROUGHPUT_CONFIG = ValidationConfig(
    max_concurrent_validations=50,
    max_concurrent_per_host=10,
    connectivity_timeout=3.0,
    comprehensive_timeout=10.0,
    external_api_timeout=2.0,
    validation_batch_size=30,
    validation_interval_seconds=15,
    min_quality_for_comprehensive=25,
    fast_fail_latency_ms=2000,
)

# Conservative config for shared environments
CONSERVATIVE_CONFIG = ValidationConfig(
    max_concurrent_validations=15,
    max_concurrent_per_host=3,
    connectivity_timeout=8.0,
    comprehensive_timeout=20.0,
    external_api_timeout=5.0,
    validation_batch_size=10,
    validation_interval_seconds=60,
    min_quality_for_comprehensive=35,
    fast_fail_latency_ms=5000,
)

# Default config
DEFAULT_CONFIG = PRODUCTION_CONFIG


def get_validator_config() -> ValidationConfig:
    """Get validator config from environment or default to production"""
    import os
    
    env = os.getenv("VALIDATION_MODE", "production").lower()
    
    configs = {
        "production": PRODUCTION_CONFIG,
        "high_throughput": HIGH_THROUGHPUT_CONFIG,
        "conservative": CONSERVATIVE_CONFIG,
        "development": ValidationConfig(
            max_concurrent_validations=5,
            connectivity_timeout=10.0,
            validation_batch_size=5,
            validation_interval_seconds=120,
        ),
    }
    
    return configs.get(env, DEFAULT_CONFIG)