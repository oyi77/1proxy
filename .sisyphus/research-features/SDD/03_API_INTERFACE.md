# API INTERFACE SPECIFICATION

**Module:** Hunter / API  
**Focus:** Admin Control & Automation

---

## 1. ADMIN ENDPOINTS (`app/routers/admin.py`)

New endpoints protected by `Depends(require_admin)`.

### 1.1. List Candidates
- **GET** `/api/v1/admin/candidates`
- **Params:** `status` (pending/all), `limit`, `offset`.
- **Response:** List of `CandidateSource` objects with metadata.

### 1.2. Approve Candidate
- **POST** `/api/v1/admin/candidates/{id}/approve`
- **Action:**
  1.  Create new `Source` row from candidate URL.
  2.  Set Candidate status to `approved`.
  3.  Trigger immediate scrape of the new Source.
- **Response:** The created `Source` object.

### 1.3. Trigger Hunt
- **POST** `/api/v1/admin/hunter/trigger`
- **Params:** `strategy` (github/ai/search/all).
- **Action:** Manually trigger a background hunt task.
- **Response:** Task ID or status message.

---

## 2. AUTOMATION SCHEDULER

### 2.1. Startup Task (`app/main.py`)
- On startup, `asyncio.create_task(hunter_scheduler_loop())`.

### 2.2. Schedule
- **Cycle:** Every 6 hours (configurable via env `HUNTER_INTERVAL_HOURS`).
- **Logic:**
  1.  Check if previous hunt is running.
  2.  If not, launch `HunterService.run_all_strategies()`.
  3.  Wait `HUNTER_INTERVAL_HOURS`.
