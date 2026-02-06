# Deployment Fix

## Problem

Current Dockerfile runs:
```dockerfile
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

**Issue**: When this command runs:
1. Environment variables from `docker-compose.yml` may not be loaded yet
2. `alembic upgrade head` detects database type from URL
3. If `DATABASE_URL` is not set, defaults to SQLite
4. Dev with SQLite: ✅ Works
5. Prod with PostgreSQL: ❌ Migration runs on wrong DB (SQLite), creating schema mismatch

## Solution Options

### Option 1: Pass DATABASE_URL in docker-compose.yml (Recommended)

Add to `docker-compose.yml` backend service:
```yaml
services:
  backend:
    environment:
      - DATABASE_URL=${DATABASE_URL:-sqlite+aiosqlite:///./data/1proxy.db}
      - PYTHONUNBUFFERED=1
      - REDIS_URL=redis://redis:6379
```

**Pros**:
- Simple, explicit configuration
- Works for both dev (defaults to SQLite) and prod (set DATABASE_URL)
- No Dockerfile changes needed

**Cons**:
- Requires DATABASE_URL to be set in `.env` for production
- All developers need to know about `.env` for prod deployments

### Option 2: Create proper startup script

Replace Dockerfile CMD with:
```dockerfile
CMD ["/app/docker-entrypoint.sh"]
```

Create `1proxy-backend/docker-entrypoint.sh`:
```bash
#!/bin/sh
set -e

# Load .env if exists
if [ -f /app/.env ]; then
    export $(cat /app/.env | grep -v '^#' | xargs)
fi

# Run migrations
alembic upgrade head

# Start application
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Pros**:
- Always loads .env before migrations
- Works regardless of how DATABASE_URL is set
- Explicit environment loading

**Cons**:
- More files to maintain
- Entrypoint complexity

### Option 3: App-managed migrations

Add lifespan event handler in `app/main.py`:
```python
from alembic.config import main as alembic_main
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Run migrations here
    await alembic_main(['upgrade', 'head'])

app = FastAPI(lifespan=lifespan(app))
```

**Pros**:
- Migrations run by the app itself
- Access to app config and environment
- No shell script issues

**Cons**:
- Requires code changes
- More complex setup

## Recommendation

**Use Option 1** - Pass DATABASE_URL explicitly in docker-compose.yml for production. This is the simplest approach that makes the configuration explicit and works in all environments.
