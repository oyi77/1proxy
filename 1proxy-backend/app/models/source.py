from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from typing import Optional
from enum import Enum


class SourceType(str, Enum):
    GITHUB_RAW = "github_raw"
    SUBSCRIPTION_BASE64 = "subscription_base64"
    GENERIC_TEXT = "generic_text"


class SourceConfig(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    url: HttpUrl
    type: SourceType
    enabled: bool = True
    selector: Optional[str] = None
    interval: int = Field(default=3600, gt=0)
