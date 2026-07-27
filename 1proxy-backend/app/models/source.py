from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from typing import Optional
from enum import Enum


class SourceType(str, Enum):
    GITHUB_RAW = "github_raw"
    SUBSCRIPTION_BASE64 = "subscription_base64"
    GENERIC_TEXT = "generic_text"
    TOR_EXIT = "tor_exit"


class SourceConfig(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    url: (
        str  # Changed from HttpUrl to str for more flexibility with various URL formats
    )
    type: SourceType
    enabled: bool = True
    selector: Optional[str] = None
    interval: int = Field(default=3600, gt=0)
