# 1proxy: Community-Driven Proxy Aggregation Platform

![CI Status](https://github.com/oyi77/1proxy/actions/workflows/deploy-frontend.yml/badge.svg)

A high-performance, multi-user proxy aggregation platform where anyone can contribute proxy sources while maintaining public access to all proxies. Built with modern async Python, Next.js 15, and enterprise-grade validation.

## 📊 System Architecture

```mermaid
graph TD
    subgraph "External World"
        G[GitHub Sources]
        U[Public Users]
        C[Contributors]
    end

    subgraph "Frontend (GitHub Pages)"
        FE[Next.js 15 App]
    end

    subgraph "Backend (HuggingFace Spaces)"
        API[FastAPI Service]
        VAL[Proxy Validator]
        DB[(SQLite / PostgreSQL)]
        SCH[Background Scheduler]
    end

    G -->|Scrape| API
    U -->|Browse/Export| FE
    FE -->|Requests| API
    C -->|OAuth/Submit| FE
    API --> VAL
    VAL --> DB
    SCH -->|Trigger| VAL
```

## ✨ Key Features

### For Everyone (Public Access)
- 🌐 **10+ Auto-Updated Sources** - GitHub repos refreshing daily/hourly.
- 🔍 **Advanced Filtering** - By protocol, country, anonymity, quality, speed.
- 📊 **Quality Scoring** - 0-100 score based on latency, anonymity, Google access.
- 💾 **Export Formats** - TXT, JSON, CSV.

### For Contributors (OAuth Required)
- 🔐 **GitHub/Google Login** - Secure authentication via standard providers.
- ➕ **Add Your Sources** - Share proxy lists with the community.
- ✅ **Real-time Validation** - Instant feedback on submitted source quality.

## 🚀 Quick Links

- **Frontend**: [https://oyi77.is-a.dev/1proxy/](https://oyi77.is-a.dev/1proxy/)
- **Backend API**: [https://paijo77-1proxy.hf.space](https://paijo77-1proxy.hf.space)
- **API Documentation**: [https://paijo77-1proxy.hf.space/docs](https://paijo77-1proxy.hf.space/docs)

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | Next.js 15, TypeScript, Tailwind CSS |
| **Backend** | FastAPI, SQLAlchemy (Async), Pydantic v2 |
| **Validation** | aiohttp, BeautifulSoup4, Custom Scoring |
| **Database** | SQLite (Dev) / PostgreSQL (Prod), Alembic |
| **Deployment** | GitHub Pages (FE), HuggingFace Spaces (BE) |

---

## 🎯 Operational Flows

### 1. Proxy Validation Pipeline
```mermaid
sequenceDiagram
    participant P as Proxy Source
    participant S as Scraper
    participant V as Validator
    participant D as Database

    S->>P: Fetch Raw Data
    S->>S: Extract via Multi-Protocol Regex
    loop Every Proxy
        S->>V: Send for Validation
        V->>V: Check Connection (Latency)
        V->>V: Detect Anonymity Level
        V->>V: Verify Google Access
        V->>V: Calculate Quality Score (0-100)
        V->>D: Upsert (Update if exists)
    end
```

### 2. User Contribution Flow
```mermaid
sequenceDiagram
    actor User
    participant Auth as OAuth Provider
    participant App as 1proxy App

    User->>App: Login Request
    App->>Auth: Redirect to Provider
    Auth-->>App: Auth Callback
    App->>User: Access Token
    User->>App: Submit New Source URL
    App->>App: Immediate Source Validation
    alt Valid Source
        App-->>User: Success (Queued for scraping)
    else Invalid Source
        App-->>User: Error Details
    end
```

---

## 📖 Documentation & Maintenance

- **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - Step-by-step deployment to HF/GH.
- **[LLM_CONTEXT.md](./docs/LLM_CONTEXT.md)** - 🤖 **Recommended for AI Assistants**. Machine-readable commands and context.
- **[SDD.md](./docs/SDD.md)** - Software Design Document & API Reference.

---

## 🏗️ Local Development

### Backend Setup
```bash
cd 1proxy-backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd 1proxy-frontend
npm install
npm run dev
```

---

**Built by [oyi77](https://github.com/oyi77)**  
*Community driven, open source, and anti-gravity.*
