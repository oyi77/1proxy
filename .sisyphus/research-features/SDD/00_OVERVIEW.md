# PROJECT PROMETHEUS: ARCHITECTURE OVERVIEW

**Project:** 1proxy "Prometheus" Update  
**Version:** 1.0  
**Status:** DRAFT  
**Date:** 2026-01-13

---

## 1. VISION
Transform 1proxy from a **passive** aggregator (waiting for users to add sources) into an **autonomous active hunter**. The system will proactively discover, validate, and ingest new proxy sources from the open web, utilizing GitHub API, Search Engines, and AI Agents.

## 2. SYSTEM BOUNDARIES

### 2.1. The "Hunter" Module
A new, isolated module (`app/hunter/`) responsible for:
1.  **Discovery:** Finding potential source URLs.
2.  **Extraction:** converting unstructured web content into structured proxy candidates.
3.  **Candidacy:** Holding discovered sources in a staging area for verification.

### 2.2. Integration Points
- **Database:** Reads/Writes to new `candidate_sources` table.
- **Proxy Pool:** Uses existing *working* proxies to perform anonymous scraping (Google/Bing).
- **Validator:** Sends extracted proxies to the existing validation pipeline.

## 3. COMPONENT DIAGRAM

```mermaid
graph TD
    User[Admin User] -->|Approve/Reject| API[Admin API]
    
    subgraph "Hunter Core"
        Scheduler[Task Scheduler] --> Orchestrator[Hunter Service]
        Orchestrator -->|Dispatch| StratGitHub[GitHub Strategy]
        Orchestrator -->|Dispatch| StratSearch[Search Strategy]
        Orchestrator -->|Dispatch| StratAI[AI Strategy (G4F)]
        
        StratGitHub -->|Raw URLs| Extractor[Universal Extractor]
        StratSearch -->|Raw URLs| Extractor
        StratAI -->|Raw URLs| Extractor
        
        Extractor -->|Proxy Objects| CandidateMgr[Candidate Manager]
    end
    
    subgraph "Data Layer"
        CandidateMgr --> DB[(Candidate DB)]
    end
    
    subgraph "Validation"
        CandidateMgr -->|Sample Check| Validator[Proxy Validator]
        Validator -->|Score| DB
    end
```

## 4. KEY CONSTRAINTS
1.  **Safety:** The Hunter must never perform scraping that risks the server's primary IP reputation. All scraping MUST go through the proxy pool.
2.  **Cost:** The solution must assume **zero budget** for APIs (use G4F, scraping, free tiers).
3.  **Quality:** "Discovered" sources are guilty until proven innocent. They stay in `pending` state until validated.
