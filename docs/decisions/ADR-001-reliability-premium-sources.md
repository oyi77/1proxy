# ADR-001: Keep Database Warm and Surface Premium Source Workflow

## Status

Accepted

## Context

1proxy runs as a FastAPI + SQLAlchemy async backend with background scraping/validation workers and a Next.js frontend. The observed flaws were dormant database behavior, inconsistent proxy source quality, no project-local MCP/skills scaffolding, weak premium source discoverability, and a need for more high-quality public source candidates.

## Decision

- Add explicit database ping/dispose helpers and run a periodic keepalive worker alongside scraper and validation workers.
- Track background tasks in FastAPI app state and cancel them on shutdown before disposing the async engine.
- Preserve `source_id` during bulk proxy insertion so scraped proxies remain attributable to their source.
- Update source health metadata after each scrape, including empty extraction failures.
- Add a small number of maintained public raw source candidates while keeping validation mandatory before serving proxies.
- Add a dashboard source menu with separate free and premium source paths, plus premium prefill and badges.
- Add `.mcp/` and `skills/` placeholder documentation instead of fake MCP servers or fake skills.

## Consequences

- The backend emits one lightweight DB ping every five minutes while running.
- Source quality is more visible, but `success_rate` is currently based on newly processed yield rather than long-term validation success.
- Premium proxy support remains a source flag and workflow, not credential storage or paid-provider integration.
- Future MCP servers and skills have documented guardrails but are not implemented until their contracts are designed.
