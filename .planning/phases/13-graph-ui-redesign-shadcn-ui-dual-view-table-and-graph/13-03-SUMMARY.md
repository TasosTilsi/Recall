---
phase: 13-multi-provider-llm
plan: 03
subsystem: cli
tags: [health-command, startup-validation, provider-health, typer, pytest]

# Dependency graph
requires:
  - phase: 13-01
    provides: LLMConfig llm_mode/llm_primary_* fields and ProviderClient with ping_primary()/ping_embed()
  - phase: 13-02
    provides: make_llm_client()/make_embedder() factories; GraphService wired to provider routing
provides:
  - "_check_provider() in health.py returns 0-3 check dicts (Provider/Embed/Fallback rows)"
  - "health_command() shows provider rows and hides Ollama rows when llm_mode='provider'"
  - "validate_provider_startup() hooked into main_callback() for fail-fast on startup"
  - "5 unit tests in test_health_command.py covering all provider health row scenarios"
affects:
  - "Phase 14 Graph UI — startup validation guards all graph commands including UI commands"
  - "Phase 15 Local Memory — any graphiti subcommand benefits from fail-fast provider gate"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "check dict shape: {name, status, detail} — all health check functions return this dict"
    - "provider row format: '<sdk>/<first-model> @ <hostname> [OK|UNREACHABLE]'"
    - "startup validation: validate_provider_startup() called synchronously before asyncio.run()"
    - "skip list pattern: _skip_validation_for = {'health', 'config', None} — subcommands exempt from startup gate"

key-files:
  created:
    - tests/test_health_command.py
  modified:
    - src/cli/commands/health.py
    - src/cli/__init__.py

key-decisions:
  - "Startup validation skips 'health' and 'config' subcommands — they handle provider interaction themselves"
  - "Fallback tier shown as 'configured' not pinged at health time — avoids extra local Ollama ping in provider mode"
  - "Ollama cloud/local rows suppressed entirely when llm_mode='provider' — mutually exclusive display"
  - "validate_provider_startup() wrapped in try/except: only re-raises SystemExit; other exceptions are non-fatal to preserve legacy path"

patterns-established:
  - "Pattern: health check conditional branching — provider mode vs legacy mode controlled by llm_mode field"
  - "Pattern: startup gate — synchronous validation before asyncio.run() entry point"

requirements-completed: [PROV-03, PROV-04]

# Metrics
duration: continuation (checkpoint resume)
completed: 2026-03-18
---

# Phase 13 Plan 03: Provider Health Rows and Startup Validation Summary

**Provider health rows in `graphiti health` (Provider/Embed/Fallback with OK/UNREACHABLE) and fail-fast startup gate via validate_provider_startup() hooked into main_callback()**

## Performance

- **Duration:** continuation (human-verify checkpoint approved)
- **Started:** prior session (Task 1 committed 5b1772a)
- **Completed:** 2026-03-18T17:23:32Z
- **Tasks:** 2 (1 auto + 1 human-verify)
- **Files modified:** 3

## Accomplishments

- Added `_check_provider()` to health.py returning 0-3 check dicts with format `<sdk>/<model> @ <hostname> [OK|UNREACHABLE]`
- Updated `health_command()` to show provider rows (not Ollama rows) when `llm_mode='provider'`; Ollama rows shown unchanged in legacy mode
- Hooked `validate_provider_startup()` into `main_callback()` for fail-fast behavior on all subcommands except `health` and `config`
- 5 unit tests in `tests/test_health_command.py` covering absent rows in legacy mode, OK format, UNREACHABLE format, embed row presence, and absent fallback row
- All 24/24 verify_phase_13.py checks green (human approved)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add failing health row tests and write _check_provider() + startup hook** - `5b1772a` (feat)
2. **Task 2: Human verification** - human-approved (no code commit)

## Files Created/Modified

- `tests/test_health_command.py` - 5 unit tests for provider health row scenarios (created)
- `src/cli/commands/health.py` - Added `_check_provider()` function; updated `health_command()` checks assembly block
- `src/cli/__init__.py` - Added startup validation hook in `main_callback()` with skip list for health/config

## Decisions Made

- Startup validation skips `health` and `config` subcommands — these subcommands display or interact with provider state themselves and must not be gated
- Fallback tier row shows `[configured]` rather than pinging — avoids a live local Ollama ping in provider mode at health time; label is still informative
- Ollama cloud/local rows are suppressed entirely when `llm_mode='provider'` — the two modes are mutually exclusive in the health display
- `validate_provider_startup()` is wrapped so only `SystemExit` propagates; other exceptions are silently swallowed to avoid blocking the legacy path if an unexpected error occurs during config load

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 13 (Multi-Provider LLM) is now complete: Plans 01 (config + ProviderClient), 02 (adapter factories + GraphService wiring), and 03 (health rows + startup gate) all done
- Phase 14 (Graph UI Redesign) can proceed — all graph reads go through service.py which is now provider-aware
- Phase 15 (Local Memory) can proceed — startup validation guards all CLI entry points

---
*Phase: 13-multi-provider-llm*
*Completed: 2026-03-18*
