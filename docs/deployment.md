# 1proxy Deployment Guide

This guide provides comprehensive instructions for deploying the 1proxy platform in various environments.

## 🚀 Deployment Options

### 1. Local Development (Docker Compose)
The easiest way to run 1proxy locally is using the provided Docker Compose configuration.

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/1proxy.git
cd 1proxy

# 2. Setup environment variables
cp .env.example .env
# Edit .env with your OAuth credentials (GitHub/Google)

# 3. Start services
docker-compose up -d

# 4. Access the platform
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

### 2. Production Deployment (Fly.io) - Recommended
Fly.io is recommended for the backend due to its global edge capabilities and free tier.

**Prerequisites:**
- [flyctl](https://fly.io/docs/hands-on/install-flyctl/) installed
- [Cloudflare R2](https://www.cloudflare.com/products/r2/) bucket (for Litestream backups)

**Steps:**
```bash
cd 1proxy-backend

# 1. Initialize Fly app
fly launch

# 2. Set secrets
fly secrets set   SECRET_KEY=your-secret   GITHUB_CLIENT_ID=xxx   GITHUB_CLIENT_SECRET=yyy   R2_ACCESS_KEY=aaa   R2_SECRET_KEY=bbb

# 3. Deploy
fly deploy
```

### 3. Production Deployment (Railway)
Railway is an excellent alternative for a unified deployment of both frontend and backend.

1. Connect your GitHub repository to Railway.
2. Add a **PostgreSQL** or **Redis** service if not using the self-hosted Docker defaults.
3. Configure environment variables in the Railway dashboard.
4. Deploy the `1proxy-backend` and `1proxy-frontend` services.

---

## 🔑 Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | SQLite or Postgres connection string | Yes | `sqlite+aiosqlite:///./data/1proxy.db` |
| `SECRET_KEY` | For JWT signing (min 32 chars) | Yes | - |
| `GITHUB_CLIENT_ID` | GitHub OAuth Client ID | Yes | - |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth Client Secret | Yes | - |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | Yes | - |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret | Yes | - |
| `API_URL` | Public URL of the backend API | Yes | `http://localhost:8000` |
| `FRONTEND_URL` | Public URL of the frontend | Yes | `http://localhost:3000` |

---

## 🗄️ Database Management

### Migrations
All schema changes are handled via Alembic.

```bash
# In the backend directory
alembic upgrade head
```

### Backups (Litestream)
For production SQLite deployments, Litestream is used for continuous replication to S3-compatible storage (like Cloudflare R2).

1. Configure `litestream.yml`.
2. Ensure `LITESTREAM_ENABLED=true` in your environment.

---

## 🏥 Health Checks

The backend provides a health check endpoint at `/health`.

- **Success**: Returns HTTP 200 with service stats.
- **Failure**: Returns HTTP 503 if the database is unreachable.

