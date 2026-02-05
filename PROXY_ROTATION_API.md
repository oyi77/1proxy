# Proxy Rotation API

The 1proxy API now includes automated proxy rotation endpoints with state management and multiple rotation strategies.

## Overview

Proxy rotation allows you to get different proxies on each request while maintaining session state to avoid reusing the same proxy too frequently.

## Rotation Strategies

### 1. `random` (Default)
Randomly selects a proxy from available options. Good for simple use cases.

### 2. `round_robin`
Cycles through proxies in a fixed order. Ensures all proxies get used equally.

### 3. `quality`
Prioritizes highest quality proxies first. Best for performance-critical applications.

### 4. `least_used`
Selects proxies that have been used least frequently. Best for load balancing.

---

## API Endpoints

### 1. Rotate Proxy (Get Next Proxy)

**GET** `/api/v1/proxies/rotate`

Get the next proxy in your rotation sequence. Automatically creates a session if none exists.

**Query Parameters:**
- `session_id` (optional): Rotation session ID. Auto-generated if not provided.
- `strategy` (optional): `random`, `round_robin`, `quality`, `least_used` (default: `random`)
- `protocol` (optional): Filter by protocol (http, https, socks4, socks5, vmess, vless, etc.)
- `country_code` (optional): Filter by country code (US, GB, DE, etc.)
- `min_quality` (optional): Minimum quality score 0-100 (default: no filter)
- `anonymity` (optional): Filter by anonymity (transparent, anonymous, elite)
- `max_latency` (optional): Maximum latency in milliseconds
- `max_usage_per_proxy` (optional): Max times to use each proxy (default: 5)
- `cooldown_minutes` (optional): Minutes before reusing same proxy (default: 5)

**Response:**
```json
{
  "id": 123,
  "url": "http://192.168.1.1:8080",
  "protocol": "http",
  "ip": "192.168.1.1",
  "port": 8080,
  "country_code": "US",
  "country_name": "United States",
  "latency_ms": 150,
  "speed_mbps": 50.5,
  "anonymity": "anonymous",
  "quality_score": 85,
  "is_working": true,
  "last_validated": "2024-01-15T10:30:00"
}
```

**Example Usage:**
```bash
# Get random proxy (auto-creates session)
curl "https://api.1proxy.com/api/v1/proxies/rotate"

# Get next proxy with session tracking
curl "https://api.1proxy.com/api/v1/proxies/rotate?session_id=my-session&strategy=round_robin&protocol=socks5"

# Quality-based rotation
curl "https://api.1proxy.com/api/v1/proxies/rotate?strategy=quality&min_quality=80&max_latency=500"
```

---

### 2. Create Rotation Session

**POST** `/api/v1/proxies/rotate/session`

Create a new rotation session with custom settings.

**Request Body:**
```json
{
  "session_id": "my-custom-session",  // Optional - auto-generated if not provided
  "strategy": "round_robin",
  "max_usage_per_proxy": 10,
  "cooldown_minutes": 10
}
```

**Response:**
```json
{
  "session_id": "my-custom-session",
  "strategy": "round_robin",
  "created_at": "2024-01-15T12:00:00",
  "max_usage_per_proxy": 10,
  "cooldown_minutes": 10,
  "message": "Use this session_id in /proxies/rotate requests"
}
```

**Use Case:**
- Create multiple independent sessions for different tasks
- Pre-configure rotation settings
- Manage separate rotations for different use cases

---

### 3. Get Session Stats

**GET** `/api/v1/proxies/rotate/session/{session_id}/stats`

Get statistics and usage information for a rotation session.

**Response:**
```json
{
  "session_id": "my-session",
  "strategy": "round_robin",
  "created_at": "2024-01-15T12:00:00",
  "last_used": "2024-01-15T12:15:30",
  "total_proxies_used": 15,
  "unique_proxies_used": 15,
  "excluded_ips_count": 3,
  "proxy_index": 5
}
```

**Use Case:**
- Monitor rotation activity
- Track proxy usage
- Debug rotation issues

---

### 4. Reset Rotation Session

**POST** `/api/v1/proxies/rotate/session/{session_id}/reset`

Reset a rotation session's state (clears usage history and excluded IPs).

**Response:**
```json
{
  "session_id": "my-session",
  "message": "Rotation session reset successfully",
  "previous_stats": { ... }
}
```

