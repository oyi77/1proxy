# Deployment Guide

Current production topology:

- **Frontend:** GitHub Pages static export at `https://oyi77.is-a.dev/1proxy/`.
- **Backend:** Local FastAPI service exposed through Cloudflare Tunnel at `https://1proxy-api.aitradepulse.com`.
- **Database:** Local SQLite by default, or Supabase Postgres through `DATABASE_URL`.

Do not commit real tokens, OAuth secrets, Supabase service-role keys, or Cloudflare tokens. Store them only in local `.env` files or provider secret managers.

## Architecture

```mermaid
graph LR
    GH[GitHub main branch] --> GA[GitHub Actions]
    GA --> GP[GitHub Pages frontend]
    LOCAL[Local FastAPI backend] --> CF[Cloudflare Tunnel]
    LOCAL --> DB[(SQLite or Supabase Postgres)]
    GP -->|NEXT_PUBLIC_API_URL| CF
```

## Frontend: GitHub Pages

The frontend is deployed by `.github/workflows/deploy-frontend.yml`.

Required build-time environment:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_BASE_PATH` | `/1proxy` |
| `NEXT_PUBLIC_API_URL` | `https://1proxy-api.aitradepulse.com` |

Manual verification build:

```bash
cd 1proxy-frontend
NEXT_PUBLIC_BASE_PATH=/1proxy \
NEXT_PUBLIC_API_URL=https://1proxy-api.aitradepulse.com \
npm run build:clean
```

## Backend: Local FastAPI + Cloudflare Tunnel

Run the backend locally on port `8000`, then route `1proxy-api.aitradepulse.com` to port `8000` through `~/.cloudflare-router`.

Set these backend variables:

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_URL` | SQLite or Supabase Postgres async connection | `sqlite+aiosqlite:///./data/1proxy.db` |
| `SECRET_KEY` | JWT signing key | output of `openssl rand -hex 32` |
| `API_URL` | Public backend URL | `https://1proxy-api.aitradepulse.com` |
| `FRONTEND_URL` | Public frontend origin/path | `https://oyi77.is-a.dev/1proxy` |
| `FRONTEND_BASE_PATH` | Frontend subpath for redirects | `/1proxy` |
| `GITHUB_CLIENT_ID` | GitHub OAuth app client ID | provider value |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth app client secret | provider secret |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | provider value |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | provider secret |
| `GITHUB_REPO_OWNER` | Admin access repository owner | `oyi77` |
| `GITHUB_REPO_NAME` | Admin access repository name | `1proxy` |

Optional:

| Variable | Purpose |
|----------|---------|
| `REDIS_URL` | Redis URL if a Railway Redis service is attached |

Set `API_URL` explicitly for OAuth callbacks.

## Database: Supabase Postgres

Use the Supabase **connection string**, not the Supabase anon JWT or service-role JWT, for SQLAlchemy/Alembic.

Recommended production pattern:

1. In Supabase, copy a Postgres connection string for the project.
2. Convert it to SQLAlchemy async format if needed:
   - `postgres://...` -> `postgresql+asyncpg://...`
   - `postgresql://...` -> `postgresql+asyncpg://...`
3. Store it as Railway `DATABASE_URL`.
4. Run `alembic upgrade head` before starting Uvicorn.

Keep Supabase service-role JWTs out of the frontend and out of the repository. The current app does not need Supabase REST keys; it uses Postgres via SQLAlchemy.

## OAuth Callback URLs

Configure provider callbacks to the backend domain:

| Provider | Callback URL |
|----------|--------------|
| GitHub | `https://1proxy-api.aitradepulse.com/auth/github/callback` |
| Google | `https://1proxy-api.aitradepulse.com/auth/google/callback` |

After successful login, backend redirects to `FRONTEND_URL` plus `FRONTEND_BASE_PATH`-aware routes.

## Local Development

```bash
cp .env.example .env
cp 1proxy-backend/.env.example 1proxy-backend/.env

cd 1proxy-backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

```bash
cd 1proxy-frontend
npm install
npm run dev
```

## Secret Rotation Checklist

Rotate credentials immediately if they are posted in chat, logs, screenshots, issues, or commits:

1. Railway account/project token.
2. Supabase service-role JWT and database password.
3. GitHub OAuth client secret.
4. Google OAuth client secret.
5. Backend `SECRET_KEY` if exposed.

Then update Railway variables and redeploy.
