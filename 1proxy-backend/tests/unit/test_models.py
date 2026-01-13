import pytest
from app.models.proxy import Proxy
from uuid import UUID


def test_proxy_model_creation():
    proxy_data = {
        "ip": "127.0.0.1",
        "port": 8080,
        "protocol": "http",
        "source": "manual",
    }
    proxy = Proxy(**proxy_data)
    assert proxy.ip == "127.0.0.1"
    assert proxy.port == 8080
    assert isinstance(proxy.id, UUID)
    assert proxy.anonymity == "transparent"
