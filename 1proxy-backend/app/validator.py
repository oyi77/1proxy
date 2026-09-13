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
import logging
from collections import OrderedDict

from app.validation_config import get_validator_config

from app.validation_config import ValidationConfig as ProxyValidationConfig

logger = logging.getLogger(__name__)
IP_REGEX = re.compile(r"(\d{1,3}\.){3}\d{1,3}:\d{1,5}")

from ._validator_validationresult import (  # noqa: E402  (must follow the names it imports back)
    LRUCache,
    ValidationResult,
    get_default_config,
)

from ._validator_optimizedproxyvalidator import (  # noqa: E402  (must follow the names it imports back)
    OptimizedProxyValidator,
)

optimized_validator = OptimizedProxyValidator()
proxy_validator = optimized_validator
ProxyValidator = OptimizedProxyValidator


__all__ = [
    "Any",
    "BaseModel",
    "Dict",
    "IP_REGEX",
    "LRUCache",
    "List",
    "OptimizedProxyValidator",
    "Optional",
    "OrderedDict",
    "ProxyValidationConfig",
    "ProxyValidator",
    "Tuple",
    "ValidationResult",
    "aiohttp",
    "asyncio",
    "certifi",
    "get_default_config",
    "get_validator_config",
    "hashlib",
    "logger",
    "logging",
    "optimized_validator",
    "proxy_validator",
    "re",
    "ssl",
    "time",
]
