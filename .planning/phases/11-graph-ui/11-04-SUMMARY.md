---
phase: 11-graph-ui
plan: "04"
subsystem: ui
tags: [typer, fastapi, uvicorn, cli, graph-ui, aiofiles]

# Dependency graph
requires:
  - phase: 11-02
    provides: FastAPI create_app() factory and LLMConfig.ui_api_port field
  - phase: 11-03
    provides: Pre-built Next.js ui/out/ static export committed to git
provides:
  - graphiti ui Typer command with port pre-flight, scope resolution, and uvicorn launch
  - ui_command registered in src/cli/__init__.py (18th command)
  - aiofiles>=23.0.0 and fastapi>=0.135.0 declared in pyproject.toml
  - Phase 11 VALIDATION.md marked complete (nyquist_compliant, wave_0_complete)
affects:
  - phase-12-multi-provider-llm (uses same CLI registration pattern)
  - MANIFEST.in / wheel packaging (TODO comment left for Phase 12)

# Tech tracking
tech-stack:
  added:
    - aiofiles>=23.0.0 (required by FastAPI StaticFiles async file serving)
    - fastapi>=0.135.0 (updated from 0.111.0 to match plan requirement)
  patterns:
    - Port pre-flight check via socket.bind() before server launch
    - Module-level _REPO_ROOT via os.path.dirname chain for testable path resolution
    - subprocess imported at module level (patchable) even when not called at runtime

key-files:
  created:
    - src/cli/commands/ui.py
  modified:
    - src/cli/__init__.py
    - pyproject.toml
    - .planning/phases/11-graph-ui/11-VALIDATION.md

key-decisions:
  - "_REPO_ROOT computed via os.path.dirname chain at module level so Path() calls inside the function body are patchable by tests (Path(__file__).parent chain is not patchable via mock_path_cls.return_value.__truediv__)"
  - "subprocess imported at module level to satisfy test_global_flag patch target even though it is not called at runtime"
  - "ui/out/ path uses Path(_REPO_ROOT) / 'ui/out' (single truediv) so the mock chain mock_path_cls.return_value.__truediv__.return_value.exists matches the test expectation"
  - "aiofiles added to deps (required by FastAPI StaticFiles for async serving); fastapi spec bumped to >=0.135.0"
  - "ui/out/ wheel packaging deferred to Phase 12 — TODO comment added to pyproject.toml"

patterns-established:
  - "Pre-flight pattern: socket.bind() probe → exit 1 with message → static dir exists check → resolve_scope → launch"
  - "Module-level _REPO_ROOT string constant avoids Path mock interference while keeping path resolution correct"

requirements-completed:
  - UI-01
  - UI-02
  - UI-03

# Metrics
duration: 15min
completed: "2026-03-09"
---

# Phase 11 Plan 04: CLI Wiring Summary

**`graphiti ui` Typer command wired to FastAPI backend with port pre-flight, scope resolution, and uvicorn launch — all 8 Phase 11 tests GREEN, 293 total tests passing**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-09T10:30:00Z
- **Completed:** 2026-03-09T10:45:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Created `src/cli/commands/ui.py` — port pre-flight check (socket.bind), static dir check, resolve_scope, uvicorn.run foreground launch
- Registered `graphiti ui` as the 18th command in `src/cli/__init__.py`
- Added `aiofiles>=23.0.0` and updated `fastapi>=0.135.0` in `pyproject.toml`; added TODO for wheel packaging
- All 8 Phase 11 tests GREEN; full 293-test suite passing with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create src/cli/commands/ui.py** - `30ae7e2` (feat)
2. **Task 2: Register UI command, add deps** - `c06beee` (feat)
3. **Task 3: Mark validation complete** - `aa984a5` (docs)

## Files Created/Modified

- `src/cli/commands/ui.py` — graphiti ui Typer command (port pre-flight, scope, uvicorn launch)
- `src/cli/__init__.py` — ui_command import and registration (18th command)
- `pyproject.toml` — aiofiles dep added, fastapi bumped to >=0.135.0, TODO for wheel packaging
- `.planning/phases/11-graph-ui/11-VALIDATION.md` — nyquist_compliant and wave_0_complete set to true, all automated rows marked green

## Decisions Made

- `_REPO_ROOT` computed via `os.path.dirname` chain at module level (not `Path(__file__)`), so `Path(...)` calls inside the function body are patchable. The test mock `mock_path_cls.return_value.__truediv__.return_value` only matches `Path(x) / y` (one truediv), not `Path(x).parent.parent.../` chains.
- `import subprocess` added at module level to satisfy `patch("src.cli.commands.ui.subprocess")` in `test_global_flag` — the test patches it even though the command never calls it at runtime.
- `Path(_REPO_ROOT) / "ui/out"` uses a single truediv so the mock chain aligns with test expectations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Path mock alignment — restructured static_dir path construction**
- **Found during:** Task 1 (test_missing_static_dir failure)
- **Issue:** Plan specified `Path(__file__).parent.parent.parent.parent / "ui" / "out"` but `test_missing_static_dir` mocks `Path` and checks `mock_path_cls.return_value.__truediv__.return_value.exists` — this only intercepts a single truediv, not a chained `.parent` + two truedevs
- **Fix:** Compute `_REPO_ROOT` via `os.path.dirname` chain at module level; use `Path(_REPO_ROOT) / "ui/out"` (single truediv) in the function body
- **Files modified:** `src/cli/commands/ui.py`
- **Verification:** `test_missing_static_dir` passes
- **Committed in:** `30ae7e2` (Task 1 commit)

**2. [Rule 3 - Blocking] Added missing subprocess import for test patch target**
- **Found during:** Task 1 (test_global_flag AttributeError on subprocess)
- **Issue:** `test_global_flag` patches `src.cli.commands.ui.subprocess` but plan code didn't import subprocess
- **Fix:** Added `import subprocess` at module level
- **Files modified:** `src/cli/commands/ui.py`
- **Verification:** `test_global_flag` passes
- **Committed in:** `30ae7e2` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes required for tests to pass. No scope creep — path resolution behaviour is functionally identical.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## Next Phase Readiness

- Phase 11 (Graph UI) is fully complete — all 3 requirements (UI-01, UI-02, UI-03) delivered
- `graphiti ui` command available end-to-end: port pre-flight → scope resolution → FastAPI + Next.js static UI on port 8765
- Phase 12 (Multi-Provider LLM) is next — pre-check: verify graphiti-core 0.28.1 internal openai version pin before adding openai SDK 2.x dep

---
*Phase: 11-graph-ui*
*Completed: 2026-03-09*
