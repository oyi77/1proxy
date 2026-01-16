# 1PROXY FRONTEND (NEXT.JS 15)

**Location:** `1proxy-frontend/`  
**Focus:** Client-side UI for proxy browsing, user dashboards, and admin controls.

## OVERVIEW
Next.js 15 App Router application with "Retro-Cyber" design system, client-side auth context, and type-safe API integration. Emphasizes CSR for high-frequency updates.

## STRUCTURE
```
1proxy-frontend/
├── app/             # File-based routing (→ see app/AGENTS.md)
│   ├── page.tsx            # Landing page (SSR)
│   ├── home-client.tsx     # Dashboard logic (316 lines CSR)
│   ├── dashboard/          # User dashboard & source management
│   ├── admin/              # Admin-only pages
│   └── login/              # OAuth login page
├── components/      # Reusable UI
│   ├── ProxyTable.tsx      # Main proxy display component
│   ├── TabNavigation.tsx   # Tab switching UI
│   └── tabs/               # Tab components (→ see tabs/AGENTS.md)
├── lib/             # Core utilities (→ see lib/AGENTS.md)
│   ├── api.ts              # Typed API client
│   └── auth-context.tsx    # Auth state + ProtectedRoute
├── public/          # Static assets
├── __tests__/       # Vitest test suite
├── tailwind.config.ts      # "Retro-Cyber" design tokens
├── vitest.config.ts        # Test configuration
└── next.config.ts
```

## WHERE TO LOOK
| Task | File |
|------|------|
| Add new route | `app/<route>/page.tsx` |
| Modify API calls | `lib/api.ts` |
| Change auth logic | `lib/auth-context.tsx` |
| Update design tokens | `tailwind.config.ts` |
| Add reusable component | `components/*.tsx` |
| Add tests | `__tests__/components/*.test.tsx` |

## CONVENTIONS
- **Rendering**: Uses CSR (`'use client'`) for dashboard pages to handle high-frequency state updates
- **Routing**: App Router file-based (nested folders = nested routes)
- **Auth**: Context-based with `<ProtectedRoute>` wrapper for authenticated pages
- **Styling**: Tailwind with custom `retro-*` classes (retro-pink, retro-yellow, retro-shadow)
- **API Integration**: Centralized client in `lib/api.ts` with TypeScript interfaces
- **Testing**: Vitest with jsdom, mocks for Next.js navigation and image components

## UNIQUE STYLES
### Retro-Cyber Design System
```tsx
// Custom Tailwind tokens in tailwind.config.ts
colors: {
  'retro-pink': '#FF69B4',
  'retro-yellow': '#FFD93D',
  'retro-blue': '#6BCB77',
}
boxShadow: {
  'retro': '4px 4px 0px 0px rgba(0,0,0,1)',
}
borderWidth: {
  'retro': '3px',
}
```

### Client-Side Auth Pattern
```tsx
// Protected routes use ProtectedRoute wrapper
<ProtectedRoute adminOnly={true}>
  <YourComponent />
</ProtectedRoute>
```

## ANTI-PATTERNS
- **NO** Server Components for dashboard (use CSR with `'use client'`)
- **NO** inline styles (use Tailwind or `retro-*` tokens)
- **NO** direct `fetch` calls (use `lib/api.ts` wrappers)
- **NO** hardcoded API URLs (use `NEXT_PUBLIC_API_URL` env var)

## NOTES
- **Testing**: Vitest setup complete (vitest.config.ts, vitest.setup.tsx)
- **Large file**: `home-client.tsx` (316 lines) - tabs partially extracted to `components/tabs/`
- **CSR strategy**: Dashboard uses `dynamic(..., {ssr: false})` to prevent hydration errors
- **Standalone output**: Production builds use Next.js `standalone` mode for Docker optimization
