---
phase: 10-configurable-capture-modes
plan: "04"
subsystem: indexer
tags: [capture-mode, extraction, git-indexer, prompt-selection, tdd]

requires:
  - phase: 10-02
    provides: LLMConfig.capture_mode field and load_config() parsing [capture] TOML section

provides:
  - capture_mode-aware extract_commit_knowledge() with NARROW/BROAD free-form prompt selection
  - FREE_FORM_EXTRACTION_PROMPT_NARROW and FREE_FORM_EXTRACTION_PROMPT_BROAD constants in extraction.py
  - FREE_FORM_EXTRACTION_PROMPT backward-compatible alias pointing to BROAD
  - GitIndexer.run() loads config once and passes capture_mode to both extract_commit_knowledge() call sites
  - TestIndexerCaptureMode (2 tests) covering decisions-only and decisions-and-patterns modes

affects:
  - graphiti index CLI behavior (now mode-aware)
  - any future plan touching extraction.py or indexer.py

tech-stack:
  added: []
  patterns:
    - "capture_mode param with decisions-only default — narrower scope is safe default, opt-in for broad"
    - "load_config() called once at run() top-level — not per-commit — to avoid repeated disk reads during batch index"
    - "asyncio.run() in sync test methods — project convention, no pytest-asyncio needed"

key-files:
  created: []
  modified:
    - src/indexer/extraction.py
    - src/indexer/indexer.py
    - tests/test_capture_modes.py

key-decisions:
  - "FREE_FORM_EXTRACTION_PROMPT alias retained pointing to BROAD prompt for backward compatibility with any existing callers"
  - "Test code uses asyncio.run() in sync test methods matching project convention — plan template used pytest.mark.asyncio which is not installed"
  - "load_config() called once at GitIndexer.run() start, not per-commit, to minimize disk reads during batch index"
  - "capture_mode='decisions-only' is the safe default — narrower scope; users opt into broader capture via TOML"

patterns-established:
  - "Prompt selection via capture_mode: 'decisions-and-patterns' -> BROAD, else -> NARROW (any unknown value defaults to narrow)"
  - "Backward-compatible alias pattern: old constant name = new BROAD constant for zero regression risk"

requirements-completed: [CAPT-01, CAPT-02]

duration: 3min
completed: "2026-03-08"
---

# Phase 10 Plan 04: Indexer Capture Mode Wiring Summary

**Mode-aware FREE_FORM_EXTRACTION_PROMPT selection in extract_commit_knowledge() with NARROW/BROAD constants and GitIndexer.run() wiring via load_config()**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-08T00:24:06Z
- **Completed:** 2026-03-08T00:27:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Replaced single FREE_FORM_EXTRACTION_PROMPT with NARROW (omits bugs/deps) and BROAD (all categories) named constants plus backward-compatible alias
- Added capture_mode: str = "decisions-only" parameter to extract_commit_knowledge() with freeform_prompt_template selection before Pass 2
- Wired capture_mode through GitIndexer.run() via load_config() called once at run() start, threading capture_mode=cfg.capture_mode to both asyncio.run() and loop.run_until_complete() call sites
- Added TestIndexerCaptureMode (2 tests) confirming decisions-only omits bugs/deps and decisions-and-patterns includes them
- All 285 tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Write TestIndexerCaptureMode tests (RED) then implement extraction.py changes** - `906bc26` (feat)
2. **Task 2: Wire capture_mode through indexer.py** - `cfb5c01` (feat, bundled with Plan 10-03 commit)

_Note: Task 2 indexer.py changes were committed alongside Plan 10-03 changes in cfb5c01 — both sets of changes were in the working tree and staged together by the concurrent process._

## Files Created/Modified
- `src/indexer/extraction.py` - Added NARROW/BROAD prompt constants, FREE_FORM_EXTRACTION_PROMPT alias, capture_mode param, freeform_prompt_template selection before Pass 2
- `src/indexer/indexer.py` - Added load_config import, cfg = load_config() at run() start, capture_mode=cfg.capture_mode to both extract_commit_knowledge() call sites
- `tests/test_capture_modes.py` - Appended TestIndexerCaptureMode class with 2 sync asyncio.run() tests

## Decisions Made
- Retained FREE_FORM_EXTRACTION_PROMPT alias pointing to BROAD for backward compatibility with any existing importers
- Used asyncio.run() in sync test methods to match project convention (pytest-asyncio not installed); plan template used @pytest.mark.asyncio which required a Rule 3 auto-fix
- load_config() called once at GitIndexer.run() start (not per-commit) to minimize disk reads during batch indexing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Replaced @pytest.mark.asyncio with asyncio.run() in test methods**
- **Found during:** Task 1 (TestIndexerCaptureMode RED tests)
- **Issue:** Plan test template used `@pytest.mark.asyncio` and `async def` but project does not have pytest-asyncio installed; tests failed with "async def functions are not natively supported"
- **Fix:** Rewrote TestIndexerCaptureMode tests as sync methods using `asyncio.run()` to match established project convention (documented in test_record_access.py and test_retention_manager.py)
- **Files modified:** tests/test_capture_modes.py
- **Verification:** Both tests collected and passed GREEN after fix
- **Committed in:** 906bc26 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 3 - blocking)
**Impact on plan:** Required fix for project convention compliance. No scope creep.

## Issues Encountered
- Task 2 indexer.py changes were bundled into cfb5c01 (Plan 10-03 commit) by a concurrent process that staged the working tree. All changes are committed and verified correct via grep and test run.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 10 complete: capture_mode field in LLMConfig, NARROW/BROAD prompts in summarizer.py and extraction.py, GitIndexer wired, CLI config show/set with validation — full pipeline coverage
- Ready for Phase 11 (Graph UI) or Phase 12 (Multi-Provider LLM)
- No blockers from this plan

---
*Phase: 10-configurable-capture-modes*
*Completed: 2026-03-08*

## Self-Check: PASSED

- FOUND: src/indexer/extraction.py
- FOUND: src/indexer/indexer.py
- FOUND: tests/test_capture_modes.py
- FOUND: .planning/phases/10-configurable-capture-modes/10-04-SUMMARY.md
- FOUND commit: 906bc26 (Task 1)
- FOUND commit: cfb5c01 (Task 2)
