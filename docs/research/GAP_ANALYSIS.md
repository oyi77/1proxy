# Gap Analysis — 1proxy

**Classification:**
- **P0** — Competitor has it, we don't. Blocker to being competitive. Fix first.
- **P1** — We have it but competitor does it better. Fix to surpass.
- **P2** — Nobody has it. First-mover opportunity. Reserve 20% capacity.

---

## P0 Gaps (Must Fix)

| GAP-ID | Feature | Competitor(s) | Impact | Effort | Status |
|--------|---------|---------------|--------|--------|--------|
| GAP-001 | CAPTCHA solving / anti-bot bypass | Bright Data, Oxylabs, ScraperAPI | Critical - blocks hardest targets | XL | ❌ Open |
| GAP-002 | JavaScript rendering (headless) | Bright Data, Oxylabs, ScraperAPI | Critical - modern sites need JS | XL | ❌ Open |
| GAP-003 | Browser fingerprint spoofing | Bright Data, Oxylabs, ScraperAPI | High - detection avoidance | L | ❌ Open |
| GAP-004 | City/ASN level geo-targeting | Bright Data, Oxylabs, Smartproxy | High - precise targeting needed | M | ❌ Open |
| GAP-005 | ISP/Org-based routing | Bright Data, Oxylabs, Smartproxy | Medium - enterprise feature | M | ❌ Open |
| GAP-006 | GraphQL API | None directly | Low - modern API expectation | L | ❌ Open |
| GAP-007 | Webhooks for proxy events | Bright Data, Oxylabs, ScraperAPI | Medium - integration need | M | ❌ Open |
| GAP-008 | Built-in proxy pool (residential) | All SaaS competitors | Critical - core value prop | XL | ❌ Open |

---

## P1 Gaps (Surpass, Don't Just Match)

| GAP-ID | Feature | Current State | Competitor Better | Surpass Idea | Effort | Status |
|--------|---------|---------------|-------------------|--------------|--------|--------|
| GAP-101 | Rotation strategies | Basic round-robin | Bright Data, Rota have 4+ strategies | Add ML-based adaptive rotation | M | ❌ Open |
| GAP-102 | Analytics depth | Basic metrics | Bright Data has TimescaleDB + custom dashboards | Real-time + historical with custom queries | M | ❌ Open |
| GAP-103 | Health check scheduling | Fixed intervals | Bright Data has smart scheduling | Predictive health (ML-based failure prediction) | L | ❌ Open |
| GAP-104 | Multi-user RBAC | Basic admin/user | Bright Data, Oxylabs have granular perms | Resource-level permissions (per-source, per-pool) | M | ❌ Open |
| GAP-105 | Proxy list export | txt/json/csv | All have similar | Add: PAC file, Proxy Auto-Config, Sing-box/Clash configs | S | ❌ Open |
| GAP-105 | Source management UI | Admin-only | Magpie has subscription UI | User-facing source subscription marketplace | M | ❌ Open |
| GAP-106 | Mobile/ISP proxies | Metadata only | Bright Data, Oxylabs offer mobile IPs | Partner integration for mobile ISP pool | XL | ❌ Open |
| GAP-107 | Real-time unblocker | None | Bright Data Web Unlocker | Lightweight challenge solver for common CAPTCHAs | XL | ❌ Open |

---

## P2 Gaps (First-Mover Moats)

| GAP-ID | Feature | Why Unique | Effort | Status |
|--------|---------|------------|--------|--------|
| GAP-201 | **Priority Tier Auto-Routing** | Route requests to Tier 1 first, cascade down on failure - nobody does this | M | ✅ **Done** (implemented in priority_tier_worker) |
| GAP-202 | **Validation Status Pipeline** | pending→validated/failed with auto-retry - full lifecycle | M | ✅ **Done** |
| GAP-203 | **Background Scraper** | Auto-discovers free proxies from GitHub/raw sources on schedule | M | ✅ **Done** |
| GAP-204 | **Quality Score + Tier + ISP/Org** | Rich per-proxy metadata for intelligent routing | M | ✅ **Done** |
| GAP-205 | **Source Registry + Auto-seed** | Declarative sources with admin auto-seeding | S | ✅ **Done** |
| GAP-206 | **AI-Powered Proxy Scoring** | ML model predicting success rate per target domain | L | 🔍 Research |
| GAP-207 | **Cost-Aware Routing** | Route to cheapest working proxy per domain | M | 🔍 Research |
| GAP-208 | **Plugin Architecture** | Custom rotation/health/validation plugins | L | 🔍 Research |
| GAP-209 | **Proxy Marketplace Integration** | One-click buy from Webshare/Decodo/etc. | L | 🔍 Research |
| GAP-210 | **Audit Trail / Compliance** | SOC2-ready logging for enterprise | M | 🔍 Research |

---

## Closed Gaps (This Session)

| GAP-ID | Feature | Commit |
|--------|---------|--------|
| GAP-FIX-001 | SQLite migration crash (ALTER COLUMN) | c205656 |
| GAP-FIX-002 | SQLite WAL mode for concurrency | 3d51339 |
| GAP-FIX-003 | Staggered worker startup | 3d51339 |
| GAP-FIX-004 | batch_alter_table consistency across migrations | 3d51339 |

---

## Next Sprint Priority (Top 3)

1. **GAP-105** - Export formats (PAC, Sing-box, Clash) - Low effort, high user value
2. **GAP-101** - Multiple rotation strategies - Core differentiator, medium effort
3. **GAP-206** - AI-powered proxy scoring research - Start P2 moat research

---

## "Switch Test" — What Would Make a Competitor User Switch to 1proxy RIGHT NOW?

> **For self-hosted users (Rota/Magpie/Mubeng):**
> - ✅ OAuth + RBAC built-in (they don't have)
> - ✅ Background auto-scraper (they don't have)
> - ✅ Priority tier auto-routing (they don't have)
> - ✅ Better web UI with dark mode

> **For SaaS users (Bright Data/Oxylabs/Smartproxy):**
> - 💰 **Zero marginal cost** - self-hosted, no per-GB fees
> - 🔒 **Full data sovereignty - your data, your infra
> - ⚡ Priority tier routing (unique)
> - 🤖 Background free proxy discovery (unique)
> - 🛠️ Extensible (open source)

**Missing for SaaS switchers:** CAPTCHA/JS rendering, residential IP pool, city-level geo