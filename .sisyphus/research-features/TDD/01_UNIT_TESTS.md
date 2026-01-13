# UNIT TEST PLAN

**Phase:** 1 - Foundation  
**Target:** Extractor & Models

---

## 1. TEST SUITE: `tests/unit/test_hunter_extractor.py`

### Test 1: IP:Port Regex
- **Input:** `"Hello 1.1.1.1:80 world 192.168.1.1:8080"`
- **Expected:** `["1.1.1.1:80", "192.168.1.1:8080"]`

### Test 2: Base64 Decoding
- **Input:** `base64_encode("1.1.1.1:80\n2.2.2.2:443")`
- **Expected:** `["1.1.1.1:80", "2.2.2.2:443"]`
- **Constraint:** Must handle padding (`=`) errors gracefully.

### Test 3: Mixed Protocols
- **Input:** `"http://1.1.1.1:80\nvmess://abcd...\nss://xyz..."`
- **Expected:** 3 distinct proxy objects with correct types.

### Test 4: Messy HTML
- **Input:** `<html><body><p>Proxy: 1.1.1.1:80</p></body></html>`
- **Expected:** `["1.1.1.1:80"]` (Tags stripped).

---

## 2. TEST SUITE: `tests/unit/test_candidate_model.py`

### Test 1: Creation & Defaults
- **Action:** Create `CandidateSource(url="http://test.com", discovery_method="manual")`.
- **Assert:** `status == "pending"`, `confidence_score == 0`.

### Test 2: Uniqueness
- **Action:** Add two candidates with same URL.
- **Assert:** `IntegrityError` or `SQLAlchemyError`.
