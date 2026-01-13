# 1PROXY GRABBER ENGINE

**Location:** `1proxy-backend/app/grabber/`  
**Focus:** Proxy scraping, URL normalization, and protocol-specific parsing.

## OVERVIEW
Handles the discovery and extraction of proxies from various sources through asynchronous fetching and regex-based protocol parsing.

## WHERE TO LOOK
| File | Responsibility |
|------|----------------|
| `base.py` | `BaseGrabber` abstract class & extraction workflow |
| `github_grabber.py` | GitHub-specific fetching with URL normalization |
| `patterns.py` | `ProxyPatterns` regex registry for all protocols |
| `parsers.py` | Config parsers for VMess, VLESS, Trojan, and SS |
| `__init__.py` | Package exports |

## CONVENTIONS
- **GitHub Normalization**: Auto-converts `github.com/.../raw/` URLs to `raw.githubusercontent.com` to avoid HTML wrapping.
- **Protocol Patterns**: Uses compiled regex for HTTP (IP:Port), VMess, VLESS, Trojan, and Shadowsocks.
- **Base64 Padding**: Automatically appends missing `=` characters to VMess/Subscription strings before decoding.
- **Error Resilience**: `BaseGrabber` ignores individual parsing failures to maximize yield from messy sources.
- **Retry Logic**: 3-stage exponential backoff for network-related fetching errors.

## UNIQUE ALGORITHMS
### 1. VMess Config Extraction
Decodes Base64 → Appends padding → JSON load → Maps `add` (host) and `port` fields to `Proxy` model.

### 2. Multi-Protocol Pipeline
1. Fetch raw content (Text or Base64-encoded subscription)
2. Optional subscription decoding via `SubscriptionDecoder`
3. Concurrent regex matching for HTTP/VMess/VLESS/Trojan/SS
4. Protocol-specific URI parsing (UUID, transport, server, port)

## ADDING NEW SOURCES
1. Add new regex to `patterns.py`
2. Create parser in `parsers.py`
3. Update `BaseGrabber.parse_content` in `base.py`
