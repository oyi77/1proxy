# 1proxy - Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Prerequisites
- Python 3.12 (with venv already created at `/Users/paijo/1proxy/backend-venv`)
- Node.js 18+
- SQLite (comes with Python)

### Step 1: Start the Backend

```bash
source /Users/paijo/1proxy/backend-venv/bin/activate
cd /Users/paijo/1proxy/1proxy-backend

# Run migrations (should already be done)
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

**Expected Output:**
```
✅ Admin user created/verified: admin (ID: 1)
✅ Admin sources seeded
INFO: Uvicorn running on http://0.0.0.0:8000
INFO: Application startup complete
```

Backend is now running at: **http://localhost:8000**

### Step 2: Start the Frontend

In a new terminal:

```bash
cd /Users/paijo/1proxy/1proxy-frontend
npm install  # Only needed first time
npm run dev
```

**Expected Output:**
```
  ▲ Next.js
  - Local:        http://localhost:3000
  - Environments: .env.local
```

Frontend is now running at: **http://localhost:3000**

### Step 3: Verify Everything Works

1. **Check Backend Health**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status": "healthy", "database": "connected", ...}`

2. **Check API Documentation**
   - Visit: http://localhost:8000/docs
   - See all available endpoints with Swagger UI

3. **Check Frontend**
   - Visit: http://localhost:3000
   - See the home page

### Step 4: Test OAuth (Requires Setup)

To actually test login, you need to:

1. Create GitHub OAuth App:
   - https://github.com/settings/developers
   - New OAuth App
   - Get Client ID & Secret
   - Add to `1proxy-backend/.env`

2. Create Google OAuth App:
   - https://console.cloud.google.com/apis/credentials
   - Create OAuth 2.0 Client ID
   - Get credentials
   - Add to `1proxy-backend/.env`

Then:
- Visit http://localhost:3000/login
- Click "Login with GitHub" or "Login with Google"

### Step 5: Add a Proxy Source (After Login)

1. Login via OAuth
2. Go to http://localhost:3000/dashboard
3. Click "Add New Source"
4. Enter a GitHub raw URL:
   ```
   https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt
   ```
5. Select type: "GitHub Raw"
6. Click "Add Source"
7. Source will be validated and added

---

## 📊 What You Have

### Backend (Running on 8000)
- ✅ FastAPI server with 23 endpoints
- ✅ SQLite database with 4 tables
- ✅ Admin user created automatically
- ✅ 10 proxy sources seeded
- ✅ OAuth ready (needs credentials)
- ✅ API documentation at /docs

### Frontend (Running on 3000)
- ✅ Home page with proxy list
- ✅ Login page (OAuth ready)
- ✅ User dashboard (protected)
- ✅ Add source form
- ✅ Auth context for state management

### Database
- ✅ SQLite at `1proxy-backend/data/1proxy.db`
- ✅ 4 tables: users, proxy_sources, proxies, validation_history
- ✅ Admin user: admin@1proxy.local
- ✅ 10 admin sources seeded

---

## 🔗 Quick Links

| Resource | URL |
|----------|-----|
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |
| Login Page | http://localhost:3000/login |
| Dashboard | http://localhost:3000/dashboard |
| Database | 1proxy-backend/data/1proxy.db |

---

## 📁 Key Files

- **Backend**: `/Users/paijo/1proxy/1proxy-backend/app/main.py`
- **Frontend**: `/Users/paijo/1proxy/1proxy-frontend/app/page.tsx`
- **Config (Backend)**: `/Users/paijo/1proxy/1proxy-backend/.env`
- **Config (Frontend)**: `/Users/paijo/1proxy/1proxy-frontend/.env.local`
- **Database**: `/Users/paijo/1proxy/1proxy-backend/data/1proxy.db`

---

## 🆘 Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill if needed
lsof -ti:8000 | xargs kill -9

# Activate venv again
source /Users/paijo/1proxy/backend-venv/bin/activate
```

### Frontend won't start
```bash
# Delete node_modules and reinstall
cd 1proxy-frontend
rm -rf node_modules
npm install
npm run dev
```

### Database errors
```bash
# Delete and recreate database
rm 1proxy-backend/data/*.db
cd 1proxy-backend
alembic upgrade head
```

### Can't activate venv
```bash
# Recreate venv
pyenv exec python -m venv /Users/paijo/1proxy/backend-venv
source /Users/paijo/1proxy/backend-venv/bin/activate
pip install -r 1proxy-backend/requirements.txt
```

---

## 📖 Next Steps

1. **Explore the API**
   - Visit http://localhost:8000/docs
   - Try GET /api/v1/proxies
   - Try GET /api/v1/sources

2. **Check the Database**
   ```bash
   sqlite3 1proxy-backend/data/1proxy.db
   .tables
   SELECT * FROM users;
   SELECT COUNT(*) FROM proxy_sources;
   .exit
   ```

3. **Set Up OAuth** (When ready)
    - Follow instructions in docs/deployment.md
    - Get GitHub OAuth credentials
    - Get Google OAuth credentials
    - Update .env files

4. **Read Documentation**
    - `docs/README.md` - Documentation index
    - `docs/FINAL_IMPLEMENTATION_REPORT.md`
    - `docs/MULTIUSER_ARCHITECTURE.md`
    - `docs/deployment.md`

---

## ✅ Verification Checklist

- [ ] Backend started without errors
- [ ] Admin user message appeared
- [ ] Frontend started successfully
- [ ] http://localhost:8000/health returns 200
- [ ] http://localhost:3000 loads
- [ ] http://localhost:8000/docs accessible
- [ ] Database file exists at data/1proxy.db

---

**Platform is ready to use! 🎉**

For OAuth testing, complete setup in `SETUP_GUIDE.md`
