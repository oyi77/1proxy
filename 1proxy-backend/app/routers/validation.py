from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.validator import proxy_validator, ValidationResult

router = APIRouter(prefix="/api/v1/validate", tags=["validation"])


class ValidateProxyRequest(BaseModel):
    proxy_url: str
    ip: Optional[str] = None


class ValidateProxyResponse(BaseModel):
    success: bool
    latency_ms: Optional[int] = None
    anonymity: Optional[str] = None
    can_access_google: Optional[bool] = None
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    proxy_type: Optional[str] = None
    quality_score: Optional[int] = None
    error_message: Optional[str] = None


@router.post("/proxy", response_model=ValidateProxyResponse)
async def validate_proxy(request: ValidateProxyRequest):
    if not request.ip:
        try:
            ip_port = request.proxy_url.replace("http://", "").replace("https://", "").replace("socks4://", "").replace("socks5://", "")
            ip = ip_port.split(":")[0]
        except Exception:
            raise HTTPException(status_code=400, detail="Could not extract IP from proxy_url. Please provide IP explicitly.")
    else:
        ip = request.ip
    
    try:
        result = await proxy_validator.validate_comprehensive(request.proxy_url, ip)
        
        quality_score = None
        if result.success:
            quality_score = await proxy_validator.calculate_quality_score(
                result.latency_ms,
                result.anonymity,
                result.can_access_google,
                result.proxy_type
            )
        
        return ValidateProxyResponse(
            success=result.success,
            latency_ms=result.latency_ms,
            anonymity=result.anonymity,
            can_access_google=result.can_access_google,
            country_code=result.country_code,
            country_name=result.country_name,
            proxy_type=result.proxy_type,
            quality_score=quality_score,
            error_message=result.error_message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/proxy/format", response_model=dict)
async def validate_proxy_format(request: ValidateProxyRequest):
    is_valid = await proxy_validator.validate_format(request.proxy_url)
    return {
        "valid": is_valid,
        "proxy_url": request.proxy_url
    }
