---
phase: 19-wire-ui-03-retention-filter
plan: "03"
subsystem: testing
tags: [pytest, fastapi, testclient, integration-tests, retention-status]

requires:
  - phase: 19-01
    provides: retention_status field computed in list_entities_readonly() and exposed in /api/graph
  - phase: 19-02
    provides: Entities.tsx retention filter Combobox + Graph.tsx border rings

provides:
  - 5 integration tests covering retention_status end-to-end pipeline (service -> API -> node shape)
  - Full test suite green (395 pass, 2 pre-existing storage failures unrelated to Phase 19)
  - TypeScript build clean (tsc -b passes, vite build succeeds)
  - Human smoke test checklist documented (pending human verification)
  - _is_recall_hook alias added to installer.py (bug fix)

affects: [phase-20, milestone-complete, v20-MILESTONE-AUDIT]

tech-stack:
  added: []
  patterns:
    - "Integration tests use TestClient + patch('src.ui_server.app.GraphService') — same pattern as test_ui_server.py"
    - "Service-level tests bypass __init__ via GraphService.__new__() and mock _resolve_db_path, _get_group_id"
    - "get_retention_manager patched at src.graph.service.get_retention_manager for isolation"

key-files:
  created:
    - tests/test_phase19_integration.py
  modified:
    - src/hooks/installer.py
    - ui/out/ (rebuilt static assets)

key-decisions:
  - "Pre-existing test_storage failures (test_project_driver_creation, test_project_switching) are out of scope — logged to deferred-items"
  - "_is_recall_hook alias added as backward compat rather than renaming _is_graphiti_hook — avoids breaking any callers of the original name"
  - "Task 19-03-03 (human smoke test) documented as pending human verification — not blocked"

patterns-established:
  - "Integration test pattern: _make_entity() helper + patch-based TestClient for API shape assertions"
  - "Fallback test pattern: patch get_retention_manager with side_effect=RuntimeError, assert all entities get 'Normal'"

requirements-completed: [UI-03]

duration: 12min
completed: 2026-03-27
---

# Phase 19 Plan 03: Integration Tests + Human Smoke Test Summary

**5 end-to-end integration tests verifying retention_status flows from service through /api/graph API to Sigma.js node shape, with full suite green (395/397 tests pass)**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-27T22:56:26Z
- **Completed:** 2026-03-27T23:08:30Z
- **Tasks:** 3 (2 automated + 1 pending human verification)
- **Files modified:** 3

## Accomplishments

- 5 integration tests cover the full retention_status pipeline: all statuses present, archived not excluded, Pinned priority over Archived, graceful fallback on exception, dashboard unaffected
- Full Python test suite: 395 passed, 2 pre-existing storage failures (pre-Phase-19, out of scope)
- TypeScript build: `tsc -b` clean, `vite build` successful with updated hashed bundles
- Auto-fixed `_is_recall_hook` missing from installer.py (quick task commit had updated tests but not the impl)

## Task Commits

Each task was committed atomically:

1. **Task 19-03-01: Create integration test file + auto-fix _is_recall_hook** - `a12451b` (test + fix)
2. **Task 19-03-02: Full suite verification + TypeScript build** - `6a03b27` (chore: rebuild UI)

**Plan metadata:** (to be added after docs commit)

## Files Created/Modified

- `tests/test_phase19_integration.py` - 5 integration tests for retention_status end-to-end pipeline
- `src/hooks/installer.py` - Added `_is_recall_hook = _is_graphiti_hook` alias (auto-fix)
- `ui/out/` - Rebuilt static assets (hashed bundle names updated by vite build)

## Decisions Made

