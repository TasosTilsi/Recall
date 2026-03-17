---
phase: 12-db-migration
plan: "01"
subsystem: database
tags: [real-ladybug, ladybugdb, kuzu, spike, testing]

requires: []
provides:
  - "real-ladybug==0.15.1 installed and importable in .venv"
  - "spike_notes.txt documenting all 4 spike questions with vendoring scope conclusion"
  - "tests/test_storage.py rewritten with zero kuzu imports"
  - "tests/test_backend_config.py — 4 Wave 2/3 skipped stubs"
  - "tests/test_backend_integration.py — 3 Wave 2 skipped stubs"
affects:
  - "12-db-migration (plans 02–04 all depend on spike findings)"
  - "DB-01 requirement: LadybugDriver vendoring scope now known"
  - "DB-02 requirement: GraphProvider.LADYBUG absence documented"

tech-stack:
  added:
    - "real-ladybug==0.15.1 (installed in .venv)"
  patterns:
    - "Lazy import real_ladybug inside test methods to avoid kuzu C-extension conflict"
    - "Wave N skip stubs: all stub tests decorated @pytest.mark.skip(reason='Wave N: ...')"

key-files:
  created:
    - "spike_notes.txt — spike findings and vendoring conclusion"
    - "tests/test_backend_config.py — 4 BackendConfig + Neo4j URI stubs"
    - "tests/test_backend_integration.py — 3 LadybugDriver integration stubs"
  modified:
    - "tests/test_storage.py — removed import kuzu; replaced kuzu.Connection with lb.Connection; renamed .kuzu fixtures to .lbdb"

key-decisions:
  - "LadybugDriver must be vendored locally (~280 lines): real_ladybug provides only low-level C bindings (Database, Connection, AsyncConnection), no graphiti-compatible driver"
  - "GraphProvider.LADYBUG absent from graphiti-core 0.28.1: use GraphProvider.KUZU as alias (identical Cypher dialect, same FTS schema)"
  - "DB file suffix renamed from .kuzu to .lbdb: prevents accidental opens of old format files"
  - "kuzu and real_ladybug are incompatible in same Python process: use lazy imports for real_ladybug in tests until kuzu is fully removed in Wave 2"
  - "AsyncConnection is available in real_ladybug: use lb.AsyncConnection(db) as primary async engine in LadybugDriver"

patterns-established:
  - "Lazy import pattern: import real_ladybug as lb inside test method body when kuzu still present at module level"
  - "Wave stub pattern: @pytest.mark.skip(reason='Wave N: [component] not yet implemented') for all future-wave test targets"

requirements-completed: [DB-01, DB-02]

duration: 5min
completed: "2026-03-17"
---

# Phase 12 Plan 01: DB Migration Spike Summary

**real-ladybug==0.15.1 installed and spike confirmed: LadybugDriver must be vendored locally (~280 lines); kuzu and real_ladybug cannot coexist in same process; test infrastructure scaffolded for Wave 2**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-17T16:27:23Z
- **Completed:** 2026-03-17T16:32:32Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Installed `real-ladybug==0.15.1` in project `.venv` and verified importability
- Resolved all 4 spike questions; documented findings with conclusion in `spike_notes.txt`
- Rewrote `tests/test_storage.py` — zero `import kuzu` occurrences; 5/5 TestGraphSelector tests passing
- Created `tests/test_backend_config.py` (4 skipped stubs) and `tests/test_backend_integration.py` (3 skipped stubs) for Wave 2/3 targets

## Spike Findings (CONCLUSION section verbatim)

Based on spike results:

1. **LadybugDriver MUST be vendored locally (~280 lines):**
   - real_ladybug provides only low-level bindings (Database, Connection, AsyncConnection)
   - No graphiti-compatible driver exists in the package
   - Must implement: LadybugDriver class with execute_query(), setup_schema(),
     retrieve_episodes(), build_indices_and_constraints(), with_database(), clone()
   - The driver wraps lb.Database (stored as self.db) + lb.AsyncConnection for queries

2. **GraphProvider.LADYBUG does NOT exist — use GraphProvider.KUZU as alias:**
   - LadybugDB is a Kuzu fork with identical Cypher dialect and FTS schema
   - Passing GraphProvider.KUZU to get_fulltext_indices() will return the correct
     FTS index definitions for LadybugDB
   - No enum patching required

3. **.lbdb file creation works cleanly:**
   - lb.Database(path) creates directory-based DB at given path
   - Connection API is identical to kuzu: rows_as_dict(), execute() return same types
   - Safe to rename DB suffix from .kuzu to .lbdb (different format; do NOT try to open old files)

