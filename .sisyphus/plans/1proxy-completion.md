# 1proxy Project Completion Plan

## Context

### Original Request
Complete the 1proxy codebase based on its stated goals and current progress (85% complete as per documentation).

### Interview Summary
**Research Findings** (from 6 explore/librarian agents + direct analysis):

- **Project Status**: 85% complete per `docs/README.md`
- **Backend**: Phases 1-5 complete (Foundation, Auth, Validation, Sources, Advanced Features)
- **Frontend**: Phase 6 pending (integration work)
- **Deployment**: Phase 7 pending (no CI/CD, no production config)

**Critical Issues Discovered**:
1. Notifications stored in-memory (data loss on restart)
2. Rate limiting missing on auth/source endpoints (security gap)
3. No CI/CD pipeline exists (0% automation)
4. Frontend has no tests
5. 4 files >500 lines need refactoring

**Architectural Decisions Made**:
- Background workers use `asyncio.create_task()` not Celery (per implementation)
- SQLite + Litestream for persistence (Litestream not yet configured)
- "Retro-Cyber" design system established in Tailwind

---

## Work Objectives

### Core Objective
Bring 1proxy from 85% to 100% completion by fixing critical bugs, adding CI/CD, completing frontend integration, and preparing for deployment.

### Concrete Deliverables
- Persistent notification storage (DB model)
- Rate limiting on all sensitive endpoints
- GitHub Actions CI pipeline
- Frontend test infrastructure
- User management admin endpoints
- Production-ready deployment guide

### Definition of Done
- [ ] All P0 bugs fixed and verified
- [ ] CI pipeline passes on main branch
- [ ] Frontend has basic test coverage
- [ ] `docs/deployment.md` exists with working instructions
- [ ] No in-memory data stores remain

### Must Have
- Notification persistence (DB)
- Rate limiting on auth endpoints
- GitHub Actions CI workflow
- Frontend test setup (Vitest)
- User management endpoints

### Must NOT Have (Guardrails)
- NO new features beyond completion scope
- NO major architectural changes (keep asyncio workers)
- NO database migration to Postgres (stay SQLite for now)
- NO changes to the Retro-Cyber design system
- NO implementation of Celery (use existing asyncio pattern)

---

## Verification Strategy

### Test Decision
- **Backend Infrastructure exists**: YES (pytest)
- **Frontend Infrastructure exists**: NO (needs setup)
- **User wants tests**: YES (TDD for backend, setup for frontend)
- **Framework**: Backend: pytest | Frontend: Vitest

### Backend Verification
Each backend task verified via:
```bash
cd 1proxy-backend && pytest tests/ --cov=app -m "not slow"
```

### Frontend Verification
Each frontend task verified via:
```bash
cd 1proxy-frontend && npm run lint && npm run build
```
After test setup:
```bash
cd 1proxy-frontend && npm test
```

### Manual Verification (for UI changes)
- Playwright browser automation for visual verification
- API testing via curl commands

---

## Task Flow

```
Phase 6A (Critical Fixes)
    ├── Task 1: Notification DB model
    ├── Task 2: Rate limiting (auth)
    └── Task 3: Rate limiting (sources)
              ↓
Phase 6B (CI/CD)
    └── Task 4: GitHub Actions CI
              ↓
Phase 6C (Frontend)
    ├── Task 5: Frontend test setup (Vitest)
    ├── Task 6: Missing API routes
    └── Task 7: Admin page api.ts migration
              ↓
Phase 6D (Backend Polish)
    ├── Task 8: User management endpoints
    ├── Task 9: Pagination on admin lists
    └── Task 10: Proxy deletion endpoint
              ↓
Phase 6E (Refactoring)
    └── Task 11: Split home-client.tsx
              ↓
Phase 7 (Deployment)
    ├── Task 12: Write deployment.md
    └── Task 13: Production docker-compose
```

## Parallelization

| Group | Tasks | Reason |
|-------|-------|--------|
| A | 1, 2, 3 | Independent bug fixes |
| B | 5, 6, 7 | Independent frontend tasks |
| C | 8, 9, 10 | Independent backend tasks |

| Task | Depends On | Reason |
|------|------------|--------|
| 4 | 1, 2, 3 | CI should test fixed code |
| 11 | 5 | Refactoring needs test coverage first |
| 12, 13 | All prior | Deployment docs need stable codebase |

---

## TODOs

### Phase 6A: Critical Bug Fixes

