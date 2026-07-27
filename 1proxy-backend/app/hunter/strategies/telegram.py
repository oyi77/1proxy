import logging
import aiohttp
from typing import List
from app.hunter.strategy import BaseStrategy

logger = logging.getLogger(__name__)


class TelegramStrategy(BaseStrategy):
    """
    Scrapes proxy URLs from popular Telegram proxy channels via their web preview.
    """

    CHANNELS = [
        "proxy_list",
        "proxyme",
        "sh_proxy",
        "V2rayNG_VPNN",
        "v2ray_configs",
        "FreeV2rayVPN",
        "v2rayngvpn",
        "VLESS_V2RAY_TROJAN",
        # Additional proxy channels
        "ProxyListBot",
        "socks5_list",
        "HTTP_proxy_list",
        "proxy_socks5",
        "daily_proxy_list",
        "live_proxy_list",
    ]

    @property
    def name(self) -> str:
        return "telegram"

    async def discover(self) -> List[str]:
        found_urls = []
        async with aiohttp.ClientSession() as session:
            for channel in self.CHANNELS:
                try:
                    url = f"https://t.me/s/{channel}"
                    async with session.get(url, timeout=10) as resp:
                        if resp.status == 200:
                            _ = await resp.text()
                            # Telegram web preview encodes special chars, but universal extractor handles it
                            # We just need to return the URL of the preview page or the text content
                            # However, HunterService fetches the URL. So we'll return the channel URL itself
                            # and let the UniversalExtractor handle the HTML content.
                            found_urls.append(url)
                except Exception as e:
                    logger.debug(f"Telegram strategy failed for {channel}: {e}")
        return found_urls
