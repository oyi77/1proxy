# GitHub Pages Deployment Configuration

This document explains how to configure the frontend for different GitHub Pages deployment scenarios.

## 📋 Deployment Scenarios

### Scenario 1: Custom Domain at Root
**URL**: `https://yourdomain.com/`  
**Configuration**: No base path needed

```yaml
# .github/workflows/deploy-frontend.yml
env:
  NEXT_PUBLIC_BASE_PATH: ''  # Empty string for root
  NEXT_PUBLIC_API_URL: 'https://your-backend-url.com'
```

### Scenario 2: GitHub Pages Subdirectory
**URL**: `https://username.github.io/repo-name/`  
**Configuration**: Use repository name as base path

```yaml
# .github/workflows/deploy-frontend.yml
env:
  NEXT_PUBLIC_BASE_PATH: '/repo-name'
  NEXT_PUBLIC_API_URL: 'https://your-backend-url.com'
```

### Scenario 3: Custom Domain with Subdirectory
**URL**: `https://yourdomain.com/1proxy/`  
**Configuration**: Use subdirectory path

```yaml
# .github/workflows/deploy-frontend.yml
env:
  NEXT_PUBLIC_BASE_PATH: '/1proxy'
  NEXT_PUBLIC_API_URL: 'https://your-backend-url.com'
```

---

## 🔧 How It Works

The build process uses the `NEXT_PUBLIC_BASE_PATH` environment variable:

1. **GitHub Actions** sets the variable during build
2. **gh-pages-export.js** script reads it:
   ```javascript
   const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || '/1proxy';
   ```
3. **HTML files** are rewritten with the correct paths:
   - Empty: `/_next/static/...`
   - With prefix: `/1proxy/_next/static/...`

---

## 📝 Current Configuration

**Domain**: `https://oyi77.is-a.dev/`  
**Base Path**: `/1proxy`  
**Full URL**: `https://oyi77.is-a.dev/1proxy/`

---

## 🔄 Changing Deployment Path

### To Deploy at Root Domain

1. Update `.github/workflows/deploy-frontend.yml`:
   ```yaml
   NEXT_PUBLIC_BASE_PATH: ''
   ```

2. Update your DNS/domain settings to point to root

3. Push changes - GitHub Actions will rebuild

### To Change Subdirectory

1. Update `.github/workflows/deploy-frontend.yml`:
   ```yaml
   NEXT_PUBLIC_BASE_PATH: '/new-path'
   ```

2. Push changes - GitHub Actions will rebuild

---

## 🧪 Local Testing

Test with different base paths locally:

```bash
cd 1proxy-frontend

# Test root deployment (no base path)
NEXT_PUBLIC_BASE_PATH='' npm run build
npx serve out

# Test subdirectory deployment
NEXT_PUBLIC_BASE_PATH='/1proxy' npm run build
npx serve out -p 3000

# Visit: http://localhost:3000/1proxy/
```

---

## 🐛 Troubleshooting

### Assets still 404?

1. Check the BASE_PATH in GitHub Actions logs:
   ```
   🔧 Building for deployment at: /1proxy
   ```

2. Verify HTML has correct paths:
   ```bash
   curl https://yourdomain.com/1proxy/ | grep '_next/static'
   # Should show: /1proxy/_next/static/...
   ```

3. Check GitHub Pages settings:
   - Settings → Pages → Source: **GitHub Actions**
   - Custom domain configured correctly

### Wrong base path?

Update the workflow file and push - GitHub Actions will rebuild automatically.

---

## 📚 Related Files

- `.github/workflows/deploy-frontend.yml` - Sets `NEXT_PUBLIC_BASE_PATH`
- `1proxy-frontend/scripts/gh-pages-export.js` - Rewrites HTML paths
- `1proxy-frontend/next.config.ts` - Next.js configuration

---

**Last Updated**: 2026-02-02
