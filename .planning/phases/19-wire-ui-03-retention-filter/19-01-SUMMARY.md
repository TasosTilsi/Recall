---
phase: 19
plan: 01
subsystem: backend
tags: [retention, graph-service, api-route, typescript]
dependency_graph:
  requires: []
  provides: [retention_status-field, list_entities_readonly-archived-passthrough]
  affects: [src/graph/service.py, src/ui_server/routes.py, ui/src/types/api.ts]
tech_stack:
  added: []
  patterns: [per-entity-retention-status-inline-computation, module-level-import-for-testability]
key_files:
  created: []
  modified:
    - src/graph/service.py
    - src/ui_server/routes.py
    - ui/src/types/api.ts
    - tests/test_graph_service_ui.py
    - tests/test_ui_server.py
decisions:
  - Stale computed inline from created_at vs retention_days (no get_stale_uuids method exists in RetentionManager)
  - get_retention_manager promoted to module-level import so patch("src.graph.service.get_retention_manager") works in tests
  - RetentionStatus type moved to top of api.ts so GraphNode interface can reference it without forward-reference ambiguity
metrics:
  duration: 4 minutes
  completed: "2026-03-27"
  tasks_completed: 3
  files_modified: 5
requirements: [UI-03]
---

# Phase 19 Plan 01: Backend retention_status Field Summary

Add `retention_status` field to `GraphService.list_entities_readonly()`, `/api/graph` node shape, and `GraphNode` TypeScript interface — computed server-side with priority Pinned > Archived > Stale > Normal.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 19-01-01 | RED test stubs + bug fixes | 7c8d6dd | tests/test_graph_service_ui.py, tests/test_ui_server.py, src/graph/service.py |
| 19-01-02 | Compute retention_status in list_entities_readonly() | 04515a0 | src/graph/service.py |
| 19-01-03 | Add retention_status to /api/graph + GraphNode TS interface | 58be9b0 | src/ui_server/routes.py, ui/src/types/api.ts |

## Decisions Made

1. **Stale computed inline** — `get_stale_uuids()` does not exist on `RetentionManager`; stale status computed by comparing entity `created_at` with `retention_days` config directly.
2. **Module-level `get_retention_manager` import** — promoted from local function import to module-level so `patch("src.graph.service.get_retention_manager")` works in unit tests.
3. **`RetentionStatus` moved to top of `api.ts`** — ensures the type is defined before `GraphNode` references it.

## Verification

```
36 passed, 1 warning in 1.48s
```

All 36 UI tests pass including the 3 new `TestListEntitiesRetentionStatus` tests and `test_graph_node_shape_includes_retention_status`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `self.graph_manager` → `self._graph_manager` in list_entities_readonly() and list_edges()**
- **Found during:** Task 19-01-01 (RED tests were failing with AttributeError instead of assertion failure)
- **Issue:** Both `list_entities_readonly()` and `list_edges()` used `self.graph_manager` (no underscore) while the rest of the service uses `self._graph_manager`; this caused the methods to fail silently
- **Fix:** Changed both occurrences to `self._graph_manager`
- **Files modified:** src/graph/service.py
- **Commit:** 7c8d6dd

**2. [Rule 2 - Missing functionality] Promoted `get_retention_manager` to module-level import**
- **Found during:** Task 19-01-02 (patch target `src.graph.service.get_retention_manager` failed because it was a local import)
- **Issue:** Tests using `patch("src.graph.service.get_retention_manager")` fail when function is imported locally inside the try block
- **Fix:** Added module-level `from src.retention import get_retention_manager` with ImportError guard; removed local import from retention block
- **Files modified:** src/graph/service.py
- **Commit:** 04515a0

**3. [Rule 1 - Bug] Moved `RetentionStatus` type to top of api.ts**
- **Found during:** Task 19-01-03
- **Issue:** `GraphNode` interface references `RetentionStatus` defined at end of file — forward reference ambiguity in TypeScript
- **Fix:** Moved `RetentionStatus` type declaration to line 1 so it precedes all uses
- **Files modified:** ui/src/types/api.ts
- **Commit:** 58be9b0

## Known Stubs

None — all service-layer data flows through. Archived entities now pass through to the API response (no stub); client-side filtering in Plan 19-02 will hide them by default.

## Self-Check: PASSED
