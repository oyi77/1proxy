# 1PROXY GRABBER ENGINE

**Location:** `1proxy-backend/app/grabber/`  
**Focus:** Proxy scraping, URL normalization, and protocol-specific parsing.

## OVERVIEW
Handles discovery and extraction of proxies from various sources through asynchronous fetching and regex-based protocol parsing. Supports HTTP, VMess, VLESS, Trojan, and Shadowsocks.

## STRUCTURE
```
grabber/
├── base.py            # BaseGrabber abstract class & extraction workflow
├── github_grabber.py  # GitHub-specific fetching with URL normalization
├── patterns.py        # ProxyPatterns regex registry for all protocols
├── parsers.py         # Config parsers for VMess, VLESS, Trojan, SS
└── __init__.py        # Package exports
```

## WHERE TO LOOK
| Task | File |
|------|------|
| Base extraction logic | `base.py` → `BaseGrabber` |
| GitHub URL conversion | `github_grabber.py` → `normalize_github_url()` |
| Add new protocol | `patterns.py` → add regex, `parsers.py` → add parser |
| VMess/VLESS parsing | `parsers.py` → `VMessParser`, `VLESSParser` |

## CONVENTIONS
- **GitHub Normalization**: Auto-converts `github.com/.../blob/` URLs to `raw.githubusercontent.com`
- **Protocol Patterns**: Uses compiled regex for all proxy formats
- **Base64 Padding**: Automatically appends missing `=` characters before decoding
- **Error Resilience**: `BaseGrabber` ignores individual parsing failures to maximize yield
- **Retry Logic**: 3-stage exponential backoff for network errors

## UNIQUE ALGORITHMS
### 1. VMess Config Extraction
```
Raw text → Base64 decode → Add padding → JSON parse → Extract host/port
```

### 2. Multi-Protocol Pipeline
```
1. Fetch raw content (text or Base64 subscription)
2. Optional subscription decoding via SubscriptionDecoder
3. Concurrent regex matching (HTTP/VMess/VLESS/Trojan/SS)
4. Protocol-specific URI parsing (UUID, transport, server, port)
```

## ADDING NEW PROTOCOLS
1. Add regex pattern to `patterns.py` → `ProxyPatterns`
2. Create parser class in `parsers.py` (inherit from base or standalone)
3. Update `BaseGrabber.parse_content()` in `base.py` to call new parser

## ANTI-PATTERNS
- **NO** blocking I/O - use `aiohttp` for all fetches
- **NO** hardcoded GitHub tokens - use env vars
- **NO** failing on single parse error - catch and continue

## KNOWN ISSUES
- **Base64 padding duplicated**: Logic exists in both `utils/base64_decoder.py` and `parsers.py`
- **IP validation duplicated**: `patterns.py` has `is_valid_ip()` that also exists in `validator.py`
