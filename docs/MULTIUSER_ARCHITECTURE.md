# 1proxy Platform - Multi-User Architecture Design

## Overview
Transform 1proxy into a **community-driven proxy platform** where users can contribute sources while maintaining public access to all proxies.

---

## 🎯 Key Requirements

### User Management
- ✅ **OAuth Login**: GitHub/Google authentication
- ✅ **Role System**: Admin vs Regular Users
- ✅ **Public Access**: Browse proxies without login
- ✅ **Contributor Access**: Add sources requires login

### Source Management
- ✅ **User-Owned Sources**: Users can add/edit/delete their sources
- ✅ **Admin Protection**: Admin sources cannot be deleted by anyone except admin
- ✅ **Source Validation**: Validate before accepting (check reachability, format)
- ✅ **Duplicate Prevention**: No duplicate sources across platform
- ✅ **Validation Feedback**: Clear error messages on failure

### Proxy Features
- ✅ **Public Proxy List**: All proxies viewable by everyone
- ✅ **Advanced Filtering**: Latency, anonymity, type, country, speed, quality
- ✅ **Google Access Test**: Test if proxy can access Google
- ✅ **Type Detection**: Datacenter vs Residential
- ✅ **Duplicate Prevention**: No duplicate proxies
- ✅ **Comprehensive Validation**: Multi-layer checks

---

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    oauth_provider VARCHAR(20) NOT NULL,  -- 'github' or 'google'
    oauth_id VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(100) NOT NULL,
    avatar_url TEXT,
    role VARCHAR(20) DEFAULT 'user',  -- 'admin' or 'user'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    UNIQUE(oauth_provider, oauth_id)
);
```

### Proxy Sources Table
```sql
CREATE TABLE proxy_sources (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    url TEXT NOT NULL UNIQUE,  -- Prevent duplicates
    type VARCHAR(50) NOT NULL,  -- 'github_raw', 'subscription_base64', etc.
    name VARCHAR(200),  -- User-friendly name
    description TEXT,
    is_paid BOOLEAN DEFAULT false,  -- User can mark as paid/free
    enabled BOOLEAN DEFAULT true,
    validated BOOLEAN DEFAULT false,  -- Passed initial validation
    validation_error TEXT,  -- Error message if validation failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_scraped TIMESTAMP,
    total_scraped INTEGER DEFAULT 0,
    success_rate FLOAT DEFAULT 0.0,
    is_admin_source BOOLEAN DEFAULT false  -- Protected flag
);

