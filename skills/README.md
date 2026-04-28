# 1proxy Agent Skills

This folder is reserved for project-local agent skills. Skills should encode repeatable workflows that are specific to 1proxy and safe to run in development environments.

## Proposed Skills

- `proxy-source-audit`: validate new public source candidates, check freshness, and record caveats.
- `scraper-regression-check`: run parser, scraper, and validation tests for source changes.
- `deployment-health-check`: verify `/health`, `/api/v1/stats`, background worker logs, and DB keepalive status after deploy.

## Skill Requirements

- Include exact commands and expected outputs.
- Avoid destructive operations by default.
- Document external network calls and rate-limit expectations.
- Keep code and docs in sync with `AGENTS.md` and `docs/` decisions.
