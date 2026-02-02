# 🚀 Deployment Guide - GitHub Pages + HuggingFace

This document explains how to deploy 1proxy with:
- **Frontend**: GitHub Pages (free static hosting)
- **Backend**: HuggingFace Spaces (free API hosting)

## ✅ Current Setup

### Backend (HuggingFace Space)
- **URL**: https://paijo77-1proxy.hf.space
- **API Docs**: https://paijo77-1proxy.hf.space/docs
- **Status**: ✅ Deployed and running

### Frontend (GitHub Pages) 
- **Will be at**: https://[username].github.io/1proxy/
- **Status**: ⏳ Ready to deploy

---

## 📋 One-Time Setup

### 1. Enable GitHub Pages

1. Go to your repository settings: `https://github.com/[username]/1proxy/settings/pages`
2. Under "Build and deployment":
   - Source: **GitHub Actions**
3. Click **Save**

That's it! The workflow in `.github/workflows/deploy-frontend.yml` will handle the rest.

---

## 🔧 Configuration

### Frontend Environment Variables

The frontend is already configured to connect to your HuggingFace backend:

```typescript
// Configured in .github/workflows/deploy-frontend.yml
NEXT_PUBLIC_API_URL=https://paijo77-1proxy.hf.space
```

### Backend CORS (Already Configured)

The backend accepts requests from:
- ✅ `https://*.github.io` (GitHub Pages)
- ✅ `https://*.hf.space` (HuggingFace Spaces)
- ✅ `http://localhost:3000` (Local development)

---

## 🚀 Deployment Workflow

### Automatic Deployment

Whenever you push changes to `1proxy-frontend/`, GitHub Actions will:

1. ✅ Install dependencies
2. ✅ Build Next.js for static export
3. ✅ Run post-build script (copies to `out/`)
4. ✅ Deploy to GitHub Pages

**Build Time**: ~2-3 minutes

### Manual Deployment

To manually trigger a deployment:

1. Go to **Actions** tab in GitHub
2. Click **Deploy Frontend to GitHub Pages**
3. Click **Run workflow**

---

## 🧪 Local Testing

Test the production build locally:

```bash
cd 1proxy-frontend

# Build for GitHub Pages
npm run build

# Serve the out/ directory
npx serve out

# Visit: http://localhost:3000
```

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  User Browser                                           │
│                                                         │
└──────────────┬──────────────────────────────────────────┘
               │
               ├─── HTML/CSS/JS ──────────────────────────┐
               │                                          │
               │                                          ▼
               │                              ┌───────────────────────┐
               │                              │                       │
               │                              │  GitHub Pages         │
               │                              │  (Static Frontend)    │
               │                              │                       │
               │                              │  *.github.io/1proxy   │
               │                              │                       │
               │                              └───────────────────────┘
               │
               └─── API Calls (fetch) ────────────────────┐
                                                          │
                                                          ▼
                                              ┌───────────────────────┐
                                              │                       │
                                              │  HuggingFace Space    │
                                              │  (Backend API)        │
                                              │                       │
                                              │  *.hf.space           │
                                              │                       │
                                              └───────────────────────┘
```

---

## 🔐 OAuth Configuration (Optional)

To enable user authentication:

1. Create GitHub OAuth App:
   - Go to: https://github.com/settings/developers
   - Callback URL: `https://paijo77-1proxy.hf.space/auth/github/callback`

2. Add to HuggingFace Space settings:
   ```
   GITHUB_CLIENT_ID=your_client_id
   GITHUB_CLIENT_SECRET=your_client_secret
   ```

3. Same for Google OAuth:
   - Create at: https://console.cloud.google.com/apis/credentials
   - Callback URL: `https://paijo77-1proxy.hf.space/auth/google/callback`

---

## 🐛 Troubleshooting

### Frontend shows "Failed to fetch"

**Problem**: API calls are failing  
**Solution**: Check that `NEXT_PUBLIC_API_URL` matches your HuggingFace Space URL

### GitHub Pages shows 404

**Problem**: Build didn't deploy  
**Solution**: Check Actions tab for build errors

### CORS errors in browser console

**Problem**: Backend doesn't allow GitHub Pages origin  
**Solution**: Already fixed! Backend includes `https://*.github.io` in CORS

---

## 📝 Next Steps

1. **Push this repository to GitHub**
2. **Enable GitHub Pages** (see "One-Time Setup" above)
3. **Wait 2-3 minutes** for first deployment
4. **Visit** `https://[username].github.io/1proxy/`

---

## 💰 Cost

| Service | Plan | Cost |
|---------|------|------|
| GitHub Pages | Free Tier | $0/month |
| HuggingFace Space | Free Tier | $0/month |
| **Total** | | **$0/month** |

**Limits**:
- GitHub Pages: 100 GB bandwidth/month
- HuggingFace: 16GB RAM, 2 CPU cores (free tier)

---

## 🔗 Quick Links

- **Frontend (GitHub Pages)**: https://[username].github.io/1proxy/
- **Backend API**: https://paijo77-1proxy.hf.space
- **API Docs**: https://paijo77-1proxy.hf.space/docs
- **HF Space Settings**: https://huggingface.co/spaces/paijo77/1proxy/settings
- **GitHub Actions**: https://github.com/[username]/1proxy/actions

---

**Built with ❤️ - 100% Free Deployment**
