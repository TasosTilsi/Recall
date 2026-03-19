---
phase: 15-local-memory-system
plan: "01"
subsystem: cli-sync-and-hooks-installer
tags: [cli, hooks, installer, sync, phase15]
dependency_graph:
  requires: []
  provides: [graphiti-sync-command, install_global_hooks, is_global_hooks_installed]
  affects: [src/cli/__init__.py, src/hooks/installer.py]
tech_stack:
  added: []
  patterns: [TDD-red-green, incremental-git-indexing, settings-json-clean-overwrite]
key_files:
  created:
    - src/cli/commands/sync.py
    - tests/test_sync_command.py
    - tests/test_global_hooks_installer.py
  modified:
    - src/cli/__init__.py
    - src/hooks/installer.py
decisions:
  - "sync_command uses full=False to enforce incremental-only semantics (no --full flag exposed)"
  - "install_global_hooks() uses clean overwrite for graphiti entries: remove all matching, re-add new"
  - "_is_graphiti_hook() detects all 4 Phase 15 scripts (session_start, inject_context, capture_entry, session_stop)"
  - "sys.executable used for Python interpreter path to match the active venv"
metrics:
  duration_seconds: 178
  completed_date: "2026-03-19"
  tasks_completed: 2
  files_changed: 5
---

# Phase 15 Plan 01: sync CLI command and global hooks installer Summary

Implemented the two Phase 15 foundation pieces in ~3 minutes: `graphiti sync` CLI command (incremental git indexing alias) and `install_global_hooks()` (global `~/.claude/settings.json` writer for all 5 Phase 15 hook types).

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Add graphiti sync CLI command | 49ffe1a | src/cli/commands/sync.py, src/cli/__init__.py |
| 2 | Add install_global_hooks() to installer.py | f6e373f | src/hooks/installer.py, tests/test_global_hooks_installer.py |

## What Was Built

### Task 1: graphiti sync CLI command

`src/cli/commands/sync.py` — new Typer command that:
- Calls `resolve_scope()` and exits 1 on non-git directories
- Invokes `GitIndexer(project_root=root).run(full=False)` for incremental-only semantics
- Handles cooldown case (up-to-date message, exits 0)
- Catches all exceptions with graceful error message and exit 1
- Registered in `src/cli/__init__.py` as the 19th command (after `index`)

### Task 2: install_global_hooks() in installer.py

Added three functions to `src/hooks/installer.py`:

- `_is_graphiti_hook(entry)` — detects if any command in an entry references session_start.py, inject_context.py, capture_entry.py, or session_stop.py
- `install_global_hooks()` — writes all 5 hook types (SessionStart, UserPromptSubmit, PostToolUse, PreCompact, Stop) to `~/.claude/settings.json`; preserves non-graphiti entries; overwrites existing graphiti entries (clean install semantics)
- `is_global_hooks_installed()` — returns True only when all 5 hook types have a graphiti entry

## Verification Results

- `sync registered OK` — `graphiti sync` appears in `app.registered_commands`
- `sync_command incremental OK` — `full=False` confirmed in source
- `installer exports OK` — all 3 new functions importable
- `_is_graphiti_hook OK` — detection and false-positive tests pass
- Full test suite: 340 passed, 2 skipped (no regressions)

## Deviations from Plan

None — plan executed exactly as written.

Tests for Task 1 (`test_sync_command.py`) were found pre-existing in the repo (created during planning). Tests for Task 2 (`test_global_hooks_installer.py`) were written as part of TDD RED phase execution.

## Self-Check: PASSED

Files verified to exist:
- src/cli/commands/sync.py — FOUND
- src/hooks/installer.py — FOUND (modified)
- tests/test_sync_command.py — FOUND
- tests/test_global_hooks_installer.py — FOUND

Commits verified:
- 49ffe1a — FOUND (feat(15-01): add graphiti sync CLI command)
- f6e373f — FOUND (feat(15-01): add install_global_hooks() and is_global_hooks_installed() to installer.py)