**Use Case:**
- Start fresh rotation
- Reuse previously used proxies
- Clear excluded IPs

---

### 5. Delete Rotation Session

**DELETE** `/api/v1/proxies/rotate/session/{session_id}`

Delete a rotation session completely.

**Response:**
```json
{
  "session_id": "my-session",
  "message": "Rotation session deleted successfully"
}
```

**Use Case:**
- Clean up unused sessions
- End rotation for a specific task

---

### 6. Exclude Proxy from Rotation

**POST** `/api/v1/proxies/rotate/session/{session_id}/exclude`

Manually exclude a proxy IP from rotation in a session.

**Request Body:**
```json
{
  "ip": "192.168.1.1"
}
```

**Response:**
```json
{
  "session_id": "my-session",
  "excluded_ip": "192.168.1.1",
  "message": "IP 192.168.1.1 excluded from rotation for this session"
}
```

**Use Case:**
- Avoid problematic proxies encountered during use
- Manually filter out bad proxies
- Exclude specific IPs from rotation

---

## Session Lifecycle

1. **Creation**: Session auto-created on first `/rotate` request, or explicitly with `/rotate/session`
2. **Usage**: Call `/rotate` repeatedly with same `session_id` to get different proxies
3. **Maintenance**: Use `/exclude` to block bad proxies, `/reset` to start fresh
4. **Expiration**: Sessions automatically expire after 60 minutes of inactivity
5. **Cleanup**: Use DELETE to manually end a session

---

## Best Practices

### For Web Scraping
```bash
# Create session
curl -X POST "https://api.1proxy.com/api/v1/proxies/rotate/session" \
  -d '{"strategy": "round_robin", "cooldown_minutes": 2, "max_usage_per_proxy": 3}'

# Use in scraping loop
curl "https://api.1proxy.com/api/v1/proxies/rotate?session_id=my-scrape-session&protocol=socks5"
```

### For High-Performance Requests
```bash
# Use quality-based rotation with high-quality proxies
curl "https://api.1proxy.com/api/v1/proxies/rotate?strategy=quality&min_quality=80&max_latency=300"
```

### For Load Balancing
```bash
# Use least-used strategy to distribute load evenly
curl "https://api.1proxy.com/api/v1/proxies/rotate?strategy=least_used"
```

### For Country-Specific Requests
```bash
# Rotate through US proxies only
curl "https://api.1proxy.com/api/v1/proxies/rotate?country_code=US"
```

---

## Rate Limiting

- `/proxies/rotate`: 60 requests/minute per IP
- `/proxies/rotate/session`: 30 requests/minute per IP
- Other rotation endpoints: 30 requests/minute per IP

---

## Error Handling

### 404 Not Found
- No proxies matching the specified criteria
- Session ID not found or expired
- All proxies excluded or used max times

### 400 Bad Request
- Invalid rotation strategy
- Invalid parameters (e.g., negative quality score)

### 429 Too Many Requests
- Rate limit exceeded

---

## Example Implementation (Python)

```python
import requests
import time

# Create rotation session
session = requests.post("https://api.1proxy.com/api/v1/proxies/rotate/session", json={
    "strategy": "round_robin",
    "max_usage_per_proxy": 3,
    "cooldown_minutes": 5
}).json()

session_id = session["session_id"]

# Use proxies in rotation
for i in range(10):
    # Get next proxy
    proxy = requests.get(
        f"https://api.1proxy.com/api/v1/proxies/rotate?session_id={session_id}&min_quality=60"
    ).json()

    print(f"Using proxy: {proxy['url']} (Quality: {proxy['quality_score']})")

    # Make request through proxy
    response = requests.get(
        "https://example.com",
        proxies={"http": proxy['url'], "https": proxy['url']},
        timeout=10
    )

    # If proxy fails, exclude it
    if response.status_code != 200:
        requests.post(
            f"https://api.1proxy.com/api/v1/proxies/rotate/session/{session_id}/exclude",
            json={"ip": proxy['ip']}
        )
        print(f"Excluded bad proxy: {proxy['ip']}")

    time.sleep(2)  # Be respectful
```

---

## Notes

- Sessions are stored in-memory and expire after 60 minutes of inactivity
- Automatic cleanup of expired sessions occurs periodically
- Proxy caching improves performance (5-minute cache TTL)
- All proxies returned are validated and working (is_working=True)
- Rotation state is per-session, allowing multiple independent rotations
