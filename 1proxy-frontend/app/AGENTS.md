# FRONTEND APP ROUTER

**Location:** `1proxy-frontend/app/`  
**Focus:** Next.js 15 file-based routing and page components.

## OVERVIEW
App Router directory implementing the main UI structure: landing page, dashboard, admin panel, and authentication flows.

## STRUCTURE
```
app/
├── page.tsx              # Landing page (SSR)
├── layout.tsx            # Root layout (HTML shell)
├── home-client.tsx       # Dashboard logic (772 lines CSR)
├── theme-provider.tsx    # Dark mode context
├── login/
│   └── page.tsx          # OAuth login page
├── dashboard/
│   ├── page.tsx          # User dashboard
│   └── add-source/
│       └── page.tsx      # Source creation form
├── admin/
│   ├── layout.tsx        # Admin-only layout wrapper
│   └── page.tsx          # Admin panel (416 lines)
└── sources/
    └── page.tsx          # Public sources list
```

## WHERE TO LOOK
| Task | File |
|------|------|
| Landing page | `page.tsx` |
| Dashboard UI | `home-client.tsx` (main logic) |
| Add source form | `dashboard/add-source/page.tsx` |
| Admin controls | `admin/page.tsx` |
| Auth flow | `login/page.tsx` |

## CONVENTIONS
- **Client Components**: Use `'use client'` directive for interactive pages
- **Layouts**: `layout.tsx` wraps children, provides common UI (nav, footer)
- **Protected Routes**: Admin routes wrapped with `<ProtectedRoute adminOnly>`
- **Data Fetching**: Client-side `useEffect` + `fetch` (no Server Components for dashboard)

## UNIQUE PATTERNS
### Client Component Colocation
`home-client.tsx` lives in `app/` (not `components/`) to keep dashboard logic close to routing:
```tsx
// app/page.tsx (Server Component)
export default function Home() {
  return <HomeClient /> // Delegates to CSR
}

// app/home-client.tsx (Client Component)
'use client'
export default function HomeClient() {
  // All dashboard logic here
}
```

### Admin Layout Pattern
```tsx
// app/admin/layout.tsx
export default function AdminLayout({ children }) {
  return (
    <ProtectedRoute adminOnly>
      {children}
    </ProtectedRoute>
  )
}
```

## ANTI-PATTERNS
- **NO** Server Components for dashboard pages (breaks state management)
- **NO** mixing tab logic across multiple files (keep in `home-client.tsx` for now)
- **REFACTOR NEEDED**: `home-client.tsx` (772 lines) should split tabs into separate components

## NOTES
- **Largest file**: `home-client.tsx` (772 lines) - contains Home, Proxies, Sources, Admin tabs
- **CSR strategy**: Main pages use `dynamic(..., {ssr: false})` to avoid hydration issues
- **Routing**: Dashboard subroutes (`/dashboard/add-source`) nest under main dashboard
