---
phase: 09-smart-retention
plan: "01"
subsystem: retention
tags: [sqlite, structlog, retention, staleness-scoring, singleton]

# Dependency graph
requires: []
provides:
  - RetentionManager class with SQLite sidecar at ~/.graphiti/retention.db
  - get_retention_manager() / reset_retention_manager() singleton helpers
  - record_access(), pin_node(), unpin_node(), archive_node(), clear_archive() CRUD
  - is_pinned(), is_archived(), get_access_record() accessors
  - get_pin_state_uuids(), get_archive_state_uuids() bulk set reads
  - compute_score() static method (staleness scoring 0.0-1.0)
  - LLMConfig.retention_days field (default 90, minimum 30 enforced)
affects:
  - 09-02  # TTL sweep / APScheduler plan will use RetentionManager directly
  - 09-03  # CLI retention commands will call record_access, list_stale_uuids
  - 09-04  # any plan consuming retention config from LLMConfig

# Tech tracking
tech-stack:
  added: []
  patterns:
    - SQLite sidecar (stdlib sqlite3 only, WAL mode, row_factory=sqlite3.Row)
    - Module-level singleton with reset helper for test isolation
    - TDD red-green for every new module

key-files:
  created:
    - src/retention/__init__.py
    - src/retention/manager.py
    - tests/test_retention_manager.py
    - tests/test_retention_config.py
  modified:
    - src/llm/config.py

key-decisions:
  - "stdlib sqlite3 only — no aiosqlite, no APScheduler in this plan (keeps module dependency-free)"
  - "WAL mode set on every _get_conn() call — safe for multi-thread access from later queue worker"
  - "compute_score() is a static method — callable without a live DB connection (useful in tests and CLI display)"
  - "retention_days minimum 30 enforced in load_config(), not in dataclass — keeps frozen dataclass simple"

patterns-established:
  - "Retention singleton: get_retention_manager() / reset_retention_manager() pattern — all Phase 9 plans follow this"
  - "Timezone normalization: naive datetimes replaced with tzinfo=timezone.utc before arithmetic"
  - "INSERT OR IGNORE for idempotent pin/archive operations"

requirements-completed: [RETN-03, RETN-06]

# Metrics
duration: 3min
completed: "2026-03-05"
---

# Phase 9 Plan 01: Retention Infrastructure Foundation Summary

**SQLite sidecar RetentionManager with three-table schema, WAL mode, full CRUD, staleness scoring, and LLMConfig.retention_days field (min 30, default 90)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-05T21:22:12Z
- **Completed:** 2026-03-05T21:25:04Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created `src/retention/manager.py` (258 lines) with three-table SQLite schema (access_log, pin_state, archive_state), WAL mode, all CRUD methods, staleness compute_score() static method, and singleton helpers
- Created `src/retention/__init__.py` exporting RetentionManager, get_retention_manager, reset_retention_manager
- Extended `src/llm/config.py` with `retention_days: int = 90` field and load_config() extraction with below-30 enforcement + structlog warning
- 38 new tests pass (29 retention manager + 9 retention config); 235 total tests pass with zero regressions

## Task Commits

Each task was committed atomically via TDD red-green:

1. **Task 1 RED: add failing tests for RetentionManager** - `46c7962` (test)
2. **Task 1 GREEN: implement RetentionManager with SQLite sidecar** - `1f93de3` (feat)
3. **Task 2 RED: add failing tests for LLMConfig retention_days** - `257933a` (test)
4. **Task 2 GREEN: extend LLMConfig with retention_days field** - `e5ea49f` (feat)

_TDD tasks each have two commits (test RED then feat GREEN)._

## Files Created/Modified

- `src/retention/manager.py` — RetentionManager class with schema init, CRUD, compute_score static method; 258 lines; stdlib sqlite3 only
- `src/retention/__init__.py` — Package init exporting RetentionManager, get_retention_manager, reset_retention_manager
- `src/llm/config.py` — Added retention_days field and load_config() [retention] extraction with minimum enforcement
- `tests/test_retention_manager.py` — 29 tests covering singleton, schema, WAL, all CRUD, compute_score edge cases
- `tests/test_retention_config.py` — 9 tests covering default, explicit, boundary, below-minimum, no-file cases

## RetentionManager Public Method Signatures

```python
class RetentionManager:
    def __init__(self, db_path: Path) -> None: ...

    # Access logging
    def record_access(self, uuid: str, scope: str) -> None: ...
    def get_access_record(self, uuid: str, scope: str) -> dict: ...
        # returns {"last_accessed_at": datetime | None, "access_count": int}

    # Pin state
    def pin_node(self, uuid: str, scope: str) -> None: ...
    def unpin_node(self, uuid: str, scope: str) -> None: ...
    def is_pinned(self, uuid: str, scope: str) -> bool: ...
    def get_pin_state_uuids(self, scope: str) -> set[str]: ...

    # Archive state
    def archive_node(self, uuid: str, scope: str) -> None: ...
    def clear_archive(self, uuid: str, scope: str) -> None: ...  # no-op if not archived
    def is_archived(self, uuid: str, scope: str) -> bool: ...
    def get_archive_state_uuids(self, scope: str) -> set[str]: ...

    # Staleness scoring
    @staticmethod
    def compute_score(
        created_at: datetime,
        last_accessed_at: datetime | None,
        access_count: int,
        retention_days: int,
    ) -> float: ...  # returns 0.0-1.0, rounded to 3 decimals; lower = more stale

# Singleton helpers
def get_retention_manager() -> RetentionManager: ...
def reset_retention_manager() -> None: ...
```

## LLMConfig.retention_days Field

```python
# In LLMConfig frozen dataclass:
retention_days: int = 90  # Days before a node is considered stale (min 30)

# In load_config():
retention = config_data.get("retention", {})
raw_days = retention.get("retention_days", 90)
if raw_days < 30:
    # structlog warning logged, falls back to 90
    raw_days = 90
# passed as retention_days=raw_days to LLMConfig(...)
```

## Decisions Made

- stdlib sqlite3 only — no additional dependencies added to the project
- WAL mode on every connection rather than once at init — ensures correct mode even if DB is accessed concurrently later
- `compute_score()` as static method makes it testable and usable without a live DB connection (e.g., CLI display)
- Minimum 30-day enforcement in `load_config()` rather than in the dataclass validator — keeps frozen dataclass uncomplicated

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. The `~/.graphiti/` directory and `retention.db` file are created automatically on first use.

## Next Phase Readiness

- RetentionManager is fully operational — all Phase 9 plans that build on this foundation can import from `src.retention`
- `LLMConfig.retention_days` available for TTL sweep plans
- Singleton pattern established: `get_retention_manager()` / `reset_retention_manager()` for test isolation
- No blockers for 09-02 (TTL sweep / APScheduler)

---
*Phase: 09-smart-retention*
*Completed: 2026-03-05*

## Self-Check: PASSED

All 6 files verified present. All 4 commits (46c7962, 1f93de3, 257933a, e5ea49f) verified in git log.
