from pydantic import BaseModel, computed_field
from typing import Optional, List
from datetime import datetime, timezone


class ProxyResponse(BaseModel):
    id: int
    url: str
    protocol: str
    ip: Optional[str]
    port: Optional[int]
    country_code: Optional[str]
    country_name: Optional[str]
    state: Optional[str]
    city: Optional[str]
    latency_ms: Optional[int]
    speed_mbps: Optional[float]
    anonymity: Optional[str]
    proxy_type: Optional[str]
    can_access_google: Optional[bool]
    quality_score: Optional[int]
    is_working: bool
    validation_status: Optional[str]
    last_validated: Optional[str]

    @computed_field
    @property
    def last_seen_hours_ago(self) -> Optional[float]:
        if self.last_validated is None:
            return None
        try:
            lv = datetime.fromisoformat(self.last_validated)
            delta = (datetime.now(timezone.utc).replace(tzinfo=None) - lv.replace(tzinfo=None)).total_seconds() / 3600
            return round(delta, 1)
        except (ValueError, TypeError):
            return None

    model_config = {"from_attributes": True}


class ProxiesListResponse(BaseModel):
    total: int
    count: int
    offset: int
    limit: int
    proxies: List[ProxyResponse]


class ProxyTestRequest(BaseModel):
    proxy_url: str
    target_url: str = "https://www.google.com"
    timeout: int = 5


class ProxyTestResponse(BaseModel):
    proxy_url: str
    target_url: str
    working: bool
    latency_ms: Optional[int]
    status_code: Optional[int]
    error: Optional[str]
    tested_at: str


class RotationSessionCreate(BaseModel):
    session_id: Optional[str] = None
    strategy: str = "random"
    max_usage_per_proxy: int = 5
    cooldown_minutes: int = 5
