---
phase: 10-configurable-capture-modes
plan: 03
subsystem: capture
tags: [capture-mode, cli-config, git-worker, conversation, llm-config]

# Dependency graph
requires:
  - phase: 10-01
    provides: BATCH_SUMMARIZATION_PROMPT_NARROW and BROAD, capture_mode param in summarize_batch/summarize_and_store
  - phase: 10-02
    provides: LLMConfig.capture_mode field, load_config() reading [capture] TOML section
provides:
  - CLI config show with Capture Settings and Retention Settings sections
  - graphiti config --set capture.mode with allowed_values validation
  - graphiti config --get capture.mode returning actual mode value
  - capture_mode threaded from load_config() to summarize_and_store() in git_worker.py
  - capture_mode threaded from load_config() to summarize_and_store() in conversation.py
affects: [phase 11, phase 12, any future CLI config additions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "allowed_values validation pattern in VALID_CONFIG_KEYS for constrained string config keys"
    - "load_config() called once at top of async function to thread mode through pipeline"

key-files:
  created: []
  modified:
    - src/cli/commands/config.py
    - src/capture/git_worker.py
    - src/capture/conversation.py
    - tests/test_cli_commands.py

key-decisions:
  - "allowed_values enforcement happens after _parse_value() and before _set_nested_value() in --set handler — clean separation of type parsing and domain validation"
  - "load_config() called once per process_pending_commits() invocation, not per commit — acceptable disk I/O, no caching needed"
  - "table.add_row() with section header rows appended after the existing for-loop — avoids refactoring the loop structure"

patterns-established:
  - "VALID_CONFIG_KEYS allowed_values: list enforces domain-specific valid values for --set; validated before TOML write"

requirements-completed: [CAPT-01, CAPT-02, CAPT-03]

# Metrics
duration: 10min
completed: 2026-03-08
---

# Phase 10 Plan 03: CLI Config + Call Site Wiring Summary

**capture.mode CLI support complete with allowed_values validation; git_worker and conversation now thread capture_mode from load_config() to summarize_and_store() at all call sites**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-08T00:21:00Z
- **Completed:** 2026-03-08T00:26:36Z
- **Tasks:** 2 (Task 3 is checkpoint:human-verify — pending user approval)
- **Files modified:** 4

## Accomplishments
- CLI `graphiti config show` now renders Capture Settings and Retention Settings sections with correct rows
- `graphiti config --set capture.mode=decisions-and-patterns` validates against allowed values and persists to TOML
- `graphiti config --set capture.mode=invalid` exits non-zero with "Valid values: decisions-only, decisions-and-patterns"
- `graphiti config --get capture.mode` returns actual mode (not blank) via attr_map entry
- git_worker.py loads config once per batch and passes `capture_mode=cfg.capture_mode` to both summarize_and_store() call sites (full batch + partial batch flush)
- conversation.py loads config and passes `capture_mode=cfg.capture_mode` to summarize_and_store()
- All 285 tests passing — no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Update CLI config command** - `95882aa` (feat)
2. **Task 2: Wire capture_mode through git_worker and conversation** - `cfb5c01` (feat)

## Files Created/Modified
- `src/cli/commands/config.py` - Added capture.mode and retention.retention_days to VALID_CONFIG_KEYS, attr_map, table rows, and JSON output; added allowed_values validation in --set handler
- `src/capture/git_worker.py` - Added load_config import; cfg = load_config() at top of process_pending_commits(); capture_mode=cfg.capture_mode on both summarize_and_store() calls
- `src/capture/conversation.py` - Added load_config import; cfg = load_config() before summarize_and_store(); capture_mode=cfg.capture_mode on call
- `tests/test_cli_commands.py` - Added capture_mode and retention_days to _create_mock_config() (bug fix)

## Decisions Made
- allowed_values validation added after _parse_value() and before _set_nested_value() to keep type parsing and domain validation separate
- load_config() called once at the top of process_pending_commits() rather than per-commit to minimize disk I/O while still reading current config
- Section header rows appended after the existing for-loop rather than refactoring the loop to avoid risk of breaking existing rows

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed _create_mock_config() missing capture_mode and retention_days attributes**
- **Found during:** Task 2 verification (full test suite run)
- **Issue:** test_cli_commands.py::test_config_show_all failed with NotRenderableError because the Mock config object didn't have capture_mode or retention_days set, causing Rich to try to render Mock objects directly in table cells
- **Fix:** Added `mock_config.capture_mode = "decisions-only"` and `mock_config.retention_days = 90` to _create_mock_config() helper
- **Files modified:** tests/test_cli_commands.py
- **Verification:** Full test suite 285/285 passed after fix
- **Committed in:** cfb5c01 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 bug)
**Impact on plan:** Fix essential — the Mock helper was already in the pattern of listing all config attributes explicitly (prior FIXed comments show this pattern). Adding the new Phase 10 attributes maintains the same invariant. No scope creep.

## Issues Encountered
None beyond the auto-fixed mock config regression.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 10 implementation complete pending human-verify checkpoint approval
- All 3 requirements (CAPT-01, CAPT-02, CAPT-03) are GREEN
- 285 tests passing
- Checkpoint awaiting user visual verification of `graphiti config show` output

---
*Phase: 10-configurable-capture-modes*
*Completed: 2026-03-08*
