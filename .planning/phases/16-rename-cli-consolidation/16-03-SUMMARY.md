---
phase: 16-rename-cli-consolidation
plan: "03"
subsystem: cli
tags: [recall, hooks, git-indexer, cleanup, binary-rename]

# Dependency graph
requires:
  - phase: 16-01
    provides: "__init__.py cleaned of 11 command registrations; recall entrypoint established"
  - phase: 16-02
    provides: "search auto-sync via GitIndexer; list command expansion"
provides:
  - "11 dead command files deleted from src/cli/commands/"
  - "session_start.py calls GitIndexer directly (no subprocess, no binary dependency)"
  - "manager.py uses _RECALL_CLI pointing to recall binary"
  - "installer.py legacy hook updated from graphiti capture to recall note"
affects: [phase-17, testing, hooks-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Direct GitIndexer call pattern in hook context (no subprocess/binary dep)"]

key-files:
  created: []
  modified:
    - src/hooks/session_start.py
    - src/hooks/manager.py
    - src/hooks/installer.py
  deleted:
    - src/cli/commands/add.py
    - src/cli/commands/capture.py
    - src/cli/commands/compact.py
    - src/cli/commands/hooks.py
    - src/cli/commands/memory.py
    - src/cli/commands/mcp.py
    - src/cli/commands/queue_cmd.py
    - src/cli/commands/show.py
    - src/cli/commands/stale.py
    - src/cli/commands/summarize.py
    - src/cli/commands/sync.py

key-decisions:
  - "session_start.py calls GitIndexer directly instead of subprocess to recall sync — sync command is deleted, direct call is simpler and eliminates binary name dependency"
  - "capture_entry.py, session_stop.py, inject_context.py had no graphiti binary refs — .graphiti/ directory path strings are unchanged (data directory, not CLI binary)"
  - "installer.py uninstall_claude_hook detects both graphiti capture and recall note for backward compat during migration"

patterns-established:
  - "Hook scripts: import src.* directly, never subprocess to CLI binary — avoids PATH/binary-name brittleness"
  - "_RECALL_CLI pattern in manager.py for any subprocess calls that do need the binary"

requirements-completed: [CLI-01, CLI-02]

# Metrics
duration: 8min
completed: 2026-03-20
---

# Phase 16 Plan 03: Delete Dead Commands and Rename Hook Binary References Summary

**11 obsolete CLI command files deleted; session_start.py upgraded to call GitIndexer directly (no subprocess); all hook manager/installer references updated from graphiti to recall binary**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-20T10:15:00Z
- **Completed:** 2026-03-20T10:23:00Z
- **Tasks:** 2
- **Files modified:** 3 modified, 11 deleted

## Accomplishments
- Deleted 11 dead command files (add, capture, compact, hooks, memory, mcp, queue_cmd, show, stale, summarize, sync) — index.py kept as hidden command
- Replaced subprocess `[graphiti, "sync"]` in session_start.py with direct `GitIndexer(project_root).run(full=False)` call — eliminates binary name dependency entirely
- Renamed `_GRAPHITI_CLI` to `_RECALL_CLI` in manager.py pointing to recall binary
- Updated installer.py legacy hook command from `graphiti capture` to `recall note`; detection logic handles both old and new command strings for backward compat

## Task Commits

Each task was committed atomically:

1. **Task 1: Delete 11 removed command files** - `145f5d7` (chore)
2. **Task 2: Update hook scripts to recall binary; GitIndexer direct call** - `806cd36` (feat)

## Files Created/Modified
- `src/hooks/session_start.py` - Removed subprocess sync, added direct GitIndexer call; removed _GRAPHITI_CLI, SYNC_TIMEOUT_SECONDS, import subprocess
- `src/hooks/manager.py` - _GRAPHITI_CLI renamed to _RECALL_CLI pointing to recall binary
- `src/hooks/installer.py` - Legacy install_claude_hook() command updated; uninstall/check funcs detect both graphiti capture and recall note

**Deleted (11 files):** src/cli/commands/add.py, capture.py, compact.py, hooks.py, memory.py, mcp.py, queue_cmd.py, show.py, stale.py, summarize.py, sync.py

## Decisions Made
- `capture_entry.py`, `session_stop.py`, `inject_context.py` needed no changes — they use no graphiti binary subprocess calls; only reference `.graphiti/` as a data directory path (unchanged)
- `installer.py` backward-compat: uninstall checks detect both `graphiti capture` and `recall note` so existing project-local hooks can be cleanly removed after Phase 16 rename

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 16 rename is complete across CLI and hooks
- recall binary is the sole CLI entrypoint; no references to graphiti binary remain in hooks
- Any existing project-local .claude/settings.json entries with graphiti capture can be uninstalled via recall (backward-compat detection in installer.py)

---
*Phase: 16-rename-cli-consolidation*
*Completed: 2026-03-20*
