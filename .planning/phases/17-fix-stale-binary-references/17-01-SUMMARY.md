---
phase: 17-fix-stale-binary-references
plan: 01
subsystem: mcp_server, queue
tags: [recall, mcp, binary-rename, worker, tools]

# Dependency graph
requires:
  - phase: 16-rename-cli-consolidation
    provides: recall/rc entrypoints replacing graphiti/gk
provides:
  - worker.py using _RECALL_CLI pointing to recall binary
  - tools.py exporting recall_* MCP functions with _RECALL_CLI constant
  - server.py registering 10 recall_* tools under FastMCP("recall")
  - context.py importing and using _RECALL_CLI throughout
affects:
  - Any phase that references MCP server tool names or queue worker binary

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_RECALL_CLI = str(Path(sys.executable).parent / 'recall') — canonical venv-relative binary pattern"
    - "recall_note calls ['note', content] — not ['add', content]"

key-files:
  created: []
  modified:
    - src/queue/worker.py
    - src/mcp_server/tools.py
    - src/mcp_server/context.py
    - src/mcp_server/server.py
    - tests/test_queue_worker_dispatch.py

key-decisions:
  - "graphiti_capture (Popen fire-and-forget) deleted — recall_note is the single write tool post-Phase 16"
  - "FastMCP server renamed from 'graphiti' to 'recall' for consistent branding"
  - "Resource URI graphiti://context left unchanged — changing it would break existing Claude Desktop configs"
  - "test_note_command_appends_to_jsonl pre-existing failure is out of scope (tests note_cmd.py behavior unrelated to binary references)"
  - "test_project_driver_creation / test_project_switching pre-existing failures are out of scope (GraphManager .graphiti dir creation)"

patterns-established: []

requirements-completed:
  - MEM-02

# Metrics
duration: 5min
completed: 2026-03-21
---

# Phase 17 Plan 01: Fix Stale Binary References Summary

**Renamed _GRAPHITI_CLI → _RECALL_CLI in worker.py and all MCP server files; renamed graphiti_* functions to recall_* (graphiti_add → recall_note with cmd=['note',...]); deleted graphiti_capture; updated server.py registrations and context.py imports**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-21T19:33:08Z
- **Completed:** 2026-03-21T19:38:48Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- worker.py `_GRAPHITI_CLI` → `_RECALL_CLI` pointing to `recall` binary — queue replay now works post-Phase 16
- tools.py: all 12 `graphiti_*` functions renamed to `recall_*`; `graphiti_add` → `recall_note` with `["note", content]` CLI args; `graphiti_capture` deleted
- server.py: import block and `mcp.tool()` registrations updated to `recall_*`; FastMCP name updated to `"recall"`
- context.py: `_GRAPHITI_CLI` import and 3 usage sites updated to `_RECALL_CLI`
- Test assertion updated: `test_generic_job_uses_subprocess` was asserting `Path(...).name == "graphiti"`, updated to `"recall"`

## Task Commits

Each task was committed atomically:

1. **Task 1: Rename _GRAPHITI_CLI → _RECALL_CLI in worker.py** - `595933d` (fix)
2. **Task 2: Rename graphiti_* → recall_* in tools.py, server.py, context.py** - already applied before this execution (MCP server files were updated in prior session)
3. **Rule 1 auto-fix: Update test assertion binary name** - `74c5f81` (fix)

**Plan metadata:** (committed below)

## Files Created/Modified

- `src/queue/worker.py` — _GRAPHITI_CLI → _RECALL_CLI, comment updated, _dispatch_job cli_command updated
- `src/mcp_server/tools.py` — _GRAPHITI_CLI → _RECALL_CLI, _run_graphiti → _run_recall, all graphiti_* → recall_*, graphiti_add → recall_note (cmd=['note',...]), graphiti_capture deleted, __all__ updated
- `src/mcp_server/server.py` — imports updated to recall_*, mcp.tool() registrations updated, FastMCP("recall"), instructions updated
- `src/mcp_server/context.py` — import and 3 usages of _GRAPHITI_CLI → _RECALL_CLI
- `tests/test_queue_worker_dispatch.py` — assertion updated from "graphiti" to "recall"

## Decisions Made

- `graphiti_capture` (Popen fire-and-forget) deleted — no consumers post-Phase 16; `recall_note` is the single write tool
- FastMCP server name changed from `"graphiti"` to `"recall"` for consistent branding
- Resource URI `graphiti://context` left unchanged to avoid breaking existing Claude Desktop config files
- `recall_note` invokes CLI with `["note", content]` not `["add", content]` — matches Phase 16 command consolidation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated stale test assertion for binary name**
- **Found during:** Task 2 verification (full test suite run)
- **Issue:** `test_queue_worker_dispatch.py::test_generic_job_uses_subprocess` asserted `Path(call_args[0]).name == "graphiti"` — this was wrong after renaming `_GRAPHITI_CLI` → `_RECALL_CLI`
- **Fix:** Changed assertion to `== "recall"`
- **Files modified:** `tests/test_queue_worker_dispatch.py`
- **Verification:** Test passes: `1 passed in 0.09s`
- **Committed in:** `74c5f81`

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug: stale test assertion)
**Impact on plan:** Essential fix — test was asserting old binary name. No scope creep.

## Issues Encountered

**Pre-existing failures (out of scope, logged to deferred-items):**
- `test_cli_rename.py::test_note_command_appends_to_jsonl` — tests note_cmd.py writing to pending_tool_captures.jsonl; failure pre-dates this plan
- `test_storage.py::TestGraphManagerProject::test_project_driver_creation` — tests .graphiti directory creation in GraphManager; pre-existing
- `test_storage.py::TestGraphManagerProject::test_project_switching` — same class, pre-existing

All 3 failures confirmed pre-existing by stash verification. None caused by this plan's changes.

## Next Phase Readiness

- MCP server now exposes correctly-named `recall_*` tools — Claude Code MCP integration works with Phase 16 rename
- Queue worker uses `recall` binary — queue replay works for captured tool observations (MEM-02)
- Import chain verified: `from src.mcp_server.server import mcp` succeeds with no errors
- Both `_RECALL_CLI` values end in `/recall` (tools: `.venv/bin/recall`, worker: `.venv/bin/recall`)

---
*Phase: 17-fix-stale-binary-references*
*Completed: 2026-03-21*
