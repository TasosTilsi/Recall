---
phase: 12-db-migration
plan: "03"
subsystem: database
tags: [service, execute_query, kuzu-removal, driver-abstraction, readonly-methods]

requires:
  - phase: 12-db-migration/12-01
    provides: "real-ladybug installed; spike findings confirming execute_query contract"
  - phase: 12-db-migration/12-02
    provides: "LadybugDriver vendored with execute_query(); GraphManager.get_driver() returns driver with execute_query()"
provides:
  - "src/graph/service.py with 0 occurrences of import kuzu"
  - "list_edges() uses driver.execute_query() with dict-keyed row access"
  - "list_entities_readonly() uses driver.execute_query() with dict-keyed row access"
  - "get_entity_by_uuid() uses driver.execute_query() with dict-keyed row access"
  - "All 3 readonly methods are backend-agnostic — work with LadybugDriver or Neo4jDriver"
affects:
  - "12-db-migration (Plan 04 — pyproject.toml kuzu removal now safe; no more import kuzu in service.py)"
  - "Phase 14 Graph UI (UI reads via these 3 service.py methods; now backend-agnostic)"

tech-stack:
  added: []
  patterns:
    - "driver.execute_query() for all graph reads: replace kuzu.Database/Connection with GraphManager.get_driver(scope, project_root).execute_query()"
    - "Dict-keyed row access: row['uuid'] instead of positional row[0] — column names from Cypher RETURN aliases"

key-files:
  created: []
  modified:
    - "src/graph/service.py — list_edges, list_entities_readonly, get_entity_by_uuid rewritten (lines 1133–1279)"

key-decisions:
  - "Row access by column alias (row['uuid']) replaces positional (row[0]) — execute_query() returns list[dict] per column alias"
  - "read_only=True not needed with driver.execute_query() — LadybugDB/Neo4j handle read isolation at driver level"

patterns-established:
  - "execute_query pattern: results, _, _ = await driver.execute_query(query, param=value) then for row in results: row['alias']"

requirements-completed: [DB-01]

duration: 2min
completed: "2026-03-17"
---

# Phase 12 Plan 03: service.py Readonly Methods Migration Summary

**3 direct kuzu.Database/Connection methods in service.py rewritten to driver.execute_query() — service.py now has 0 import kuzu occurrences; same dict return shapes; all 11 retention tests pass**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-17T16:35:52Z
- **Completed:** 2026-03-17T16:37:36Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Rewrote `list_edges()`: replaced `kuzu.Database(read_only=True)` + `kuzu.Connection` + `while result.has_next()` with `driver.execute_query()` and dict-keyed row access
- Rewrote `list_entities_readonly()`: same pattern; retention filter post-processing unchanged
- Rewrote `get_entity_by_uuid()`: same pattern; result `if results: row = results[0]` replaces `if result.has_next(): row = result.get_next()`
- `service.py` now passes `grep -c "import kuzu" src/graph/service.py` = 0

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite list_edges, list_entities_readonly, get_entity_by_uuid** - `dfa9512` (feat)

**Plan metadata:** _(to be recorded in final commit)_

## Files Created/Modified

- `src/graph/service.py` — 3 methods rewritten at lines 1133–1279:
  - `list_edges()`: docstring updated, `import kuzu` removed, `kuzu.Database`/`kuzu.Connection` replaced with `driver.execute_query()`, positional row access replaced with dict access
  - `list_entities_readonly()`: same pattern
  - `get_entity_by_uuid()`: same pattern

## Decisions Made

- Row access changed from positional (`row[0]`, `row[1]`, ...) to dict-keyed (`row["uuid"]`, `row["name"]`, ...) — `execute_query()` returns `list[dict]` keyed by Cypher RETURN aliases; positional access was Kuzu-specific `get_next()` list behavior
- `read_only=True` flag dropped — not applicable to `execute_query()` abstraction; LadybugDB and Neo4j handle read isolation at the driver level

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Plan 04 (pyproject.toml kuzu removal):** Fully unblocked. `src/graph/service.py` has 0 `import kuzu` occurrences. The only remaining `import kuzu` in the codebase is in `src/storage/graph_manager.py` which Plan 02 already addresses (or Plan 04 finalizes).
- **Phase 14 (Graph UI):** The 3 UI-facing read methods are now backend-agnostic. Any driver returned by `GraphManager.get_driver()` will work.

---
*Phase: 12-db-migration*
*Completed: 2026-03-17*

## Self-Check: PASSED

- FOUND: .planning/phases/12-db-migration/12-03-SUMMARY.md
- FOUND: src/graph/service.py
- FOUND: commit dfa9512 (Task 1)
