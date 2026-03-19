---
phase: 15-local-memory-system
plan: "04"
subsystem: cli
tags: [typer, hooks, memory-search, cli-registration]

# Dependency graph
requires:
  - phase: 15-01
    provides: install_global_hooks() and is_global_hooks_installed() in src/hooks/installer.py
  - phase: 15-02
    provides: hook scripts for Claude Code SessionStart and inject_context flows
  - phase: 15-03
    provides: write-path hooks and capture_entry / session_stop workers

provides:
  - graphiti memory search <query> CLI command with --limit, --global, --format flags
  - graphiti hooks install calls install_global_hooks() writing all 5 entries to ~/.claude/settings.json
  - graphiti hooks status shows Claude Code global (memory hooks) row
  - install_global_hooks and is_global_hooks_installed exported from src/hooks/__init__
  - memory_app Typer sub-app registered in src/cli/__init__.py (20 total commands)

affects: [16-rename-recall, 15-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Typer sub-app pattern for memory command group (mirrors hooks_app, queue_app)
    - resolve_scope() + get_service() + run_graph_operation() pipeline for CLI search commands

key-files:
  created:
    - src/cli/commands/memory.py
  modified:
    - src/cli/commands/hooks.py
    - src/cli/__init__.py
    - src/hooks/__init__.py

key-decisions:
  - "memory_app registered via app.add_typer() consistent with hooks_app and queue_app pattern"
  - "install_global_hooks called unconditionally in install_command (after local hooks block) — no --global-only flag needed"
  - "status_command always queries is_global_hooks_installed() regardless of root context"

patterns-established:
  - "CLI search command pattern: resolve_scope -> get_service -> run_graph_operation -> tabular output with --format json fallback"
  - "Global hooks wiring: install_command calls install_global_hooks() with separate console.status() block after project-local hooks"

requirements-completed: [MEM-03, MEM-05]

# Metrics
duration: 5min
completed: 2026-03-19
---

# Phase 15 Plan 04: CLI Wiring — Memory Search and Global Hooks Summary

**graphiti memory search CLI command and global hooks install wiring added: memory_app Typer sub-app with BM25+semantic search, hooks install now writes all 5 entries to ~/.claude/settings.json**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-19T21:44:07Z
- **Completed:** 2026-03-19T21:49:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `src/cli/commands/memory.py` with `memory_app` Typer sub-app and `memory_search_command` supporting --limit, --global, --format flags
- Updated `src/cli/commands/hooks.py` install_command to call `install_global_hooks()` after project-local hooks, and status_command to show "Claude Code global (memory hooks)" row
- Registered `memory_app` in `src/cli/__init__.py` (20 total CLI commands)
- Exported `install_global_hooks` and `is_global_hooks_installed` from `src/hooks/__init__.py`

## Task Commits

Each task was committed atomically:

1. **Task 1: Update hooks CLI and create memory CLI sub-app** - `d6a2311` (feat)
2. **Task 2: Wire memory app and update hooks __init__ exports** - `0ccd8ee` (feat)

**Plan metadata:** (docs commit — created below)

## Files Created/Modified

- `src/cli/commands/memory.py` - New memory_app Typer sub-app with memory_search_command
- `src/cli/commands/hooks.py` - install_global_hooks() call added to install_command; is_global_hooks_installed() row in status_command
- `src/cli/__init__.py` - memory_app imported and registered; command count updated to 20
- `src/hooks/__init__.py` - install_global_hooks and is_global_hooks_installed added to exports and __all__

## Decisions Made

- `memory_app` registered via `app.add_typer()` matching existing hooks_app and queue_app pattern for consistency
- `install_global_hooks()` is called unconditionally inside install_command after the local hooks block (no separate --global-only flag needed)
- `status_command` always queries `is_global_hooks_installed()` as a simple boolean — no project root dependency required for global hook status

## Deviations from Plan

None - plan executed exactly as written. All code was already present from a prior execution; this run committed the Task 2 changes (src/cli/__init__.py and src/hooks/__init__.py wiring) which were uncommitted in the working tree.

## Issues Encountered

None - 340 tests passed with 0 regressions.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 15-04 complete: `graphiti memory search`, `graphiti hooks install` global wiring, and `graphiti hooks status` global row all functional
- Ready for Phase 15-05 (MCP progressive disclosure layer or remaining Phase 15 plans)
- All 20 CLI commands registered; test suite green (340 passed, 2 skipped)

---
*Phase: 15-local-memory-system*
*Completed: 2026-03-19*
