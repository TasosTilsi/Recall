---
phase: 11-graph-ui
plan: "01"
subsystem: testing
tags: [typer, fastapi, tdd, red-scaffold, ui, graph-visualization]

# Dependency graph
requires: []
provides:
  - "RED test scaffold for graphiti ui CLI command (4 failing tests)"
  - "RED test scaffold for FastAPI UI server and LLMConfig UI ports (4 failing tests)"
affects:
  - "11-02 (must turn TestAPIRoutes and TestLLMConfigUI GREEN)"
  - "11-04 (must turn TestUICommand GREEN)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED scaffold: imports deferred into test methods so 4 tests are collected but fail at runtime (avoids collection-error vs FAILED distinction)"

key-files:
  created:
    - tests/test_ui_command.py
    - tests/test_ui_server.py
  modified: []

key-decisions:
  - "Defer src.cli.commands.ui import inside _make_app() helper so pytest collects 4 tests rather than 1 collection error — cleaner RED count"
  - "TestLLMConfigUI uses load_config() directly (not a new import) so the AttributeError on ui_api_port is the sole RED signal — no chain of missing imports needed"

patterns-established:
  - "RED scaffold pattern: lazy imports inside test methods allow collection without production module existing"

requirements-completed:
  - UI-01
  - UI-02
  - UI-03

# Metrics
duration: 2min
completed: 2026-03-08
---

# Phase 11 Plan 01: Graph UI RED Test Scaffold Summary

**8-test TDD RED scaffold for graphiti ui CLI command and FastAPI UI server — all fail with ModuleNotFoundError or AttributeError, establishing contracts for Plans 11-02 and 11-04**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-08T10:33:42Z
- **Completed:** 2026-03-08T10:35:22Z
- **Tasks:** 2
- **Files modified:** 2 (new)

## Accomplishments
- 4 RED tests in `tests/test_ui_command.py` covering CLI help, missing static dir, port conflict, --global flag
- 4 RED tests in `tests/test_ui_server.py` covering /api/graph endpoint, /api/nodes/{uuid} endpoint, static file mount, and [ui] TOML config fields
- All 285 pre-existing tests remain green (new files are excluded from the passing suite)

## Task Commits

Each task was committed atomically:

1. **Task 1: CLI test scaffold (RED) — test_ui_command.py** - `8b49cf4` (test)
2. **Task 2: Server test scaffold (RED) — test_ui_server.py** - `b1915e9` (test)

## Files Created/Modified
- `tests/test_ui_command.py` — 4 RED tests for `graphiti ui` CLI command (TestUICommand)
- `tests/test_ui_server.py` — 4 RED tests for FastAPI server routes, app factory, and LLMConfig UI ports (TestAPIRoutes, TestAppFactory, TestLLMConfigUI)

## Decisions Made
- Deferred `src.cli.commands.ui` import inside `_make_app()` helper method rather than at module top-level, so pytest collects 4 individual FAILED tests instead of 1 collection ERROR — cleaner RED signal and closer to plan spec
- `TestLLMConfigUI.test_ui_ports_from_toml` uses `load_config()` directly (it already exists) so the RED failure is `AttributeError: 'LLMConfig' object has no attribute 'ui_api_port'` — no chain of missing imports needed

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- Initial attempt placed import at module top-level, causing a collection ERROR rather than 4 collected FAILED tests. Fixed by moving import inside the `_make_app()` helper method (Rule 1 — auto-fix).

## Next Phase Readiness
- `tests/test_ui_command.py` and `tests/test_ui_server.py` establish the full test contract for Phase 11
- Plan 11-02 can now implement `src/ui_server/app.py` and extend `LLMConfig` to turn `TestAPIRoutes`, `TestAppFactory`, `TestLLMConfigUI` GREEN
- Plan 11-04 can implement `src/cli/commands/ui.py` to turn `TestUICommand` GREEN
- No blockers

---
*Phase: 11-graph-ui*
*Completed: 2026-03-08*
