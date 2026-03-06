---
phase: 09-smart-retention
plan: "04"
subsystem: retention
tags: [retention, pin, mcp, typer, sqlite, toon]

# Dependency graph
requires:
  - phase: 09-01
    provides: RetentionManager with pin_node/unpin_node methods, get_retention_manager()
  - phase: 09-02
    provides: GraphService._get_group_id() for consistent scope_key derivation
provides:
  - pin_command: CLI command to pin a node UUID against TTL archiving
  - unpin_command: CLI command to remove pin protection from a node UUID
  - graphiti_stale MCP tool: preview stale nodes via subprocess+TOON pattern
affects:
  - 09-05 (wires pin/unpin into CLI app registration)
  - mcp-server (exposes graphiti_stale to LLM tool surface)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pin/unpin commands are synchronous-only (SQLite, no async graph operations)"
    - "scope_key derived from get_service()._get_group_id() for consistency with retention sidecar"
    - "MCP stale tool follows existing _run_graphiti + _parse_json_or_raw + TOON pattern"

key-files:
  created:
    - src/cli/commands/pin.py
  modified:
    - src/mcp_server/tools.py

key-decisions:
  - "Use get_service()._get_group_id() in pin.py (not manual scope string) to guarantee scope_key matches access_log/archive_state values already written by GraphService"
  - "pin_command/unpin_command use structlog (not stdlib logging) — they live in src/cli/, not src/mcp_server/"
  - "graphiti_stale MCP tool uses --format json --all flags to get full parseable list without cap"
  - "graphiti_stale committed as part of 09-03 compact session (was already present in tools.py when 09-04 executed — no duplicate commit needed)"

patterns-established:
  - "Pin pattern: resolve_scope -> _get_group_id -> get_retention_manager().pin/unpin_node"
  - "MCP retention tools follow identical subprocess pattern as list/search: _run_graphiti + _parse_json_or_raw"

requirements-completed: [RETN-04, RETN-05]

# Metrics
duration: 3min
completed: 2026-03-06
---

# Phase 9 Plan 04: Pin/Unpin CLI and graphiti_stale MCP Tool Summary

**pin_command/unpin_command Typer functions for SQLite-only node pinning, plus graphiti_stale MCP subprocess tool returning TOON-encoded stale node list**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-06T06:33:29Z
- **Completed:** 2026-03-06T06:36:01Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created `src/cli/commands/pin.py` with `pin_command` and `unpin_command` Typer functions
- Both commands resolve scope, derive `scope_key` via `get_service()._get_group_id()` for retention sidecar consistency
- `graphiti_stale` MCP tool added to `src/mcp_server/tools.py` following the existing `_run_graphiti + _parse_json_or_raw` pattern
- Zero regressions — 257 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create src/cli/commands/pin.py** - `7264810` (feat)
2. **Task 2: Add graphiti_stale MCP tool** - committed in `75da315` (was already applied as part of 09-03 compact session)

## Files Created/Modified
- `src/cli/commands/pin.py` - pin_command and unpin_command Typer functions (created)
- `src/mcp_server/tools.py` - graphiti_stale function + __all__ export added (modified)

## Decisions Made
- `get_service()._get_group_id()` used in pin.py instead of manual scope string to guarantee the `scope_key` written to `pin_state` matches what `access_log` and `archive_state` tables use — required for correct pin exclusion in `list_stale()`
- `structlog.get_logger(__name__)` used in pin.py (not stdlib logging) because pin.py is not in `src/mcp_server/` and must follow project logging conventions
- `graphiti_stale` uses `--format json --all` so the full stale list is returned as parseable JSON, not capped at the default display limit

## Deviations from Plan

**1. [Note] graphiti_stale was already committed in 09-03 session**
- During the 09-03 execution (compact --expire work), `graphiti_stale` was added to `tools.py` in commit `75da315`.
- When 09-04 executed, the function was already present and the Edit was a no-op — no duplicate commit was made.
- This is not a deviation from correctness — the function is present, importable, and matches the plan spec exactly.

None - plan executed exactly as written (pin.py created fresh, graphiti_stale already present from 09-03).

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `pin_command` and `unpin_command` are implemented and importable
- Both commands need to be registered in the CLI app (Plan 09-05: wire all new commands into `__init__.py`)
- `graphiti_stale` is already registered in `__all__` and ready for FastMCP tool registration in MCP server (Plan 09-05)

---
*Phase: 09-smart-retention*
*Completed: 2026-03-06*
