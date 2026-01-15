# HUNTER DISCOVERY STRATEGIES

**Location:** `1proxy-backend/app/hunter/strategies/`  
**Focus:** Individual discovery strategy implementations.

## OVERVIEW
Each strategy is a standalone module that discovers proxy source URLs using different methods.

## WHERE TO LOOK
| Strategy | File | Method |
|----------|------|--------|
| Search Engine Scraping | `search.py` | DuckDuckGo via existing proxies |
| AI-Powered Discovery | `ai.py` | LLM queries (g4f) |
| GitHub URL Conversion | `github.py` | Normalize to raw.githubusercontent.com |

## STRATEGY PATTERN
All strategies inherit from `BaseStrategy` (or implement a common interface):
```python
class SearchStrategy:
    name = "search"
    async def discover(self) -> List[str]:
        # Returns list of candidate URLs
        pass
```

## CONVENTIONS
- **Return Type**: Always `List[str]` (URLs only, no metadata)
- **Error Handling**: Strategies swallow individual failures, log warnings, continue
- **Concurrency**: `HunterService` runs all strategies in parallel via `asyncio.gather`
- **Deduplication**: Service-level (not strategy-level) - strategies can return duplicates

## UNIQUE PATTERNS
### Self-Bootstrapping (search.py)
Uses the project's own validated proxies to avoid IP blocks:
```python
proxies = await get_working_proxies(limit=10)
for proxy in proxies:
    results = await duckduckgo_search(query, proxy=proxy.url)
```

### AI Hallucination Filtering (ai.py)
LLMs may return fake URLs. Strategy validates URLs before returning:
```python
urls = extract_urls(llm_response)
return [u for u in urls if is_valid_http_url(u)]
```
