# 1PROXY BACKEND TEST SUITE

## OVERVIEW
Comprehensive pytest suite for 1proxy backend validation, scraping, and model logic.

## STRUCTURE
```
tests/
├── unit/           # Atomic tests for validators, parsers, and grabbers
├── integration/    # End-to-end scraper and API integration tests
├── fixtures/       # Static test data (raw proxy lists, base64 blobs)
└── conftest.py     # Global async fixtures and shared models
```

## WHERE TO LOOK
- **Add unit test**: `tests/unit/test_<module>.py`
- **Add integration test**: `tests/integration/test_<flow>.py`
- **Global fixtures**: `tests/conftest.py` (includes `event_loop`, `sample_proxy`)
- **Raw test data**: `tests/fixtures/*.txt`

## CONVENTIONS
- **Markers**: Use `@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.slow`
- **Async Testing**: `pytest-asyncio` enabled; all tests are `async` by default
- **Mocking**: Use `aioresponses` for mocking external GitHub/subscription HTTP calls
- **Fixtures**: Prefer `conftest.py` for model factories to maintain consistency
- **Event Loop**: Custom `event_loop` fixture in `conftest.py` ensures clean session teardown

## CONFIGURATION (pytest.ini)
- **Asyncio**: `asyncio_mode = auto` (no `@pytest.mark.asyncio` required)
- **Coverage**: Mandatory `--cov=app` with terminal-missing reports
- **Strictness**: `--strict-markers` enabled to prevent typo-based marker silent failures
- **Filters**: Deselect slow tests with `pytest -m "not slow"`
