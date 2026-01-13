import pytest
from app.grabber.patterns import ProxyPatterns


class TestHTTPPatterns:
    def test_http_ip_port_pattern(self):
        text = "192.168.1.1:8080\n10.0.0.1:3128"
        matches = ProxyPatterns.extract_http_proxies(text)

        assert len(matches) == 2
        assert matches[0] == ("192.168.1.1", "8080")
        assert matches[1] == ("10.0.0.1", "3128")

    def test_http_url_pattern(self):
        text = "192.168.1.1:8080\n10.0.0.1:3128"
        matches = ProxyPatterns.extract_http_proxies(text)

        assert len(matches) >= 1


class TestVMessPatterns:
    def test_vmess_url_detection(self):
        url = "vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0Ijo0NDMsImlkIjoidXVpZCJ9"
        assert ProxyPatterns.is_vmess(url) is True

    def test_vmess_extraction(self):
        text = """
        Some text
        vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0Ijo0NDN9
        More text
        """
        matches = ProxyPatterns.extract_vmess_urls(text)

        assert len(matches) == 1
        assert matches[0].startswith("vmess://")


class TestVLESSPatterns:
    def test_vless_url_detection(self):
        url = "vless://uuid@server:443?type=tcp"
        assert ProxyPatterns.is_vless(url) is True

    def test_vless_extraction(self):
        text = "vless://some-uuid@192.168.1.1:443?encryption=none&type=tcp"
        matches = ProxyPatterns.extract_vless_urls(text)

        assert len(matches) == 1


class TestTrojanPatterns:
    def test_trojan_url_detection(self):
        url = "trojan://password@server:443"
        assert ProxyPatterns.is_trojan(url) is True

    def test_trojan_extraction(self):
        text = "trojan://pass123@example.com:443?sni=example.com"
        matches = ProxyPatterns.extract_trojan_urls(text)

        assert len(matches) == 1


class TestShadowsocksPatterns:
    def test_ss_url_detection(self):
        url = "ss://base64encoded@server:8388"
        assert ProxyPatterns.is_shadowsocks(url) is True

    def test_ss_extraction(self):
        text = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@192.168.1.1:8388"
        matches = ProxyPatterns.extract_ss_urls(text)

        assert len(matches) == 1
