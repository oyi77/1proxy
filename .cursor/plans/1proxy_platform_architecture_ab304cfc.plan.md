---
name: 1proxy Platform Architecture
overview: Build a comprehensive proxy aggregation platform with grab, validation, testing, and rotation capabilities. Optimized for high-frequency updates, advanced anonymity detection, and resilient scraping.
todos:
  - id: setup-project
    content: "Initialize project structure: create backend, frontend, CLI directories with base configurations (requirements.txt, package.json, pyproject.toml)"
    status: pending
  - id: database-setup
    content: "Implement hybrid storage: PostgreSQL (persistence/metrics) with TimeScaleDB partitioning and Redis (hot-write status buffer)"
    status: pending
    dependencies:
      - setup-project
  - id: grabber-module
    content: "Implement Adaptive Grabber: multi-tier strategy (Exact, Semantic, LLM-fallback) with automated selector healing"
    status: pending
    dependencies:
      - database-setup
  - id: validator-module
    content: "Implement multi-layered validator: basic headers, IP reputation, protocol leaks (DNS/WebRTC), and TLS fingerprinting"
    status: pending
    dependencies:
      - database-setup
  - id: tester-module
    content: "Implement tester module: performance scoring system with adaptive re-validation cycles (Scylla pattern)"
    status: pending
    dependencies:
      - database-setup
  - id: rotator-module
    content: "Implement rotator module: Token-based sticky sessions, scoring-weighted selection, and consistent hashing fallback"
    status: pending
    dependencies:
      - validator-module
      - tester-module
  - id: forward-proxy-interface
    content: "Develop Forward Proxy Server: allow users to use the platform as a single entry point with transparent rotation"
    status: pending
    dependencies:
      - rotator-module
  - id: api-layer
    content: "Build FastAPI application: async endpoints for management, statistics, and proxy retrieval"
    status: pending
    dependencies:
      - rotator-module
  - id: celery-tasks
    content: "Set up Celery with Redis: async pipelines for parallel scraping, validation, and batch persistence to DB"
    status: pending
    dependencies:
      - api-layer
  - id: opencode-dev-setup
    content: "Set up OpenCode/Oh-My-OpenCode development environment: configuration for parallel sub-agent module development"
    status: pending
    dependencies:
      - setup-project
  - id: frontend-dashboard
    content: "Build Next.js frontend: real-time dashboard with metrics, geographic distribution, and source health tracking"
    status: pending
    dependencies:
      - api-layer
  - id: cli-tool
    content: "Develop CLI tool: modern Typer-based client with rich output and configuration management"
    status: pending
    dependencies:
      - api-layer
  - id: documentation
    content: "Create comprehensive documentation: architecture, API spec, and setup guides"
    status: pending
    dependencies:
      - frontend-dashboard
      - cli-tool
---

# 1proxy Platform - Advanced Architecture Plan

## Executive Summary

1proxy is a high-performance proxy aggregation platform designed to consolidate, validate, and serve free proxies with enterprise-grade reliability. This refined plan incorporates high-frequency database optimizations, multi-layered anonymity detection, and a resilient "Adaptive Grabber" system.

## Architecture Overview

```mermaid
graph TB
    subgraph Sources["Proxy Sources"]
        GH[GitHub Repos]
        WEB[Web Scraping]
        TG[Telegram Channels]
        API[Public APIs]
    end
    
    subgraph HotLayer["Hot Write / Real-time"]
        REDIS[(Redis Buffer)]
        ROT[Rotator Module]
        STICKY[Sticky Session Cache]
    end
    
    subgraph Core["Core Engine (Celery/Async)"]
        AG[Adaptive Grabber]
        VAL[Multi-Layer Validator]
        TEST[Performance Tester]
        CELERY[Worker Pool]
    end

    subgraph Persistence["Cold Storage / Analytics"]
        DB[(PostgreSQL + TimeScaleDB)]
        METRICS[Metrics Aggregator]
    end
    
    subgraph Interfaces["Serving Layer"]
        API_LAYER[REST API]
        FWD_PROXY[Forward Proxy Server]
        WEB_UI[Web Dashboard]
        CLI_TOOL[CLI Client]
    end
    
    Sources --> AG
    AG --> REDIS
    REDIS --> VAL
    VAL --> TEST
    TEST --> REDIS
    
    CELERY --> AG
    CELERY --> VAL
    CELERY --> TEST
    CELERY --> BATCH_WRITE[Batch Persister]
    
    BATCH_WRITE --> DB
    REDIS --> ROT
    ROT --> FWD_PROXY
    DB --> METRICS
    METRICS --> WEB_UI
    
    DB --> API_LAYER
    DB --> CLI_TOOL
    
    style HotLayer fill:#fff4e1
    style Core fill:#e1f5ff
    style Persistence fill:#e1ffe1
```

