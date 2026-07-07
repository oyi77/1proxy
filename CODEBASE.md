# CODEBASE.md — 1proxy
> Auto-generated codebase memory for AI agents. Last updated: 2026-06-19.

## Purpose
Community-driven proxy aggregation platform that scrapes, validates, and serves free proxies from 10+ GitHub sources. Features real-time validation, quality scoring (0-100), multi-protocol support, and OAuth-based contributor submissions.

## Tech Stack
- **Backend**: Python (FastAPI, SQLAlchemy async, Pydantic v2, aiohttp, BeautifulSoup4)
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS
- **Database**: SQLite (dev) / Supabase PostgreSQL (prod), Alembic migrations
- **Deployment**: GitHub Pages (frontend), Railway/Cloudflare Tunnel (backend)

## Entry Points
- **Backend API**: `1proxy-backend/app/main.py` — FastAPI application
- **Backend runner**: `1proxy-backend/run.py` — Uvicorn launcher
- **Frontend**: `1proxy-frontend/` — Next.js app
- **Start scripts**: `start.sh` (Linux), `start.ps1` (Windows)

## Directory Structure
```
1proxy-backend/         Python FastAPI backend
  app/                  Application code (main.py, routes, models)
  tests/                Pytest test suite
  alembic/              Database migration scripts
  scripts/              Utility scripts
  requirements.txt      Python dependencies
  Dockerfile.railway    Railway deployment Dockerfile
1proxy-frontend/        Next.js 15 frontend
  lib/                  Shared libraries
  public/               Static assets
  scripts/              Frontend build scripts
  package.json          Node.js dependencies
skills/                 Agent skill definitions
docs/                   Documentation (deployment, SDD, LLM context)
  LLM_CONTEXT.md        Machine-readable AI assistant context
  SDD.md                Software Design Document
  DEPLOYMENT_GUIDE.md   Deployment runbook
.github/workflows/      CI/CD (frontend deploy)
```

## Key Files
| File | Purpose |
|------|---------|
| `1proxy-backend/app/main.py` | FastAPI app with all API routes |
| `1proxy-backend/run.py` | Uvicorn server launcher |
| `1proxy-backend/requirements.txt` | Python dependencies |
| `1proxy-backend/alembic/` | Database migrations |
| `1proxy-frontend/package.json` | Frontend dependencies |
| `docker-compose.yml` | Docker deployment |
| `.env.example` | Environment variable template |
| `start.sh` | One-command startup script |

## Architecture
```
GitHub Proxy Sources → Scraper → Validator (aiohttp)
  → Quality Score (latency, anonymity, Google access)
    → Database (SQLite/PostgreSQL via SQLAlchemy async)
      → FastAPI REST API (:8000)
        → Next.js Frontend (GitHub Pages)
        → Contributors (OAuth: GitHub/Google)
        → Export (TXT, JSON, CSV)
```
Background scheduler triggers periodic scraping. OAuth-gated contributor submissions with real-time validation. Alembic handles schema migrations.

## Run Commands
```bash
# Backend
cd 1proxy-backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload    # http://localhost:8000

# Frontend
cd 1proxy-frontend
npm install
npm run dev                       # http://localhost:3000

# Docker (full stack)
docker-compose up -d

# API docs
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

## Environment Variables
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Database connection string (default: SQLite) |
| `SECRET_KEY` | Application secret key (openssl rand -hex 32) |
| `GITHUB_CLIENT_ID` | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth client secret |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `GITHUB_REPO_OWNER` | Admin access control repo owner |
| `GITHUB_REPO_NAME` | Admin access control repo name |
| `FRONTEND_URL` | Frontend public URL |
| `API_URL` | Backend API public URL |
| `FRONTEND_BASE_PATH` | Frontend subpath for GitHub Pages |