- [x] 1. Implement Notification Database Model

  **What to do**:
  - Create `Notification` SQLAlchemy model in `db_models.py`
  - Add fields: id, user_id, type, title, message, severity, created_at, read
  - Create Alembic migration for the new table
  - Update `notifications.py` router to use DB instead of in-memory dict
  - Add `NotificationStorage` methods to `db_storage.py`

  **Must NOT do**:
  - Don't change the API response format (keep backward compatible)
  - Don't add notification preferences (out of scope)

  **Parallelizable**: YES (with 2, 3)

  **References**:
  - `1proxy-backend/app/db_models.py` - Existing SQLAlchemy model patterns
  - `1proxy-backend/app/routers/notifications.py:24` - Current in-memory implementation to replace
  - `1proxy-backend/app/db_storage.py` - Repository pattern to follow
  - `1proxy-backend/alembic/versions/` - Migration pattern

  **Acceptance Criteria**:
  - [ ] `Notification` model exists in `db_models.py`
  - [ ] Migration created: `alembic revision --autogenerate -m "add notifications table"`
  - [ ] Migration applied: `alembic upgrade head`
  - [ ] Router updated to use `db_storage` methods
  - [ ] `pytest tests/ -k notification` → PASS (if tests exist)
  - [ ] Manual: Restart server, notifications persist

  **Commit**: YES
  - Message: `fix(backend): persist notifications to database instead of memory`
  - Files: `db_models.py`, `db_storage.py`, `notifications.py`, migration file
  - Pre-commit: `pytest tests/ --cov=app`

---

- [x] 2. Add Rate Limiting to Auth Endpoints

  **What to do**:
  - Import `limiter` from `main.py` into `auth.py`
  - Add `@limiter.limit()` decorator to all auth endpoints:
    - `/auth/me`: 60/minute
    - `/auth/github`, `/auth/google`: 10/minute
    - `/auth/github/callback`, `/auth/google/callback`: 20/minute
    - `/auth/logout`: 30/minute
  - Ensure proper error handling for rate limit exceeded

  **Must NOT do**:
  - Don't change auth logic, only add rate limiting
  - Don't add IP blocking (out of scope)

  **Parallelizable**: YES (with 1, 3)

  **References**:
  - `1proxy-backend/app/routers/auth.py` - Target file (currently no rate limits)
  - `1proxy-backend/app/routers/proxies.py:52` - Example of rate limiting pattern
  - `1proxy-backend/app/main.py` - Where `limiter` is defined

  **Acceptance Criteria**:
  - [ ] All 6 auth endpoints have `@limiter.limit()` decorators
  - [ ] `pytest tests/ -k auth` → PASS
  - [ ] Manual: Hit `/auth/me` >60 times in 1 min → 429 response

  **Commit**: YES
  - Message: `fix(security): add rate limiting to auth endpoints`
  - Files: `auth.py`
  - Pre-commit: `pytest tests/ --cov=app`

---

- [x] 3. Add Rate Limiting to Source Creation

  **What to do**:
  - Add rate limiting to `sources.py`:
    - `POST /my-sources`: 10/hour (prevents spam)
    - `GET /my-sources`: 60/minute
    - `PUT /my-sources/{id}`: 30/minute
    - `DELETE /my-sources/{id}`: 30/minute
  - Add SSRF protection: validate source URLs don't point to internal networks

  **Must NOT do**:
  - Don't change source validation logic
  - Don't add URL content scanning

  **Parallelizable**: YES (with 1, 2)

  **References**:
  - `1proxy-backend/app/routers/sources.py:97` - `create_source` endpoint (no rate limit)
  - `1proxy-backend/app/routers/proxies.py` - Rate limiting patterns
  - `1proxy-backend/app/source_validator.py` - Where to add SSRF check

  **Acceptance Criteria**:
  - [ ] Rate limits on all source CRUD endpoints
  - [ ] SSRF protection: reject `localhost`, `127.0.0.1`, `10.x.x.x`, `192.168.x.x`
  - [ ] `pytest tests/ -k source` → PASS
  - [ ] Manual: Create >10 sources in 1 hour → 429 response

  **Commit**: YES
  - Message: `fix(security): add rate limiting and SSRF protection to sources`
  - Files: `sources.py`, `source_validator.py`
  - Pre-commit: `pytest tests/ --cov=app`

---

### Phase 6B: CI/CD Setup

