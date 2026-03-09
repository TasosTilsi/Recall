---
phase: 11-graph-ui
plan: 03
subsystem: ui
tags: [next.js, react, typescript, tailwindcss, react-force-graph-2d, static-export]

# Dependency graph
requires:
  - phase: 11-02
    provides: FastAPI backend serving /api/graph and /api/nodes/{uuid} endpoints
provides:
  - Next.js 16 + TypeScript frontend with ForceGraph2D visualization
  - Pre-built static export committed to git (ui/out/index.html)
  - Five React components: GraphCanvas, NodeSidebar, SearchFilter, Legend, page.tsx
  - Typed API helpers in ui/src/lib/api.ts
  - Entity-type and scope color palette in ui/src/lib/colors.ts
affects: [11-graph-ui, python-package-distribution]

# Tech tracking
tech-stack:
  added:
    - next@16.1.6 (static export mode)
    - react@19.2.4
    - react-force-graph-2d@1.29.1 (ForceGraph2D with dagMode)
    - tailwindcss@4.2.1 (v4 with @import "tailwindcss")
    - typescript@5.9.3
  patterns:
    - SSR guard via next/dynamic with ssr:false for browser-only canvas libraries
    - Static export committed to git — no Node.js required at Python package install time
    - dagMode toggle (td/undefined) for hierarchical vs force layout
    - Node dimming via nodeColor callback — client-side filtering without API calls

key-files:
  created:
    - ui/src/app/layout.tsx
    - ui/src/app/page.tsx
    - ui/src/app/globals.css
    - ui/src/components/GraphCanvas.tsx
    - ui/src/components/NodeSidebar.tsx
    - ui/src/components/SearchFilter.tsx
    - ui/src/components/Legend.tsx
    - ui/out/index.html (pre-built static export)
  modified:
    - ui/tsconfig.json (Next.js auto-updated jsx to react-jsx and include paths)

key-decisions:
  - "SSR guard (dynamic/ssr:false) required for react-force-graph-2d — uses window/canvas which crashes Next.js SSR"
  - "ui/out/ committed to git as pre-built artifact — Python package ships UI without Node.js dependency"
  - "Scope toggle re-fetches via loadGraph(newScope) callback — no page reload needed"
  - "Node dimming (color #1e293b for non-matching) chosen over node removal — preserves graph topology during search"

patterns-established:
  - "SSR guard pattern: dynamic(() => import(...).then(mod => ({default: mod.GraphCanvas})), {ssr: false})"
  - "Tailwind v4 import: @import 'tailwindcss' in globals.css (no config file needed)"
  - "ForceGraph2D dagMode: layout === 'hierarchical' ? 'td' : undefined"

requirements-completed: [UI-01, UI-02, UI-03]

# Metrics
duration: 15min
completed: 2026-03-09
---

# Phase 11 Plan 03: Next.js Graph UI Frontend Summary

**Next.js 16 + TypeScript static export with ForceGraph2D visualization, scope/layout/color-mode toggles, and pre-built ui/out/ committed to git for zero-Node.js Python distribution**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-09T00:00:00Z
- **Completed:** 2026-03-09T00:15:00Z
- **Tasks:** 2 (Task 1 was pre-committed; Task 2 executed in this session)
- **Files modified:** 10 created + 1 modified + 33 build artifacts committed

## Accomplishments
- Created all React components with dark-mode Tailwind v4 styling
- SSR guard via `next/dynamic` with `ssr: false` prevents window/canvas crash during static generation
- `npm run build` exits 0 — TypeScript clean, no SSR errors, static pages generated
- Pre-built `ui/out/` (index.html + JS/CSS chunks) committed to git as distribution artifact
- ForceGraph2D with dagMode hierarchy toggle, node dimming for search/filter, scope color-mode switching

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold Next.js project with react-force-graph-2d** - `ecfb3f6` (feat)
2. **Task 2: Build React components, run next build, commit ui/out/** - `c3e0d75` (feat)

## Files Created/Modified
- `ui/src/app/layout.tsx` - Root HTML layout with dark class and metadata
- `ui/src/app/globals.css` - Tailwind v4 import (`@import "tailwindcss"`)
- `ui/src/app/page.tsx` - Root page: scope/layout/color-mode controls + dynamic GraphCanvas import
- `ui/src/components/GraphCanvas.tsx` - ForceGraph2D wrapper with dagMode, nodeColor dimming, canvas labels
- `ui/src/components/NodeSidebar.tsx` - Right-panel entity detail with relationships list
- `ui/src/components/SearchFilter.tsx` - Text search input + entity-type dropdown
- `ui/src/components/Legend.tsx` - Color legend filtered to active entity types
- `ui/src/lib/api.ts` - Typed fetch helpers for /api/graph and /api/nodes/{uuid}
- `ui/src/lib/colors.ts` - Entity-type and scope color palettes with getNodeColor/getLegendEntries
- `ui/out/index.html` - Pre-built static export (and associated JS/CSS chunks)
- `ui/tsconfig.json` - Auto-updated by Next.js (jsx: react-jsx, include .next/dev/types)

## Decisions Made
- SSR guard pattern (`dynamic` with `ssr: false`) required because react-force-graph-2d accesses `window` and canvas APIs during rendering — would crash Next.js static generation without it
- Node dimming (`#1e293b` / slate-800) chosen over hiding nodes during search — preserves graph topology so users can see structural context around matches
- `ui/out/` committed directly to git — Python package users get the UI without needing Node.js; rebuild only required when UI changes

## Deviations from Plan

None — plan executed exactly as written. The tsconfig.json auto-modification by Next.js during build is expected behavior (not a deviation).

## Issues Encountered
None — `npm run build` passed on first attempt. TypeScript strict mode clean, no SSR window errors, Tailwind v4 `@import` syntax works correctly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `ui/out/` is ready for `src/ui_server/app.py` to serve via `StaticFiles` (Plan 11-02 already configured this path)
- All three UI requirements (UI-01, UI-02, UI-03) are complete
- Phase 11 is now complete — graph visualization available via `graphiti ui` command

---
*Phase: 11-graph-ui*
*Completed: 2026-03-09*