## Strategic Improvements

### 1. Hybrid Storage Strategy

To handle thousands of proxy status updates per second without bottlenecking the database:

- **Redis (Hot)**: Stores ephemeral state, scores, and rotation pools. Uses Sorted Sets for O(log N) retrieval of top-scoring proxies.
- **PostgreSQL + TimeScaleDB (Cold)**: Stores metadata and historical metrics. Partitioned by time for efficient cleanup and analytical queries.
- **Batch Persistence**: A dedicated background process periodically flushes status snapshots from Redis to PostgreSQL to minimize I/O.

### 2. Multi-Layer Anonymity Detection

Goes beyond standard headers to ensure "Elite" status:

- **Layer 1**: Header analysis (Via, X-Forwarded-For, etc.).
- **Layer 2**: IP Reputation (AbuseIPDB, VirusTotal integration).
- **Layer 3**: Protocol Leak Detection (DNS/WebRTC leaks via headless browser checks).
- **Layer 4**: TLS Fingerprinting (JA3 signatures) to ensure the proxy mimics real browser behavior.

### 3. Adaptive Grabber Module

Solves the "brittle scraper" problem:

- **Tiered Strategy**: Uses hardcoded CSS/XPath selectors first.
- **Semantic Fallback**: If exact selectors fail, searches for semantic patterns (e.g., "text containing 'IP'").
- **LLM Healing**: Periodically uses LLMs to analyze broken pages and propose new selectors, which are then cached.

### 4. Advanced Rotation & Sessions

- **Forward Proxy Server**: Provides a single `host:port` entry point for users. Each request is automatically routed to the best available upstream proxy.
- **Sticky Sessions**: Token-based affinity. If a user provides a session ID, they keep the same proxy for a configurable TTL, provided it stays healthy.
- **Consistent Hashing**: Fallback mechanism to ensure balanced distribution without state when possible.

### 5. Cold Start & Bootstrapping

- **Aggressive Seeding**: Multi-threaded scraping of 20+ known public aggregators.
- **Verification Loop**: Rapid initial re-validation (every 2-5 mins) to filter out volatile free proxies quickly.
- **Contributor Credits**: Allow users to submit lists for API priority.

## Implementation Roadmap

### Phase 1: Storage & Infrastructure (Weeks 1-2)

- Hybrid Redis/Postgres setup.
- TimeScaleDB partitioning for history.
- Core Pydantic models with validation.

### Phase 2: The Validation Pipeline (Weeks 3-4)

- Async validation engine (aiohttp).
- Multi-layer leak detection.
- Adaptive re-validation logic (Scylla pattern).

### Phase 3: Adaptive Grabbing (Weeks 5-6)

- Base Grabber with registry pattern.
- Semantic selector fallback.
- GitHub/Telegram/Web fetchers.

### Phase 4: Serving & Rotation (Weeks 7-8)

- Forward Proxy interface (Python/Go).
- Sticky session logic in Redis.
- FastAPI REST endpoints.

### Phase 5: UI & CLI (Weeks 9-10)

- Next.js 14 real-time dashboard.
- Typer-based CLI with table/JSON output.
- Global metrics & source health tracking.

## Technology Stack (Refined)

- **Backend**: FastAPI (Python 3.12+), Celery, Redis.
- **Persistence**: PostgreSQL + TimeScaleDB (for metrics).
- **Frontend**: Next.js 14, Tailwind CSS, shadcn/ui.
- **Scraping**: Playwright (for JS-heavy sources), aiohttp (for high-speed fetch).
- **ML/LLM**: Local Ollama/Llama-cpp for selector healing.