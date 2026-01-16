# FRONTEND TAB COMPONENTS

**Location:** `1proxy-frontend/components/tabs/`  
**Focus:** Isolated tab content components for the main dashboard.

## OVERVIEW
Modular tab components that encapsulate the logic for Home, Proxies, and Sources views. Extracted from the monolithic `home-client.tsx` to improve maintainability.

## STRUCTURE
```
tabs/
├── HomeTab.tsx       # Landing/welcome content
├── ProxiesTab.tsx    # Proxy browsing and filtering
└── SourcesTab.tsx    # Source management interface
```

## WHERE TO LOOK
| Task | File |
|------|------|
| Modify welcome content | `HomeTab.tsx` |
| Add proxy filters | `ProxiesTab.tsx` |
| Change source display | `SourcesTab.tsx` |

## CONVENTIONS
- **Props Interface**: Each tab receives `{ user, onTabChange }` props
- **State Management**: Tabs use local `useState` for internal state, lift shared state to `home-client.tsx`
- **API Calls**: Use centralized `lib/api.ts` methods, not direct `fetch`
- **Styling**: Retro-Cyber tokens (`retro-pink`, `retro-shadow`) from Tailwind config

## UNIQUE PATTERNS
### Tab Communication
```tsx
// Tabs signal navigation via callback
<button onClick={() => onTabChange('proxies')}>
  View Proxies
</button>
```

### Filter Persistence
`ProxiesTab` manages filter state internally but exposes it via URL params for deep linking.

## ANTI-PATTERNS
- **NO** direct state mutation - use setter functions
- **NO** hardcoded API URLs - use `process.env.NEXT_PUBLIC_API_URL`
- **NO** inline styles - use Tailwind classes

## NOTES
- Refactored from 772-line `home-client.tsx` (2026-01)
- Each tab is a client component (`'use client'`)
- AdminTab remains in `app/admin/` due to auth boundary
