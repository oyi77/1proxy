# Adaptive Grabber Usage Examples

## Quick Start

```python
import asyncio
from app.grabber import GitHubGrabber
from app.models import SourceConfig, SourceType

async def main():
    # Create a GitHub grabber
    grabber = GitHubGrabber()
    
    # Configure source
    source = SourceConfig(
        url="https://raw.githubusercontent.com/user/repo/main/proxies.txt",
        type=SourceType.GITHUB_RAW,
        enabled=True
    )
    
    # Extract proxies
    proxies = await grabber.extract_proxies(source)
    
    # Print results
    for proxy in proxies:
        print(f"{proxy.protocol}://{proxy.ip}:{proxy.port}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Supported Protocols

### HTTP/HTTPS Proxies
```python
# Plain IP:Port format
content = """
192.168.1.1:8080
10.0.0.1:3128
"""
proxies = await grabber.parse_content(content, SourceType.GENERIC_TEXT)
```

### VMess
```python
# Base64 encoded JSON config
vmess_url = "vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0Ijo0NDN9"
proxies = await grabber.parse_content(vmess_url, SourceType.GENERIC_TEXT)
```

### VLESS
```python
# UUID@server:port format
vless_url = "vless://uuid@example.com:443?type=tcp&encryption=none"
proxies = await grabber.parse_content(vless_url, SourceType.GENERIC_TEXT)
```

### Trojan
```python
# password@server:port format
trojan_url = "trojan://password@server.com:443?sni=example.com"
proxies = await grabber.parse_content(trojan_url, SourceType.GENERIC_TEXT)
```

### Shadowsocks
```python
# Base64 method:password@server:port
ss_url = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@server.com:8388"
proxies = await grabber.parse_content(ss_url, SourceType.GENERIC_TEXT)
```

## Base64 Subscriptions

```python
from app.utils import SubscriptionDecoder

# Decode subscription
encoded_content = "dm1lc3M6Ly90ZXN0..."
decoded = SubscriptionDecoder.decode(encoded_content)

# Or use directly with grabber
source = SourceConfig(
    url="https://example.com/subscription",
    type=SourceType.SUBSCRIPTION_BASE64
)
proxies = await grabber.extract_proxies(source)
```

## Custom Grabber Implementation

```python
from app.grabber import BaseGrabber

class CustomGrabber(BaseGrabber):
    async def fetch_content(self, source: SourceConfig) -> str:
        # Implement your custom fetching logic
        # Return raw proxy list content
        pass

# Use it
grabber = CustomGrabber(
    max_retries=3,
    retry_delay=1.0,
    timeout=30
)
```

## Error Handling

```python
try:
    proxies = await grabber.extract_proxies(source)
except FileNotFoundError:
    print("Source URL not found (404)")
except asyncio.TimeoutError:
    print("Request timed out")
except Exception as e:
    print(f"Error: {e}")
```

## Advanced Configuration

```python
# Configure retry behavior
grabber = GitHubGrabber(
    max_retries=5,        # Retry up to 5 times
    retry_delay=2.0,      # Wait 2 seconds between retries
    timeout=60            # 60 second timeout
)

# Source with selector (Tier 1 - exact selector)
source = SourceConfig(
    url="https://example.com/proxies",
    type=SourceType.GENERIC_TEXT,
    selector=".proxy-list li",  # CSS selector
    interval=3600  # Scrape every hour
)
```

## Testing

```python
import pytest
from aioresponses import aioresponses

@pytest.mark.asyncio
async def test_my_grabber():
    grabber = GitHubGrabber()
    source = SourceConfig(
        url="https://raw.githubusercontent.com/test/repo/main/list.txt",
        type=SourceType.GITHUB_RAW
    )
    
    with aioresponses() as mocked:
        mocked.get(
            str(source.url),
            status=200,
            body="192.168.1.1:8080"
        )
        
        proxies = await grabber.extract_proxies(source)
        assert len(proxies) == 1
```
