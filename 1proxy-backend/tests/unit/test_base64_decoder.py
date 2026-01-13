import pytest
import base64
from app.utils.base64_decoder import SubscriptionDecoder


class TestBase64Decoder:
    def test_decode_simple_base64(self):
        original = "vmess://test123\nvless://test456"
        encoded = base64.b64encode(original.encode()).decode()

        decoded = SubscriptionDecoder.decode(encoded)
        assert decoded == original

    def test_decode_with_padding(self):
        original = "proxy list"
        encoded_with = base64.b64encode(original.encode()).decode()
        encoded_without = encoded_with.rstrip("=")

        assert SubscriptionDecoder.decode(encoded_with) == original
        assert SubscriptionDecoder.decode(encoded_without) == original

    def test_decode_multiline(self):
        original = "line1\nline2\nline3"
        encoded = base64.b64encode(original.encode()).decode()

        decoded = SubscriptionDecoder.decode(encoded)
        assert decoded.count("\n") == 2
        assert "line1" in decoded

    def test_invalid_base64(self):
        with pytest.raises(ValueError):
            SubscriptionDecoder.decode("not!@#$%valid&*base64")

    def test_empty_string(self):
        result = SubscriptionDecoder.decode("")
        assert result == ""
