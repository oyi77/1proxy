# HUNTER DISCOVERY STRATEGIES

**Location:** `1proxy-backend/app/hunter/strategies/`  
**Focus:** Individual discovery strategy implementations following plugin architecture.

## OVERVIEW
Each strategy is a standalone module discovering proxy source URLs using different methods. All inherit from `BaseStrategy` interface.

## STRUCTURE
```
strategies/
├── search.py   # DuckDuckGo scraping using existing proxies
├── ai.py       # LLM-based discovery (g4f)
└── github.py   # GitHub URL normalization
```

## WHERE TO LOOK
| Strategy | File | Method |
|----------|------|--------|
| Search Engine Scraping | `search.py` | DuckDuckGo via existing proxies |
| AI-Powered Discovery | `ai.py` | LLM queries (g4f) |
| GitHub URL Conversion | `github.py` | Normalize to raw.githubusercontent.com |

## STRATEGY PATTERN
All strategies follow this interface:
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
- **Graceful Degradation**: `try-import` pattern for heavy dependencies (e.g., `g4f`)

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

### Prompt Engineering (ai.py)
AI prompts must explicitly state: **"Do not explain. Just list the URLs starting with https://."**

## ANTI-PATTERNS
- **NO** returning non-URL data (metadata, scores, etc.)
- **NO** raising exceptions on individual failures (catch and continue)
- **NO** accessing database directly (pass proxy provider interface)

## ADDING NEW STRATEGIES
1. Create `new_strategy.py` in this directory
2. Implement `name` property and `async def discover() -> List[str]`
3. Register in `HunterService` (auto-discovery or manual import)
4. Test with `/api/v1/admin/hunter/trigger`
