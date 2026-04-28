# MCP Server Notes

This repository does not ship active MCP server implementations yet. The `.mcp/` directory is reserved for future Model Context Protocol server definitions that expose safe, read-only or explicitly authenticated 1proxy operations to agent clients.

## Candidate Servers

- `1proxy-public-api`: read-only proxy/source/stats access.
- `1proxy-admin-api`: authenticated admin workflows such as source validation and Hunter Protocol triggers.
- `1proxy-devtools`: local-only helpers for test fixtures, mock source generation, and diagnostics.

## Guardrails

- Never expose raw secrets, OAuth tokens, or premium proxy credentials.
- Mutating tools must require explicit auth and rate limits.
- Public proxy exports must only return already validated proxies.
- Server configs should be documented here before implementation.
