from typing import List
from app.models import SourceConfig, SourceType


class SourceRegistry:
    """
    Registry of auto-updated GitHub proxy list sources.
    These repositories auto-update daily/hourly with fresh proxies.
    """

    SOURCES: List[SourceConfig] = [
        SourceConfig(
            url="https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            type=SourceType.GITHUB_RAW,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
            type=SourceType.GITHUB_RAW,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
            type=SourceType.GITHUB_RAW,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
            type=SourceType.GITHUB_RAW,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/mmpx12/proxy-list/master/https.txt",
            type=SourceType.GITHUB_RAW,
            enabled=True,
        ),
        # V2Ray / VMess / VLESS / Trojan / Shadowsocks Sources
        SourceConfig(
            url="https://raw.githubusercontent.com/vorz1k/v2box/main/supreme_vpns_1.txt",
            type=SourceType.SUBSCRIPTION_BASE64,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/Sage-77/V2ray-configs/main/vmess.txt",
            type=SourceType.SUBSCRIPTION_BASE64,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/Sage-77/V2ray-configs/main/vless.txt",
            type=SourceType.SUBSCRIPTION_BASE64,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/Sage-77/V2ray-configs/main/trojan.txt",
            type=SourceType.SUBSCRIPTION_BASE64,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/Sage-77/V2ray-configs/main/ss.txt",
            type=SourceType.SUBSCRIPTION_BASE64,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/Sage-77/V2ray-configs/main/config.txt",
            type=SourceType.SUBSCRIPTION_BASE64,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/http.txt",
            type=SourceType.GITHUB_RAW,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/TopChina/proxy-list/main/http.txt",
            type=SourceType.GITHUB_RAW,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/officialputuid/KangProxy/KangProxy/http/http.txt",
            type=SourceType.GITHUB_RAW,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/gfpcom/free-proxy-list/main/http.txt",
            type=SourceType.GITHUB_RAW,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
            type=SourceType.GITHUB_RAW,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/http.txt",
            type=SourceType.GITHUB_RAW,
            enabled=True,
        ),
        SourceConfig(
            url="https://raw.githubusercontent.com/zloi-user/hideip.me/main/http.txt",
            type=SourceType.GITHUB_RAW,
            enabled=True,
        ),
    ]

    @classmethod
    def get_enabled_sources(cls) -> List[SourceConfig]:
        return [source for source in cls.SOURCES if source.enabled]

    @classmethod
    def get_all_sources(cls) -> List[SourceConfig]:
        return cls.SOURCES
