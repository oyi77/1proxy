# Deployment Guide - GitHub Pages + Railway + Supabase

This is the short production runbook. The detailed operations guide lives at [`deployment.md`](./deployment.md).

## Current Production Topology

| Layer | Provider | Current URL / Setting |
|-------|----------|-----------------------|
| Frontend | GitHub Pages | `https://oyi77.is-a.dev/1proxy/` |
| Backend API | Railway | `https://helpful-alignment-production-2ae5.up.railway.app` |
| API docs | Railway | `https://helpful-alignment-production-2ae5.up.railway.app/docs` |
| Database | Supabase Postgres | Set through Railway `DATABASE_URL` |

## Deploy Frontend

Push to `main`. `.github/workflows/deploy-frontend.yml` builds `1proxy-frontend` with:

```yaml
NEXT_PUBLIC_BASE_PATH: /1proxy
NEXT_PUBLIC_API_URL: https://helpful-alignment-production-2ae5.up.railway.app
```

## Deploy Backend

Railway uses `railway.json` and `1proxy-backend/Dockerfile.railway`. The container command runs:

```bash
alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Required Railway variables:

- `DATABASE_URL` - Supabase Postgres SQLAlchemy async URL.
- `SECRET_KEY` - random JWT signing key.
- `API_URL` - Railway backend public URL.
- `FRONTEND_URL` - `https://oyi77.is-a.dev/1proxy`.
- `FRONTEND_BASE_PATH` - `/1proxy`.
- `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`.
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.
- `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME` for admin role detection.

## Security Rule

Never commit real Railway tokens, Supabase JWTs, OAuth secrets, database passwords, or `.env` files. Use placeholders in docs and provider dashboards for real values.

If secrets were pasted into chat or logs, rotate them before the next production deploy.
