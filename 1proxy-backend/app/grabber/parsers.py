import base64
import json
from typing import Optional
from app.models.proxy import Proxy


class VMessParser:
    @staticmethod
    def parse(url: str) -> Proxy:
        if not url.startswith("vmess://"):
            raise ValueError("Invalid VMess URL")

        try:
            encoded = url.replace("vmess://", "")
            missing_padding = len(encoded) % 4
            if missing_padding:
                encoded += "=" * (4 - missing_padding)

            decoded = base64.b64decode(encoded).decode("utf-8")
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
