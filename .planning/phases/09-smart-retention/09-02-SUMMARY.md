---
phase: 09-smart-retention
plan: "02"
subsystem: retention
tags: [retention, graphiti, sqlite, archive, staleness, entity-filtering]

# Dependency graph
requires:
  - phase: 09-01
    provides: RetentionManager with get_archive_state_uuids, get_pin_state_uuids, archive_node, clear_archive, record_access, compute_score
provides:
  - GraphService.list_stale() — stale entity listing excluding archived/pinned, sorted by score ascending
  - GraphService.archive_nodes() — SQLite-only archiving for given UUIDs, returns count
  - GraphService.record_access() — access event upsert with exception isolation
  - list_entities() post-filters archived nodes via get_archive_state_uuids() batch call
  - search() post-filters archived nodes via get_archive_state_uuids() batch call
  - add() reactivation hook — clears archive_state when graphiti-core dedup matches archived entity
  - uuid field added to list_entities() and get_entity() result dicts
affects:
  - 09-03  # CLI retention commands call list_stale, archive_nodes
  - 09-04  # APScheduler sweep uses archive_nodes
  - 09-05  # retention summary/stats use list_stale

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Lazy import of get_retention_manager inside method bodies — avoids circular import from src.graph.service to src.retention
    - Batch retention reads: get_archive_state_uuids() and get_pin_state_uuids() called once per method invocation (not N+1)
    - Archive filtering with try/except fallback — retention DB unavailability never crashes core graph operations
    - TDD red-green pattern (asyncio.run() in sync tests — no pytest-asyncio needed)
    - Reactivation fast path: skip entity query entirely when archive_state is empty

key-files:
  created:
    - tests/test_graph_service_retention.py
    - tests/test_record_access.py
    - tests/test_reactivation.py
  modified:
    - src/graph/service.py

key-decisions:
  - "Lazy imports inside each method (from src.retention import get_retention_manager) — prevents circular import; module-level import would create src.graph.service → src.retention → src.graph circular dependency risk"
  - "uuid field added to list_entities() and get_entity() result dicts — required for archive filtering to work; previously missing"
  - "search() result dicts get uuid/source_node_uuid/target_node_uuid fields added — needed for edge-level archive filtering"
  - "Reactivation fast path: when get_archive_state_uuids() returns empty set, skip EntityNode.get_by_group_ids() entirely — avoids Kuzu query on most add() calls"
  - "asyncio.run() in sync test functions — consistent with project test pattern; pytest-asyncio not installed"

patterns-established:
  - "Archive post-filter pattern: try/except block at end of list method; on exception, log retention_filter_failed and return unfiltered list"
  - "Record access isolation pattern: wrap in try/except, log warning on failure, never propagate to caller"
  - "Reactivation block pattern: placed after add_episode() and before return; entire block in try/except"

requirements-completed: [RETN-01, RETN-02, RETN-06]

# Metrics
duration: 22min
completed: "2026-03-05"
---

# Phase 9 Plan 02: GraphService Retention Integration Summary

**GraphService extended with list_stale, archive_nodes, record_access methods; list_entities and search post-filter archived nodes; add() reactivates archived entities matched by graphiti-core dedup**

## Performance

- **Duration:** 22 min
- **Started:** 2026-03-05T23:10:00Z
- **Completed:** 2026-03-05T23:32:00Z
- **Tasks:** 3
- **Files modified:** 4 (src/graph/service.py + 3 new test files)

## Accomplishments

- Added `list_stale(scope, project_root)`: fetches all entities, excludes archived and pinned via batch reads, filters by age > retention_days, computes staleness score via `RetentionManager.compute_score()`, returns sorted ascending by score (most stale first)
- Added `archive_nodes(uuids, scope, project_root)`: calls `retention.archive_node()` per UUID, SQLite-only (Kuzu graph untouched), returns count
- Added `record_access(uuid, scope, project_root)`: upserts access_log via retention manager; exception isolated with structlog warning
- Extended `list_entities()`: added `uuid` to result dicts; post-filters archived nodes via `get_archive_state_uuids()` one batch call; graceful fallback on DB error
- Extended `search()`: added `uuid`/`source_node_uuid`/`target_node_uuid` to result dicts; post-filters archived nodes; graceful fallback on DB error
- Instrumented `add()`: reactivation block after `add_episode()`; fast path when archive_state empty; `clear_archive()` called for any archived UUID matching current entities; `logger.info("retention_node_reactivated")` logged
- Instrumented `get_entity()`: added `uuid` to entity dicts; `record_access()` called for each found entity; exception isolated
- 22 new tests (11 + 6 + 5), all passing; 257 total tests pass with zero regressions

## Task Commits

Each task was committed atomically via TDD red-green:

1. **Task 1 RED: list_stale, archive_nodes, archive filtering tests** - `fe68274` (test)
2. **Task 1 GREEN: implement list_stale, archive_nodes, archive filtering** - `af09e5c` (feat)
3. **Task 2 RED: record_access and get_entity instrumentation tests** - `a712c18` (test)
4. **Task 2 GREEN: implement record_access and get_entity instrumentation** - `64ff63d` (feat)
5. **Task 3 RED: add() reactivation tests** - `75c6b7c` (test)
6. **Task 3 GREEN: implement add() reactivation hook** - `017d4af` (feat)

