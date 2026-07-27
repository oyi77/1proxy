from app.utils.base64_decoder import SubscriptionDecoder


def proxy_to_dict(proxy, source_id: int | None = None) -> dict:
    """Normalise a proxy object into the dict shape expected by the storage layer.

    Accepts a Pydantic model (preferred) or any object with the same attributes.
    Optionally attaches *source_id* for the source-tracking column.
    """
    data = proxy.model_dump() if hasattr(proxy, "model_dump") else proxy.__dict__
    result = {
        "url": f"{data.get('protocol', 'http')}://{data.get('ip')}:{data.get('port')}",
        "protocol": data.get("protocol", "http"),
        "ip": data.get("ip"),
        "port": data.get("port"),
        "country_code": data.get("country_code"),
        "country_name": data.get("country_name"),
        "city": data.get("city"),
        "latency_ms": data.get("latency_ms"),
        "speed_mbps": data.get("speed_mbps"),
        "anonymity": data.get("anonymity"),
        "proxy_type": data.get("proxy_type"),
    }
    if source_id is not None:
        result["source_id"] = source_id
    return result


__all__ = [
    "SubscriptionDecoder",
    "proxy_to_dict",
]
