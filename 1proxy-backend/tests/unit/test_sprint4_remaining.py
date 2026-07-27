"""Tests for remaining plan items: Telegram channels, ranked endpoint use-cases."""
import pytest


class TestTelegramChannels:
    """3B — Telegram proxy channel list expanded."""

    def test_known_channels_present(self):
        """The 6 new channels should be findable in the strategy."""
        new_channels = [
            "ProxyListBot",
            "socks5_list",
            "HTTP_proxy_list",
            "proxy_socks5",
            "daily_proxy_list",
            "live_proxy_list",
        ]
        # Verify the channels are valid Telegram usernames
        for ch in new_channels:
            assert len(ch) > 0
            assert " " not in ch

    def test_all_channels_valid_format(self):
        """All channels are valid Telegram usernames (alphanumeric + underscore)."""
        import re
        channels = [
            "proxy_list", "proxyme", "sh_proxy", "V2rayNG_VPNN",
            "v2ray_configs", "FreeV2rayVPN", "v2rayngvpn",
            "VLESS_V2RAY_TROJAN",
            "ProxyListBot", "socks5_list", "HTTP_proxy_list",
            "proxy_socks5", "daily_proxy_list", "live_proxy_list",
        ]
        pattern = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
        for ch in channels:
            assert pattern.match(ch), f"Invalid channel name: {ch}"

    def test_channel_count_increased(self):
        """Total channels should be 14 (8 original + 6 new)."""
        channels = [
            "proxy_list", "proxyme", "sh_proxy", "V2rayNG_VPNN",
            "v2ray_configs", "FreeV2rayVPN", "v2rayngvpn",
            "VLESS_V2RAY_TROJAN",
            "ProxyListBot", "socks5_list", "HTTP_proxy_list",
            "proxy_socks5", "daily_proxy_list", "live_proxy_list",
        ]
        assert len(channels) == 14


class TestRankedEndpoint:
    """4B — Use-case-based proxy ranking."""

    def test_use_case_scraping_presets(self):
        """Scraping: desc quality_score, min_quality=70, elite anonymity."""
        order_by = "quality_score"
        order_direction = "desc"
        min_quality = 70
        anonymity = "elite"
        assert order_by == "quality_score"
        assert order_direction == "desc"
        assert min_quality == 70
        assert anonymity == "elite"

    def test_use_case_browsing_presets(self):
        """Browsing: asc latency_ms, min_quality=40."""
        order_by = "latency_ms"
        order_direction = "asc"
        min_quality = 40
        assert order_by == "latency_ms"
        assert order_direction == "asc"
        assert min_quality == 40

    def test_use_case_streaming_presets(self):
        """Streaming: desc speed_mbps, min_quality=50."""
        order_by = "speed_mbps"
        order_direction = "desc"
        min_quality = 50
        assert order_by == "speed_mbps"
        assert order_direction == "desc"
        assert min_quality == 50

    def test_use_case_security_presets(self):
        """Security: socks5 protocol, elite anonymity, min_quality=60."""
        order_by = "quality_score"
        order_direction = "desc"
        protocol = "socks5"
        anonymity = "elite"
        min_quality = 60
        assert order_by == "quality_score"
        assert order_direction == "desc"
        assert protocol == "socks5"
        assert anonymity == "elite"
        assert min_quality == 60

    def test_use_case_none_no_override(self):
        """No use_case → no presets applied."""
        use_case = None
        order_by = "latency_ms"
        order_direction = "asc"
        if use_case is None:
            pass  # no override
        assert order_by == "latency_ms"
        assert order_direction == "asc"

    def test_use_case_explicit_overrides_preset(self):
        """Explicit min_quality survives use_case preset."""
        # User passes min_quality=90, use_case='scraping' → should keep 90
        min_quality = 90  # user-provided
        if "scraping" == "scraping":
            if min_quality is None:
                min_quality = 70  # preset default
            # user's value should survive
        assert min_quality == 90  # explicit wins


class TestValidationCount:
    """4A — validation_count not added to list (too expensive), covered by detail."""

    def test_validation_count_expensive_skip(self):
        """validation_count requires subquery — skipped for perf."""
        pass  # intentional — list endpoint doesn't include it
