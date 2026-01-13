import pytest
from app.models.source import SourceConfig, SourceType


def test_source_config_creation():
    """Test that SourceConfig model can be created with required fields."""
    source = SourceConfig(
        url="https://github.com/user/proxies/raw/main/list.txt",
        type=SourceType.GITHUB_RAW,
        enabled=True,
    )

    assert str(source.url) == "https://github.com/user/proxies/raw/main/list.txt"
    assert source.type == SourceType.GITHUB_RAW
    assert source.enabled is True


def test_source_config_defaults():
    """Test default values for optional fields."""
    source = SourceConfig(
        url="https://example.com/proxies.txt", type=SourceType.GENERIC_TEXT
    )

    assert source.enabled is True
    assert source.selector is None
    assert source.interval == 3600


def test_source_type_enum():
    """Test that SourceType enum contains all required types."""
    assert hasattr(SourceType, "GITHUB_RAW")
    assert hasattr(SourceType, "SUBSCRIPTION_BASE64")
    assert hasattr(SourceType, "GENERIC_TEXT")
