---
phase: 17-fix-stale-binary-references
plan: 02
subsystem: testing
tags: [docs, pytest, neo4j, graphiti, recall, verification]

# Dependency graph
requires:
  - phase: 15-local-memory-system
    provides: "MEM-03 requirement and verification report being corrected"
  - phase: 16-rename-cli-consolidation
    provides: "recall CLI surface that replaced graphiti memory search"
  - phase: 12-db-migration
    provides: "Neo4j fail-fast implementation (sys.exit in _make_driver)"
provides:
  - "15-VERIFICATION.md MEM-03 row uses correct recall search CLI reference"
  - "test_neo4j_unreachable_raises_on_init active and passing (Neo4j fail-fast confirmed)"
affects: [future-audits, test-suite, verification-reports]

# Tech tracking
tech-stack:
  added: []
  patterns: ["unittest.mock.patch for lazy local imports (patch module.function not caller)"]

key-files:
  created: []
  modified:
    - ".planning/phases/15-local-memory-system/15-VERIFICATION.md"
    - "tests/test_backend_config.py"

key-decisions:
  - "patch src.llm.config.load_config (not src.storage.graph_manager.load_config) because load_config is a lazy local import inside _make_driver — patching the defining module is the correct approach"
  - "Updated test body to match current GraphManager API: no config= kwarg in __init__, GraphScope.GLOBAL required for get_driver()"

patterns-established:
  - "When unskipping a test, verify the test body matches the current implementation API — skip decorators can mask API drift"

requirements-completed: [MEM-03]

# Metrics
duration: 2min
completed: 2026-03-21
---

# Phase 17 Plan 02: Fix Stale Binary References (Docs + Test) Summary

**MEM-03 VERIFICATION.md reference corrected from graphiti memory search to recall search; stale Wave 3 skip removed from test_neo4j_unreachable_raises_on_init with test body updated to current GraphManager API — 4 passed, 0 skipped**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-21T16:13:13Z
- **Completed:** 2026-03-21T16:15:11Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Replaced all 3 occurrences of `graphiti memory search` in 15-VERIFICATION.md with `recall search` — MEM-03 table row, artifact description, and summary paragraph all updated
- Removed stale `@pytest.mark.skip(reason="Wave 3: Neo4j fail-fast not yet implemented")` from `test_neo4j_unreachable_raises_on_init`
- Updated test body to match current `GraphManager` API: `GraphManager()` (no args), `get_driver(scope=GraphScope.GLOBAL)`, patching `src.llm.config.load_config` for local import isolation
- Test suite for `test_backend_config.py` went from 3 passed 1 skipped to 4 passed 0 skipped
- 15-VERIFICATION.md overall `status: passed` and all verification scores unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Update Phase 15 VERIFICATION.md MEM-03 reference** - `b6c6ccf` (docs)
2. **Task 2: Remove stale @pytest.mark.skip from test_neo4j_unreachable_raises_on_init** - `061aa99` (fix)

## Files Created/Modified
- `.planning/phases/15-local-memory-system/15-VERIFICATION.md` - Replaced 3 occurrences of `graphiti memory search` with `recall search` (MEM-03 row, artifact row, summary line)
- `tests/test_backend_config.py` - Removed skip decorator; updated test body to current GraphManager API with mock.patch for lazy import

## Decisions Made
- **Patch target for lazy import:** `src.llm.config.load_config` not `src.storage.graph_manager.load_config` — `_make_driver` uses a local import `from src.llm.config import load_config`, so mock.patch must target the defining module
- **Test API update:** Replaced `GraphManager(config=config)` (old Phase 12 draft API) with `GraphManager()` + `patch` to inject Neo4j config; replaced `get_driver(scope=None)` with `get_driver(scope=GraphScope.GLOBAL)`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed stale API calls in test body after removing skip**
- **Found during:** Task 2 (Remove @pytest.mark.skip)
- **Issue:** Test body used old GraphManager API from Phase 12 draft: `GraphManager(config=config)` (constructor doesn't accept `config=`) and `get_driver(scope=None)` (requires a `GraphScope` enum). Test was written before the final API was finalized, then immediately skipped.
- **Fix:** Updated constructor to `GraphManager()`, added `unittest.mock.patch("src.llm.config.load_config")` to inject Neo4j config, updated `get_driver(scope=GraphScope.GLOBAL)`. Removed unused `tomllib` import.
- **Files modified:** `tests/test_backend_config.py`
- **Verification:** `pytest tests/test_backend_config.py -v` → 4 passed, 0 skipped
- **Committed in:** `061aa99` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in test body)
**Impact on plan:** Necessary for test correctness — skip masked API drift from Phase 12 implementation. No scope creep.

## Issues Encountered
- `mock.patch("src.storage.graph_manager.load_config")` raised `AttributeError` because `load_config` is a lazy local import inside `_make_driver`, not at module scope. Fixed by patching `src.llm.config.load_config` (the defining module).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 17-02 correctness fixes complete — no blockers
- Phase 17 gap closure: both stale binary references (17-01 pyproject entrypoints, 17-02 docs + test) now corrected

---
*Phase: 17-fix-stale-binary-references*
*Completed: 2026-03-21*
