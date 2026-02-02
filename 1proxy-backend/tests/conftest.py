import pytest
import asyncio
import base64
import os

# Ensure data directory exists for SQLite BEFORE any app imports
if not os.path.exists("./data"):
    os.makedirs("./data", exist_ok=True)

from typing import List
from app.models.proxy import Proxy, ValidationResult
from app.models.source import SourceConfig, SourceType
from app.database import engine, Base


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Double check test environment."""
    os.makedirs("./data", exist_ok=True)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def init_test_db():
    """Initialize the test database schema."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def sample_http_proxy() -> Proxy:
    return Proxy(
        ip="192.168.1.1", port=8080, protocol="http", source="test", anonymity="elite"
    )


@pytest.fixture
def sample_vmess_proxy() -> Proxy:
    return Proxy(ip="10.0.0.1", port=443, protocol="vmess", source="test")


@pytest.fixture
def sample_proxy_list() -> List[Proxy]:
    return [
        Proxy(ip="192.168.1.1", port=8080, protocol="http", source="test"),
        Proxy(ip="192.168.1.2", port=3128, protocol="http", source="test"),
        Proxy(ip="10.0.0.1", port=443, protocol="vmess", source="test"),
        Proxy(ip="10.0.0.2", port=443, protocol="vless", source="test"),
    ]


@pytest.fixture
def github_raw_source() -> SourceConfig:
    return SourceConfig(
        url="https://raw.githubusercontent.com/user/repo/main/list.txt",
        type=SourceType.GITHUB_RAW,
        enabled=True,
    )


@pytest.fixture
def subscription_source() -> SourceConfig:
    return SourceConfig(
        url="https://example.com/subscription",
        type=SourceType.SUBSCRIPTION_BASE64,
        enabled=True,
    )


@pytest.fixture
def sample_validation_result(sample_http_proxy) -> ValidationResult:
    return ValidationResult(
        proxy_id=sample_http_proxy.id,
        passed=True,
        latency_ms=123.45,
        is_elite=True,
        headers={"User-Agent": "test"},
    )


@pytest.fixture
def http_proxy_list_content() -> str:
    return """
192.168.1.1:8080
192.168.1.2:3128
10.0.0.1:8888
10.0.0.2:9999
"""


@pytest.fixture
def mixed_protocol_content() -> str:
    return """
192.168.1.1:8080
vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0Ijo0NDN9
vless://uuid-test@example.com:443?type=tcp
trojan://password@server.com:443
ss://YWVzLTI1Ni1nY206cGFzcw@10.0.0.1:8388
"""


@pytest.fixture
def base64_subscription_content() -> str:
    content = "vmess://test1\nvless://test2"
    return base64.b64encode(content.encode()).decode()
