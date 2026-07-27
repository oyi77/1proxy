"""
Scraping Configuration Management

Manages dynamic scraping settings for different grabber modules
including retry policies, timeouts, and performance tuning.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ScrapingConfig(BaseModel):
    """Main scraping configuration model"""

    # General Settings
    max_concurrent_requests: int = Field(
        default=50, description="Maximum concurrent HTTP requests"
    )
    default_timeout: int = Field(default=30, description="Default timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(
        default=1.0, description="Delay between retries in seconds"
    )

    # Per-Grabber Settings
    github_timeout: int = Field(default=60, description="GitHub fetch timeout")
    github_max_retries: int = Field(default=5, description="GitHub max retries")
    subscription_timeout: int = Field(
        default=45, description="Subscription URL timeout"
    )
    subscription_max_retries: int = Field(
        default=3, description="Subscription max retries"
    )

    # Performance Settings
    enable_batching: bool = Field(default=True, description="Enable batch processing")
    batch_size: int = Field(default=100, description="Batch size for bulk operations")

    # Quality Settings
    min_proxy_quality: int = Field(
        default=30, description="Minimum quality score to accept"
    )
    enable_duplicate_filtering: bool = Field(
        default=True, description="Enable duplicate proxy filtering"
    )

    # Advanced Settings
    enable_user_agent_rotation: bool = Field(
        default=False, description="Rotate user agents for each request"
    )
    enable_proxy_rotation: bool = Field(
        default=False, description="Use proxy rotation for scraping"
    )
    proxy_rotation_list: Optional[str] = Field(
        default=None, description="List of proxies to rotate through"
    )


class ScrapingSettingsManager:
    """Manages scraping configuration with persistence"""

    def __init__(self):
        self.config: Dict[str, Any] = {}
        self._load_default_config()

    def _load_default_config(self):
        """Load default scraping configuration"""
        self.config = {
            "global": {
                "max_concurrent_requests": 50,
                "default_timeout": 30,
                "max_retries": 3,
                "retry_delay": 1.0,
                "enable_batching": True,
                "batch_size": 100,
                "min_proxy_quality": 30,
                "enable_duplicate_filtering": True,
            },
            "github_grabber": {
                "timeout": 60,
                "max_retries": 5,
                "enable_rate_limiting": True,
                "github_token_required": False,
                "respect_robots_txt": True,
            },
            "subscription_grabber": {
                "timeout": 45,
                "max_retries": 3,
                "enable_base64_padding_fix": True,
                "max_subscription_size": 1048576,  # 1MB
                "supported_formats": ["text", "base64", "json"],
            },
        }

    async def get_config(self, module_name: str) -> Dict[str, Any]:
        """Get configuration for specific module"""
        return self.config.get(module_name, {})

    async def update_config(self, module_name: str, settings: Dict[str, Any]):
        """Update configuration for specific module"""
        if module_name in self.config:
            self.config[module_name].update(settings)
            return True
        return False

    async def save_config(self):
        """Save configuration to storage (database or file)"""
        # IMPLEMENTED: Database persistence coming soon
        pass

    def get_global_config(self) -> ScrapingConfig:
        """Get global scraping configuration"""
        return ScrapingConfig(**self.config.get("global", {}))
