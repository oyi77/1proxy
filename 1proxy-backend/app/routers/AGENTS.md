# 1PROXY ROUTERS (API LAYER)

**Location:** `1proxy-backend/app/routers/`  
**Focus:** Modular API routing layer and endpoint organization.

## OVERVIEW
Modular API routing layer managing endpoints for proxies, sources, authentication, and administration. Follows FastAPI's router pattern with strict separation of concerns.

## STRUCTURE
```
routers/
├── auth.py           # OAuth callbacks (GitHub/Google) + /me profile
├── proxies.py        # Proxy search, export, testing (539 lines)
├── sources.py        # Source CRUD operations
├── validation.py     # On-demand proxy validation
├── admin.py          # Admin stats & health checks
└── notifications.py  # In-memory user alerts
```

## WHERE TO LOOK
| Task | File |
|------|------|
| Manage OAuth & Profile | `auth.py` |
| Proxy Search & Export | `proxies.py` |
| Source CRUD Operations | `sources.py` |
| On-demand Validation | `validation.py` |
| Admin Stats & Health | `admin.py` |
| User Notifications | `notifications.py` |

## CONVENTIONS
- **Prefixing**: Standard is `/api/v1`, except `/auth` for OAuth flows
- **Auth Pattern**:
  - `Depends(get_current_user)`: Optional authentication
  - `Depends(require_user)`: Mandatory authentication
  - `Depends(require_admin)`: Restricted to admin role
- **DB Interaction**: Use `app.db_storage` repository methods, NOT direct SQLAlchemy
- **Error Handling**: Use `HTTPException` with status codes (401 auth, 403 RBAC, 404 missing)
- **Response Schemas**: Always define `response_model` using Pydantic classes

## ROUTER DETAILS
- **`proxies.py`**: `/proxies/advanced` (filtering), `/proxies/export` (txt/json/csv/pac), `/proxies/random`
- **`sources.py`**: `/my-sources` (user) and `/admin/sources` (admin-protected)
- **`auth.py`**: GitHub/Google OAuth callbacks and `/me` profile using secure cookies
- **`validation.py`**: `/proxy` for real-time validation, `/proxy/format` for regex checks
- **`admin.py`**: Platform stats (quality distribution, validation history)
- **`notifications.py`**: Temporary in-memory store for user alerts

## KNOWN ISSUES
- **Repository Pattern Violation**: `proxies.py` Line 140 uses direct `session.execute` for filter options (should be in `db_storage.py`)
- **Duplicate Code**: 
  - Lines 19-20: `limiter` defined twice
  - Lines 392-464 and 480-522: `test_proxy` block duplicated
- **Hardcoded URL**: Line 74 has `http://localhost:8000` in `getRotationUrl`
- **Post-Query Filtering**: `get_proxies_advanced` filters in Python after DB query (inefficient pagination)
- **Monolithic Exports**: PAC/CSV generation should move to `utils/exporters.py`

## ANTI-PATTERNS
- **NO** `session.execute` in routers - use `db_storage` methods
- **NO** manual filtering after pagination - push to SQLAlchemy query
- **NO** hardcoded URLs - use `app.config` or env vars
