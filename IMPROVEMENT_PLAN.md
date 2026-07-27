# 1proxy Improvement Plan — Better Free Proxy Quality

## Current Baseline
- **17 sources** (GitHub raw proxy lists) + **Tor exit nodes**
- **Two-phase validation** (Phase 1: connectivity → Phase 2: comprehensive)
- **Quality score**: latency(40) + anonymity(25) + access(20) + type(10) + SSL(10)
- **Background workers**: scraper (10min), validator (60s/20 batch), revalidator (24h)
- **ipquery.io**: single-call geo + proxy type + risk scoring
- **56% test coverage**, **194 tests pass**

## Strategy

The core insight: **free proxies are inherently low-quality**. You can't make a dead proxy work. But you can:
1. **Discard dead proxies faster** — stale data pollutes results
2. **Surface reliable proxies** — track history, not snapshots
3. **Validate more thoroughly** — catch proxies that pretend to work
4. **Find more sources** — volume lets you be picky

---

# PHASE 1 — Reliability & Freshness (Effort: 🟢 Low | Impact: 🔴 High)

## 1A. Stale Proxy Auto-Purge
**Problem:** Proxies live forever in the DB once validated. Free proxies churn in minutes. Endpoint returns proxies that died hours ago.

**Solution:**
- New background worker: `stale_proxy_purger`
- Deletes proxies where `last_validated < NOW - 6h` AND `is_working = False`
- Also marks proxies that were validated but haven't been rechecked in 24h as `is_working = False` (soft-stale)

```python
# In background_validator.py
async def stale_proxy_purger(stale_hours: int = 6):
    """Delete or soft-mark proxies not seen/validated in N hours."""
    async with AsyncSessionLocal() as session:
        cutoff = datetime.utcnow() - timedelta(hours=stale_hours)
        # Hard-delete failed proxies older than cutoff
        await session.execute(
            delete(Proxy).where(
                Proxy.is_working == False,
                Proxy.last_validated < cutoff
            )
        )
        # Soft-mark working-but-stale (were validated but never rechecked)
        stale_cutoff = datetime.utcnow() - timedelta(hours=24)
        await session.execute(
            update(Proxy).where(
                Proxy.is_working == True,
                Proxy.last_validated < stale_cutoff
            ).values(is_working=False)
        )
```

**Files touched:** `background_validator.py`, `lifecycle_workers.py`
**Tests:** 3 (purge dead, soft-mark stale, no-op when fresh)
**New coverage:** +3%

## 1B. Historical Reliability Scoring
**Problem:** Quality score is a single-snapshot value. A proxy that passed 10/10 checks over 24h has the same score as one that passed once.

**Solution:**
- Use `validation_failures` + `last_validated` + `ValidationHistory` count to compute reliability multiplier
- New formula: `effective_score = quality_score × reliability_factor`
- reliability_factor degrades over time since last check

```python
def _calculate_reliability_factor(self, proxy_data):
    hours_since_check = (utcnow() - proxy_data.last_validated).total_seconds() / 3600
    if hours_since_check > 24:
        return 0.3
    if hours_since_check > 6:
        return 0.6
    if hours_since_check > 1:
        return 0.85
    return 1.0
```

**Files touched:** `validator.py` (new method), `db_storage.py` (sorting)
**Tests:** 5 (fresh, 1h stale, 6h stale, 24h stale, with failures)
**New coverage:** +5%

## 1C. Source Trust Scoring
**Problem:** `SourceTrustScore` table exists but is never populated. Some sources produce garbage but are treated equally.

**Solution:**
- After each scrape, update `SourceTrustScore` per source: ratio of validated/total
- Use trust score to weight proxies from reliable sources higher (+10 bonus for 90%+ trust)
- Use trust score to auto-disable consistently bad sources (< 10% validation rate over 5 scrapes)

**Files touched:** `db_storage.py`, `background_validator.py`
**Tests:** 3 (trust update, high-trust bonus, low-trust auto-disable)

---

# PHASE 2 — Validation Quality (Effort: 🟡 Medium | Impact: 🟡 Medium)

## 2A. Multi-Endpoint Validation
**Problem:** Currently only checks httpbin, google, openai. A proxy that routes to a fake google won't be caught.

