---
phase: 30-mcp-server
plan: 30-01
subsystem: mcp_server
tags: [fastmcp, mcp, sqlite, fts5, stdio, knowledge-graph]

# Dependency graph
requires:
  - phase: 26-foundation
    provides: Config, DatabaseManager base class
  - phase: 28-git-extractor-indexer
    provides: SQLite schema (entities, backlinks, commits, fts_index)
  - phase: 29-cli-commands
    provides: CLI surface including 'recall mcp serve' entry point
provides:
  - FastMCP stdio server with six read-only tools registered
  - DatabaseManager query helpers: search_fts, get_entity_by_id, get_entity_by_name, get_backlinks, get_backlinks_recursive, get_entities_by_type
  - src/mcp_server/tools.py with all six tool functions
  - src/mcp_server/server.py with logging-first safety and tool registration
affects: [31-ui-server, INST-01, INST-02, SKILL-01, SKILL-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "logging.basicConfig(stream=sys.stderr) as first executable line in MCP server — stdout-clean safety invariant"
    - "mcp.tool()(fn) decorator registration pattern for FastMCP"
    - "UUID-first then name fallback lookup for flexible entity addressing"
    - "BFS with visited-set cycle prevention for multi-hop backlink traversal"

key-files:
  created:
    - src/mcp_server/tools.py
    - src/mcp_server/server.py
  modified:
    - src/mcp_server/__init__.py
    - src/db/manager.py

key-decisions:
  - "Query helpers added to DatabaseManager (not a separate QueryLayer) — single responsibility kept, tools.py calls db directly"
  - "Schema column names (from_id/to_id/relationship) aliased to interface names (source_id/target_id/label) in get_backlinks() SQL — no schema migration needed"
  - "get_backlinks_recursive implements BFS in Python (not recursive CTE) — simpler, testable, cycle-safe"

patterns-established:
  - "MCP server: stdlib logging only, stderr only, never structlog, never print"
  - "DatabaseManager._row_to_entity() as canonical row→dict converter"

requirements-completed: [MCP-01, MCP-02]

# Metrics
duration: 12min
completed: 2026-04-19
---

# Phase 30 Plan 01: MCP Server Summary

**FastMCP stdio server with six read-only tools (search, entity lookup, backlinks, decisions, bugs, patterns) backed directly by SQLite DatabaseManager**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-19T00:00:00Z
- **Completed:** 2026-04-19T00:12:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Six MCP tool functions implemented in tools.py: search_knowledge, get_entity, get_backlinks, get_decisions, get_bugs, get_patterns
- server.py has logging.basicConfig(stream=sys.stderr) as the very first executable line — stdout is never written
- get_entity performs UUID-first lookup with automatic name fallback via two distinct DatabaseManager methods
- get_backlinks accepts hops parameter and BFS-traverses the backlinks graph with cycle prevention
- Added six query helper methods to DatabaseManager to support tool calls directly against SQLite

## Task Commits

1. **Task 1: Delete v2.0 MCP files and write tools.py** - `007097a` (feat)
2. **Task 2: Rewrite server.py with six tools** - `6783300` (feat)

**Plan metadata:** (to be recorded after final commit)

## Files Created/Modified

- `src/mcp_server/tools.py` - Six tool functions; stdlib logging; no structlog, no subprocess, no stdout
- `src/mcp_server/server.py` - FastMCP instance; logging-first safety; six tools registered via mcp.tool()
- `src/mcp_server/__init__.py` - Exposes only serve()
- `src/db/manager.py` - Added search_fts, get_entity_by_id, get_entity_by_name, get_backlinks, get_backlinks_recursive, get_entities_by_type

## Decisions Made

- Query helpers were added to DatabaseManager directly (not a separate query layer) — tools.py calls _db() per invocation and uses these methods; keeps all DB logic in one place
- Schema column names (from_id, to_id, relationship) are aliased to the documented interface names (source_id, target_id, label) in the get_backlinks() SQL SELECT — no schema migration required
- BFS implemented in Python with a visited set rather than recursive SQL CTE — more readable, testable, and avoids SQLite recursion depth limits

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added six query helpers to DatabaseManager**
- **Found during:** Task 1 (writing tools.py)
- **Issue:** Plan's interface spec documented search_fts, get_entity_by_id, get_entity_by_name, get_backlinks, get_backlinks_recursive, get_entities_by_type on DatabaseManager — but the actual src/db/manager.py only had init_db() and connect(). tools.py cannot function without these.
- **Fix:** Added all six helper methods to DatabaseManager, plus _row_to_entity() converter. Column aliasing in get_backlinks() maps schema names to documented interface names.
- **Files modified:** src/db/manager.py
- **Verification:** All six tools import cleanly; 80 existing tests pass
- **Committed in:** 007097a (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical functionality)
**Impact on plan:** Auto-fix was essential — tools.py is the plan's primary deliverable and requires these DB methods to function. No scope creep.

## Issues Encountered

- v2.0 files (toon_utils.py, context.py, install.py) were already absent — the mcp_server package only had a stub __init__.py. Task 1 deletion step was a no-op; all effort went to writing new files.
- Plan's verification check `grep -q "ModuleNotFoundError"` for toon_utils fails because `from src.mcp_server import toon_utils` raises `ImportError` (not `ModuleNotFoundError`). Verified via `importlib.import_module('src.mcp_server.toon_utils')` which correctly raises `ModuleNotFoundError`.
- Pre-existing test failures in tests/cli/ due to missing `tomli_w` package in test environment — out of scope; 80 non-CLI tests all pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- MCP server is complete and ready: `recall mcp serve` will start the stdio server
- Six tools are registered and backed by SQLite — functional once a DB exists (created by `recall init` or `recall sync`)
- Phase 31 (UI server) can proceed independently — no MCP dependency

---
*Phase: 30-mcp-server*
*Completed: 2026-04-19*
