# 1PROXY ROUTERS (API LAYER)

**Location:** `1proxy-backend/app/routers/`  
**Focus:** API routing layer and endpoint organization.

## OVERVIEW
The modular API routing layer for 1proxy, managing endpoints for proxies, sources, authentication, and administration.

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
- **Prefixing**: Standard is `/api/v1`, except for `/auth` for OAuth flows.
- **Auth Pattern**:
  - `Depends(get_current_user)`: Optional authentication.
  - `Depends(require_user)`: Mandatory authentication.
  - `Depends(require_admin)`: Restricted to admin role.
- **DB Interaction**: Prefer `app.db_storage` repository methods over direct SQLAlchemy calls in routes.
- **Error Handling**: Use `fastapi.HTTPException` with appropriate status codes (401 for Auth, 403 for RBAC, 404 for missing resources).
- **Response Schemas**: Always define `response_model` using Pydantic classes from the same file or `app.models`.

## ROUTER DETAILS
- **`proxies.py`**: Handles `/proxies/advanced` (filtering), `/proxies/export` (txt/json/csv), and `/proxies/random`.
- **`sources.py`**: Manages `/my-sources` (user) and `/admin/sources` (admin-protected) paths.
- **`auth.py`**: Implements GitHub/Google OAuth callbacks and `/me` profile info using secure cookies.
- **`validation.py`**: Provides `/proxy` for real-time validation and `/proxy/format` for regex checks.
- **`admin.py`**: Aggregates platform-wide stats like quality distribution and recent validation history.
- **`notifications.py`**: Temporary in-memory store for user alerts (e.g., source validation results).
