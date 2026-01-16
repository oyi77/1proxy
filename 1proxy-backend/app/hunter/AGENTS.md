# HUNTER PROTOCOL (AUTO-DISCOVERY ENGINE)

**Location:** `1proxy-backend/app/hunter/`  
**Focus:** Autonomous proxy source discovery using AI, search engines, and existing proxies.

## OVERVIEW
Multi-strategy discovery engine allowing 1proxy to grow autonomously by finding new proxy sources without human intervention. Uses a confidence scoring system to rank candidates.

## STRUCTURE
```
hunter/
├── strategies/        # Discovery strategy implementations (→ see strategies/AGENTS.md)
│   ├── search.py      # DuckDuckGo scraping via existing proxies
│   ├── ai.py          # LLM-based discovery (g4f)
│   └── github.py      # GitHub URL normalization
├── service.py         # Orchestrates all strategies + confidence scoring
├── extractor.py       # Universal proxy parser (HTML, Base64, VMess)
└── __init__.py
```

## WHERE TO LOOK
| Task | File |
|------|------|
| Add new discovery strategy | `strategies/*.py` |
| Modify confidence scoring | `service.py` → `_calculate_confidence()` |
| Change extraction logic | `extractor.py` → `UniversalExtractor` |
| Trigger manual hunt | `routers/admin.py` → `/hunter/trigger` |

## HUNTER WORKFLOW
1. **Discovery**: Each strategy returns candidate URLs
2. **Extraction**: `UniversalExtractor` parses proxies from each URL
3. **Scoring**: Candidates get `confidence_score` (0-100) based on domain trust + proxy yield
4. **Storage**: Saved as `CandidateSource` with status `pending`
5. **Approval**: Admin promotes candidates to active `ProxySource` via `/admin/candidates/{id}/approve`

## CONVENTIONS
- **Self-Bootstrapping**: SearchStrategy uses existing validated proxies to bypass rate limits
- **Confidence Formula**: Domain trust (GitHub +20, Pastebin +10) + Proxy yield (500+ = +20) + Protocol diversity
- **Universal Extraction**: Handles raw text, Base64, HTML-wrapped, VMess/VLESS configs
- **GitHub Normalization**: Auto-converts `github.com/.../blob/` → `raw.githubusercontent.com/...`
- **Parallel Execution**: `HunterService` runs all strategies via `asyncio.gather()`

## UNIQUE ALGORITHMS
### Recursive Discovery Pattern
```python
# SearchStrategy uses proxies to find more proxies
existing_proxies = await get_working_proxies()
for proxy in existing_proxies:
    results = await search_via_proxy(proxy, query="free proxy list")
    for url in results:
        candidates.append(url)
```

### AI-Augmented Search
```python
# AIStrategy treats LLM as a search engine
prompt = "List 10 URLs to free proxy lists (GitHub, Pastebin, etc.)"
llm_response = await g4f.ChatCompletion.create(...)
urls = extract_urls_from_text(llm_response)
```

## ANTI-PATTERNS
- **NO** hardcoded source URLs in strategies (discover dynamically)
- **NO** blocking candidates without confidence scoring
- **NO** direct promotion to ProxySource (must go through CandidateSource)

## KNOWN ISSUES
- **Database Coupling**: `SearchStrategy` directly accesses `db_storage` and `database.get_db()` (should receive proxy provider interface)
- **Environment Coupling**: `GitHubStrategy` directly reads `os.getenv("GITHUB_TOKEN")` (should use config object)
