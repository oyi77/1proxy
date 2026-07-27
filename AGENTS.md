# AGENTS.md — 1proxy

## MANDATORY PROCESS (8 Steps — No Skipping)

Every task follows this sequence. No exceptions.

1. **AUDIT** — Read existing code. Understand current state.
2. **THINK** — Understand WHY. Intent vs literal.
3. **BRAINSTORM** — ≥3 approaches. Score options.
4. **PLAN** — Decompose. Risks. Rollback plan.
5. **EXECUTE** — Build. TDD when possible.
6. **TEST** — Run all tests. Break it first.
7. **VERIFY** — Prove with literal output.
8. **REVIEW** — Read your own diff before committing.

Full details: `~/.1ai/core/PROCESS.md` (auto-injected by hooks)

## This repo
Community-driven proxy aggregation platform: scrapes, validates, and serves free proxies from 10+ GitHub sources. Quality scoring (0-100), multi-protocol, two-phase validation.
Stack: Python (FastAPI, SQLAlchemy async, aiohttp) / Next.js 15 / SQLite (dev) / Supabase PostgreSQL (prod)
Domain: proxy aggregation, validation pipeline, community-driven proxy sources

## Rules — thin loader, no submodule
Rules are NOT vendored into this repo. This repo does NOT need a rules submodule.
`AGENTS.md` is only the repo-local loader: domain, commands, conventions, and pointers to `~/.1ai`.

Engineering rules are enforced by machine-level loaders when `setup-dev.sh` has been run:
- Claude Code: SessionStart hook injects `~/.1ai/core/RULES.md`
- OpenCode: plugin injects `~/.1ai/core/RULES.md`
- OMP: wrapper appends `~/.1ai/core/RULES.md` to launch sessions

Primary rules file:
```bash
cat ~/.1ai/core/RULES.md
```

Pre-ship gate:
```bash
cat ~/.1ai/core/GATE.md
```

If `~/.1ai` or auto-load is missing, run:
```bash
bash ~/.1ai/scripts/setup-dev.sh
```

Do NOT add the rules repo as a git submodule. Update rules centrally, then run/sync the thin `AGENTS.md` template.

## Hard rules
1. Read code before writing code.
2. No completion claim without literal receipt.
3. Compile/test/use like a real user before claiming work is ready.
4. Task must match this repo domain.
5. Run GATE.md before commit/PR.

## Repo-specific conventions
- Two-phase validation: Phase 1 (fast connectivity + latency), Phase 2 (comprehensive: anonymity, geo, access)
- ipquery.io preferred over separate geo/proxy-type APIs — single call for location + risk + ISP
- All external API calls cached via LRUCache (5K-10K entries, TTL configurable per API)
- Repository pattern for DB — never execute() in routers, use db_storage methods
- Async-first: aiohttp for HTTP, asyncio for background workers, SQLAlchemy async for DB
- Quality score 0-100: latency(40) + anonymity(25) + access(20) + type(10) + SSL(10) - penalties
- Rate limited: public 100/hr, auth 500/hr, admin unlimited (configurable)

## Commands
- Dev:   `npm run dev`
- Test:  `npm run test`
- Build: `npm run build`
- Lint:  `npm run lint`
