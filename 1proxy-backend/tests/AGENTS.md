# 1PROXY BACKEND TEST SUITE

**Location:** `1proxy-backend/tests/`  
**Focus:** Comprehensive pytest suite for validation, scraping, and model logic.

## OVERVIEW
Structured pytest suite with async support, strict markers, and mandatory coverage reporting. Tests are organized by granularity (unit vs integration) and execution speed.

## STRUCTURE
```
tests/
├── unit/           # Atomic tests for validators, parsers, grabbers
├── integration/    # End-to-end scraper and API integration tests
├── fixtures/       # Static test data (raw proxy lists, base64 blobs)
└── conftest.py     # Global async fixtures and shared models
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| Add unit test | `tests/unit/test_<module>.py` |
| Add integration test | `tests/integration/test_<flow>.py` |
| Global fixtures | `tests/conftest.py` (event_loop, sample_proxy) |
| Raw test data | `tests/fixtures/*.txt` |

## CONVENTIONS
- **Markers**: Use `@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.slow`
- **Async Testing**: `pytest-asyncio` enabled; all tests are `async` by default
- **Mocking**: Use `aioresponses` for mocking external GitHub/subscription HTTP calls
- **Fixtures**: Prefer `conftest.py` for model factories to maintain consistency
- **Event Loop**: Custom `event_loop` fixture ensures clean session teardown

## CONFIGURATION (pytest.ini)
- **Asyncio**: `asyncio_mode = auto` (no `@pytest.mark.asyncio` required)
- **Coverage**: Mandatory `--cov=app` with terminal-missing reports
- **Strictness**: `--strict-markers` enabled to prevent typo-based silent failures
- **Filters**: Deselect slow tests with `pytest -m "not slow"`

## KEY FIXTURES (conftest.py)
- **`init_test_db`**: Handles schema creation/teardown using SQLAlchemy async engine
- **`sample_proxy`**: Factory for `Proxy` model instances
- **`sample_source`**: Factory for `SourceConfig` instances
- **`event_loop`**: Overridden to ensure clean async session teardown

## TEST DATA (fixtures/)
- `github_raw_http.txt`: Sample HTTP proxy list
- `subscription_vmess.txt`: Base64-encoded VMess subscription
- Used for parser and grabber tests

## ANTI-PATTERNS
- **NO** `pytest.mark.asyncio` decorator (redundant with `asyncio_mode = auto`)
- **NO** hardcoded test data in test files (use `fixtures/` directory)
- **NO** skipping tests without `@pytest.mark.slow` justification

## KNOWN ISSUES
- **Mocking Repetition**: 10+ line `aiohttp` response mock repeated across `test_validator.py` (extract to fixture)
- **Test file size**: `test_validator.py` is 532 lines (consider splitting by validation type)
