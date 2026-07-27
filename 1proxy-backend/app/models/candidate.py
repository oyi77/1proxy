from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timezone


class CandidateResponse(BaseModel):
    id: int
    url: str
    domain: Optional[str]
    discovery_method: str
    status: str
    confidence_score: int
    proxies_found_count: int
    created_at: datetime
    last_checked_at: Optional[datetime]
    meta_data: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}
