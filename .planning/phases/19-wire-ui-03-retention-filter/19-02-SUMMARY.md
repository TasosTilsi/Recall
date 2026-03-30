---
phase: 19-wire-ui-03-retention-filter
plan: "02"
subsystem: ui
tags: [shadcn, sigma, react, typescript, retention, combobox, graph]

# Dependency graph
requires:
  - phase: 19-01
    provides: retention_status field in GraphNode API response + types/api.ts update
provides:
  - Multi-select retention filter Combobox in Entities toolbar
  - Dynamic retention status badge in Entities table (replaces hardcoded "Normal")
  - Sigma.js node border rings (borderColor + borderSize) for Pinned/Stale/Archived entities
  - GraphLegend retention ring panel stacked below entity-type legend
  - getRetentionBorderColor() helper in colors.ts
affects: [19-03-testing, graph-ui, entities-table]

# Tech tracking
tech-stack:
  added: [shadcn popover, shadcn command, cmdk]
  patterns:
    - Multi-select Combobox via Popover + Command (shadcn official recipe)
    - Sigma.js borderColor/borderSize node attributes for retention rings
    - Stacked glassmorphism legend panels (flex-col gap-3) in GraphLegend

key-files:
  created:
    - ui/src/components/ui/popover.tsx
    - ui/src/components/ui/command.tsx
    - ui/src/components/ui/dialog.tsx
    - ui/src/components/ui/input-group.tsx
    - ui/src/components/ui/textarea.tsx
  modified:
    - ui/src/lib/colors.ts
    - ui/src/components/graph/GraphCanvas.tsx
    - ui/src/components/graph/GraphLegend.tsx
    - ui/src/routes/Entities.tsx
    - ui/src/components/ui/button.tsx
    - ui/package.json
    - ui/package-lock.json

key-decisions:
  - "shadcn popover was already partially installed (skipped as identical); command.tsx was newly installed"
  - "getRetentionBorderColor uses string | undefined parameter (not strict RetentionStatus type) to match GraphNode.retention_status optional field"
  - "Retention ring legend stacked below entity-type legend in single absolute-positioned wrapper div"

patterns-established:
  - "Retention filter: empty array = show all non-Archived (default); non-empty = show only selected statuses"
  - "Sigma rings: entity nodes only (not episode squares); borderSize=0 for Normal/undefined"

requirements-completed: [UI-03]

# Metrics
duration: 2min
completed: 2026-03-27
---

# Phase 19 Plan 02: Frontend Retention Filter + Graph Node Rings Summary

**Multi-select retention filter Combobox in Entities toolbar, dynamic retention badges, Sigma.js colored border rings on entity nodes, and stacked GraphLegend retention panel — all wired to retention_status from 19-01 API**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-27T17:46:39Z
- **Completed:** 2026-03-27T17:48:58Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments
- Installed shadcn popover + command components (Wave 0 prerequisite for Combobox)
- Added `getRetentionBorderColor()` helper, Sigma node rings in `GraphCanvas.tsx`, and stacked retention legend in `GraphLegend.tsx`
- Added multi-select retention filter Combobox to Entities toolbar with correct default behavior (hides Archived) and dynamic status badges

## Task Commits

Each task was committed atomically:

1. **Task 1: Install shadcn popover + command** - `b0cb2c4` (chore)
2. **Task 2: Graph node rings + legend panel** - `af8fa49` (feat)
3. **Task 3: Entities filter Combobox + dynamic badge** - `93d84e5` (feat)

## Files Created/Modified
- `ui/src/components/ui/popover.tsx` - Radix UI Popover wrapper (shadcn)
- `ui/src/components/ui/command.tsx` - cmdk Command palette wrapper (shadcn)
- `ui/src/components/ui/dialog.tsx` - shadcn dependency installed alongside command
- `ui/src/components/ui/input-group.tsx` - shadcn dependency installed alongside command
- `ui/src/components/ui/textarea.tsx` - shadcn dependency installed alongside command
- `ui/src/lib/colors.ts` - Added `getRetentionBorderColor()` helper
- `ui/src/components/graph/GraphCanvas.tsx` - Added `borderColor` + `borderSize` to entity node attributes
- `ui/src/components/graph/GraphLegend.tsx` - Restructured to stack entity-type and retention ring legend panels
- `ui/src/routes/Entities.tsx` - Multi-select Combobox, retention filter useMemo logic, dynamic badges
- `ui/src/components/ui/button.tsx` - Updated by shadcn install (minor)

## Decisions Made
- `getRetentionBorderColor` parameter typed as `string | undefined` (not strict `RetentionStatus`) to gracefully handle the optional field from `GraphNode.retention_status?`
- shadcn `popover.tsx` was already present in the repo (skipped as identical by shadcn installer); `command.tsx` was newly created
- Retention legend placed as second card below entity-type legend inside a single `absolute bottom-4 right-4 z-10` wrapper with `flex flex-col gap-3`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `npx shadcn@latest add popover command --yes` prompted interactively for `button.tsx` overwrite. Piped `echo "y"` to handle non-interactively. Both components installed successfully.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 19-03 (tests + human smoke test) is unblocked
- Retention filter is fully wired end-to-end: API (19-01) → Entities table filter + graph rings (19-02) → verification (19-03)
- `recall ui` smoke test: visit Entities tab, verify Archived entities hidden by default, select "Archived" in dropdown to reveal them

---
*Phase: 19-wire-ui-03-retention-filter*
*Completed: 2026-03-27*

## Self-Check: PASSED

- FOUND: ui/src/components/ui/popover.tsx
- FOUND: ui/src/components/ui/command.tsx
- FOUND: ui/src/lib/colors.ts (with getRetentionBorderColor)
- FOUND: ui/src/routes/Entities.tsx (retentionFilter state + Combobox)
- FOUND: .planning/phases/19-wire-ui-03-retention-filter/19-02-SUMMARY.md
- FOUND: commit b0cb2c4 (task 1)
- FOUND: commit af8fa49 (task 2)
- FOUND: commit 93d84e5 (task 3)
- FOUND: commit cd8346d (metadata)
