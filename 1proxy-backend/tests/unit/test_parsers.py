import pytest
from app.grabber.parsers import VMessParser, VLESSParser, TrojanParser, SSParser
from app.models.proxy import Proxy


class TestVMessParser:
    def test_parse_valid_vmess(self):
        vmess_json = '{"add": "127.0.0.1", "port": 443, "id": "test-uuid", "aid": 0}'
        import base64

        encoded = base64.b64encode(vmess_json.encode()).decode()
        url = f"vmess://{encoded}"

        proxy = VMessParser.parse(url)

        assert proxy is not None
        assert proxy.ip == "127.0.0.1"
        assert proxy.port == 443
        assert proxy.protocol == "vmess"

    def test_parse_invalid_vmess(self):
        url = "vmess://invalid-base64!@#"

        with pytest.raises(ValueError):
            VMessParser.parse(url)


class TestVLESSParser:
    def test_parse_valid_vless(self):
        url = "vless://uuid-here@192.168.1.1:443?type=tcp&encryption=none"

        proxy = VLESSParser.parse(url)

        assert proxy is not None
        assert proxy.ip == "192.168.1.1"
        assert proxy.port == 443
        assert proxy.protocol == "vless"

    def test_parse_vless_with_domain(self):
        url = "vless://uuid@example.com:443?type=tcp"

        proxy = VLESSParser.parse(url)

        assert proxy is not None
        assert "example.com" in proxy.ip or proxy.ip != ""


class TestTrojanParser:
    def test_parse_valid_trojan(self):
        url = "trojan://password123@10.0.0.1:443?sni=example.com"

        proxy = TrojanParser.parse(url)

        assert proxy is not None
        assert proxy.ip == "10.0.0.1"
        assert proxy.port == 443
        assert proxy.protocol == "trojan"


class TestSSParser:
    def test_parse_valid_ss(self):
        method_pass = "aes-256-gcm:password123"
        import base64

        encoded = base64.b64encode(method_pass.encode()).decode()
        url = f"ss://{encoded}@192.168.1.1:8388"

        proxy = SSParser.parse(url)

        assert proxy is not None
        assert proxy.ip == "192.168.1.1"
        assert proxy.port == 8388
        assert proxy.protocol == "shadowsocks"
