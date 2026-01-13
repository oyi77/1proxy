# INTEGRATION TEST PLAN

**Phase:** 2 & 3 - Strategies & Service  
**Target:** Strategies, DB, Service Layer

---

## 1. TEST SUITE: `tests/integration/test_hunter_strategies.py`

### Test 1: GitHub Strategy (Mocked)
- **Mock:** `aiohttp.ClientSession.get` returning GitHub JSON search results.
- **Action:** Call `GitHubStrategy.search()`.
- **Assert:** Returns list of raw content URLs.

### Test 2: AI Strategy (Mocked)
- **Mock:** `g4f.ChatCompletion.create` returning text "Here is a list: https://raw.github...".
- **Action:** Call `AIStrategy.find_sources()`.
- **Assert:** Parses the text and extracts the URL.

---

## 2. TEST SUITE: `tests/integration/test_hunter_service.py`

### Test 1: Deduplication
- **Setup:** Database already has `Source(url="http://existing.com")`.
- **Action:** Hunter finds `http://existing.com` again.
- **Assert:** NO new row in `candidate_sources`.

### Test 2: New Candidate Flow
- **Action:** Hunter finds `http://new.com`.
- **Assert:** New row in `candidate_sources` with status `pending`.

### Test 3: Confidence Scoring
- **Action:** Mock Extractor to find 100 proxies.
- **Action:** Run `HunterService.process_candidate(url)`.
- **Assert:** `candidate.confidence_score` increases (e.g., > 20).
