# Infrastructure Setup Guide

This document describes the infrastructure requirements and setup for deploying the 1proxy platform.

## Overview

1proxy is a distributed proxy aggregation platform consisting of:
- **Backend**: FastAPI async service (Python 3.12+)
- **Frontend**: Next.js 15 application (React + TypeScript)
- **Database**: SQLite (development) / PostgreSQL (production)
- **Cache**: Redis 7 for session storage and caching

## Minimum Requirements

### Development
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 10 GB
- **Network**: 10 Mbps

### Production
- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Storage**: 50+ GB SSD
- **Network**: 100 Mbps

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Load Balancer (Optional)                   │
│                              (Nginx/Traefik)                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │   Backend   │ │  Frontend   │ │    Redis    │
            │  (FastAPI)  │ │   (Next.js) │ │   (Cache)   │
            └─────────────┘ └─────────────┘ └─────────────┘
                    │
                    ▼
            ┌─────────────┐
            │  Database   │
            │(SQLite/PG)  │
            └─────────────┘
```

## Environment Setup

### 1. Clone Repository
```bash
git clone https://github.com/oyi77/1proxy.git
cd 1proxy
```

### 2. Backend Setup
```bash
cd 1proxy-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration
```

### 3. Frontend Setup
```bash
cd 1proxy-frontend

# Install dependencies
npm install

# Configure environment
# No .env needed for development (uses localhost)
```

### 4. Database Setup (Development)
```bash
cd 1proxy-backend

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

### 5. Frontend Development
```bash
cd 1proxy-frontend
npm run dev
```

## Production Deployment

### Using Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/oyi77/1proxy.git
cd 1proxy

# Set up environment variables
cp 1proxy-backend/.env.example 1proxy-backend/.env
# Edit .env with production values

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

### Manual Production Deployment

#### Backend
```bash
cd 1proxy-backend

# Install production dependencies
pip install -r requirements.txt

# Build for production
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or use systemd/hypervisor for process management
```

#### Frontend
```bash
cd 1proxy-frontend

# Build for production
npm run build
npm run start

# Or use PM2 for process management
pm2 start npm --name "1proxy-frontend" -- run start
```

## Environment Variables

### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/1proxy

# Security
SECRET_KEY=your-super-secret-key-min-32-characters

# OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# URLs
API_URL=https://api.yourdomain.com
FRONTEND_URL=https://yourdomain.com

# Redis
REDIS_URL=redis://localhost:6379
```

## Monitoring

### Health Checks
- Backend: `GET /health`
- Redis: `redis-cli ping`

### Logging
- Logs are written to stdout (JSON format)
- Configure log aggregation (ELK, CloudWatch, etc.)

### Metrics
- Python metrics available via `/metrics` (if prometheus-client installed)

## Security Considerations

1. **Use HTTPS in production**
2. **Keep secrets secure** (.env files not committed)
3. **Configure CORS properly** for production domains
4. **Use strong SECRET_KEY** (32+ characters)
5. **Rate limiting enabled** - adjust for production needs
6. **Regular security updates** for dependencies

## Scaling

### Horizontal Scaling
- Backend: Scale by adding more instances behind load balancer
- Redis: Use Redis Cluster for high availability
- Database: Use PostgreSQL with connection pooling

### Vertical Scaling
- Increase RAM for larger proxy caches
- Increase CPU cores for concurrent validation
- Use SSD storage for faster I/O

## Troubleshooting

### Common Issues
1. **Connection refused**: Check service is running on correct port
2. **Database errors**: Verify DATABASE_URL and connection
3. **OAuth failures**: Check callback URLs in OAuth provider settings
4. **Memory issues**: Monitor with `docker stats` or `htop`

### Logs
```bash
# Docker
docker-compose logs -f backend
docker-compose logs -f frontend

# Manual
tail -f 1proxy-backend/logs/app.log
```

## Next Steps

After infrastructure setup, proceed to [Deployment Procedures](./deployment.md) for production deployment instructions.

---

**Last Updated**: January 16, 2026  
**Version**: 1.0
