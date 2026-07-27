import json
from app.grabber.patterns import ProxyPatterns
from app.models.proxy import Proxy
from app.utils.base64_decoder import SubscriptionDecoder


class VMessParser:
    @staticmethod
    def parse(url: str) -> Proxy:
        if not url.startswith("vmess://"):
            raise ValueError("Invalid VMess URL")

        try:
            encoded = url.replace("vmess://", "")
            decoded = SubscriptionDecoder.decode(encoded)
            config = json.loads(decoded)

            return Proxy(
                ip=config.get("add", ""),
                port=int(config.get("port", 0)),
                protocol="vmess",
                source="subscription",
            )
        except Exception as e:
            raise ValueError(f"Failed to parse VMess URL: {e}")


class VLESSParser:
    @staticmethod
    def parse(url: str) -> Proxy:
        if not url.startswith("vless://"):
            raise ValueError("Invalid VLESS URL")

        try:
            url_parts = url.replace("vless://", "")
            uuid_part, server_part = url_parts.split("@", 1)
            server_port = server_part.split("?")[0]
            server, port = server_port.rsplit(":", 1)

            return Proxy(
                ip=server, port=int(port), protocol="vless", source="subscription"
            )
        except Exception as e:
            raise ValueError(f"Failed to parse VLESS URL: {e}")


class TrojanParser:
    @staticmethod
    def parse(url: str) -> Proxy:
        if not url.startswith("trojan://"):
            raise ValueError("Invalid Trojan URL")

        try:
            url_parts = url.replace("trojan://", "")
            password_part, server_part = url_parts.split("@", 1)
            server_port = server_part.split("?")[0]
            server, port = server_port.rsplit(":", 1)

            return Proxy(
                ip=server, port=int(port), protocol="trojan", source="subscription"
            )
        except Exception as e:
            raise ValueError(f"Failed to parse Trojan URL: {e}")


class SSParser:
    @staticmethod
    def parse(url: str) -> Proxy:
        if not url.startswith("ss://"):
            raise ValueError("Invalid Shadowsocks URL")

        try:
            url_parts = url.replace("ss://", "")
            config_part, server_part = url_parts.split("@", 1)
            server, port = server_part.split(":", 1)

            return Proxy(
                ip=server, port=int(port), protocol="shadowsocks", source="subscription"
            )
        except Exception as e:
            raise ValueError(f"Failed to parse Shadowsocks URL: {e}")


class TorExitParser:
    """Parse Tor exit node JSON from Onionoo API -> SOCKS5 proxies."""

    @staticmethod
    def parse(content: str) -> list[Proxy]:
        proxies: list[Proxy] = []
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return proxies

        for relay in data.get("relays", []):
            for addr in relay.get("or_addresses", []):
                # or_addresses format: "1.2.3.4:443" or "[::1]:443"
                addr = addr.strip()
                if addr.startswith("["):
                    # IPv6 — skip for now, only grab IPv4
                    continue
                if ":" not in addr:
                    continue
                ip, port_str = addr.rsplit(":", 1)
                try:
                    port = int(port_str)
                except ValueError:
                    continue
                if not ProxyPatterns.is_valid_ip(ip):
                    continue
                if not ProxyPatterns.is_valid_port(port):
                    continue
                proxies.append(
                    Proxy(
                        ip=ip,
                        port=port,
                        protocol="socks5",
                        source="tor_exit",
                    )
                )
        return proxies