- [x] 4. Create GitHub Actions CI Workflow

  **What to do**:
  - Create `.github/workflows/ci.yml` with:
    - Backend job: Python 3.12, pytest with coverage
    - Frontend job: Node 20, lint, build
    - Trigger: push to main, pull requests
  - Add status badge to README.md
  - Create `.github/workflows/lint.yml` for PR checks

  **Must NOT do**:
  - Don't add deployment workflow yet (manual deployment for now)
  - Don't add complex matrix builds

  **Parallelizable**: NO (depends on 1, 2, 3)

  **References**:
  - `1proxy-backend/pytest.ini` - Test configuration
  - `1proxy-frontend/package.json` - npm scripts (lint, build)
  - GitHub Actions docs: https://docs.github.com/en/actions

  **Acceptance Criteria**:
  - [ ] `.github/workflows/ci.yml` exists
  - [ ] Workflow runs: Backend pytest passes
  - [ ] Workflow runs: Frontend lint + build passes
  - [ ] Badge visible in README.md
  - [ ] Manual: Push commit → CI runs and passes

  **Commit**: YES
  - Message: `ci: add GitHub Actions workflow for testing and linting`
  - Files: `.github/workflows/ci.yml`, `README.md`
  - Pre-commit: N/A (CI file)

---

### Phase 6C: Frontend Completion

- [x] 5. Setup Frontend Test Infrastructure (Vitest)

  **What to do**:
  - Install Vitest and testing-library: `npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom`
  - Create `vitest.config.ts` with jsdom environment
  - Add `test` script to `package.json`
  - Create example test: `__tests__/components/ProxyTable.test.tsx`
  - Create test setup file with global mocks

  **Must NOT do**:
  - Don't write comprehensive tests (just setup + 1 example)
  - Don't add E2E tests (Playwright setup is separate)

  **Parallelizable**: YES (with 6, 7)

  **References**:
  - `1proxy-frontend/package.json` - Add test dependencies
  - `1proxy-frontend/tsconfig.json` - TypeScript config for tests
  - Vitest docs: https://vitest.dev/guide/

  **Acceptance Criteria**:
  - [ ] `npm test` command works
  - [ ] `vitest.config.ts` exists
  - [ ] Example test file exists and passes
  - [ ] `npm test` → 1+ tests pass

  **Commit**: YES
  - Message: `test(frontend): setup Vitest testing infrastructure`
  - Files: `vitest.config.ts`, `package.json`, test files
  - Pre-commit: `npm run lint`

---

- [x] 6. Add Missing API Routes to Frontend

  **What to do**:
  - Add to `lib/api.ts`:
    - `getRandomProxy(exclude?: string[])` → `/proxies/random`
    - `deleteProxy(id: number)` → (when backend adds it)
    - `getAdminUsers()` → `/admin/users` (when backend adds it)
    - `triggerValidation(sourceId: number)` → `/validation/trigger`
  - Add proper TypeScript interfaces for responses

  **Must NOT do**:
  - Don't implement UI for these yet (just API client)
  - Don't change existing working routes

  **Parallelizable**: YES (with 5, 7)

  **References**:
  - `1proxy-frontend/lib/api.ts` - Existing API patterns
  - `1proxy-backend/app/routers/proxies.py:300` - Random proxy endpoint
  - `1proxy-backend/app/routers/admin.py` - Admin endpoints

  **Acceptance Criteria**:
  - [ ] New functions added to `api.ts`
  - [ ] TypeScript compiles without errors
  - [ ] `npm run build` → succeeds

  **Commit**: YES
  - Message: `feat(frontend): add missing API client routes`
  - Files: `lib/api.ts`
  - Pre-commit: `npm run lint && npm run build`

---

- [x] 7. Migrate Admin Page to api.ts Client

  **What to do**:
  - Refactor `app/admin/page.tsx` to use `lib/api.ts` instead of raw `fetch`
  - Replace all direct fetch calls with typed API client calls
  - Add proper error handling using the API client patterns

  **Must NOT do**:
  - Don't change the UI layout
  - Don't add new features to admin page

  **Parallelizable**: YES (with 5, 6)

  **References**:
  - `1proxy-frontend/app/admin/page.tsx` - Target file (417 lines, uses raw fetch)
  - `1proxy-frontend/lib/api.ts` - API client to use
  - `1proxy-frontend/app/home-client.tsx` - Example of api.ts usage

  **Acceptance Criteria**:
  - [ ] No raw `fetch()` calls remain in admin page
  - [ ] All API calls use `lib/api.ts` functions
  - [ ] `npm run build` → succeeds
  - [ ] Manual: Admin page works identically

  **Commit**: YES
  - Message: `refactor(frontend): migrate admin page to typed API client`
  - Files: `app/admin/page.tsx`
  - Pre-commit: `npm run lint && npm run build`

---

### Phase 6D: Backend Polish

