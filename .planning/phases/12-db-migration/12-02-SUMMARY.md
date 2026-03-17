---
phase: 12-db-migration
plan: "02"
subsystem: database
tags: [real-ladybug, ladybugdb, ladybug-driver, kuzu-removal, graph-manager, vendor]

requires:
  - "12-01 (spike findings: vendoring scope, AsyncConnection API, .lbdb creation)"
provides:
  - "src/storage/ladybug_driver.py — vendored LadybugDriver class, graphiti-core compatible"
  - "src/storage/graph_manager.py — rewritten with LadybugDriver, zero Kuzu workarounds"
  - "src/config/paths.py — DB suffix renamed from .kuzu to .lbdb"
  - "pyproject.toml — real-ladybug==0.15.1 added, kuzu==0.11.3 removed, graphiti-core[neo4j]"
  - "tests/test_storage.py — 14/14 passing with real LadybugDB connections"
  - "tests/test_backend_integration.py — test_ladybug_driver_creates_fresh_db passing"
affects:
  - "12-03 and 12-04 (storage layer now LadybugDB, no kuzu anywhere)"
  - "DB-01 requirement: LadybugDriver vendored and in production use"

tech-stack:
  added:
    - "real-ladybug==0.15.1 as direct pyproject.toml dependency"
    - "graphiti-core[neo4j]==0.28.1 (replaces [kuzu] extra)"
  patterns:
    - "Embed SCHEMA_QUERIES locally to avoid importing graphiti_core.driver.kuzu_driver (which has top-level import kuzu)"
    - "Import GraphProvider from graphiti_core.driver.driver (not kuzu_driver) — no kuzu transitive dep"
    - "AsyncConnection as primary query engine; Connection for schema setup only"

key-files:
  created:
    - "src/storage/ladybug_driver.py — vendored LadybugDriver + LadybugDriverSession (~200 lines)"
  modified:
    - "src/storage/graph_manager.py — zero kuzu imports, zero workarounds, uses LadybugDriver"
    - "src/config/paths.py — .kuzu suffix renamed to .lbdb throughout"
    - "pyproject.toml — kuzu==0.11.3 removed, real-ladybug==0.15.1 added"
    - "tests/test_backend_integration.py — Wave 2 skip removed; assertion bug fixed"

key-decisions:
  - "Import GraphProvider from graphiti_core.driver.driver not kuzu_driver — kuzu_driver has top-level import kuzu which fails after kuzu uninstall"
  - "Embed SCHEMA_QUERIES as string constant in ladybug_driver.py to break the kuzu_driver import chain"
  - "LadybugDriverSession mirrors KuzuDriverSession exactly (no-op session for embedded DB)"
  - "provider = GraphProvider.KUZU on LadybugDriver — Cypher dialect is identical; no enum patching needed"

requirements-completed: [DB-01]

duration: 7min
completed: "2026-03-17"
---

# Phase 12 Plan 02: Vendor LadybugDriver and Rewrite GraphManager Summary

**Vendored LadybugDriver (~200 lines) wrapping real_ladybug AsyncConnection; GraphManager rewritten with zero Kuzu imports or workarounds; paths renamed .kuzu -> .lbdb; kuzu removed from deps**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-17T16:35:50Z
- **Completed:** 2026-03-17T16:43:13Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Vendored `src/storage/ladybug_driver.py` (~200 lines): full graphiti-compatible LadybugDriver + LadybugDriverSession
- All 3 KuzuDB workarounds eliminated:
  1. `clone()` returns real copy with `_database` set (KuzuDriver returned self — no-op)
  2. `setup_schema()` in `__init__` creates tables/FTS (KuzuDriver `build_indices_and_constraints` was no-op)
  3. Zero `import kuzu` anywhere in `src/storage/`
- `GraphManager.get_driver()` returns `LadybugDriver` — verified via runtime type check
- `src/config/paths.py`: `.kuzu` → `.lbdb` suffix for both GLOBAL_DB_PATH and PROJECT_DB_NAME
- `pyproject.toml`: `kuzu==0.11.3` removed, `real-ladybug==0.15.1` added, `graphiti-core[neo4j]` replaces `[kuzu]`
- Removed Wave 2 skip from `test_ladybug_driver_creates_fresh_db`; test now passes
- All 15 tests pass (14 test_storage.py + 1 integration)

## Key Implementation Details

### ladybug_driver.py: Breaking the kuzu_driver import chain

