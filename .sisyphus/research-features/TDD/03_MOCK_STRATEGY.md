# MOCKING STRATEGY

**Focus:** Avoiding External API Calls in Tests

---

## 1. MOCKING GITHUB API
We use `aioresponses` to intercept calls to `api.github.com`.

```python
@pytest.fixture
def mock_github(aioresponses):
    aioresponses.get(
        re.compile(r"^https://api\.github\.com/search/code.*$"),
        payload={
            "items": [
                {"name": "proxy.txt", "html_url": "https://github.com/user/repo/blob/main/proxy.txt"}
            ]
        }
    )
```

## 2. MOCKING AI PROVIDER
We patch the `g4f` module directly.

```python
with patch("app.hunter.strategies.ai.g4f.ChatCompletion.create") as mock_chat:
    mock_chat.return_value = '{"urls": ["https://pastebin.com/raw/abcd"]}'
    # Run test...
```

## 3. MOCKING GOOGLE SEARCH
We mock the internal scraping function, not Google itself, to avoid complex HTML parsing in tests.

```python
with patch("app.hunter.strategies.search.scrape_google_results") as mock_scrape:
    mock_scrape.return_value = ["https://found-url.com"]
    # Run test...
```
