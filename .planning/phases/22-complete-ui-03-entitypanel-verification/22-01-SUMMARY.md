---
phase: 22-complete-ui-03-entitypanel-verification
plan: "01"
subsystem: ui-server
tags: [ui, retention, api, typescript]
dependency_graph:
  requires: [19-wire-ui-03-retention-filter]
  provides: [retention_status in /api/detail entity response, DetailEntity.retention_status TypeScript field]
  affects: [src/ui_server/routes.py, ui/src/types/api.ts]
tech_stack:
  added: []
  patterns: [TDD red-green, lazy import in try/except, retention priority Pinned>Stale>Archived>Normal]
key_files:
  created: []
  modified:
    - src/ui_server/routes.py
    - ui/src/types/api.ts
    - tests/test_ui_server.py
decisions:
  - "Priority order Pinned > Stale > Archived > Normal — follows Phase 19 CONTEXT.md, same as /api/graph"
  - "Test created_at dates use 2026-03-15 (within 90-day window) to avoid Stale classification in non-stale tests"
  - "Patch target for retention manager is src.retention.get_retention_manager (lazy import inside try block, not routes module attribute)"
metrics:
  duration_minutes: 2
  completed_date: "2026-04-03"
  tasks_completed: 1
  files_changed: 3
---

# Phase 22 Plan 01: Add retention_status to /api/detail Entity Response — Summary

**One-liner:** Wired `/api/detail` entity branch to compute and return `retention_status` (Pinned/Stale/Archived/Normal) using same retention manager calls as `/api/graph`, with `DetailEntity` TypeScript interface updated to accept the new field.

## What Was Built

The entity detail panel in the Recall UI always showed "Normal" retention status because `/api/detail` never computed `retention_status` — it only set `pinned: bool`. This plan fixes the server side by extending the existing retention `try/except` block and updating the TypeScript type.

### Changes

**`src/ui_server/routes.py`** — Extended retention enrichment block (lines 181-217):
- Added `get_pin_state_uuids()` and `get_archive_state_uuids()` calls (batch, consistent with Phase 19 pattern)
- Compute `retention_status` using priority: Pinned > Stale > Archived > Normal
- Staleness computed inline from `entity.get("created_at")` vs `load_config().retention_days`
- Fallback: `entity.setdefault("retention_status", "Normal")` on any exception

**`ui/src/types/api.ts`** — Added `retention_status?: RetentionStatus` to `DetailEntity` interface after `pinned?` field. `RetentionStatus` type already defined at line 1.

**`tests/test_ui_server.py`** — Added `TestDetailEntityRetentionStatus` class (4 tests):
- `test_pinned_entity_returns_retention_status_pinned`
- `test_normal_entity_returns_retention_status_normal`
- `test_archived_entity_returns_retention_status_archived`
- `test_pinned_wins_over_archived`

## Verification Results

```
pytest tests/test_ui_server.py::TestDetailEntityRetentionStatus -x -q
4 passed, 1 warning in 0.80s

pytest tests/test_ui_server.py -q
21 passed, 1 warning in 6.76s

grep "retention_status" ui/src/types/api.ts
  retention_status?: RetentionStatus;

grep -c "retention_status" src/ui_server/routes.py
6
```

## Commits

| Hash | Message |
|------|---------|
| 80f9860 | test(22-01): add failing tests for retention_status on /api/detail entity response |
| fb70e4a | feat(22-01): add retention_status to /api/detail entity response and DetailEntity type |

## Deviations from Plan

**1. [Rule 1 - Bug] Test dates corrected for 90-day stale threshold**
- **Found during:** Task 1 GREEN phase
- **Issue:** Plan's `_make_app` used `created_at="2026-01-01T00:00:00Z"` (92 days before 2026-04-03) which is stale. `test_normal_entity_returns_retention_status_normal` and `test_archived_entity_returns_retention_status_archived` both expected non-stale results but entities were classified as Stale.
- **Fix:** Changed `created_at` to `"2026-03-15T00:00:00Z"` (19 days, well within 90-day window) for tests that need Normal/Archived results. The "Normal" test now correctly asserts Normal; the "Archived" test correctly asserts Archived (not Stale).
- **Files modified:** `tests/test_ui_server.py`
- **Commit:** fb70e4a

**2. [Rule 1 - Bug] Patch target corrected from routes.GraphService to retention module**
- **Found during:** Task 1 RED phase
- **Issue:** Plan's test template patched `src.ui_server.routes.GraphService` which doesn't exist as a module-level name in routes.py (service comes from `app.state`).
- **Fix:** Removed the `src.ui_server.routes.GraphService` patch; patched `src.retention.get_retention_manager` (the actual lazy import target inside the try block) alongside `src.ui_server.app.GraphService` for the service mock.
- **Files modified:** `tests/test_ui_server.py`
- **Commit:** fb70e4a

## Known Stubs

None — `retention_status` is computed from live retention manager data and returned in every entity detail response.

## Self-Check: PASSED

- [x] `src/ui_server/routes.py` — contains 6 occurrences of `retention_status`
- [x] `ui/src/types/api.ts` — contains `retention_status?: RetentionStatus` in `DetailEntity`
- [x] `tests/test_ui_server.py` — `TestDetailEntityRetentionStatus` class with 4 passing tests
- [x] Commit 80f9860 exists (RED test commit)
- [x] Commit fb70e4a exists (GREEN implementation commit)
- [x] Full test suite: 21 passed, 0 failures
