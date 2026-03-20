---
phase: 16-rename-cli-consolidation
plan: "02"
subsystem: cli
tags: [typer, recall, cli-consolidation, git-sync]

# Dependency graph
requires:
  - phase: 16-01-rename-cli-consolidation
    provides: "recall/rc entrypoints, 10+1 command skeleton in src/cli/__init__.py"
provides:
  - "recall list with --name/--stale/--compact/--queue flags absorbing show/stale/compact/queue commands"
  - "recall search with silent auto-sync before every query (CLI-03)"
affects: [16-03, 16-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Flag-dispatch pattern: top-level routing block before default behavior routes to named helpers"
    - "_auto_sync fail-open pattern: try/except Exception wrapping GitIndexer.run() for silent best-effort sync"

key-files:
  created: []
  modified:
    - src/cli/commands/list_cmd.py
    - src/cli/commands/search.py

key-decisions:
  - "Rename existing --compact/-c (one-line view) to --one-line/-c to avoid collision with new --compact (archive stale) flag"
  - "Queue status keys: use status['pending'] and status['dead_letter'] matching actual get_status() return dict (not status['pending_count'] as in plan draft)"
  - "_auto_sync placed after resolve_scope before console.status spinner — runs synchronously, bounded by GitIndexer cooldown"

patterns-established:
  - "Flag-dispatch at top of command: queue -> stale -> compact -> name -> default table"
  - "Helper functions prefixed with _ before command function — keeps command signatures clean"

requirements-completed: [CLI-02, CLI-03]

# Metrics
duration: 12min
completed: 2026-03-20
---

# Phase 16 Plan 02: Expand list and search commands Summary

**recall list absorbs show/stale/compact/queue via 4 new flags; recall search silently auto-syncs git before every query**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-20T10:00:00Z
- **Completed:** 2026-03-20T10:12:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `recall list <name>` replaces `recall show` — entity detail with Rich panel display, ambiguous-match resolution, access recording
- `recall list --stale/--compact/--queue` replaces 3 hidden plumbing commands via flag-dispatch routing
- `recall search` auto-syncs git history before every query via `_auto_sync()` — silent, fail-open, cooldown-bounded

## Task Commits

Each task was committed atomically:

1. **Task 1: Expand list_cmd.py with --name/--stale/--compact/--queue flags** - `b8ce5ad` (feat)
2. **Task 2: Add auto-sync to search.py (CLI-03)** - `a1173e2` (feat)

## Files Created/Modified
- `src/cli/commands/list_cmd.py` - Expanded with 4 new flags + 4 helper functions; --compact/-c renamed to --one-line/-c
- `src/cli/commands/search.py` - Added _auto_sync() helper; called after resolve_scope before search spinner

## Decisions Made
- Renamed existing `--compact/-c` (one-line-per-item view) to `--one-line/-c` to avoid collision with the new `--compact` (archive stale nodes) flag — behavior preserved, only option name changed
- Used actual `get_status()` return keys (`pending`, `dead_letter`, `max_size`) rather than plan draft keys (`pending_count`, `dead_count`, `capacity`) — corrected by reading actual queue module

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected queue status dict keys in _show_queue_status**
- **Found during:** Task 1 (expand list_cmd.py)
- **Issue:** Plan's `_show_queue_status` draft used `status.get("pending_count", 0)` and `status.get("dead_count", 0)` but `get_status()` returns keys `pending`, `dead_letter`, `max_size`
- **Fix:** Used correct keys: `status.get("pending", 0)`, `status.get("dead_letter", 0)`, `status.get("max_size", 0)`
- **Files modified:** src/cli/commands/list_cmd.py
- **Verification:** Verified by reading src/queue/__init__.py get_status() docstring
- **Committed in:** b8ce5ad (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug - incorrect dict keys)
**Impact on plan:** Essential correctness fix. No scope creep.

## Issues Encountered
- `src/cli/__init__.py` imported `init_cmd` and `note_cmd` (set up in plan 16-01) which were staged but not yet committed — they got committed as part of Task 1's `git add`. These files unblocked the import chain for the acceptance criteria check.

## Next Phase Readiness
- `list_cmd.py` and `search.py` fully updated per CLI-02 and CLI-03
- Ready for plan 16-03 (recall init command) and 16-04 (recall note command)
- The `show`, `stale`, `compact`, `queue` commands still exist in the codebase — they will be deleted in a later plan

---
*Phase: 16-rename-cli-consolidation*
*Completed: 2026-03-20*
