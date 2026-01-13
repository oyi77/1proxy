import re
from typing import List, Tuple


class ProxyPatterns:
    HTTP_IP_PORT = re.compile(
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
        r":([0-9]{1,5})\b"
    )

    VMESS_URL = re.compile(r"vmess://[A-Za-z0-9+/=]+")

    VLESS_URL = re.compile(r"vless://[a-zA-Z0-9-]+@[a-zA-Z0-9.-]+:[0-9]+[^\s]*")

    TROJAN_URL = re.compile(r"trojan://[^@\s]+@[a-zA-Z0-9.-]+:[0-9]+[^\s]*")

    SS_URL = re.compile(r"ss://[A-Za-z0-9+/=]+@[a-zA-Z0-9.-]+:[0-9]+")

    @classmethod
    def extract_http_proxies(cls, text: str) -> List[Tuple[str, str]]:
        result = []
        for match in cls.HTTP_IP_PORT.finditer(text):
            ip_port = match.group(0)
            ip, port = ip_port.rsplit(":", 1)
            result.append((ip, port))
        return result

    @classmethod
    def is_vmess(cls, url: str) -> bool:
        return bool(cls.VMESS_URL.match(url))

    @classmethod
    def extract_vmess_urls(cls, text: str) -> List[str]:
        return cls.VMESS_URL.findall(text)

    @classmethod
    def is_vless(cls, url: str) -> bool:
        return bool(cls.VLESS_URL.match(url))

    @classmethod
    def extract_vless_urls(cls, text: str) -> List[str]:
        return cls.VLESS_URL.findall(text)

    @classmethod
    def is_trojan(cls, url: str) -> bool:
        return bool(cls.TROJAN_URL.match(url))

    @classmethod
    def extract_trojan_urls(cls, text: str) -> List[str]:
        return cls.TROJAN_URL.findall(text)

    @classmethod
    def is_shadowsocks(cls, url: str) -> bool:
        return bool(cls.SS_URL.match(url))

    @classmethod
    def extract_ss_urls(cls, text: str) -> List[str]:
        return cls.SS_URL.findall(text)

    @classmethod
    def is_valid_ip(cls, ip: str) -> bool:
        try:
            octets = ip.split(".")
            return len(octets) == 4 and all(0 <= int(o) <= 255 for o in octets)
        except (ValueError, AttributeError):
            return False

    @classmethod
    def is_valid_port(cls, port: int) -> bool:
        return 1 <= port <= 65535
