# Quick Start Guide - 1proxy Platform

## ✅ Recommended: Start Services Manually

The PowerShell script has job persistence issues. Use these simple commands instead:

### Terminal 1: Backend
```powershell
cd 1proxy-backend
python run.py
```

**You'll see:**
```
✅ Loaded environment from: C:\Users\Snap-PC-Dev-026\1proxy\1proxy-backend\.env
🚀 Starting 1proxy Backend Server...
🌐 Server will be available at: http://localhost:8000
📚 API Documentation: http://localhost:8000/docs

INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
🔄 Background validation worker started
🔄 Background scraper started (runs every 10 minutes)
🔄 Starting automatic proxy scraping...
✅ Auto-scraping complete: 1234 scraped, 56 new proxies added
```

### Terminal 2: Frontend
```powershell
cd 1proxy-frontend
npm run dev
```

**You'll see:**
```
▲ Next.js 15.5.9
- Local:        http://localhost:3000
✓ Ready in 2.2s
```

## 🎯 Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## ⚡ What Happens Automatically

1. **Startup (t=0s)**
   - Database initialized
   - Admin user created
   - 18 proxy sources loaded

2. **First Scrape (t=10s)**
   - Automatically fetches from all sources
   - Stores proxies in database
   - Starts validation

3. **Continuous Updates (Every 10 min)**
   - Auto-scrapes new proxies
   - Validates existing proxies
   - Updates quality scores

## 🔍 Verify It's Working

```powershell
# Check backend health
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","database":"connected","proxies":1234,"sources":18,"users":1}
```

## 🛑 To Stop

- Press `Ctrl+C` in each terminal window

## 📊 Current Status

✅ Backend: Running on port 8000
✅ Auto-scraper: Every 10 minutes
✅ Validation: Every 60 seconds
✅ Database: 18 sources, 1 user
✅ Caching: SQLite (ultra-fast)

## ⚠️ Note

The `start.ps1` script has PowerShell job persistence issues. Starting services manually in separate terminals is more reliable and gives you better visibility into logs.