- [x] 8. Add User Management Endpoints

  **What to do**:
  - Add to `admin.py`:
    - `GET /admin/users` - List all users (paginated)
    - `GET /admin/users/{id}` - Get user details
    - `PUT /admin/users/{id}/role` - Change user role
    - `DELETE /admin/users/{id}` - Soft-delete user
  - Add `UserStorage` methods to `db_storage.py`
  - Add rate limiting to new endpoints

  **Must NOT do**:
  - Don't add user registration (OAuth only)
  - Don't add password management

  **Parallelizable**: YES (with 9, 10)

  **References**:
  - `1proxy-backend/app/routers/admin.py` - Add endpoints here
  - `1proxy-backend/app/db_models.py:User` - User model
  - `1proxy-backend/app/db_storage.py` - Repository patterns

  **Acceptance Criteria**:
  - [ ] 4 new endpoints in `admin.py`
  - [ ] All endpoints protected by `require_admin`
  - [ ] All endpoints have rate limits
  - [ ] `pytest tests/ -k admin` → PASS
  - [ ] Manual: `curl /admin/users` → returns user list

  **Commit**: YES
  - Message: `feat(backend): add user management endpoints for admins`
  - Files: `admin.py`, `db_storage.py`
  - Pre-commit: `pytest tests/ --cov=app`

---

- [x] 9. Add Pagination to Admin Source List

  **What to do**:
  - Update `admin_get_all_sources` in `sources.py`:
    - Add `offset`, `limit` query parameters
    - Add `total` count in response
    - Default: limit=50, max limit=200
  - Update response model to include pagination metadata

  **Must NOT do**:
  - Don't change the source data structure
  - Don't add complex filtering (just pagination)

  **Parallelizable**: YES (with 8, 10)

  **References**:
  - `1proxy-backend/app/routers/sources.py:230` - Target endpoint
  - `1proxy-backend/app/routers/proxies.py:52` - Pagination example

  **Acceptance Criteria**:
  - [ ] Endpoint accepts `offset` and `limit` params
  - [ ] Response includes `total`, `offset`, `limit`
  - [ ] `pytest tests/ -k sources` → PASS
  - [ ] Manual: `curl /admin/sources?limit=10` → returns 10 items + total

  **Commit**: YES
  - Message: `feat(backend): add pagination to admin source list`
  - Files: `sources.py`
  - Pre-commit: `pytest tests/ --cov=app`

---

- [x] 10. Add Proxy Deletion Endpoint

  **What to do**:
  - Add to `proxies.py`:
    - `DELETE /proxies/{id}` - Admin-only proxy deletion
  - Add `delete_proxy` method to `db_storage.py`
  - Include cascade delete for related validation_history

  **Must NOT do**:
  - Don't add bulk deletion (single proxy only)
  - Don't add soft-delete (hard delete is fine for proxies)

  **Parallelizable**: YES (with 8, 9)

  **References**:
  - `1proxy-backend/app/routers/proxies.py` - Add endpoint here
  - `1proxy-backend/app/db_storage.py` - Add delete method
  - `1proxy-backend/app/db_models.py:Proxy` - Model with relationships

  **Acceptance Criteria**:
  - [ ] `DELETE /proxies/{id}` endpoint exists
  - [ ] Endpoint protected by `require_admin`
  - [ ] Validation history cascades on delete
  - [ ] `pytest tests/ -k proxy` → PASS
  - [ ] Manual: Delete proxy → 204 No Content

  **Commit**: YES
  - Message: `feat(backend): add admin proxy deletion endpoint`
  - Files: `proxies.py`, `db_storage.py`
  - Pre-commit: `pytest tests/ --cov=app`

---

### Phase 6E: Refactoring

- [x] 11. Split home-client.tsx into Tab Components

  **What to do**:
  - Extract from `home-client.tsx` (772 lines):
    - `components/tabs/HomeTab.tsx` - Stats and overview
    - `components/tabs/ProxiesTab.tsx` - Proxy table and filters
    - `components/tabs/SourcesTab.tsx` - Source management
  - Keep state management in parent, pass props to tabs
  - Ensure all functionality preserved

  **Must NOT do**:
  - Don't change any functionality
  - Don't change the Retro-Cyber styling
  - Don't add new features during refactor

  **Parallelizable**: NO (depends on 5 for test coverage)

  **References**:
  - `1proxy-frontend/app/home-client.tsx` - File to refactor (772 lines)
  - `1proxy-frontend/components/` - Where to add new components
  - React patterns for lifting state up

  **Acceptance Criteria**:
  - [ ] `home-client.tsx` reduced to <300 lines
  - [ ] 3 new tab components exist
  - [ ] All tests pass (if any)
  - [ ] `npm run build` → succeeds
  - [ ] Manual: All tabs work identically to before

  **Commit**: YES
  - Message: `refactor(frontend): split home-client into tab components`
  - Files: `home-client.tsx`, new component files
  - Pre-commit: `npm run lint && npm run build`

