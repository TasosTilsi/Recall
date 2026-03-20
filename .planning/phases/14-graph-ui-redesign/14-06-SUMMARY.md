---
phase: 14-graph-ui-redesign
plan: "06"
subsystem: ui
tags: [react, shadcn, typescript, vite, detail-panel, breadcrumb, tables]

# Dependency graph
requires:
  - phase: 14-04
    provides: "shadcn components installed (Table, Badge, Card, Select, Breadcrumb, ScrollArea, Skeleton, Separator)"

provides:
  - "DetailPanel: 400px slide-in panel with breadcrumb navigation and 3 content modes (entity/edge/episode)"
  - "EntityPanel: entity detail with name, type badge, retention status, summary, metadata, relationships list"
  - "EdgePanel: edge detail with fact prominent, label badge, clickable source/target navigation"
  - "EpisodePanel: episode detail with source badge, monospace content expand/collapse, entities extracted list"
  - "Entities tab: sortable shadcn Table with type filter dropdown and DetailPanel on row click"
  - "Relations tab: shadcn Table with fact/from/to/relation/status columns and DetailPanel on row click"
  - "Episodes tab: card-style rows with source badge, source filter Select, and DetailPanel on row click"

affects:
  - 14-graph-ui-redesign
  - phase-14-remaining-plans

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Panel navigation via breadcrumb stack: fresh open resets breadcrumb, in-panel links append, ancestor click slices"
    - "Detail panel as fixed-position overlay (z-20) with 200ms ease-out slideIn CSS animation"
    - "Route tabs follow load/error/empty/content state machine with 30s polling interval"
    - "fetchGraph for entity/relation tabs; fetchDashboard for episodes tab (recent_episodes field)"

key-files:
  created:
    - ui/src/components/panels/DetailPanel.tsx
    - ui/src/components/panels/EntityPanel.tsx
    - ui/src/components/panels/EdgePanel.tsx
    - ui/src/components/panels/EpisodePanel.tsx
  modified:
    - ui/src/routes/Entities.tsx
    - ui/src/routes/Relations.tsx
    - ui/src/routes/Episodes.tsx

key-decisions:
  - "DetailPanel breadcrumb state stored as PanelItem[]; fresh open (item prop change) resets to [item]; in-panel navigate appends"
  - "Episodes tab uses fetchDashboard(scope).recent_episodes — no dedicated episodes endpoint needed"
  - "Entities tab filters out Episodic node type (graph nodes contain both entity and episodic types)"
  - "Relations.tsx plan had duplicate useAppContext import alias — removed (Rule 1 auto-fix)"

patterns-established:
  - "PanelItem type: { itemType: 'entity' | 'edge' | 'episode'; itemId: string; label: string } — consistent across all consumers"
  - "Panel content mode selection via currentItem.itemType conditional rendering (no switch/map)"
  - "Retention badge uses RETENTION_COLORS from lib/colors.ts — consistent with spec amber/green/red/slate"

requirements-completed: [UI-01, UI-02, UI-03]

# Metrics
duration: 15min
completed: 2026-03-20
---

# Phase 14 Plan 06: Data Tabs and Detail Panel Summary

**shadcn Table-based Entities/Relations/Episodes tabs with slide-in DetailPanel featuring breadcrumb in-place navigation and 3 content modes (entity/edge/episode)**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-20T18:30:00Z
- **Completed:** 2026-03-20T18:45:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- DetailPanel slide-in container with 200ms ease-out animation, 400px fixed width, X close button, breadcrumb navigation stack with in-place navigation and fresh-open reset
- EntityPanel showing name, type badge, retention status badge (using RETENTION_COLORS), summary, metadata (created_at, access_count), and clickable relationships list
- EdgePanel showing fact prominently, relation label badge, clickable source/target entity links for in-panel navigation
- EpisodePanel showing source badge (SOURCE_COLORS), monospace content with expand/collapse for >500 chars, entities extracted list with clickable navigation
- Entities tab: shadcn Table with type filter dropdown, sortable Name/Type columns, retention status badge (Normal), 30s auto-refresh, loading/error/empty states
- Relations tab: shadcn Table with Fact/From/To/Relation/Status columns, fact column prominent, 30s auto-refresh
- Episodes tab: card-style rows with source badge, source filter (git-index/hook-capture/cli-add), 30s auto-refresh, empty state CTA

## Task Commits

Each task was committed atomically:

1. **Task 1: Detail Panel (slide-in container + 3 content modes)** - `ba28043` (feat)
2. **Task 2: Entities, Relations, Episodes tabs** - `52d6eea` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `ui/src/components/panels/DetailPanel.tsx` - Slide-in container with breadcrumb navigation, X close, 3 content mode dispatch
- `ui/src/components/panels/EntityPanel.tsx` - Entity detail: name, type/retention badges, summary, metadata, relationships
- `ui/src/components/panels/EdgePanel.tsx` - Edge detail: fact prominent, label badge, clickable source/target links
- `ui/src/components/panels/EpisodePanel.tsx` - Episode detail: source badge, monospace content expand/collapse, entities extracted
- `ui/src/routes/Entities.tsx` - Entities tab with shadcn Table, type filter, sort, retention badge, DetailPanel on click
- `ui/src/routes/Relations.tsx` - Relations tab with shadcn Table, fact column, DetailPanel on click
- `ui/src/routes/Episodes.tsx` - Episodes tab with card rows, source badge, source filter, DetailPanel on click

## Decisions Made
- DetailPanel breadcrumb is a PanelItem[] state array; fresh open (item prop change) resets to [item]; in-panel navigation appends; breadcrumb ancestor click slices to that index
- Episodes tab reuses fetchDashboard(scope).recent_episodes — no dedicated episodes API endpoint exists or is needed
- Entities tab filters out nodes where type === 'Episodic' since the graph API returns both entity and episodic nodes
- PanelItem exported as type from DetailPanel.tsx so all 3 route tabs can import it from the same location

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed duplicate useAppContext import in Relations.tsx**
- **Found during:** Task 2 (Relations tab implementation)
- **Issue:** Plan template had `import { useAppContext as _ctx } from '@/context/AppContext'` as a second import of the same hook — TypeScript would error on duplicate identifier
- **Fix:** Removed the duplicate import alias; only the primary `import { useAppContext }` is used
- **Files modified:** ui/src/routes/Relations.tsx
- **Verification:** npm run build exits 0
- **Committed in:** 52d6eea (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minimal — single duplicate import removed. No scope creep.

## Issues Encountered
- Pre-existing Python test failures (circular import in `src/cli/commands/health.py`) unrelated to UI-only changes. No Python files were modified in this plan.

## Next Phase Readiness
- All 7 UI routes now render live data: Dashboard, GraphView, Search, Entities, Relations, Episodes, Settings
- DetailPanel slide-in ready for integration into Plan 05's GraphView tab (canvas node click)
- Plans 14-03 (API backend) and 14-05 (Dashboard/Graph) complete; UI is fully wired end-to-end
- Phase 14 Graph UI Redesign ready for final integration testing

---
*Phase: 14-graph-ui-redesign*
*Completed: 2026-03-20*
