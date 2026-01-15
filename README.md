# 1proxy: Community-Driven Proxy Aggregation Platform

![CI Status](https://github.com/NoeFabris/1proxy/actions/workflows/ci.yml/badge.svg)

A high-performance, multi-user proxy aggregation platform where anyone can contribute proxy sources while maintaining public access to all proxies. Built with modern async Python, Next.js, and enterprise-grade validation.


## ✨ Key Features

### For Everyone (Public Access)
- 🌐 **10+ Auto-Updated Sources** - GitHub repos refreshing daily/hourly
- 🔍 **Advanced Filtering** - By protocol, country, anonymity, quality, speed
- 📊 **Quality Scoring** - 0-100 score based on latency, anonymity, Google access
- 💾 **Export Formats** - TXT, JSON, CSV
- 🚀 **1000+ Fresh Proxies** - Updated continuously

### For Contributors (OAuth Required)
- 🔐 **GitHub/Google Login** - Secure OAuth authentication
- ➕ **Add Your Sources** - Share proxy lists with the community
- ✅ **Real-time Validation** - Instant feedback on source quality
- 📈 **Track Contributions** - Personal dashboard with stats
- 🎯 **Quality Control** - Automated validation before acceptance

### For Admins
- 🛡️ **Protected Sources** - Admin sources cannot be deleted
- 👥 **User Management** - Oversight of community contributions
- 📊 **Platform Stats** - Monitor overall proxy health

## 🚀 Quick Start

### Using Docker Compose (Recommended)
```bash
# Clone repository
git clone https://github.com/yourusername/1proxy.git
cd 1proxy

# Set up environment variables
cp .env.example .env
# Edit .env with your OAuth credentials

# Start all services
docker-compose up

# Visit the platform
open http://localhost:3000
```

### Manual Development Setup

**Backend:**
```bash
cd 1proxy-backend
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd 1proxy-frontend
npm install
npm run dev
```

## 📊 Platform Statistics

- **10 GitHub Sources** integrated (auto-updating)
- **1000-2000 Proxies** available
- **8 Validation Checks** per proxy
- **10+ Filter Options** for advanced search
- **3 Export Formats** supported

## 🔧 Technology Stack

**Backend:**
- FastAPI (Python 3.12+)
- SQLAlchemy (Async ORM)
- Alembic (Database migrations)
- OAuth (GitHub + Google)
- aiohttp (Async HTTP client)

**Frontend:**
- Next.js 15 (React)
- TypeScript
- Tailwind CSS
- Server Components

**Database:**
- SQLite (Development)
- PostgreSQL (Production ready)

**Infrastructure:**
- Docker & Docker Compose
- Redis (Caching)
- Nginx (Reverse proxy)

## 📖 Documentation

All documentation is in the [`docs/`](./docs/) folder:

- **[docs/README.md](./docs/README.md)** - Documentation index
- **[docs/FINAL_IMPLEMENTATION_REPORT.md](./docs/FINAL_IMPLEMENTATION_REPORT.md)** - Complete implementation guide
- **[docs/SDD.md](./docs/SDD.md)** - Software Design Document
- **[docs/MULTIUSER_ARCHITECTURE.md](./docs/MULTIUSER_ARCHITECTURE.md)** - Technical architecture

## 🎯 How It Works

### 1. Proxy Aggregation
```
GitHub Sources → Scraper → Validator → Database → Public API
     ↓              ↓           ↓          ↓          ↓
  10 repos    Auto-fetch   8 checks   SQLite   REST/Export
```

### 2. User Contributions
```
User Login → Add Source → Validate → Accept/Reject → Scrape → Public
    ↓            ↓           ↓            ↓           ↓         ↓
  OAuth      URL check   Test fetch   Feedback   Add proxies  Share
```

### 3. Proxy Validation
```
Proxy → Format → Connect → Anonymity → Google → GeoIP → Score → Pass/Fail
         ↓         ↓          ↓          ↓        ↓       ↓        ↓
      Regex    Latency    3 levels    Access   Country  0-100   Database
```

## 🔑 Environment Variables

Create `.env` file in root:

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./data/1proxy.db

# Auth
SECRET_KEY=your-super-secret-key-min-32-characters
GITHUB_CLIENT_ID=your_github_oauth_app_id
GITHUB_CLIENT_SECRET=your_github_oauth_secret
GOOGLE_CLIENT_ID=your_google_oauth_id
GOOGLE_CLIENT_SECRET=your_google_oauth_secret

# URLs
API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```

### Setting Up OAuth Apps

**GitHub:**
1. Visit https://github.com/settings/developers
2. Create "New OAuth App"
3. Callback URL: `http://localhost:8000/auth/github/callback`

**Google:**
1. Visit https://console.cloud.google.com/apis/credentials
2. Create "OAuth 2.0 Client ID"
3. Redirect URI: `http://localhost:8000/auth/google/callback`

## 📡 API Endpoints

### Public Endpoints (No Auth)
- `GET /api/v1/proxies/advanced` - Advanced proxy search
- `GET /api/v1/proxies/export` - Export proxies
- `GET /api/v1/sources` - List all sources
- `GET /api/v1/stats` - Platform statistics

### Authenticated Endpoints
- `GET /api/v1/my-sources` - Your sources
- `POST /api/v1/my-sources` - Add new source
- `PUT /api/v1/my-sources/:id` - Edit source
- `DELETE /api/v1/my-sources/:id` - Delete source

### OAuth Endpoints
- `GET /auth/github` - Login with GitHub
- `GET /auth/google` - Login with Google
- `GET /auth/me` - Current user info
- `POST /auth/logout` - Logout

[Full API Documentation →](./docs/MULTIUSER_ARCHITECTURE.md#api-endpoints)

## 🧪 Testing

```bash
# Backend tests
cd 1proxy-backend
pytest tests/ --cov=app

# Frontend build
cd 1proxy-frontend
npm run build
```

## 🤝 Contributing

We welcome community contributions! You can contribute in two ways:

### 1. Add Proxy Sources (No Code)
- Login with GitHub/Google
- Click "Add New Source"
- Submit your proxy list URL
- Get instant validation feedback

### 2. Code Contributions (Developers)
- Fork the repository
- Create feature branch
- Submit pull request
- See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines

## 📜 License

MIT License - See [LICENSE](./LICENSE) for details

## 🙏 Acknowledgments

- **[wzdnzd/aggregator](https://github.com/wzdnzd/aggregator)** - Original inspiration
- **[jhao104/proxy_pool](https://github.com/jhao104/proxy_pool)** - Validation logic reference (23k+ ⭐)
- **Community Contributors** - Thank you for sharing proxy sources!

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/1proxy/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/1proxy/discussions)
- **Email**: support@1proxy.io (coming soon)

---

**Built with ❤️ for the proxy community**

[Documentation](./docs/) • [Architecture](./docs/MULTIUSER_ARCHITECTURE.md) • [API Reference](./docs/SDD.md)