The critical discovery: `graphiti_core/driver/kuzu_driver.py` has `import kuzu` at the **top level**. After kuzu is uninstalled, importing `from graphiti_core.driver.kuzu_driver import GraphProvider, SCHEMA_QUERIES` raises `ModuleNotFoundError: No module named 'kuzu'`.

Solution:
1. `GraphProvider` is available from `graphiti_core.driver.driver` (no kuzu dep)
2. `SCHEMA_QUERIES` embedded as string constant in `ladybug_driver.py` directly

### Task Commits

1. **Task 1: Vendor LadybugDriver** - `afe5287` (feat)
2. **Task 2: Rewrite GraphManager, paths, pyproject.toml** - already committed in prior session

## Files Created/Modified

- `src/storage/ladybug_driver.py` — vendored LadybugDriver + LadybugDriverSession, SCHEMA_QUERIES embedded
- `src/storage/graph_manager.py` — rewritten: zero kuzu imports, zero workarounds, uses LadybugDriver
- `src/config/paths.py` — `.kuzu` → `.lbdb` suffix
- `pyproject.toml` — kuzu removed, real-ladybug added, graphiti-core[neo4j]
- `tests/test_backend_integration.py` — skip removed, assertion bug fixed

## Decisions Made

- **Embed SCHEMA_QUERIES locally**: `graphiti_core.driver.kuzu_driver` has top-level `import kuzu` — after kuzu uninstall it fails. Copied DDL string verbatim from kuzu_driver.py 0.28.1 into ladybug_driver.py.
- **GraphProvider from driver.driver**: `GraphProvider` enum lives in both `driver.driver` and `kuzu_driver` but only the former is kuzu-free.
- **AsyncConnection for queries**: spike confirmed `lb.AsyncConnection` is available; use it as primary engine matching KuzuDriver pattern.
- **delete_all_indexes + session required**: `GraphDriver` ABC requires both — implemented as no-ops (same as KuzuDriver) for embedded DB.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Import chain: graphiti_core.driver.kuzu_driver fails after kuzu uninstall**

- **Found during:** Task 1 verification
- **Issue:** The plan showed `from graphiti_core.driver.kuzu_driver import GraphProvider, SCHEMA_QUERIES` but `kuzu_driver.py` has `import kuzu` at the top level. Uninstalling kuzu causes `ModuleNotFoundError` when importing from kuzu_driver.
- **Fix:** Import `GraphProvider` from `graphiti_core.driver.driver` instead; embed `SCHEMA_QUERIES` as a local string constant copied from kuzu_driver.py 0.28.1.
- **Files modified:** `src/storage/ladybug_driver.py`
- **Commit:** `afe5287`

**2. [Rule 1 - Bug] Test assertion raises AttributeError before `or True` short-circuit**

- **Found during:** Task 1 test execution
- **Issue:** `test_ladybug_driver_creates_fresh_db` had `assert driver._database is not None or True` — but `_database` is not set on the instance, raising `AttributeError` before Python evaluates `or True`.
- **Fix:** Changed assertion to `assert getattr(driver, '_database', None) is None` (verifies `_database` not set in `__init__`, which is the correct behavior).
- **Files modified:** `tests/test_backend_integration.py`
- **Commit:** `afe5287`

---

**Total deviations:** 2 auto-fixed (Rule 1 — bugs in plan-provided code)

## Issues Encountered

- `graphiti_core.driver.kuzu_driver` imports kuzu at module level — any import from it fails post-uninstall. All needed values (GraphProvider, SCHEMA_QUERIES) must be sourced elsewhere.
- `GraphDriver` ABC now requires `session()` and `delete_all_indexes()` abstract methods (not in plan's interface reference). Both implemented as no-ops following KuzuDriver pattern.

## User Setup Required

None.

## Next Phase Readiness

- **Plan 03 (service.py migration):** Already completed in a prior session (commit `dfa9512`). Readonly methods rewritten to use `driver.execute_query()`.
- **Plan 04 (end-to-end integration):** Unblocked. All storage layer changes complete.

---
*Phase: 12-db-migration*
*Completed: 2026-03-17*

## Self-Check: PASSED

- FOUND: src/storage/ladybug_driver.py
- FOUND: src/storage/graph_manager.py
- FOUND: src/config/paths.py
- FOUND: .planning/phases/12-db-migration/12-02-SUMMARY.md
- FOUND: commit afe5287 (Task 1: vendor LadybugDriver)
- VERIFIED: 15 tests pass (test_storage.py 14 + test_backend_integration.py 1)
- VERIFIED: kuzu not installed (pip show kuzu → not found)
- VERIFIED: GraphManager.get_driver(GLOBAL) returns LadybugDriver
