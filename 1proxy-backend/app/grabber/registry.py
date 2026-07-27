"""
Provider/Plugin Registry for proxy source grabbers.

Allows new source types/providers to be registered without modifying
core scraper logic. Each provider class implements fetch + parse
and registers itself via @register_provider decorator.
"""

from typing import Dict, Type, Optional, List
from app.models.source import SourceType
from app.grabber.base import BaseGrabber
import logging

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Central registry mapping SourceType → grabber class.

    Usage:
        @ProviderRegistry.register(SourceType.GITHUB_RAW)
        class MyGrabber(BaseGrabber): ...
    """

    _providers: Dict[str, Type[BaseGrabber]] = {}

    @classmethod
    def register(cls, source_type: SourceType):
        """Decorator: register a grabber class for a SourceType."""
        def _inner(grabber_cls: Type[BaseGrabber]):
            key = source_type.value if hasattr(source_type, "value") else str(source_type)
            if key in cls._providers:
                logger.warning(
                    f"⚠️  Overwriting provider for '{key}': "
                    f"{cls._providers[key].__name__} → {grabber_cls.__name__}"
                )
            cls._providers[key] = grabber_cls
            logger.debug(f"✅ Registered provider: {grabber_cls.__name__} → '{key}'")
            return grabber_cls
        return _inner

    @classmethod
    def register_direct(cls, key: str, grabber_cls: Type[BaseGrabber]):
        """Direct registration (non-decorator path)."""
        cls._providers[key] = grabber_cls
        logger.debug(f"✅ Registered provider: {grabber_cls.__name__} → '{key}'")

    @classmethod
    def get_grabber(cls, source_type: SourceType) -> BaseGrabber:
        """
        Get an instance of the grabber for the given source type.

        Falls back to GitHubGrabber if no specific provider is registered.
        """
        key = source_type.value if hasattr(source_type, "value") else str(source_type)
        grabber_cls = cls._providers.get(key)
        if grabber_cls:
            return grabber_cls()
        # Fallback
        from app.grabber.github_grabber import GitHubGrabber
        logger.debug(f"No provider for '{key}', falling back to GitHubGrabber")
        return GitHubGrabber()

    @classmethod
    def get_grabber_for_url(cls, url: str) -> BaseGrabber:
        """
        Smart dispatch: picks the best grabber based on URL pattern.

        - github.com raw URLs → GitHubGrabber
        - Everything else → WebGrabber
        """
        url_lower = url.lower()
        if "raw.githubusercontent.com" in url_lower or (
            "github.com" in url_lower and "/raw/" in url_lower
        ):
            return cls.get_grabber(SourceType.GITHUB_RAW)
        return cls.get_grabber(SourceType.GENERIC_TEXT)

    @classmethod
    def list_providers(cls) -> List[Dict[str, str]]:
        """Debug: list all registered providers."""
        return [
            {"type": key, "class": cls.__name__}
            for key, cls in cls._providers.items()
        ]

    @classmethod
    def clear(cls):
        """Reset registry (for testing)."""
        cls._providers.clear()
