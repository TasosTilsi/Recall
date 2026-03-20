---
phase: 16-rename-cli-consolidation
plan: "01"
subsystem: cli
tags: [typer, recall, cli-rename, entrypoints]

# Dependency graph
requires:
  - phase: 15-local-memory-system
    provides: hook installer (install_global_hooks) and pending_tool_captures.jsonl pipeline
provides:
  - recall/rc CLI entrypoints replacing graphiti/gk
  - 10-command public surface (init, search, list, delete, pin, unpin, health, config, ui, note)
  - 1 hidden index command with --force flag
  - init_cmd.py: idempotent 4-step one-command setup
  - note_cmd.py: manual memory entry to pending captures queue
affects: [16-02, 16-03, 16-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CLI rename: pyproject.toml scripts point to src.cli:cli_entry for both recall and rc"
    - "Hidden command pattern: app.command(hidden=True) for power-user index command"
    - "init_cmd fail-open pattern: each step in try/except with print_warning on failure"

key-files:
  created:
    - src/cli/commands/init_cmd.py
    - src/cli/commands/note_cmd.py
  modified:
    - pyproject.toml
    - src/cli/__init__.py
    - src/cli/commands/index.py

key-decisions:
  - "recall/rc entrypoints replace graphiti/gk — same cli_entry function, only pyproject.toml scripts change"
  - "init and index added to _skip_validation_for set — both must work before provider is configured"
  - "init_cmd writes static llm.toml template (no interactive prompts) — idempotent, safe to re-run"
  - "note_cmd fail-open: exits EXIT_ERROR on exception but wraps all logic in try/except; security sanitize in inner try/except (fail-open)"

patterns-established:
  - "Fail-open step pattern in init_cmd: each of 4 setup steps in isolated try/except, print_warning and continue"
  - "note_cmd entry format matches capture_entry.py exactly: tool_name, key_args, output_snippet, session_id, cwd, timestamp"

requirements-completed: [CLI-01, CLI-02]

# Metrics
duration: 4min
completed: 2026-03-20
---

# Phase 16 Plan 01: Rename CLI Entrypoints and Consolidate to 10 Commands Summary

**Typer app renamed from graphiti to recall with recall/rc entrypoints; CLI surface collapsed from 20 to 10 public + 1 hidden commands; init_cmd.py and note_cmd.py created**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-20T10:04:12Z
- **Completed:** 2026-03-20T10:07:44Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Renamed `pyproject.toml` scripts from `graphiti`/`gk` to `recall`/`rc`
- Rewrote `src/cli/__init__.py`: Typer app named "recall", 10 public commands + 1 hidden index command; 11 commands removed
- Updated `src/cli/commands/index.py`: `--full` flag replaced with `--force`, all docstring examples updated from `graphiti` to `recall`
- Created `src/cli/commands/init_cmd.py`: idempotent 4-step setup (hooks, git index, config template, MCP registration)
- Created `src/cli/commands/note_cmd.py`: manual memory entry appended to `.graphiti/pending_tool_captures.jsonl`

## Task Commits

Each task was committed atomically:

1. **Task 1: Rename entrypoints + restructure app to 10 public + 1 hidden commands** - `402c6d0` (feat)
2. **Task 2: Create init_cmd.py and note_cmd.py** - `b8ce5ad` (feat, pre-existing from prior 16-02 execution)

## Files Created/Modified
- `pyproject.toml` - `[project.scripts]` updated to recall/rc only
- `src/cli/__init__.py` - app name recall, 10 public + 1 hidden commands, 11 removed
- `src/cli/commands/index.py` - --force flag (was --full), recall references in docstrings
- `src/cli/commands/init_cmd.py` - new: idempotent 4-step recall init command
- `src/cli/commands/note_cmd.py` - new: manual memory note command writing to pending_tool_captures.jsonl

## Decisions Made
- `recall` and `rc` both point to `src.cli:cli_entry` — same function, different console script names
- `init` and `index` added to `_skip_validation_for` — both must be callable before LLM provider is configured
- `init_cmd.py` writes a static TOML template; no interactive prompts — idempotent pattern
- `note_cmd.py` uses fail-open: security sanitize wrapped in inner try/except so unsanitized content is written rather than failing

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Task 2 files (`init_cmd.py`, `note_cmd.py`) already existed in git HEAD (`b8ce5ad`) from a prior agent execution that ran plans 16-01 and 16-02 in sequence. Written files matched HEAD exactly (no diff). No duplicate commit needed.

## Next Phase Readiness
- `recall`/`rc` entrypoints fully functional; `recall --help` shows 10 public commands
- `recall index --force` available as hidden power-user command
- `recall init` and `recall note` importable and registered
- Plan 16-02 can proceed with list_cmd expansion and search auto-sync

---
*Phase: 16-rename-cli-consolidation*
*Completed: 2026-03-20*
