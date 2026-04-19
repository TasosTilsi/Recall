---
phase: 28-git-extractor-indexer
plan: "03"
subsystem: indexer
tags: [indexer, sqlite, incremental-sync, git-walker, tdd]
dependency_graph:
  requires: [28-01, 28-02, 26-db-schema]
  provides: [run_init, run_sync, incremental-sha-filtering]
  affects: [src/indexer/indexer.py, src/indexer/__init__.py]
tech_stack:
  added: []
  patterns: [uuid5-idempotent-ids, incremental-sha-cursor, tdd-red-green]
key_files:
  created: [tests/indexer/__init__.py, tests/indexer/test_indexer.py]
  modified: [src/indexer/indexer.py, src/indexer/__init__.py]
decisions:
  - "FK constraint on entities.commit_sha requires a stub commits row before inserting entities — _insert_entities does INSERT OR IGNORE on commits first"
  - "getattr fallback for config.indexer.batch_size handles Config without IndexerConfig field"
  - "_commits_after_sha returns all commits when sha not found — safe fallback with structlog warning rather than raising"
metrics:
  duration_seconds: 11060
  completed_date: "2026-04-19"
  tasks_completed: 1
  files_changed: 4
---

# Phase 28 Plan 03: Incremental Sync Control Flow Summary

**One-liner:** `run_init`/`run_sync` entry points in `src/indexer/indexer.py` wiring git walker + extraction engine + SQLite with last_indexed_sha cursor for incremental syncs.

## What Was Built

Implemented the incremental sync control flow that ties together the three Phase 28 components:

- **`run_init(repo_root, config)`** — full rebuild: clears `last_indexed_sha` from metadata, walks all commits oldest-first, batches and extracts entities, writes HEAD sha as new cursor. Returns `{commits_processed, entities_inserted}`.
- **`run_sync(repo_root, config)`** — incremental: reads `last_indexed_sha` from metadata, filters `walk_commits()` output to only commits newer than that SHA, processes the delta. Delegates to `run_init` when no DB file exists.
- **`_commits_after_sha(commits, sha)`** — pure filter function, safe fallback returns all commits when sha not found (logs warning instead of raising).
- **`_insert_entities(conn, entities)`** — uuid5-keyed idempotent inserts, ensures FK parent commit row exists before inserting each entity.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for incremental sync | 7cdb0cf | tests/indexer/__init__.py, tests/indexer/test_indexer.py |
| 1 (GREEN) | Implement run_init, run_sync, helpers | b6e37fc | src/indexer/indexer.py, src/indexer/__init__.py |

## Verification

```
pytest tests/indexer/test_indexer.py -q → 5 passed
grep -q "last_indexed_sha" src/indexer/indexer.py → present
grep -q "0 commits to process" src/indexer/indexer.py → present
python -c "from src.indexer.indexer import run_init, run_sync; print('import ok')" → ok
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] FK constraint on entities.commit_sha**
- **Found during:** Task 1 GREEN (first test run)
- **Issue:** `entities` table has `commit_sha TEXT REFERENCES commits(sha)` with FK enforcement ON. Inserting entities with a commit_sha not yet in the commits table fails with `sqlite3.IntegrityError: FOREIGN KEY constraint failed`.
- **Fix:** `_insert_entities` now does `INSERT OR IGNORE INTO commits (sha, ...)` with stub values before each entity insert, ensuring the FK parent row exists. Uses a `seen_shas` set to avoid redundant inserts per batch call.
- **Files modified:** `src/indexer/indexer.py`
- **Commit:** b6e37fc

**2. [Rule 3 - Blocking] Worktree lacked v3.0 extractor/db modules**
- **Found during:** Task 1 RED (import error)
- **Issue:** The worktree branch (`worktree-agent-ada3a13f`) diverged from main before Phases 26-28 were merged; `src/extractor/`, `src/db/`, and `src/config.py` were absent.
- **Fix:** `git merge main` brought the worktree up to date with the v3.0 modules from Plans 26-01, 28-01, 28-02.
- **Commit:** cc7ad93 (merge commit)

**3. [Rule 1 - Bug] Legacy src/indexer/__init__.py imported GitIndexer**
- **Found during:** Task 1 RED
- **Issue:** `src/indexer/__init__.py` imported `GitIndexer` from the v2.0 codebase, causing ImportError when attempting to import from the new `indexer.py`.
- **Fix:** Rewrote `__init__.py` to export `run_init` and `run_sync`.
- **Files modified:** `src/indexer/__init__.py`
- **Commit:** b6e37fc

## Known Stubs

None — all data paths are wired. `run_init` and `run_sync` call real `walk_commits`, `extract_batch`, and `DatabaseManager` instances. The test suite patches these for isolation.

## Self-Check: PASSED

- `src/indexer/indexer.py` — exists and contains `run_init`, `run_sync`, `last_indexed_sha`, `0 commits to process`
- `tests/indexer/test_indexer.py` — exists with 5 tests
- Commits `7cdb0cf`, `b6e37fc` — both present in git log
