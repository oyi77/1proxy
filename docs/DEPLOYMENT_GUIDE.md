# Deployment Guide - GitHub Pages + Local Backend + Cloudflare Tunnel

This is the short production runbook. The detailed operations guide lives at [`deployment.md`](./deployment.md).

## Current Production Topology

| Layer | Provider | Current URL / Setting |
|-------|----------|-----------------------|
| Frontend | GitHub Pages | `https://oyi77.is-a.dev/1proxy/` |
| Backend API | Local FastAPI + Cloudflare Tunnel | `https://1proxy-api.aitradepulse.com` |
| API docs | Local FastAPI + Cloudflare Tunnel | `https://1proxy-api.aitradepulse.com/docs` |
| Database | Local SQLite or Supabase Postgres | Set through backend `DATABASE_URL` |

## Deploy Frontend

Push to `main`. `.github/workflows/deploy-frontend.yml` builds `1proxy-frontend` with:

```yaml
NEXT_PUBLIC_BASE_PATH: /1proxy
NEXT_PUBLIC_API_URL: https://1proxy-api.aitradepulse.com
```

## Deploy Backend

The local backend runs from `1proxy-backend` and is exposed by `cf-router` as `1proxy-api.aitradepulse.com`.

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Required backend variables:

- `DATABASE_URL` - SQLite or Supabase Postgres SQLAlchemy async URL.
- `SECRET_KEY` - random JWT signing key.
- `API_URL` - `https://1proxy-api.aitradepulse.com`.
- `FRONTEND_URL` - `https://oyi77.is-a.dev/1proxy`.
- `FRONTEND_BASE_PATH` - `/1proxy`.
- `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`.
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.
- `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME` for admin role detection.

## Security Rule

Never commit real Railway tokens, Supabase JWTs, OAuth secrets, database passwords, or `.env` files. Use placeholders in docs and provider dashboards for real values.

If secrets were pasted into chat or logs, rotate them before the next production deploy.
