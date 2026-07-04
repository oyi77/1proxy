# Competitor: Rota

- **URL / Repo:** https://github.com/rota-io/rota
- **Category:** direct (self-hosted)
- **Core Value Prop:** Modern, high-performance self-hosted proxy rotation platform with web UI and analytics
- **Tech Stack:** Go (core), Next.js (UI), TimescaleDB (analytics)
- **Key Features (top 5):**
  1. Multiple rotation strategies (random, round-robin, least connections, time-based)
  2. Automatic health checking and dead proxy removal
  3. Web dashboard for pool management
  4. Sticky session support
  5. Prometheus metrics + TimescaleDB analytics
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