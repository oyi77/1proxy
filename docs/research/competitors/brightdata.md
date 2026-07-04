# Competitor: Bright Data

- **URL / Repo:** https://brightdata.com
- **Category:** direct
- **Core Value Prop:** Enterprise-grade proxy infrastructure with 400M+ IPs (residential, datacenter, ISP, mobile), built-in unblocker, scraping browser, and Web Scraper IDE
- **Tech Stack:** Proprietary, global infrastructure, custom routing
- **Key Features (top 5):**
  1. Massive IP pool (400M+ residential, 1.6M+ datacenter)
  2. Web Unblocker - handles CAPTCHAs, fingerprints, JS rendering automatically
  3. Scraping Browser - headless Chrome with automatic unlocking
  4. Web Scraper IDE - no-code visual scraper builder
  5. Proxy Manager - open-source local proxy manager with dashboard
- **Known Weaknesses:**
  - Very expensive (enterprise pricing, ~$500+/month minimum)
  - Complex pricing model (per GB, per request, per domain)
  - Vendor lock-in, no self-hosted option
  - Free tier very limited
- **Pricing Model:** Pay-per-GB (residential ~$8-15/GB), custom enterprise contracts
- **User Traction (estimate):** 15,000+ customers, Fortune 500 companies
- **Last Major Update:** 2024 (continuous)
- **Unique Differentiator (their ⭐):** Web Unlocker + Scraping Browser combo - handles hardest targets automatically
- **What their users complain about:**
  - "Pricing is opaque and unpredictable and confusing"
  - "Support response times slow for non-enterprise"
  - "Documentation could be better for advanced features"
  - "Sometimes IPs get blocked on tough targets"

---

# Competitor: Oxylabs

- **URL / Repo:** https://oxylabs.io
- **Category:** direct
- **Core Value Prop:** Premium proxy network with 100M+ residential IPs, specialized for hard targets (e-commerce, SERP, travel)
- **Tech Stack:** Custom infrastructure, AI-powered proxy rotation
- **Key Features (top 5):**
  1. 100M+ residential proxies across 195 countries
  2. Real-time Crawler - API for SERP/e-commerce data
  3. Web Unblocker with AI-powered fingerprinting
  4. Dedicated datacenter proxies
  5. Proxy Rotator with smart session handling
- **Known Weaknesses:**
  - Very high pricing (enterprise only)
  - No self-hosted option
  - Minimum commit contracts
- **Pricing Model:** Custom enterprise pricing, per GB (~$10-15/GB residential)
- **User Traction (estimate):** 2,000+ enterprise clients
- **Last Major Update:** 2024
- **Unique Differentiator (their ⭐):** Real-time Crawler API - structured data extraction at scale
- **What their users complain about:**
  - "Expensive for small teams"
  - "Setup requires sales call"
  - "Occasional IP quality issues on specific geos"

---

# Competitor: Smartproxy

- **URL / Repo:** https://smartproxy.com
- **Category:** direct
- **Core Value Prop:** Developer-friendly proxy service with 65M+ IPs, great docs, and flexible pricing
- **Tech Stack:** Modern API, Chrome extension, proxy manager
- **Key Features (top 5):**
  1. 65M+ residential IPs, 400K+ datacenter
  2. Site Unblocker for CAPTCHA/JS handling
  3. Chrome/Firefox extensions for easy switching
  4. Proxy Manager desktop app (open source)
  5. Pay-as-you-go option
- **Known Weaknesses:**
  - Smaller pool than Bright Data/Oxylabs
  - Site Unblocker not as advanced
  - No mobile ISP proxies
- **Pricing Model:** Pay-as-you-go (~$7/GB residential), monthly plans from $50
- **User Traction (estimate):** 50,000+ users
- **Last Major Update:** 2024
- **Unique Differentiator (their ⭐):** Best developer experience - great docs, extensions, pay-as-you-go
- **What their users complain about:**
  - "Success rate lower on tough targets"
  - "Session stickiness sometimes fails"
  - "Support tier based on plan"

---

# Competitor: ScraperAPI

- **URL / Repo:** https://scraperapi.com
- **Category:** indirect (API-first scraping, not pure proxy)
- **Core Value Prop:** Simple API that handles proxies, browsers, CAPTCHAs - just send URL, get HTML
- **Tech Stack:** Managed infrastructure, headless Chrome clusters
- **Key Features (top 5):**
  1. Single API call - handles rotation, rendering, CAPTCHAs
  2. JavaScript rendering (headless Chrome)
  3. Automatic retries and geo-targeting
  4. Structured data extraction (JSON)
  5. Async scraping for large jobs