- Pre-existing `test_storage` failures are out of scope (existed before Phase 19). Logged to deferred-items.
- `_is_recall_hook` added as an alias rather than renaming `_is_graphiti_hook` to preserve backward compat.
- Human smoke test (Task 19-03-03) is documented below as pending human verification — not automated.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added _is_recall_hook alias to src/hooks/installer.py**
- **Found during:** Task 19-03-01 (verify existing test suite green)
- **Issue:** A recent quick task commit updated `tests/test_global_hooks_installer.py` to import `_is_recall_hook` but did not add that name to `installer.py` — the function was still named `_is_graphiti_hook`. Import error caused entire test collection to fail.
- **Fix:** Added `_is_recall_hook = _is_graphiti_hook` alias after the function definition in `installer.py`.
- **Files modified:** `src/hooks/installer.py`
- **Verification:** `pytest tests/test_global_hooks_installer.py` → 13 passed
- **Committed in:** `a12451b` (Task 19-03-01 commit)

**2. [Rule 3 - Blocking] Merged main into worktree branch to get 19-01 and 19-02 changes**
- **Found during:** Task 19-03-01 setup
- **Issue:** Worktree `worktree-agent-a01d7151` was at `0d30978` (before 19-01/02 commits). STATE.md said "Completed 19-02-PLAN.md" but the implementation wasn't in this worktree.
- **Fix:** `git merge main --no-edit` — fast-forward merge brought in all 19-01 and 19-02 changes.
- **Files modified:** 29 files (service.py, routes.py, Entities.tsx, Graph.tsx, types/api.ts, etc.)
- **Verification:** All 19-01/19-02 tests pass, integration tests pass.
- **Committed in:** Not a separate commit — part of merge operation before task execution.

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both necessary for plan execution. No scope creep.

## Human Smoke Test — PENDING HUMAN VERIFICATION

**Task 19-03-03** requires manual browser verification. Launch with:

```bash
recall ui
```

Then verify all 4 checklist items:

**1. Entities tab — default view:**
- Open `http://localhost:8765`, navigate to Entities tab
- Entity table loads with Name, Type, Status, Scope columns
- Status badges show dynamic colors (green for Normal, amber for Pinned, etc.) — NOT all hardcoded "Normal"
- Archived entities are NOT visible in default view

**2. Entities tab — retention filter:**
- Locate "All statuses" dropdown next to "All types" dropdown in toolbar
- Click "All statuses" — confirm 4 options: Pinned, Normal, Stale, Archived
- Select "Archived" — confirm archived entities appear in table
- Select "Pinned" (multi-select) — confirm both Pinned and Archived entities visible
- Deselect all — confirm returns to default (all except archived)
- Entity count updates correctly with filter changes

**3. Graph tab — node rings:**
- Confirm entity nodes render with colored border rings:
  - Pinned: amber ring (#fbbf24)
  - Stale: red ring (#f87171)
  - Archived: gray ring (#94a3b8)
  - Normal: no visible ring
- Entity-type fill colors preserved (rings are a second signal)

**4. Graph tab — legend:**
- "Retention" legend section appears
- 4 entries: Pinned, Stale, Archived, Normal with ring swatches (hollow circles)

**Status:** Pending human approval. Type "approved" if all 4 checks pass.

## Deferred Items

Pre-existing test failures (out of scope for Phase 19):

- `tests/test_storage.py::TestGraphManagerProject::test_project_driver_creation` — asserts `.graphiti` dir exists but driver creates `.recall` dir (post-Phase 16 rename). Pre-Phase-19.
- `tests/test_storage.py::TestGraphManagerProject::test_project_switching` — same root cause.

## Issues Encountered

- Worktree was behind main by 8 commits (19-01 and 19-02 work). Resolved via `git merge main`.
- `tsc` binary not found in PATH — resolved by running `npm install` in `ui/` first, then using `npm run build`.

## Next Phase Readiness

- Phase 19 is complete pending human smoke test approval (Task 19-03-03)
- All automated tests pass; TypeScript is clean
- After human approval: Phase 19 → `gsd:complete-milestone` to close v2.0

---
*Phase: 19-wire-ui-03-retention-filter*
*Completed: 2026-03-27*

## Self-Check: PASSED

- tests/test_phase19_integration.py FOUND
- src/hooks/installer.py FOUND (_is_recall_hook alias added)
- Commits a12451b, 6a03b27, 67e1674 FOUND
