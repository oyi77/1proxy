---
title: 1proxy
emoji: 🚀
colorFrom: purple
colorTo: blue
sdk: docker
sdk_version: 3.12
app_file: hf-spaces/Dockerfile
pinned: false
license: mit
---

# 1proxy - Community-Driven Proxy Aggregation Platform

A high-performance proxy aggregation platform with OAuth authentication.

## Features

- 🌐 10+ Auto-Updated Sources
- 🔍 Advanced Filtering
- 📊 Quality Scoring (0-100)
- 🔐 GitHub OAuth Authentication
- 👥 User Contributions
- 🛡️ Admin Panel

## API Access

Once deployed, access the API at:
- **Base URL**: https://paijo77-1proxy.hf.space
- **Health**: https://paijo77-1proxy.hf.space/health
- **API Docs**: https://paijo77-1proxy.hf.space/docs

## Configuration

Set these secrets in Space settings:

| Secret | Description |
|--------|-------------|
| `SECRET_KEY` | JWT signing key (min 32 chars) |
| `GITHUB_CLIENT_ID` | GitHub OAuth Client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth Client Secret |
| `GITHUB_REPO_OWNER` | Repo owner for admin access (optional) |
| `GITHUB_REPO_NAME` | Repo name for admin access (optional) |

## License

MIT
