---
phase: 31-ui-adaptation
plan: 31-02
subsystem: ui_server
tags: [react, typescript, sigma.js, graph, entity-types, v3.0]
dependency_graph:
  requires: [31-01]
  provides: [UI-02, UI-03, UI-04]
  affects:
    - ui/src/lib/colors.ts
    - ui/src/types/api.ts
    - ui/src/api/client.ts
    - ui/src/components/graph/GraphCanvas.tsx
    - ui/src/components/graph/GraphLegend.tsx
    - ui/src/components/panels/EntityPanel.tsx
    - ui/src/components/panels/DetailPanel.tsx
    - ui/src/routes/Graph.tsx
tech_stack:
  added: []
  patterns: [canonical-entity-type-colors, entity-type-filter, v3.0-detail-panel]
key_files:
  created: []
  modified:
    - ui/src/lib/colors.ts
    - ui/src/components/graph/GraphCanvas.tsx
    - ui/src/components/graph/GraphLegend.tsx
    - ui/src/routes/Graph.tsx
    - ui/src/components/panels/EntityPanel.tsx
    - ui/src/components/panels/DetailPanel.tsx
decisions:
  - "DetailPanel.tsx updated alongside EntityPanel — fetchDetail signature changed to single entityId arg; required by Rule 1 (bug fix: old call site would fail at runtime)"
  - "DetailPanel data typed as DetailEntityV3 — edge/episode panel paths cast as before; no structural change"
metrics:
  duration: "420s"
  completed_date: "2026-04-21"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 8
---

# Phase 31 Plan 02: UI Frontend v3.0 Adaptation Summary

Seven TypeScript/TSX files updated to speak the v3.0 SQLite API shape: six canonical entity type colors, Sigma.js graph renderer with type filter, six-entry legend, and a detail panel showing commit_sha, content, and backlinks.

## What Was Built

### Task 1 (pre-committed as 1d18288)
- `ui/src/types/api.ts`: replaced with v3.0 types — CanonicalEntityType, GraphNode (commit_sha, no scope/retention_status), GraphEdge (from_id/to_id/relationship), DashboardData (entity_types, recent_commits), DetailEntityV3, Backlink, SearchResults
- `ui/src/api/client.ts`: fetchGraph/fetchDashboard/fetchSearch without scope param; fetchDetail(entityId) single arg

### Task 2 (eba0677)
- `ui/src/lib/colors.ts`: ENTITY_TYPE_COLORS with exactly six entries keyed by canonical type strings and Recall Obsidian hex values; removed SCOPE_COLORS, RETENTION_COLORS, SOURCE_COLORS, getRetentionBorderColor
- `ui/src/components/graph/GraphCanvas.tsx`: node color = ENTITY_TYPE_COLORS[node.type]; selectedTypes prop for entity-type filtering; no showEpisodes, EPISODE_COLOR, or retention border logic
- `ui/src/components/graph/GraphLegend.tsx`: renders six-entry type legend; no retention ring block; no colorMode prop
- `ui/src/routes/Graph.tsx`: entity-type multi-select filter toolbar with toggle buttons per type; fetchGraph() without args; no showEpisodes/scope/colorMode state

### Task 3 (64b23d2)
- `ui/src/components/panels/EntityPanel.tsx`: accepts DetailEntityV3; renders name, type badge (canonical color), tags, commit_sha, content, backlinks list (relationship label, from_name, context snippet); no retention_status/RETENTION_COLORS/summary/uuid
- `ui/src/components/panels/DetailPanel.tsx`: call site updated — fetchDetail(itemId) without itemType/scope; data typed as DetailEntityV3; EntityPanel called without onNavigate prop

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated DetailPanel.tsx call site alongside EntityPanel**
- **Found during:** Task 3
- **Issue:** DetailPanel.tsx called `fetchDetail(currentItem.itemType, currentItem.itemId, scope)` — the old three-arg signature. After Task 1 changed fetchDetail to accept only `entityId`, this call site would throw a TypeScript error and fail at runtime
- **Fix:** Updated fetchDetail call to `fetchDetail(currentItem.itemId)`, removed `useAppContext` import, removed scope from useEffect dependency array, typed data as `DetailEntityV3`, updated EntityPanel JSX to remove `onNavigate` prop
- **Files modified:** `ui/src/components/panels/DetailPanel.tsx`
- **Commit:** 64b23d2

## Known Stubs

None — all UI components wire to real API endpoints. Graph, legend, filter, and detail panel all render live data from the v3.0 SQLite-backed API.

## Self-Check: PASSED

Files verified:
- FOUND: ui/src/lib/colors.ts
- FOUND: ui/src/components/graph/GraphCanvas.tsx
- FOUND: ui/src/components/graph/GraphLegend.tsx
- FOUND: ui/src/routes/Graph.tsx
- FOUND: ui/src/components/panels/EntityPanel.tsx
- FOUND: ui/src/components/panels/DetailPanel.tsx

Commits verified:
- 1d18288: feat(31-02): replace v2.0 API types and client with v3.0 shape
- eba0677: feat(31-02): update graph rendering to v3.0 — canonical type colors, filter, no episodes
- 64b23d2: feat(31-02): update EntityPanel and DetailPanel to v3.0 detail shape