4. **AsyncConnection is available and needed for LadybugDriver:**
   - Use lb.AsyncConnection(db) as the async execution engine in LadybugDriver
   - Wrap with acquire_connection()/release_connection() for sync compatibility

**VENDORING SCOPE: MINIMAL (~280 lines)**
File: `src/storage/ladybug_driver.py`
Key: Vendor only LadybugDriver class (no operation handler classes needed)
The real_ladybug bindings handle all low-level DB operations; we just need
the graphiti-compatible wrapper that satisfies graphiti_core's driver protocol.

## Task Commits

Each task was committed atomically:

1. **Task 1: Install real-ladybug and run spike verification** - `8a3bcf4` (chore)
2. **Task 2: Rewrite test_storage.py (remove import kuzu) and create stub test files** - `3e5477d` (test)

**Plan metadata:** _(to be recorded in final commit)_

## Files Created/Modified

- `spike_notes.txt` — spike findings with answers to all 4 questions and vendoring CONCLUSION
- `tests/test_storage.py` — removed `import kuzu`, added lazy `import real_ladybug as lb` in test methods, renamed `.kuzu` fixtures to `.lbdb`
- `tests/test_backend_config.py` — 4 Wave 2/3 skip-stub tests for BackendConfig and Neo4j URI
- `tests/test_backend_integration.py` — 3 Wave 2 skip-stub tests for LadybugDriver integration

## Decisions Made

- **LadybugDriver must be vendored**: No graphiti driver in `real_ladybug` package — PR #1296 in graphiti-core not merged. Implement `src/storage/ladybug_driver.py` locally in Plan 02.
- **Use GraphProvider.KUZU as alias**: `GraphProvider.LADYBUG` absent in 0.28.1; Kuzu Cypher dialect is identical to LadybugDB since it's a fork.
- **Lazy import pattern for real_ladybug**: Both `kuzu` and `real_ladybug` register a C-level "Database" type — loading both in the same Python process causes a segfault. Until `graph_manager.py` removes `import kuzu` in Wave 2, all `real_ladybug` usages in tests use local-scope imports.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Move real_ladybug import to function scope in test_storage.py**

- **Found during:** Task 2 (test_storage.py rewrite)
- **Issue:** Plan showed `import real_ladybug as lb` at module top-level, but `kuzu` and `real_ladybug` are C extensions that both register the "Database" type — importing both in the same process causes `ImportError: generic_type: type "Database" is already registered!` followed by segfault. `graph_manager.py` still imports kuzu at module level (removed in Wave 2), so loading `test_storage.py` would segfault.
- **Fix:** Moved `import real_ladybug as lb` inside each test method that uses `lb.Connection()` in `TestPersistence` and `TestIsolation`. Module-level import removed until Wave 2 removes kuzu entirely.
- **Files modified:** `tests/test_storage.py`
- **Verification:** `pytest tests/test_storage.py::TestGraphSelector -x -q` exits 0 (5 passed)
- **Committed in:** `3e5477d` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing critical fix for process-level segfault)
**Impact on plan:** Fix necessary for tests to run at all. No scope creep. Lazy import is the standard Python pattern for optional heavy imports.

## Issues Encountered

- `kuzu` and `real_ladybug` are mutually exclusive in the same Python process. This is an expected consequence of Phase 12: as `graph_manager.py` removes `import kuzu` in Wave 2, the lazy import workaround becomes unnecessary and the standard `import real_ladybug as lb` at module top can be restored.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Plan 02 (LadybugDriver vendor):** Fully unblocked. Spike scope is confirmed: vendor `src/storage/ladybug_driver.py` (~280 lines), use `lb.Database` + `lb.AsyncConnection`, pass `GraphProvider.KUZU` to FTS helpers.
- **Plan 03 (GraphManager migration):** Depends on Plan 02. Change `import kuzu` → `import real_ladybug as lb` in `graph_manager.py`, swap `KuzuDriver` for `LadybugDriver`, rename DB paths to `.lbdb`.
- **Wave 2 test activation:** Once `graph_manager.py` removes kuzu, restore module-level `import real_ladybug as lb` in `test_storage.py`; activate stubs in `test_backend_config.py` and `test_backend_integration.py`.

---
*Phase: 12-db-migration*
*Completed: 2026-03-17*

## Self-Check: PASSED

- FOUND: .planning/phases/12-db-migration/12-01-SUMMARY.md
- FOUND: spike_notes.txt
- FOUND: tests/test_backend_config.py
- FOUND: tests/test_backend_integration.py
- FOUND: commit 8a3bcf4 (Task 1)
- FOUND: commit 3e5477d (Task 2)
- FOUND: commit edc55fd (Plan metadata)