**Solution:** Add 3 more check endpoints:
- `https://api.ipify.org?format=json` — verify proxy IP matches expected (anti-fake)
- `https://ipapi.co/json/` — confirm geo consistency vs ipquery
- `http://httpbin.org/ip` — detect IP leakage (proxy should return its own IP, not client's)

```python
async def check_ip_integrity(self, proxy_url: str, expected_ip: str) -> bool:
    """Verify the proxy actually routes through the claimed IP."""
    try:
        async with self.session.get(
            "https://api.ipify.org?format=json",
            proxy=proxy_url,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("ip") == expected_ip
    except Exception:
        pass
    return False
```

Penalty: if IP integrity fails → quality_score × 0.5 (heavy penalty — proxy is lying)

**Files touched:** `validator.py`
**Tests:** 4 (IP match, IP mismatch, timeout, invalid response)
**New coverage:** +5%

## 2B. SOCKS-Specific Validation
**Problem:** SOCKS5 proxies from Tor exit nodes and SOCKS sources are validated as HTTP. Some SOCKS proxies only respond to SOCKS protocol.

**Solution:** 
- Phase 1 already tries HTTP → SOCKS fallback in some code paths, but let's make it explicit
- For sources with protocol `socks4`/`socks5`: run SOCKS-specific Phase 1 check first
- Use aiohttp SOCKS proxy support (or just try `socks5://` prefix)
- If SOCKS check succeeds but HTTP fails → still mark as working with socks4/socks5 protocol

```python
async def _check_socks_connectivity(self, proxy_url: str, protocol: str) -> bool:
    """Check if a SOCKS proxy responds to native SOCKS protocol."""
    try:
        # Try connecting through SOCKS to a known endpoint
        url = proxy_url.replace("http://", f"{protocol}://")
        async with self.session.get(
            "http://httpbin.org/ip",
            proxy=url,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            return resp.status == 200
    except Exception:
        pass
    return False
```

**Files touched:** `validator.py`, `background_validator.py` (check protocol field)
**Tests:** 3 (SOCKS5 works, SOCKS5 fails, HTTP works but SOCKS fails)
**New coverage:** +3%

## 2C. Proxy Performance History
**Problem:** `ProxyPerformanceHistory` table is defined but never written to. No latency trends, uptime tracking, or jitter data.

**Solution:**
- After each validation cycle, write to `ProxyPerformanceHistory` (latency, p50/p95, success)
- Use history to compute: jitter (variance in latency), uptime trend, reliability score
- Display in API response

```python
async def _record_performance(self, session, proxy_id, latency_ms, success):
    """Record validation result to performance history."""
    entry = ProxyPerformanceHistory(
        proxy_id=proxy_id,
        validated_at=datetime.utcnow(),
        latency_ms=latency_ms,
        success=success,
    )
    session.add(entry)
```

**Files touched:** `db_storage.py`, `validator.py`
**Tests:** 2 (record per cycle, query recent)
**New coverage:** +2%

---

# PHASE 3 — Discovery Expansion (Effort: 🟡 Medium | Impact: 🟢 High)

## 3A. Proxy-List Site Hunter Strategy
**Problem:** Only GitHub raw URLs are used as sources. Dozens of known proxy-list websites are ignored.

**Solution:** New hunter strategy targeting known proxy websites:

| Site | URL | Expected Format | Scraper |
|------|-----|----------------|---------|
| Free Proxy List | https://free-proxy-list.net/ | HTML table | WebGrabber |
| SSL Proxies | https://www.sslproxies.org/ | HTML table | WebGrabber |
| ProxyScrape | https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http | Text | GitHubGrabber |
| Spys.me | https://spys.me/proxy.txt | Text | GitHubGrabber |
| Proxy-List Download | https://www.proxy-list.download/ | HTML table | WebGrabber |
| OpenProxyList | https://openproxylist.xyz/ | Text | GitHubGrabber |
| Geonode | https://geonode.com/free-proxy-list/ | HTML table | WebGrabber |
| Proxy DB | https://proxydb.net/ | HTML table | WebGrabber |

New hunter strategy `ProxyListHunter` that:
1. Has a hardcoded list of known proxy sites (the above 8)
2. Adds each as `CandidateSource` with high confidence (known sites)
3. Uses existing `WebGrabber`/`GitHubGrabber` to test-extract from each
4. If extraction succeeds → auto-promotes to active source

**Wait** — actually these are so well-known we should just add them as pre-configured sources directly instead of going through the hunter pipeline.

**Revised approach:** Add 8 new SourceConfig entries in `sources.py`, each with appropriate type and `enabled=True`. The existing scraper will pick them up.

**Files touched:** `sources.py`
**Tests:** 1 (verify sources parse)

## 3B. Hunter: Telegram Proxy Aggregator Channels
**Problem:** Hunter TelegramStrategy only exists but extracts poorly.

**Solution:** Add known Telegram channels that post proxy lists as targets:
- `@ProxyListBot`
- `@socks5_list`
- `@HTTP_proxy_list`
- `@proxy_socks5`
- `@daily_proxy_list`
- `@live_proxy_list`

**Files touched:** `hunter/strategies/telegram.py`
**Tests:** 2 (extract from message, dedup)

---

# PHASE 4 — User-Facing Quality (Effort: 🔴 High | Impact: 🟡 Medium)

## 4A. Quality-Enriched API Response
**Problem:** API returns raw proxy data with quality_score. No guidance on reliability or freshness.

**Solution:** Enhance API response with:
- `reliability_score` (0-100): weighted by validation history + freshness
- `last_seen_hours_ago`: human-readable staleness
- `validation_count`: how many times this proxy has been checked
- Recommended use case: scraping / browsing / streaming based on score ranges

## 4B. Proxy Comparison / Ranked View 
**Problem:** Hard for users to pick the best proxy for their use case.

**Solution:** New endpoint `GET /api/v1/proxies/ranked?use_case=scraping` that:
- Filters proxies optimal for that use case
- Scraping: high anonymity + fast latency
- Browsing: any anonymity + low latency  
- Streaming: high bandwidth + low jitter
- Security: SOCKS5 + elite anonymity + no blacklist

## 4C. Admin Dashboard — Proxy Quality Metrics
**Problem:** No visibility into proxy quality trends.

**Solution:** Add admin endpoints:
- `GET /api/v1/admin/metrics/quality-trend` — daily average quality score over 30 days
- `GET /api/v1/admin/metrics/source-effectiveness` — best sources by validation rate
- `GET /api/v1/admin/metrics/staleness` — % of DB that's stale / dead

---

# Effort → Impact Matrix

| Item | Effort | Impact on Quality | Stage |
|------|--------|-------------------|-------|
| 1A. Stale proxy purge | 🟢 1-2h | 🔴 **High** — removes dead proxies immediately | **Start here** |
| 1B. Reliability scoring | 🟢 2-3h | 🔴 **High** — rewards proxies that stay alive | **Start here** |
| 1C. Source trust scoring | 🟢 1-2h | 🟡 Medium — gradual improvement over time | Phase 1C |
| 2A. Multi-endpoint val | 🟡 3-4h | 🟡 Medium — catches fake/misbehaving proxies | Phase 2A |
| 3A. New source configs | 🟢 1h | 🔴 **High** — more volume = more pickiness | Phase 1 (parallel) |
| 2B. SOCKS validation | 🟡 2-3h | 🟡 Medium — better SOCKS support | Phase 2B |
| 2C. Perf history | 🟢 1-2h | 🟡 Low-Med — foundation for future improvements | Phase 2C |
| 4A. Enriched API | 🟡 3-4h | 🟡 Medium — better UX, no quality change | Phase 4 |
| 3B. Telegram channels | 🟢 1h | 🟢 Low — marginal volume | Phase 3B |
| 4B+4C. Dashboard | 🔴 6-8h | 🟢 Low — operational visibility only | Phase 4 |

---

# Recommended Sprint Plan

## Sprint 1 (this session) — High Impact / Low Effort ⭐
1. **1A** — Stale proxy auto-purge worker (~2h)
2. **1B** — Reliability-weighted quality scoring (~3h)
3. **3A** — Add 8 new proxy sources (~1h)

## Sprint 2 (next session) — Quality Depth
4. **2A** — Multi-endpoint validation (~4h)
5. **1C** — Source trust scoring (~2h)
6. **2C** — Performance history tracking (~2h)

## Sprint 3 (future) — Polish
7. **2B** — SOCKS-specific validation (~3h)
8. **4A** — Enriched API / ranked endpoints (~4h)
9. **3B** — Telegram proxy channels (~1h)
10. **4C** — Admin quality metrics (~4h)

---

**Estimated total: ~25-30h dev time**
**Validator coverage target: 59% → 75%**
**Expected quality improvement:** Proxies served will be 2-3x more reliable (dead proxy rate drops from ~70% to ~30%)
