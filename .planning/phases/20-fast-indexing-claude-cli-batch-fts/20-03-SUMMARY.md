---
phase: 20-fast-indexing-claude-cli-batch-fts
plan: "03"
subsystem: hooks
tags: [fts, context-injection, toon, ladybugdb, kuzu, cypher]

requires:
  - phase: 15-local-memory-system
    provides: inject_context.py hook base with Option C XML format
  - phase: 12-db-migration
    provides: LadybugDriver with execute_query() and FTS index support

provides:
  - FTS-first 3-layer context injection replacing vector-only search
  - _fts_entity_search() instant keyword match on entity names/summaries (<50ms)
  - _fts_episode_search() instant keyword match on episode content
  - _recent_episodes() Layer 2 chronological retrieval without LLM
  - _get_nodes_by_uuids() Layer 3 full entity detail fetch
  - TOON encoding for Layer 2 and Layer 3 arrays with 3+ items

affects:
  - Phase 20 plan 04 (FTS indexer integration)
  - Phase 20 plan 05 (end-to-end verification)

tech-stack:
  added: []
  patterns:
    - 3-layer progressive disclosure: FTS keywords -> recent episodes -> full vector for top hits
    - TOON encoding applied to arrays of 3+ items for ~40% token reduction
    - asyncio.gather() for parallel Layer 1 + Layer 2 queries (both fast DB queries)
    - Fail-open: any exception in _fetch_context_async returns empty context

key-files:
  created: []
  modified:
    - src/hooks/inject_context.py

key-decisions:
  - "Use driver directly (service._graph_manager.get_driver()) for FTS queries — bypasses service.search() which triggers vector search"
  - "Layer 1 FTS queries run in parallel with Layer 2 recent-episodes via asyncio.gather() — all are fast DB queries"
  - "TOON encoding triggers at len(items) >= 3 for both Layer 2 and Layer 3 — below that, plain text is more efficient"
  - "Merge FTS episode hits into Layer 2 with deduplication by uuid — FTS episodes are more relevant than pure chronological"
  - "QUERY_FTS_INDEX alias pattern: WITH node AS n, score (not __node__) — Pitfall 4 from research"
  - "Use existing driver from service._graph_manager.get_driver() — never open new connection to avoid FTS extension loading issues (Pitfall 5)"

patterns-established:
  - "FTS-first pattern: QUERY_FTS_INDEX Cypher before any vector search for keyword-matching use cases"
  - "3-value return from _fetch_context_async: (continuity_text, layer2_items, layer3_items)"
  - "TOON encoding gating: if len(items) >= 3: encode(toon_data) else: plain text lines"

requirements-completed:
  - PERF-05

duration: pre-committed (2026-03-31)
completed: 2026-03-31
---

# Phase 20 Plan 03: FTS-First Context Injection Summary

**FTS keyword search replacing vector-only context injection: 3-layer progressive disclosure using QUERY_FTS_INDEX Cypher + TOON encoding for ~40% token savings in inject_context.py**

## Performance

- **Duration:** pre-committed in prior session (2026-03-31T19:42:06+03:00)
- **Started:** 2026-03-31T16:39:32Z (phase execution start)
- **Completed:** 2026-03-31T19:42:06+03:00
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments

- Rewrote `src/hooks/inject_context.py` with FTS-first 3-layer retrieval replacing vector-only search
- Layer 1: `CALL QUERY_FTS_INDEX('Entity', 'node_name_and_summary', ...)` and `CALL QUERY_FTS_INDEX('Episodic', 'episode_content', ...)` run in parallel (<50ms each)
- Layer 2: recent episodes by `created_at DESC` run concurrently with Layer 1 (no LLM needed)
- Layer 3: full entity details for top 5 FTS entity hits fetched via `MATCH (n:Entity) WHERE n.uuid IN $uuids`
- TOON encoding via `from toon import encode` applied to Layer 2 and Layer 3 arrays with 3+ items for ~40% token reduction
- All 4 new helper functions committed: `_fts_entity_search`, `_fts_episode_search`, `_recent_episodes`, `_get_nodes_by_uuids`
- `_build_option_c()` rewritten to accept `(continuity, layer2_items, layer3_items, token_budget)` 4-arg signature
- Fail-open behavior preserved: any exception in `_fetch_context_async` returns `{"context": ""}` and exits 0

## Task Commits

1. **Task 1: Rewrite inject_context.py with FTS-first 3-layer retrieval and TOON encoding** - `9751afd` (feat)

## Files Created/Modified

- `src/hooks/inject_context.py` - Rewritten with FTS-first 3-layer progressive disclosure, TOON encoding for Layer 2/3

## Decisions Made

- Use `driver` directly via `service._graph_manager.get_driver()` for FTS queries — bypasses `service.search()` which always runs vector search
- `asyncio.gather()` runs Layer 1 FTS + Layer 2 recent-episodes concurrently — both are fast non-LLM DB queries
- TOON encoding gating at `len(items) >= 3` — below that, plain text lines are shorter than TOON header overhead
- FTS episode hits merged into Layer 2 with uuid-deduplication — relevance over pure chronology
- `WITH node AS n, score` alias pattern (not `__node__`) per Pitfall 4 from 20-RESEARCH.md
- Reuse existing driver from `service._graph_manager.get_driver()` — never open new connection (Pitfall 5: FTS extension must be loaded on existing connection)

## Deviations from Plan

None - inject_context.py was already rewritten with the complete FTS-first implementation in a prior session. The verification check (`python3 -c "from src.hooks.inject_context import _fts_entity_search, _fts_episode_search, _recent_episodes, _build_option_c, main; print('imports OK')"`) passed immediately, and git log confirmed commit `9751afd feat(20-03): FTS-first 3-layer context injection with TOON encoding` was already present.

## Issues Encountered

None - all acceptance criteria already satisfied at execution start.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `inject_context.py` FTS-first 3-layer retrieval is ready for end-to-end testing in Phase 20 plan 05
- Requires a database with FTS indices loaded (built by Phase 20 plans 01-02 batch indexing path)
- TOON encoding operational; `trim_to_token_budget` imported from `src.mcp_server.toon_utils`

## Self-Check

- [x] `src/hooks/inject_context.py` exists and passes import check
- [x] Commit `9751afd` confirmed in `git log --oneline --all`
- [x] All acceptance criteria verified via grep checks

---
*Phase: 20-fast-indexing-claude-cli-batch-fts*
*Completed: 2026-03-31*
