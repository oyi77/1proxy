# FRONTEND APP ROUTER

**Location:** `1proxy-frontend/app/`  
**Focus:** Next.js 15 file-based routing and page components.

## OVERVIEW
App Router directory implementing main UI structure: landing page, dashboard, admin panel, and authentication flows. Emphasizes client-side rendering for interactive dashboards.

## STRUCTURE
```
app/
├── page.tsx              # Landing page (SSR)
├── layout.tsx            # Root layout (HTML shell)
├── home-client.tsx       # Dashboard logic (316 lines CSR)
├── theme-provider.tsx    # Dark mode context
├── login/
│   └── page.tsx          # OAuth login page
├── dashboard/
│   ├── page.tsx          # User dashboard
│   └── add-source/
│       └── page.tsx      # Source creation form
├── admin/
│   ├── layout.tsx        # Admin-only layout wrapper
│   └── page.tsx          # Admin panel (403 lines)
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
| Theme switching | `theme-provider.tsx` |

## CONVENTIONS
- **Client Components**: Use `'use client'` directive for interactive pages
- **Layouts**: `layout.tsx` wraps children, provides common UI (nav, footer)
- **Protected Routes**: Admin routes wrapped with `<ProtectedRoute adminOnly>`
- **Data Fetching**: Client-side `useEffect` + `fetch` (no Server Components for dashboard)
- **State Management**: Multiple `useState` hooks in `home-client.tsx` (15+ state variables)

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
- **NO** mixing tab logic across multiple files (keep in `home-client.tsx` or extract to `components/tabs/`)
- **NO** direct API URLs in components (use `lib/api.ts` methods)

## NOTES
- **Refactor Progress**: Tabs partially extracted to `components/tabs/` (HomeTab, ProxiesTab, SourcesTab)
- **CSR Strategy**: Main pages use `dynamic(..., {ssr: false})` to avoid hydration issues
- **Routing**: Dashboard subroutes (`/dashboard/add-source`) nest under main dashboard
- **State Complexity**: `home-client.tsx` manages 15+ state variables (consider useReducer or Zustand)

## KNOWN ISSUES
- **State Management**: Multiple `useState` calls could be consolidated into `useReducer` or state management library
- **Filter State**: Filter state duplicated between URL params and component state
- **API Error Handling**: Inconsistent error display across pages
