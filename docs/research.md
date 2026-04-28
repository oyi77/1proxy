# Reliability and Source Quality Research

Date: 2026-04-28

## Database Dormancy

Evidence from SQLAlchemy and FastAPI patterns supports a layered approach:

- Keep `pool_pre_ping=True` and `pool_recycle` for PostgreSQL pools so stale checked-out connections are recycled before use.
- Add a lightweight periodic `SELECT 1` worker for idle deployments where the application or database can pause.
- Dispose the async engine on shutdown with `await engine.dispose()` so pooled async connections close cleanly during container restarts.

## Proxy Source Reliability

Open-source proxy aggregators commonly track per-source health: last poll time, consecutive failures, status code, proxy count, and success ratio. For 1proxy, the immediate low-risk improvement is to update existing source fields after each scrape:

- `last_scraped` records scrape time.
- `validated` reflects whether extraction found proxies.
- `validation_error` records no-proxy, missing-file, oversized-content, or other source errors.
- `success_rate` records new-proxy yield for visible source quality.

## Source List Expansion

Additional public fallback source candidates were selected from maintained GitHub raw feeds:

- `Thordata/awesome-free-proxy-list`
- `theriturajps/proxy-list`
- `vmheaven/VMHeaven-Free-Proxy-Updated`

Free proxies remain untrusted and must continue through the existing validation pipeline before being served.

## Premium Source UX

The backend already supports `is_paid` on user sources. The missing layer was discoverability: dashboard menu choices, `?premium=true` prefill, and table badges.
