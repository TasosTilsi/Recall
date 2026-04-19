---
phase: 28-git-extractor-indexer
plan: 01
subsystem: indexer
tags: [gitpython, extractor, structlog, dataclass, typeddict, json-schema, batch-processing]

# Dependency graph
requires:
  - phase: 27-llm-client
    provides: LLM client (used by downstream plans 28-02/03)
  - phase: 26-db-schema
    provides: SQLite DatabaseManager (used by downstream plans 28-02/03)
provides:
  - src/extractor/ package with git_walker.py and prompt.py
  - CommitRecord dataclass: typed git commit representation
  - walk_commits(): oldest-first commit iteration, merge-commit filtering
  - batch_commits(): configurable chunking (default 10)
  - fetch_diff(): safe diff retrieval with 4000-char truncation
  - EXTRACTION_SCHEMA, EntityRecord, ExtractionResult types
  - build_batch_prompt(): structured prompt for LLM batch extraction
affects:
  - 28-02 (engine): imports CommitRecord, ExtractionResult, EXTRACTION_SCHEMA
  - 28-03 (indexer): uses walk_commits, batch_commits, build_batch_prompt

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD: write failing tests first, then implement, then commit each phase separately"
    - "fetch_diff uses GitCommandError guard — never crashes on unusual commits"
    - "batch_commits pure function — no side effects, easily testable"
    - "build_batch_prompt raises ValueError on empty batch — fail-fast contract"
    - "structlog used in walk_commits for completion logging (not MCP server)"

key-files:
  created:
    - src/extractor/__init__.py
    - src/extractor/git_walker.py
    - src/extractor/prompt.py
    - tests/extractor/__init__.py
    - tests/extractor/test_git_walker.py
    - tests/extractor/test_prompt.py
  modified: []

key-decisions:
  - "CommitRecord.diff field populated at walk time (not lazily) — simplifies downstream code at cost of memory"
  - "fetch_diff truncates to 4000 chars — balances git fidelity vs LLM context window"
  - "build_batch_prompt truncates per-commit diff to 800 chars — tighter control over total prompt size"
  - "VALID_ENTITY_TYPES stored as frozenset — immutable, hashable, supports O(1) membership checks"
  - "EXTRACTION_SCHEMA is a plain Python dict (not JSON string) — callers can serialize when needed"

patterns-established:
  - "extractor package is pure-Python with no async — synchronous git walk feeds async LLM engine above"
  - "merge commit filter: skip if message.strip().startswith('Merge ') — matches git default merge message format"

requirements-completed:
  - IDX-01
  - IDX-03

# Metrics
duration: 3min
completed: 2026-04-19
---

# Phase 28 Plan 01: Git Walker and Prompt Builder Summary

**GitPython-based commit walker with TDD-verified batch chunking and structured LLM extraction prompt contract for the v3.0 git extractor pipeline**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-19T09:19:26Z
- **Completed:** 2026-04-19T09:22:16Z
- **Tasks:** 2 (each with RED/GREEN TDD commits)
- **Files modified:** 6

## Accomplishments

- `src/extractor/git_walker.py`: CommitRecord dataclass + walk_commits (oldest-first, merge-skip) + batch_commits (configurable) + fetch_diff (4000-char truncation, GitCommandError-safe)
- `src/extractor/prompt.py`: VALID_ENTITY_TYPES, EXTRACTION_SCHEMA, EntityRecord/ExtractionResult TypedDicts, build_batch_prompt with 800-char per-commit diff truncation and ValueError on empty input
- 39 tests across both modules, all passing

## Task Commits

Each task was committed atomically with separate RED (test) and GREEN (impl) commits:

1. **Task 1 RED: git walker failing tests** - `1a0b331` (test)
2. **Task 1 GREEN: git walker implementation** - `041ab9f` (feat)
3. **Task 2 RED: prompt module failing tests** - `954c1f2` (test)
4. **Task 2 GREEN: prompt module implementation** - `ec6fbce` (feat)

_TDD tasks have separate test and implementation commits per protocol._

## Files Created/Modified

- `src/extractor/__init__.py` - Package marker (empty)
- `src/extractor/git_walker.py` - CommitRecord, walk_commits, batch_commits, fetch_diff
- `src/extractor/prompt.py` - VALID_ENTITY_TYPES, EXTRACTION_SCHEMA, EntityRecord, ExtractionResult, build_batch_prompt
- `tests/extractor/__init__.py` - Test package marker
- `tests/extractor/test_git_walker.py` - 16 tests for git_walker
- `tests/extractor/test_prompt.py` - 23 tests for prompt module

## Decisions Made

- CommitRecord.diff populated eagerly at walk time (not lazily) — simplifies downstream code; memory overhead acceptable for typical repo sizes
- Per-commit diff truncated to 800 chars in prompt (not 4000) — keeps total prompt size manageable for multi-commit batches
- EXTRACTION_SCHEMA stored as a Python dict — callers can `json.dumps()` it; avoids double-serialization
- VALID_ENTITY_TYPES as frozenset — immutable, hashable, O(1) membership checks

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All exports listed in plan frontmatter are importable: `CommitRecord`, `walk_commits`, `batch_commits`, `fetch_diff` from `src.extractor.git_walker`; `build_batch_prompt`, `EXTRACTION_SCHEMA`, `ExtractionResult`, `EntityRecord` from `src.extractor.prompt`
- Plan 28-02 (engine) can import these types immediately
- Plan 28-03 (indexer) can call walk_commits and batch_commits immediately

---
*Phase: 28-git-extractor-indexer*
*Completed: 2026-04-19*
