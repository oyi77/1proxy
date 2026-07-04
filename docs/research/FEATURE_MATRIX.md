# Feature Matrix — 1proxy vs Competitors

**Status symbols:** ✅ Fully implemented | 🚧 Partial/WIP | ❌ Missing | ⭐ Best-in-class | 🔍 Not researched

| Feature Category | Feature | 1proxy | Bright Data | Oxylabs | Smartproxy | ScraperAPI | Rota | Mubeng | Magpie | Resin |
|------------------|---------|--------|-------------|---------|------------|------------|------|--------|--------|-------|
| **Deployment** | Self-hosted (Docker) | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| | Managed SaaS | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| | Open Source | ✅ | ❌ | ❌ | ❌ (mgr only) | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Proxy Pool** | Built-in IP pool | ❌ | ✅ (400M+) | ✅ (100M+) | ✅ (65M+) | ✅ (managed) | ❌ | ❌ | ❌ | ❌ |
| | Bring your own proxies | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| | Free proxy scraping | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| | Subscription import | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| **Rotation** | Per-request rotation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| | Sticky sessions | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| | Multiple strategies | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| | Weighted/least-conn | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Health Checks** | Automated validation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| | Scheduled re-validation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Latency scoring | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| | Auto-remove dead | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Anti-Bot** | CAPTCHA handling | ❌ | ⭐ | ⭐ | 🚧 | ⭐ | ❌ | ❌ | ❌ | ❌ |
| | JS rendering | ❌ | ⭐ | ⭐ | ❌ | ⭐ | ❌ | ❌ | ❌ | ❌ |
| | Fingerprint spoofing | ❌ | ⭐ | ⭐ | ❌ | ⭐ | ❌ | ❌ | ❌ | ❌ |
| **Geo/Targeting** | Country targeting | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| | City/ASN targeting | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| | ISP/Org metadata | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Auth & Users** | Multi-user support | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| | OAuth (GitHub/Google) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| | Role-based access | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| | API keys / tokens | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **UI/UX** | Web dashboard | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| | Real-time metrics | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| | Historical analytics | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| | Dark mode | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **API** | REST API | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| | GraphQL | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| | Webhooks | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| | OpenAPI spec | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Export** | Proxy list (txt/json/csv) | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| | Config formats | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| **Observability** | Prometheus metrics | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| | Health endpoint | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| | Structured logging | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| **Protocols** | HTTP/HTTPS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| | SOCKS4/5 | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Advanced** | Priority tiers | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| | Quality scoring | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | 🚧 | ❌ |
| | Validation status tracking | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | 🚧 | ❌ |
| | Background scraping | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| | Source management | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

---

## 1proxy Unique Differentiators (⭐)

| Feature | Why It's ⭐ |
|---------|------------|
| **Priority Tiers** | Automatic quality-based tiering (1-4) with revalidation scheduling - no competitor has this |
| **Background Scraper** | Auto-discovers & scrapes proxies from GitHub/raw sources on schedule - fully automated |
| **Validation Status Pipeline** | pending → validated/failed with auto-retry for failed - complete lifecycle |
| **Multi-user OAuth + Self-hosted** | Only self-hosted with full OAuth (GitHub/Google) + RBAC |
| **Source Registry** | Declarative source configs with auto-seeding for admin |
| **Quality Score + Tier + ISP/Org** | Rich metadata per proxy for intelligent routing |