- **Known Weaknesses:**
  - Not a raw proxy provider - less control
  - Latency higher due to full rendering
  - Pricing per successful request
- **Pricing Model:** Per successful request ($29-299/month plans)
- **User Traction (estimate):** 10,000+ developers
- **Last Major Update:** 2024
- **Unique Differentiator (their ⭐):** Simplest API - "send URL, get data" no proxy management
- **What their users complain about:**
  - "Slow for simple requests"
  - "Expensive at scale"
  - "Limited control over request details"

---

# Competitor: Rota (Open Source)

- **URL / Repo:** https://github.com/rota-io/rota
- **Category:** direct (self-hosted)
- **Core Value Prop:** Modern, high-performance self-hosted proxy rotation platform with web UI and analytics
- **Tech Stack:** Go (core), Next.js (UI), TimescaleDB (analytics)
- **Key Features (top 5):**
  1. Multiple rotation strategies (random, round-robin, least connections, time-based)
  2. Automatic health checking and dead proxy removal
  3. Web dashboard for pool management
  4. Sticky session support
  4. Prometheus metrics + TimescaleDB analytics
- **Known Weaknesses:**
  - Must bring your own proxies (no IP pool included)
  - Newer project, smaller community
  - Requires TimescaleDB (heavy dependency)
- **Pricing Model:** Free (open source), infrastructure costs only
- **User Traction (estimate):** ~500 GitHub stars, early adopters
- **Last Major Update:** 2024
- **Unique Differentiator (their ⭐):** Full-featured web UI + analytics in self-hosted package
- **What their users complain about:**
  - "Setup complexity with TimescaleDB"
  - "Limited documentation for advanced features"
  - "No built-in proxy sourcing"

---

# Competitor: Mubeng (Open Source)

- **URL / Repo:** https://github.com/kitabisa/mubeng
- **Category:** direct (self-hosted CLI tool)
- **Core Value Prop:** Ultra-fast proxy checker and rotator, single binary, no dependencies
- **Tech Stack:** Go, CLI only
- **Key Features (top 5):**
  1. Extremely fast proxy checking (thousands/second)
  2. Multiple output formats (JSON, txt, proxy list)
  3. Rotation via local proxy server
  4. Supports HTTP, SOCKS4, SOCKS5
  5. Zero config, single binary
- **Known Weaknesses:**
  - No web UI
  - No persistent storage / analytics
  - No sticky sessions
  - CLI only - not a service
- **Pricing Model:** Free (open source)
- **User Traction (estimate):** ~2,000 GitHub stars
- **Last Major Update:** 2023
- **Unique Differentiator (their ⭐):** Simplicity and speed - "just works" for basic rotation
- **What their users complain about:**
  - "No dashboard"
  - "No health check scheduling"
  - "Manual proxy list management"

---

# Competitor: Magpie (Open Source)

- **URL / Repo:** https://github.com/Kuucheen/magpie
- **Category:** direct (self-hosted)
- **Core Value Prop:** Multi-user AIO proxy manager with web dashboard
- **Tech Stack:** Go, Vue.js
- **Key Features (top 5):**
  1. Multi-user support with auth
  2. Web dashboard for proxy management
  3. Proxy validation and scoring
  4. Subscription management (import from URLs)
  5. API for integration
- **Known Weaknesses:**
  - Less active development
  - Limited rotation strategies
  - Smaller community
- **Pricing Model:** Free (open source)
- **User Traction (estimate):** ~800 GitHub stars
- **Last Major Update:** 2023
- **Unique Differentiator (their ⭐):** Multi-user support with auth built-in
- **What their users complain about:**
  - "Development stalled"
  - "Bugs in proxy validation"
  - "Limited docs"

---

# Competitor: Resin (Open Source)

- **URL / Repo:** https://github.com/Resinat/Resin
- **Category:** direct (self-hosted)
- **Core Value Prop:** High-performance Go proxy pool gateway with sticky sessions
- **Tech Stack:** Go
- **Key Features (top 5):**
  1. High throughput proxy gateway
  2. Sticky session support
  2. Subscription-based proxy source management
  3. Health checks
  4. Lightweight, single binary
- **Known Weaknesses:**
  - No web UI
  - Limited documentation
  - Early stage
- **Pricing Model:** Free (open source)
- **User Traction (estimate):** ~300 GitHub stars
- **Last Major Update:** 2024
- **Unique Differentiator (their ⭐):** Performance-focused Go gateway with sticky sessions
- **What their users complain about:**
  - "No management UI"
  - "Hard to configure"
  - "Minimal docs"