CREATE INDEX idx_proxy_sources_user_id ON proxy_sources(user_id);
CREATE INDEX idx_proxy_sources_enabled ON proxy_sources(enabled);
CREATE UNIQUE INDEX idx_proxy_sources_url ON proxy_sources(url);
```

### Proxies Table
```sql
CREATE TABLE proxies (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES proxy_sources(id) ON DELETE SET NULL,
    url TEXT NOT NULL UNIQUE,  -- Prevent duplicates (vmess://..., http://...)
    protocol VARCHAR(50) NOT NULL,  -- 'http', 'https', 'vmess', 'vless', etc.
    ip VARCHAR(50),
    port INTEGER,
    country_code VARCHAR(2),
    country_name VARCHAR(100),
    state VARCHAR(100),
    city VARCHAR(100),
    
    -- Performance metrics
    latency_ms INTEGER,  -- Response time
    speed_mbps FLOAT,  -- Download speed
    uptime_percent FLOAT,  -- Historical uptime
    
    -- Quality indicators
    anonymity VARCHAR(20),  -- 'transparent', 'anonymous', 'elite'
    proxy_type VARCHAR(20),  -- 'datacenter', 'residential', 'mobile'
    can_access_google BOOLEAN DEFAULT NULL,
    quality_score INTEGER,  -- 0-100 composite score
    
    -- Validation
    last_validated TIMESTAMP,
    validation_failures INTEGER DEFAULT 0,
    is_working BOOLEAN DEFAULT true,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(url)
);

CREATE INDEX idx_proxies_protocol ON proxies(protocol);
CREATE INDEX idx_proxies_country ON proxies(country_code);
CREATE INDEX idx_proxies_anonymity ON proxies(anonymity);
CREATE INDEX idx_proxies_working ON proxies(is_working);
CREATE INDEX idx_proxies_latency ON proxies(latency_ms);
CREATE INDEX idx_proxies_quality ON proxies(quality_score);
CREATE UNIQUE INDEX idx_proxies_url ON proxies(url);
```

### Validation History Table
```sql
CREATE TABLE validation_history (
    id SERIAL PRIMARY KEY,
    proxy_id INTEGER REFERENCES proxies(id) ON DELETE CASCADE,
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    latency_ms INTEGER,
    anonymity VARCHAR(20),
    can_access_google BOOLEAN,
    success BOOLEAN,
    error_message TEXT
);

CREATE INDEX idx_validation_history_proxy_id ON validation_history(proxy_id);
CREATE INDEX idx_validation_history_validated_at ON validation_history(validated_at);
```

---

## 🏗️ Reference Implementation

### **jhao104/proxy_pool** (23.1k ⭐, MIT License)
- **URL**: https://github.com/jhao104/proxy_pool
- **Why**: Industry standard, comprehensive validation, active maintenance
- **Features to Adopt**:
  1. **Multi-layer Validation** (`helper/validator.py`)
     - Format validator (IP:PORT regex)
     - HTTP/HTTPS validators with timeout
     - Anonymity detection
  2. **Scoring System** (`helper/check.py`)
     - Success rate tracking
     - Auto-disable on repeated failures
  3. **Database Design** (`db/`)
     - SSDB for high-performance storage
     - TTL-based expiration

### Key Validation Layers (from jhao104/proxy_pool)

```python
# 1. Format Validation
@ProxyValidator.addPreValidator
def formatValidator(proxy):
    return True if IP_REGEX.fullmatch(proxy) else False

# 2. HTTP Connectivity
@ProxyValidator.addHttpValidator
def httpTimeOutValidator(proxy):
    proxies = {"http": "http://{}".format(proxy)}
    try:
        r = requests.get('http://httpbin.org/ip', 
                        proxies=proxies, timeout=5, verify=False)
        return True if r.status_code == 200 else False
    except:
        return False

# 3. HTTPS Connectivity
@ProxyValidator.addHttpsValidator
def httpsTimeOutValidator(proxy):
    proxies = {"https": "https://{}".format(proxy)}
    try:
        r = requests.get('https://httpbin.org/ip', 
                        proxies=proxies, timeout=5, verify=False)
        return True if r.status_code == 200 else False
    except:
        return False
```

---

## 🔒 OAuth Implementation

### Backend (FastAPI + Authlib)

```python
# Dependencies
authlib
python-jose[cryptography]
passlib[bcrypt]

# OAuth Providers
- GitHub: https://github.com/settings/developers
- Google: https://console.cloud.google.com/apis/credentials
```

### OAuth Flow
```
1. User clicks "Login with GitHub"
2. Redirect to GitHub OAuth
3. GitHub redirects back with code
4. Exchange code for access token
5. Fetch user profile
6. Create/update user in database
7. Issue JWT token
8. Store JWT in httpOnly cookie
```

---

## 🎨 Frontend Features

### Public Pages (No Auth Required)
- `/` - Dashboard with proxy stats
- `/proxies` - Advanced proxy table with filtering/sorting
- `/sources` - View all public sources

### Authenticated Pages
- `/dashboard` - User's contribution stats
- `/my-sources` - Manage user's proxy sources
- `/my-sources/add` - Add new source form
- `/my-sources/edit/:id` - Edit source

### Admin Pages
- `/admin` - Admin dashboard
- `/admin/users` - User management
- `/admin/sources` - All sources management
- `/admin/proxies` - Proxy moderation

---

## 🛡️ Advanced Proxy Validation

### Validation Pipeline (Comprehensive)

```python
class ProxyValidator:
    async def validate_comprehensive(self, proxy_url: str) -> ValidationResult:
        results = []
        
        # Layer 1: Format & Connectivity
        results.append(await self.check_format(proxy_url))
        results.append(await self.check_connectivity(proxy_url))
        
        # Layer 2: Anonymity Level
        results.append(await self.check_anonymity(proxy_url))
        
        # Layer 3: Geographic Location
        results.append(await self.get_geolocation(proxy_url))
        
        # Layer 4: Performance
        results.append(await self.measure_latency(proxy_url))
        results.append(await self.measure_speed(proxy_url))
        
        # Layer 5: Special Tests
        results.append(await self.test_google_access(proxy_url))
        results.append(await self.detect_proxy_type(proxy_url))
        
        return self.aggregate_results(results)
```

### Anonymity Detection
```python
async def check_anonymity(self, proxy_url: str) -> str:
    """
    transparent: Proxy headers visible (X-Forwarded-For, Via)
    anonymous: No real IP leaked but proxy detected
    elite: No proxy headers, looks like regular connection
    """
    async with aiohttp.ClientSession() as session:
        async with session.get('http://httpbin.org/headers', 
                               proxy=proxy_url) as resp:
            headers = await resp.json()
            
            if 'X-Forwarded-For' in headers or 'Via' in headers:
                return 'transparent'
            elif 'Proxy-Connection' in headers:
                return 'anonymous'
            else:
                return 'elite'
```

### Proxy Type Detection (Datacenter vs Residential)
```python
async def detect_proxy_type(self, ip: str) -> str:
    """
    Use IP reputation databases:
    - IPQualityScore API
    - IP2Proxy Database
    - AbuseIPDB
    """
    # Check against known datacenter IP ranges
    datacenter_asns = [16509, 14618, 15169]  # AWS, Amazon, Google
    
    # Query IP info
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://ipinfo.io/{ip}/json') as resp:
            data = await resp.json()
            
            if data.get('org', '').startswith('AS'):
                asn = int(data['org'].split('AS')[1].split()[0])
                if asn in datacenter_asns:
                    return 'datacenter'
            
            return 'residential'  # Default assumption
```

### Google Access Test
```python
async def test_google_access(self, proxy_url: str) -> bool:
    """Test if proxy can access Google (not blocked)"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://www.google.com', 
                                   proxy=proxy_url, 
                                   timeout=10) as resp:
                return resp.status == 200
    except:
        return False
```

---

## 📋 Implementation Phases

### Phase 1: Database & Auth (Week 1)
- [ ] Set up PostgreSQL database
- [ ] Create all tables with migrations
- [ ] Implement OAuth (GitHub + Google)
- [ ] JWT token management
- [ ] User registration/login flow

### Phase 2: Source Validation (Week 1-2)
- [ ] Implement source format validator
- [ ] Add reachability check
- [ ] Duplicate detection system
- [ ] Validation error messaging
- [ ] Admin source protection

### Phase 3: Proxy Validation (Week 2)
- [ ] Adopt jhao104/proxy_pool validation logic
- [ ] Implement anonymity detection
- [ ] Add latency measurement
- [ ] Google access test
- [ ] Proxy type detection (datacenter/residential)
- [ ] Quality scoring algorithm

### Phase 4: User Features (Week 2-3)
- [ ] User dashboard
- [ ] Source management UI (add/edit/delete)
- [ ] Source validation feedback
- [ ] Contribution stats
- [ ] OAuth login buttons

### Phase 5: Advanced Proxy Table (Week 3)
- [ ] Multi-column sorting
- [ ] Advanced filtering (country, anonymity, type)
- [ ] Pagination with large datasets
- [ ] Export functionality
- [ ] Real-time stats

### Phase 6: Admin Panel (Week 3-4)
- [ ] User management
- [ ] Source moderation
- [ ] Proxy quality monitoring
- [ ] System health dashboard
- [ ] Batch operations

---

## 🔐 Security Considerations

### Authentication
- JWT tokens with short expiration (1 hour)
- Refresh token rotation
- httpOnly cookies (XSS protection)
- CSRF tokens

### Authorization
- Role-based access control (RBAC)
- Resource ownership validation
- Admin-only routes protected
- Rate limiting per user

### Data Protection
- No passwords stored (OAuth only)
- Proxy URLs sanitized
- SQL injection prevention (ORM)
- Input validation on all endpoints

---

## 🎯 Success Metrics

### User Engagement
- Target: 100+ registered users in first month
- Target: 50+ user-contributed sources
- Target: 10,000+ validated proxies

### Quality Metrics
- Target: 80%+ proxy success rate
- Target: <500ms average latency
- Target: 90%+ uptime for top proxies

### Platform Health
- Source validation: <5 seconds
- Proxy validation: <30 seconds
- API response time: <100ms
- Database queries: <50ms

---

## 📚 Technology Stack (Updated)

### Backend
- **FastAPI** - API framework
- **PostgreSQL** - Primary database
- **SQLAlchemy** - ORM
- **Alembic** - Database migrations
- **Authlib** - OAuth implementation
- **python-jose** - JWT tokens
- **aiohttp** - Async HTTP client
- **pytest** - Testing

### Frontend
- **Next.js 15** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **NextAuth.js** - OAuth client
- **React Query** - Data fetching
- **Zustand** - State management

### Infrastructure
- **Docker Compose** - Local development
- **Redis** - Caching & sessions
- **GitHub Pages** - Production frontend static hosting
- **Railway** - Production backend hosting
- **Supabase Postgres** - Production database

---

## 🚀 Next Steps

1. **Research Complete** ✅
   - Found jhao104/proxy_pool as reference
   - Designed comprehensive database schema
   - Planned OAuth integration

2. **Implemented** ✅
   - SQLAlchemy/Alembic database layer
   - OAuth with GitHub and Google
   - Proxy validation pipeline
   - User source management
   - Production deployment on GitHub Pages, Railway, and Supabase

---

This design provides a production-ready, community-driven proxy platform with enterprise-grade validation and user management!
