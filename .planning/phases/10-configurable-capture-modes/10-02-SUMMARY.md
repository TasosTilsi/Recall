---
phase: 10-configurable-capture-modes
plan: "02"
subsystem: capture
tags: [llm-config, capture-modes, summarizer, prompt-selection, toml]

# Dependency graph
requires:
  - phase: 10-01
    provides: Phase 10 plan structure and RED test scaffold for capture modes
provides:
  - LLMConfig.capture_mode field with [capture] TOML section parsing and validation
  - BATCH_SUMMARIZATION_PROMPT_NARROW constant (decisions + architecture only)
  - BATCH_SUMMARIZATION_PROMPT_BROAD constant (all 4 categories)
  - BATCH_SUMMARIZATION_PROMPT backward-compatibility alias
  - VALID_CAPTURE_MODES set exported from summarizer module
  - summarize_batch() with capture_mode param selecting narrow vs broad prompt
  - summarize_and_store() with capture_mode param passed through
affects:
  - 10-03-PLAN (CLI config show/set integration reads capture_mode from LLMConfig)
  - 10-04-PLAN (indexer extraction pipeline passes capture_mode to summarize_and_store)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy structlog import inside validation if-block (follows retention_days pattern)"
    - "VALID_CAPTURE_MODES set at module level — single source of truth for validation"
    - "Prompt alias kept for backward compatibility: BATCH_SUMMARIZATION_PROMPT = BATCH_SUMMARIZATION_PROMPT_BROAD"
    - "Security gate (sanitize_content) runs unconditionally before any prompt selection — invariant must not be broken"

key-files:
  created: []
  modified:
    - src/llm/config.py
    - src/capture/summarizer.py

key-decisions:
  - "capture_mode default is 'decisions-only' — narrower scope is the safe default; users opt into broader capture"
  - "Invalid capture_mode falls back to 'decisions-only' with structlog warning — never hard-fails on bad config"
  - "BATCH_SUMMARIZATION_PROMPT alias points to BROAD (not NARROW) for backward compat — preserves pre-Phase-10 behavior"
  - "Prompt selection happens AFTER security gate — sanitize_content invariant is locked from Phase 2"

patterns-established:
  - "Capture mode validation: VALID_CAPTURE_MODES set + fallback to default + structlog warning"
  - "Two-prompt pattern: NARROW for decisions-only, BROAD for decisions-and-patterns"

requirements-completed: [CAPT-01, CAPT-02]

# Metrics
duration: 8min
completed: 2026-03-07
---

# Phase 10 Plan 02: Capture Mode Config and Dual-Prompt Architecture Summary

**LLMConfig.capture_mode field with TOML parsing, plus NARROW/BROAD prompt constants and mode-aware summarize_batch() with security gate invariant preserved**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-07T23:28:02Z
- **Completed:** 2026-03-07T23:36:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Extended LLMConfig with `capture_mode: str = "decisions-only"` field and `[capture]` TOML section parsing in `load_config()` with validation and fallback
- Added `BATCH_SUMMARIZATION_PROMPT_NARROW` (2-category) and `BATCH_SUMMARIZATION_PROMPT_BROAD` (4-category) prompt constants plus `VALID_CAPTURE_MODES` set to `src/capture/summarizer.py`
- Updated `summarize_batch()` and `summarize_and_store()` with `capture_mode` parameter; security gate (sanitize_content) runs unconditionally before prompt selection
- All 7 target tests GREEN (4 TestCaptureModeConfig + 2 TestCaptureModeSelection + 1 TestSecurityGate); 279 total tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend LLMConfig with capture_mode field** - `70c203a` (feat)
2. **Task 2: Add dual prompt constants and capture_mode parameter to summarizer.py** - `f029911` (feat, part of test(10-01) commit)

_Note: Task 2 summarizer changes were committed in the same session as the test scaffold (f029911)_

## Files Created/Modified
- `src/llm/config.py` — Added `capture_mode: str = "decisions-only"` field to LLMConfig; added `[capture]` section parsing with `VALID_CAPTURE_MODES` validation in `load_config()`
- `src/capture/summarizer.py` — Added `VALID_CAPTURE_MODES`, `BATCH_SUMMARIZATION_PROMPT_NARROW`, `BATCH_SUMMARIZATION_PROMPT_BROAD` constants; backward-compat alias; `capture_mode` param on `summarize_batch()` and `summarize_and_store()`

## Decisions Made
- `capture_mode` default is `"decisions-only"` — narrower scope is the safe default; users must opt into broader 4-category capture
- Invalid `capture_mode` values fall back to `"decisions-only"` with structlog warning rather than hard-failing — consistent with `retention_days` pattern
- `BATCH_SUMMARIZATION_PROMPT` alias points to `BATCH_SUMMARIZATION_PROMPT_BROAD` (not NARROW) to preserve pre-Phase-10 behavior for any callers not yet passing `capture_mode`
- Prompt selection logic placed AFTER `sanitize_content()` call — the security gate invariant (locked Phase 2 decision) must never be broken

## Deviations from Plan

None - plan executed exactly as written. Both files were already partially modified from a prior session; the implementation matched the plan specification exactly and all tests passed GREEN.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CAPT-01 and CAPT-02 requirements complete
- Plan 10-03 can now add CLI `config show` and `config --set capture.mode` support (reads `LLMConfig.capture_mode`, validates against `VALID_CAPTURE_MODES`)
- Plan 10-04 can now wire `capture_mode` through the indexer extraction pipeline via `summarize_and_store(capture_mode=config.capture_mode)`

---
*Phase: 10-configurable-capture-modes*
*Completed: 2026-03-07*
