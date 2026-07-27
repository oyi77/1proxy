from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID, uuid4


class Proxy(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    ip: str
    port: int
    protocol: str
    anonymity: Optional[str] = "transparent"
    country_code: Optional[str] = None
    source: str
    score: float = 0.0
    last_validated: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)


class ValidationResult(BaseModel):
    proxy_id: UUID
    passed: bool
    latency_ms: float
    is_elite: bool = False
    headers: dict = {}
    error: Optional[str] = None
    validated_at: datetime = Field(default_factory=datetime.now)
