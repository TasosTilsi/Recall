---
phase: 21-knowledge-quality-uplift
plan: 01
subsystem: indexer
tags: [extraction, prompt-engineering, claude-cli, git-indexer, knowledge-graph]

# Dependency graph
requires:
  - phase: 20-fast-indexing-claude-cli-batch-fts
    provides: extract_commits_batch() and BATCH_EXTRACTION_PROMPT in src/indexer/extraction.py
provides:
  - Extended BATCH_EXTRACTION_PROMPT with code block entity extraction (pipe-delimited format)
  - Extended BATCH_EXTRACTION_PROMPT with 7 semantic relationship verbs as preferred vocabulary
affects: [21-02, 21-03, ui-entity-panel, knowledge-graph-quality]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pipe-delimited structured entity format: Code Block: <name> | File: <path> | Language: <lang> | Type: function/class"
    - "7 semantic relationship verbs: MODIFIES, INTRODUCES, FIXES, DEPENDS_ON, REMOVES, REFACTORS, TESTS"

key-files:
  created: []
  modified:
    - src/indexer/extraction.py

key-decisions:
  - "Code block entities embedded inside entities array (not separate add_episode calls) -- single graphiti-core pass extracts both commit-level and code-level knowledge"
  - "Pipe-delimited format chosen for human-readability and parseability; | delimiter unlikely in paths or names"
  - "Episode body builder left unchanged -- structured entity strings flow through join() naturally (D-02)"

patterns-established:
  - "BATCH_EXTRACTION_PROMPT: structured entity sub-format within entities array for richer entity types"
  - "Semantic verb vocabulary steered via prompt language, not post-processing"

requirements-completed: [SC-2, SC-3, SC-4]

# Metrics
duration: 1min
completed: 2026-04-03
---

# Phase 21 Plan 01: Knowledge Quality Uplift - Batch Prompt Enrichment Summary

**BATCH_EXTRACTION_PROMPT extended with pipe-delimited code block entity format and 7 semantic relationship verbs (MODIFIES, INTRODUCES, FIXES, DEPENDS_ON, REMOVES, REFACTORS, TESTS)**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-03T06:42:45Z
- **Completed:** 2026-04-03T06:43:30Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Extended `BATCH_EXTRACTION_PROMPT` with instructions to extract function/class definitions from diff added lines as structured `Code Block: <name> | File: <path> | Language: <lang> | Type: function/class` entries in the `entities` array
- Updated the JSON example in the prompt to show both a code block entity and a semantic relationship verb usage
- Added the 7 preferred relationship verbs (MODIFIES, INTRODUCES, FIXES, DEPENDS_ON, REMOVES, REFACTORS, TESTS) with explicit instruction to use them in relationship strings
- Episode body builder (`lines 306-308`) left completely unchanged — structured entity strings flow through `', '.join()` naturally

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend BATCH_EXTRACTION_PROMPT with code block extraction + semantic relationship vocabulary** - `fafec10` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `src/indexer/extraction.py` - Extended `BATCH_EXTRACTION_PROMPT` string with code block extraction instruction and semantic relationship vocabulary

## Decisions Made
- Code block entities placed inside `entities` array (not separate `add_episode()` calls) — this matches D-02 from CONTEXT.md: graphiti-core gets full context in one pass with no extra LLM overhead
- Episode body builder left unchanged (D-02): `', '.join(extracted.get('entities', []))` naturally propagates structured `Code Block:` strings into the episode body text
- Prompt kept concise: two short instruction paragraphs added, no verbose explanations that would consume claude -p context budget

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - the prompt change is complete and functional. Structured code block entities will be produced on the next `recall index` run. Phase 21-02 (EntityPanel UI chips) will consume these entities in the UI.

## Next Phase Readiness
- Prompt enrichment complete; next `recall index` run will produce structured `Code Block:` entities and semantic relationship labels in the graph
- Phase 21-02 (EntityPanel UI chips) can now parse the pipe-delimited format from entity summaries
- Phase 21-03 (color tokens for Function/Class entity types) can proceed independently

---
*Phase: 21-knowledge-quality-uplift*
*Completed: 2026-04-03*