---

### Phase 7: Deployment

- [x] 12. Write Deployment Documentation

  **What to do**:
  - Create `docs/deployment.md` with:
    - Prerequisites (Docker, env vars)
    - Local development setup
    - Production deployment options (Fly.io, Railway, HuggingFace Spaces)
    - Environment variable reference
    - Database migration guide
    - SSL/HTTPS configuration
    - Health check endpoints

  **Must NOT do**:
  - Don't implement deployment automation (just docs)
  - Don't include secrets in docs

  **Parallelizable**: NO (needs stable codebase)

  **References**:
  - `docs/SDD.md` - Deployment strategy (sections 4, 5, 11)
  - `docker-compose.yml` - Current setup
  - `1proxy-backend/Dockerfile`, `1proxy-frontend/Dockerfile`

  **Acceptance Criteria**:
  - [ ] `docs/deployment.md` exists
  - [ ] Covers all deployment options from SDD
  - [ ] Environment variable table complete
  - [ ] Following the guide results in working deployment

  **Commit**: YES
  - Message: `docs: add comprehensive deployment guide`
  - Files: `docs/deployment.md`, update `docs/README.md`
  - Pre-commit: N/A (documentation)

---

- [x] 13. Create Production Docker Compose

  **What to do**:
  - Create `docker-compose.prod.yml`:
    - Use build args for `NEXT_PUBLIC_API_URL`
    - Add resource limits (CPU, memory)
    - Add restart policies
    - Configure logging
    - Add Traefik/Nginx for SSL termination (optional)
  - Create `.env.example` with all required variables

  **Must NOT do**:
  - Don't change development docker-compose.yml
  - Don't add Kubernetes configs

  **Parallelizable**: YES (with 12)

  **References**:
  - `docker-compose.yml` - Development version
  - `docs/SDD.md` - Resource constraints (section 4.2)
  - Docker Compose production best practices

  **Acceptance Criteria**:
  - [ ] `docker-compose.prod.yml` exists
  - [ ] `.env.example` documents all variables
  - [ ] `docker-compose -f docker-compose.prod.yml config` → valid
  - [ ] Manual: Production compose starts successfully

  **Commit**: YES
  - Message: `feat(infra): add production docker-compose configuration`
  - Files: `docker-compose.prod.yml`, `.env.example`
  - Pre-commit: N/A (config files)

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `fix(backend): persist notifications to database` | db_models.py, db_storage.py, notifications.py, migration | pytest |
| 2 | `fix(security): add rate limiting to auth endpoints` | auth.py | pytest |
| 3 | `fix(security): add rate limiting and SSRF protection to sources` | sources.py, source_validator.py | pytest |
| 4 | `ci: add GitHub Actions workflow` | .github/workflows/ci.yml, README.md | CI runs |
| 5 | `test(frontend): setup Vitest testing infrastructure` | vitest.config.ts, package.json | npm test |
| 6 | `feat(frontend): add missing API client routes` | lib/api.ts | npm build |
| 7 | `refactor(frontend): migrate admin page to typed API client` | app/admin/page.tsx | npm build |
| 8 | `feat(backend): add user management endpoints` | admin.py, db_storage.py | pytest |
| 9 | `feat(backend): add pagination to admin source list` | sources.py | pytest |
| 10 | `feat(backend): add admin proxy deletion endpoint` | proxies.py, db_storage.py | pytest |
| 11 | `refactor(frontend): split home-client into tab components` | home-client.tsx, components/tabs/*.tsx | npm build |
| 12 | `docs: add comprehensive deployment guide` | docs/deployment.md | N/A |
| 13 | `feat(infra): add production docker-compose` | docker-compose.prod.yml, .env.example | compose config |

---

## Success Criteria

### Verification Commands
```bash
# Backend tests
cd 1proxy-backend && pytest tests/ --cov=app -v

# Frontend build
cd 1proxy-frontend && npm run lint && npm run build && npm test

# CI workflow
gh workflow run ci.yml  # After pushing

# Docker production
docker-compose -f docker-compose.prod.yml config
```

### Final Checklist
- [ ] All P0 bugs fixed (notifications persist, rate limits active)
- [ ] CI pipeline green on main branch
- [ ] Frontend has working test command
- [ ] All 4 large files either refactored or documented
- [ ] `docs/deployment.md` enables successful deployment
- [ ] No in-memory data stores remain in production code
