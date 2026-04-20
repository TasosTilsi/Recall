---
phase: 29-cli-commands
plan: 01
subsystem: cli
tags: [typer, rich, cli, init, sync, health, ui, python]

# Dependency graph
requires:
  - phase: 28-git-extractor-indexer
    provides: run_init, run_sync entry points in src/indexer/
  - phase: 27-llm-provider
    provides: check_health(config) in src/llm/health.py
  - phase: 26-config
    provides: Config, load_config() in src/config.py
  - phase: 25-cleanup
    provides: CLI stub skeleton (6-command surface defined)
provides:
  - src/cli/__init__.py — Typer app with exactly 6 public commands registered
  - src/cli/output.py — Rich console, print_success/error/warning helpers
  - src/cli/utils.py — EXIT_SUCCESS, EXIT_ERROR constants
  - src/cli/commands/__init__.py — commands package
  - src/cli/commands/init_cmd.py — full reindex wrapper over run_init
  - src/cli/commands/sync_cmd.py — incremental sync wrapper over run_sync
  - src/cli/commands/health.py — v3.0 health check wired to src.llm.health
  - src/cli/commands/ui.py — FastAPI UI server launcher via uvicorn
  - src/cli/commands/search_cmd.py — Typer sub-app stub for 29-02
  - src/cli/commands/config_cmd.py — Typer sub-app stub for 29-02
affects: [29-02-search-config, 31-ui-server, 32-plugin-install]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CLI output via src.cli.output helpers (Rich console, err_console)"
    - "Exit codes via src.cli.utils constants (EXIT_SUCCESS=0, EXIT_ERROR=1)"
    - "git root discovery by walking up cwd looking for .git/"
    - "_find_git_root() pattern shared between init_cmd and sync_cmd"
    - "structlog routed to stderr in src/cli/__init__.py top-level config"

key-files:
  created:
    - src/cli/output.py
    - src/cli/utils.py
    - src/cli/commands/__init__.py
    - src/cli/commands/init_cmd.py
    - src/cli/commands/sync_cmd.py
    - src/cli/commands/health.py
    - src/cli/commands/ui.py
    - src/cli/commands/search_cmd.py
    - src/cli/commands/config_cmd.py
  modified:
    - src/cli/__init__.py

key-decisions:
  - "indexer exports run_init/run_sync (not GitIndexer class) — init_cmd/sync_cmd call these directly"
  - "check_health takes Config argument (not just timeout) — health_command loads config and passes it"
  - "output helpers created as src/cli/output.py — plan referenced them as interface contracts"
  - "search_cmd.py and config_cmd.py created as Typer sub-app stubs — 29-02 overwrites with full implementations"
  - "structlog configured to stderr at module level in src/cli/__init__.py"

patterns-established:
  - "_find_git_root(): Path | None — walks cwd parents looking for .git/, reused in both init and sync"
  - "_print_index_result(result: dict) — consistent commits/entities output format"
  - "Commands use console.status() for long-running operations with spinner"

requirements-completed: [CLI-01]

# Metrics
duration: 15min
completed: 2026-04-20
---

# Phase 29 Plan 01: CLI Commands Foundation Summary

**Typer CLI hard-reset to 6 public commands (init, sync, search, health, config, ui) wired to v3.0 indexer (run_init/run_sync), health check (HealthResult), and UI server (uvicorn)**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-19T21:26:57Z
- **Completed:** 2026-04-20T05:39:31Z
- **Tasks:** 3 (all in 1 atomic commit)
- **Files modified:** 10

## Accomplishments
- Rewrote `src/cli/__init__.py` from placeholder stubs to proper Typer app with 6 commands via `app.command()` and `app.add_typer()`
- Created `output.py` and `utils.py` CLI helpers (Rich console, print_success/error/warning, exit codes)
- Implemented `init_cmd.py` and `sync_cmd.py` wired to Phase 28 `run_init`/`run_sync` indexer functions
- Rewrote `health.py` to use Phase 27 `check_health(Config)` returning `HealthResult` dataclass
- Created `ui.py` launching FastAPI UI server via uvicorn with browser auto-open
- Created `search_cmd.py` and `config_cmd.py` as Typer sub-app stubs for plan 29-02

## Task Commits

All tasks executed as unified implementation:

1. **Task 1: Delete legacy files and rewrite src/cli/__init__.py** - `fe5205d` (feat)
2. **Task 2: Create sync_cmd.py and update init_cmd.py** - included in `fe5205d`
3. **Task 3: Rewrite health.py to use v3.0 health check** - included in `fe5205d`

**Plan metadata:** (this commit)

