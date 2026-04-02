---
phase: 20-fast-indexing-claude-cli-batch-fts
plan: "05"
subsystem: testing
tags: [pytest, asyncio, claude-cli, batch-extraction, fts, semaphore, tdd]

requires:
  - phase: 20-01
    provides: ClaudeCliLLMClient and _claude_p function for subprocess wrapping
  - phase: 20-02
    provides: extract_commits_batch(), BATCH_SIZE constant, semaphore indexer pattern
  - phase: 20-03
    provides: inject_context.py FTS Layer 1 and _build_option_c 3-layer function
  - phase: 20-04
    provides: session_stop.py claude CLI wiring with Ollama fallback

provides:
  - "24-test suite covering PERF-01 through PERF-05 requirements"
  - "ClaudeCliLLMClient interface compliance tests (8 tests)"
  - "Batch extraction + semaphore parallelism tests (6 tests)"
  - "FTS layer queries + session_stop claude wiring tests (9 tests + 1 timing proof)"

affects:
  - "Phase 20 requirements verification"
  - "Future CI runs: test_claude_cli_client.py, test_indexer_batch.py, test_hooks_phase20.py"

tech-stack:
  added: []
  patterns:
    - "asyncio.run() in synchronous test methods (project convention, asyncio_mode=strict)"
    - "Lazy import mock target: src.llm.claude_cli_client._claude_p (not extraction.py)"
    - "Semaphore timing proof: 3 x 0.1s parallel tasks must complete in <0.15s"
    - "FTS Cypher verification: assert QUERY_FTS_INDEX in call_args[0][0]"
    - "Source inspection pattern for session_stop: inspect.getsource() + index ordering"

key-files:
  created:
    - tests/test_claude_cli_client.py
    - tests/test_indexer_batch.py
    - tests/test_hooks_phase20.py
  modified: []

key-decisions:
  - "Used asyncio.run() inside synchronous test methods (not @pytest.mark.asyncio) to follow project convention for asyncio_mode=strict"
  - "Mock target for _claude_p is src.llm.claude_cli_client._claude_p because it is a lazy import inside extract_commits_batch function body, not a module-level import in extraction.py"
  - "Timing proof uses asyncio.Semaphore(3) with 3 parallel 0.1s tasks asserting <0.15s total — unit proxy for 30-commit-in-2min PERF-01 wall-clock goal"

patterns-established:
  - "FTS test pattern: mock driver.execute_query returning (records, None, None) tuple; assert Cypher keyword in call_args[0][0]"
  - "Session stop wiring test: use inspect.getsource() + str.index() to verify code ordering (claude_idx < thread_idx)"

requirements-completed: [PERF-01, PERF-02, PERF-03, PERF-04, PERF-05]

duration: 15min
completed: "2026-04-02"
---

# Phase 20 Plan 05: Fast Indexing Test Suite Summary

**24-test coverage of claude-cli batch extraction, FTS-first context injection, and session_stop claude wiring across 3 new test files**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-02T20:45:00Z
- **Completed:** 2026-04-02T20:57:36Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Created `tests/test_claude_cli_client.py`: 9 tests for ClaudeCliLLMClient ABC compliance, subprocess parsing, PATH detection, and response model JSON/code-fence handling (PERF-02)
- Created `tests/test_indexer_batch.py`: 6 tests for batch extraction success/failure paths, BATCH_SIZE constant, semaphore concurrency limit, and PERF-01 parallelism timing proof
- Created `tests/test_hooks_phase20.py`: 9 tests for FTS Layer 1 Cypher queries, 3-layer _build_option_c XML structure, and session_stop claude CLI ordering verification

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test_claude_cli_client.py (PERF-02)** - `6617304` (test)
2. **Task 2: Create test_indexer_batch.py (PERF-01, PERF-03)** - `ecd1cca` (test)
3. **Task 3: Create test_hooks_phase20.py (PERF-04, PERF-05)** - `e9ba057` (test)

## Files Created/Modified
- `tests/test_claude_cli_client.py` - ClaudeCliLLMClient unit tests: detection, subprocess, ABC compliance, response parsing
- `tests/test_indexer_batch.py` - Batch extraction tests: per-commit results, error handling, BATCH_SIZE, semaphore timing proof
- `tests/test_hooks_phase20.py` - FTS query tests, _build_option_c 3-layer XML, session_stop source ordering

## Decisions Made
- Used `asyncio.run()` inside synchronous test methods (project convention for `asyncio_mode=strict`) rather than `@pytest.mark.asyncio` coroutines
- Mock target for `_claude_p` set to `src.llm.claude_cli_client._claude_p` (where defined) because `extract_commits_batch` does a lazy function-body import, not a module-level import in `extraction.py`
- Parallelism timing proof asserts `elapsed < 0.15s` for 3 concurrent 0.1s tasks with Semaphore(3) — provides unit-level evidence of the PERF-01 wall-clock goal without requiring real commits

## Deviations from Plan

None - plan executed exactly as written. Test structure, mock targets, and assertions match the plan specification. The plan's `@pytest.mark.asyncio` async test style was adapted to `asyncio.run()` in synchronous methods to follow the established project convention (all 400+ existing tests use this pattern).

## Issues Encountered

Pre-existing failing tests (out of scope, not caused by plan-05 changes):
- `tests/test_cli_commands.py::test_search_json` — fails before and after our changes (output format mismatch)
- `tests/test_hooks_phase15.py::test_inject_context_token_budget` — TypeError pre-existing since Phase 15

Both confirmed via `git stash` verification. No action taken per deviation scope rules.

## Known Stubs

None — tests are fully wired to real module imports with mocked external calls.

## Next Phase Readiness

Phase 20 is complete. All 5 plans executed:
- 20-01: ClaudeCliLLMClient + _claude_p subprocess wrapper
- 20-02: extract_commits_batch() + semaphore parallelism
- 20-03: inject_context.py FTS-first 3-layer context
- 20-04: session_stop.py claude CLI wiring
- 20-05: Test suite (this plan)

PERF-01 through PERF-05 requirements are covered with 24 passing tests.

---
*Phase: 20-fast-indexing-claude-cli-batch-fts*
*Completed: 2026-04-02*