_TDD tasks each have two commits (test RED then feat GREEN)._

## Method Signatures Added to GraphService

```python
async def list_stale(
    self,
    scope: GraphScope,
    project_root: Optional[Path],
) -> list[dict]:
    """Returns list of {uuid, name, age_days, score} sorted ascending by score."""

async def archive_nodes(
    self,
    uuids: list[str],
    scope: GraphScope,
    project_root: Optional[Path],
) -> int:
    """Archives UUIDs in SQLite only. Returns count archived."""

async def record_access(
    self,
    uuid: str,
    scope: GraphScope,
    project_root: Optional[Path],
) -> None:
    """Records access event. Exception is swallowed with warning log."""
```

## list_entities() and search() Post-Filter Confirmation

Both methods now post-filter archived nodes at the end of their result assembly:

```python
try:
    from src.retention import get_retention_manager
    scope_key = self._get_group_id(scope, project_root)
    archived_uuids = get_retention_manager().get_archive_state_uuids(scope_key)
    result_list = [e for e in result_list if e.get("uuid") not in archived_uuids]
except Exception:
    logger.warning("retention_filter_failed", method="list_entities")
```

One batch call per method invocation. Graceful fallback returns unfiltered list if retention DB unavailable.

## add() Reactivation Hook Confirmation

```python
try:
    from src.retention import get_retention_manager
    scope_key = self._get_group_id(scope, project_root)
    retention = get_retention_manager()
    archived_uuids = retention.get_archive_state_uuids(scope_key)
    if archived_uuids:  # fast path: skip entity query when archive empty
        graphiti_instance = await self._get_graphiti(scope, project_root)
        current_entities = await EntityNode.get_by_group_ids(
            graphiti_instance._driver, group_ids=[group_id]
        )
        for entity in current_entities:
            if entity.uuid in archived_uuids:
                retention.clear_archive(uuid=entity.uuid, scope=scope_key)
                logger.info("retention_node_reactivated", uuid=entity.uuid, scope=scope_key)
except Exception:
    logger.warning("retention_reactivation_check_failed", method="add")
```

## Files Created/Modified

- `src/graph/service.py` — Added list_stale(), archive_nodes(), record_access(); extended list_entities(), search() with archive post-filter; extended get_entity() with record_access instrumentation; instrumented add() with reactivation block; added uuid field to list_entities, get_entity, and search result dicts
- `tests/test_graph_service_retention.py` — 11 tests: list_stale (5), archive_nodes (3), list_entities filter (2), search filter (1)
- `tests/test_record_access.py` — 6 tests: record_access (3), get_entity instrumentation (3)
- `tests/test_reactivation.py` — 5 tests: fast path (2), match (2), exception isolation (1)

## Decisions Made

- Lazy imports inside each method body (`from src.retention import get_retention_manager`) — avoids circular import; module-level import creates a src.graph.service → src.retention circular dependency risk
- `uuid` field added to `list_entities()` and `get_entity()` result dicts — was previously missing; required for archive filter to function via `e.get("uuid")`
- search() result dicts extended with `uuid`, `source_node_uuid`, `target_node_uuid` fields — needed for edge-level archive filtering since graphiti search returns edge-like objects
- Reactivation fast path: when `get_archive_state_uuids()` returns empty set, `EntityNode.get_by_group_ids()` is skipped entirely — avoids a Kuzu query on the vast majority of `add()` calls

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added uuid field to list_entities() result dicts**
- **Found during:** Task 1 (implementing list_entities archive post-filter)
- **Issue:** Plan specified `e.get("uuid")` for archive filtering, but the existing list_entities() result dicts did not include a `uuid` field — the uuid was available in `entity.uuid` but not surfaced in the output dict
- **Fix:** Added `"uuid": entity.uuid` to the result dict in list_entities()
- **Files modified:** src/graph/service.py
- **Committed in:** af09e5c (Task 1 GREEN commit)

**2. [Rule 2 - Missing Critical] Added uuid field to get_entity() result dicts**
- **Found during:** Task 2 (implementing get_entity access recording instrumentation)
- **Issue:** The `ed.get("uuid")` check in the record_access instrumentation block returned None because entity_dict in get_entity() also lacked a uuid field
- **Fix:** Added `"uuid": record["uuid"]` to the entity_dict in get_entity()
- **Files modified:** src/graph/service.py
- **Committed in:** 64ff63d (Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (both Rule 2 — missing critical fields needed for retention filters to function)
**Impact on plan:** Both fixes necessary for correctness — without uuid in result dicts, the archive filter silently passes everything through.

## Issues Encountered

None — all plan steps executed as specified. The two deviations were pre-existing gaps in the result dict schema, not new problems.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- GraphService retention API is fully operational: list_stale, archive_nodes, record_access, get_entity access instrumentation, list_entities/search post-filtering, and add() reactivation all working with 22 passing tests
- Phase 09-03 (CLI retention commands) can import list_stale and archive_nodes directly from GraphService
- Phase 09-04 (APScheduler TTL sweep) can call archive_nodes for batch archiving
- No blockers for 09-03

---
*Phase: 09-smart-retention*
*Completed: 2026-03-05*

## Self-Check: PASSED

All 5 files verified present. All 6 task commits (fe68274, af09e5c, a712c18, 64ff63d, 75c6b7c, 017d4af) verified in git log.