## Files Created/Modified
- `src/cli/__init__.py` — Typer app with 6 commands, structlog→stderr, --version callback
- `src/cli/output.py` — Rich console, err_console, print_success, print_error, print_warning
- `src/cli/utils.py` — EXIT_SUCCESS=0, EXIT_ERROR=1
- `src/cli/commands/__init__.py` — commands package init
- `src/cli/commands/init_cmd.py` — full reindex: _find_git_root, run_init, --force flag
- `src/cli/commands/sync_cmd.py` — incremental sync: _find_git_root, run_sync, auto-init if no DB
- `src/cli/commands/health.py` — check_health(config) via asyncio.run, HealthResult display
- `src/cli/commands/ui.py` — uvicorn launcher, --host/--port/--no-browser options
- `src/cli/commands/search_cmd.py` — Typer stub (app = typer.Typer(name="search"))
- `src/cli/commands/config_cmd.py` — Typer stub (app = typer.Typer(name="config"))

## Decisions Made
- Indexer uses `run_init`/`run_sync` function exports (not `GitIndexer` class as plan described) — adapted CLI wrappers accordingly
- `check_health` takes `Config` argument (plan described it taking only `timeout`) — load config first, pass to check_health
- Created `src/cli/output.py` and `src/cli/utils.py` — plan referenced them as assumed interfaces, created them as small dedicated modules
- `_find_git_root()` duplicated in init_cmd and sync_cmd (no shared utils module) — acceptable duplication given module boundaries

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Indexer exports run_init/run_sync, not GitIndexer class**
- **Found during:** Task 2 (init_cmd/sync_cmd implementation)
- **Issue:** Plan specified `from src.indexer import GitIndexer` with `indexer.run(full=...)` interface; actual Phase 28 implementation exports `run_init` and `run_sync` functions
- **Fix:** init_cmd.py and sync_cmd.py call `run_init(root, config)` and `run_sync(root, config)` directly
- **Files modified:** src/cli/commands/init_cmd.py, src/cli/commands/sync_cmd.py
- **Verification:** `python3 -c "from src.cli.commands.sync_cmd import sync_command; from src.cli.commands.init_cmd import init_command; print('imports ok')"` passes
- **Committed in:** fe5205d

**2. [Rule 1 - Bug] check_health takes Config argument, not timeout float**
- **Found during:** Task 3 (health.py implementation)
- **Issue:** Plan specified `check_health(timeout=5.0)` interface; actual Phase 27 implementation signature is `async check_health(config: Config) -> HealthResult`
- **Fix:** health_command calls `load_config()` first, then `asyncio.run(check_health(config))`; result is HealthResult dataclass with `.status`, `.provider`, `.model`, `.embeddings_status`, `.error`, `.embeddings_error` fields
- **Files modified:** src/cli/commands/health.py
- **Verification:** AST import check passes; no forbidden imports from src.storage/src.llm.provider/src.graph
- **Committed in:** fe5205d

**3. [Rule 2 - Missing Critical] Created src/cli/output.py and src/cli/utils.py**
- **Found during:** Task 1 (plan referenced these as import interfaces but they didn't exist)
- **Issue:** Plan code samples imported `from src.cli.output import console, print_success, ...` and `from src.cli.utils import EXIT_SUCCESS, EXIT_ERROR` but neither file existed in the codebase
- **Fix:** Created both modules as small helpers using Rich Console
- **Files modified:** src/cli/output.py, src/cli/utils.py (created)
- **Committed in:** fe5205d

---

**Total deviations:** 3 auto-fixed (2 interface mismatches Rule 1, 1 missing critical Rule 2)
**Impact on plan:** All auto-fixes required for correctness. No scope creep — fixes adapt plan assumptions to actual Phase 27/28 implementations.

## Issues Encountered
None beyond the auto-fixed interface mismatches above.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- CLI foundation complete; `recall --help` shows exactly 6 commands
- 29-02 (search + config subcommands) can overwrite search_cmd.py and config_cmd.py stubs
- health, init, sync, ui commands are functional (pending working LLM config and DB)
- No blockers for 29-02

## Self-Check

### Files exist:
- src/cli/__init__.py: FOUND
- src/cli/output.py: FOUND
- src/cli/utils.py: FOUND
- src/cli/commands/__init__.py: FOUND
- src/cli/commands/init_cmd.py: FOUND
- src/cli/commands/sync_cmd.py: FOUND
- src/cli/commands/health.py: FOUND
- src/cli/commands/ui.py: FOUND
- src/cli/commands/search_cmd.py: FOUND
- src/cli/commands/config_cmd.py: FOUND

### Commits exist:
- fe5205d: FOUND (feat(29-01): rewrite CLI to six public commands)

## Self-Check: PASSED

---
*Phase: 29-cli-commands*
*Completed: 2026-04-20*
