---
phase: 29-cli-commands
plan: 02
subsystem: cli
tags: [typer, sqlite, fts5, backlinks, config, toml, cli, python]

# Dependency graph
requires:
  - phase: 29-cli-commands
    plan: 01
    provides: search_cmd.py stub and config_cmd.py stub registered in src/cli/__init__.py
  - phase: 26-config
    provides: Config, load_config() in src/config.py
  - phase: 27-llm-provider
    provides: make_llm_client() for semantic search embeddings
provides:
  - src/cli/commands/search_cmd.py — full FTS5 keyword search, semantic search, backlink traversal
  - src/cli/commands/config_cmd.py — show/get/set subcommands against ~/.recall/config.toml
  - tests/cli/test_search_cmd.py — 5 TDD tests for search behavior
  - tests/cli/test_config_cmd.py — 5 TDD tests for config behavior
affects: [30-mcp-server, 31-ui-server, 32-plugin-install]

# Tech tracking
tech-stack:
  added:
    - tomli-w>=1.0.0 (TOML write support; tomllib stdlib read-only)
  patterns:
    - "FTS5 search via entities_fts virtual table: SELECT ... WHERE entities_fts MATCH ?"
    - "Semantic search: client.embed([query])[0] -> cosine similarity against stored embeddings blobs"
    - "Backlinks traversal: SELECT ... FROM backlinks WHERE from_id = ? (one-hop)"
    - "Config traversal: key.split('.') -> recurse nested dict; tomli_w.dumps for write-back"
    - "Typer sub-app with context_settings allow_interspersed_args=True for positional arg + options"

key-files:
  created:
    - src/cli/commands/search_cmd.py
    - src/cli/commands/config_cmd.py
    - tests/cli/__init__.py
    - tests/cli/test_search_cmd.py
    - tests/cli/test_config_cmd.py
  modified:
    - pyproject.toml (added tomli-w dependency)

key-decisions:
  - "Implement search directly against SQLite FTS5/backlinks — plan's service.fts_search/service.semantic_search don't exist in v3.0 layout; DatabaseManager has no search layer"
  - "context_settings allow_interspersed_args=True required on Typer group app — without it 'recall search JWT --semantic' fails because Typer routes --semantic as a subcommand name"
  - "Use tomllib (stdlib) for TOML read + tomli-w for TOML write — plan specified 'toml' library which is not installed; tomllib read-only since Python 3.11"
  - "FTS5 join query via rowid: entities_fts.rowid = entities.rowid — required because entities_fts is a content= virtual table"

patterns-established:
  - "_get_db_path(): resolves db path from config relative to git root — same pattern as DatabaseManager.get_db_path()"
  - "_fts_search/_semantic_search/_get_related: pure functions taking sqlite3.Connection — testable without DB manager"
  - "_run_search(): extracted core logic callable from callback — avoids duplication"
  - "Module-level CONFIG_PATH and load_config import for patchability in tests"

requirements-completed: [CLI-02, CLI-03]

# Metrics
duration: 30min
completed: 2026-04-20
---

# Phase 29 Plan 02: Search and Config CLI Commands Summary

**FTS5 keyword search + semantic vector search with backlink traversal, and full config show/get/set — 10 TDD tests green**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-04-20T06:03:25Z
- **Completed:** 2026-04-20T06:36:00Z
- **Tasks:** 2
- **Files modified:** 5 created, 1 modified

## Accomplishments
- Implemented `recall search <query>` with FTS5 keyword search against SQLite `entities_fts` virtual table
- Implemented `recall search <query> --semantic` with vector cosine similarity against `embeddings` table; embeddings guard exits with clear error message when not configured
- Implemented `recall search <query> --related` appending one-hop backlinked entities under each result
- Implemented `recall config show` / `recall config get <key>` / `recall config set <key> <value>` for full config inspection and mutation
- 10 TDD tests (5 per command) all passing

## Task Commits

1. **Task 1: search_cmd.py with --semantic and --related flags** - `4f5f1db` (feat)
2. **Task 2: config_cmd.py with show, get, set subcommands** - `b146f2b` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `src/cli/commands/search_cmd.py` — FTS5/semantic/backlink search (replaces stub)
- `src/cli/commands/config_cmd.py` — show/get/set config subcommands (replaces stub)
- `tests/cli/__init__.py` — new tests package
- `tests/cli/test_search_cmd.py` — 5 TDD tests for search behavior
- `tests/cli/test_config_cmd.py` — 5 TDD tests for config behavior
- `pyproject.toml` — added tomli-w dependency

## Decisions Made
- Implemented search directly against SQLite FTS5 tables (plan referenced `service.fts_search`/`service.semantic_search` which do not exist in the v3.0 codebase — the DatabaseManager has no search methods)
- Used `tomllib` (stdlib, read-only) + `tomli-w` (write) instead of `toml` library which is not installed
- Added `context_settings={"allow_interspersed_args": True}` to search Typer app — required for `recall search JWT --semantic` argument order to work (Typer group mode otherwise treats `--semantic` as a subcommand name)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] service.fts_search/semantic_search/get_related do not exist**
- **Found during:** Task 1 (search_cmd.py implementation)
- **Issue:** Plan specified calling `service.fts_search(query)`, `service.semantic_search(query)`, `service.get_related(entity_id)` from a `GraphService` object; v3.0 layout has no GraphService and DatabaseManager has no search methods
- **Fix:** Implemented `_fts_search`, `_semantic_search`, `_get_related` as direct SQLite functions using the v3.0 schema (entities_fts virtual table, embeddings table, backlinks table)
- **Files modified:** src/cli/commands/search_cmd.py
- **Verification:** 5 tests pass including FTS, semantic (mocked), no-results, and backlinks
- **Committed in:** 4f5f1db

**2. [Rule 3 - Blocking] Typer interspersed args needed for natural CLI argument order**
- **Found during:** Task 1 (testing `recall search JWT --semantic`)
- **Issue:** Typer group app with `invoke_without_command=True` and positional arg: `JWT --semantic` fails because Typer routes `--semantic` as a subcommand after the positional arg
- **Fix:** Added `context_settings={"allow_interspersed_args": True}` to the Typer app constructor
- **Files modified:** src/cli/commands/search_cmd.py
- **Verification:** `runner.invoke(app, ["JWT", "--semantic"])` exits with code 1 (embeddings error) not code 2 (parse error)
- **Committed in:** 4f5f1db

**3. [Rule 3 - Blocking] toml library not installed; plan specified toml.loads/toml.dumps**
- **Found during:** Task 2 (config_cmd.py implementation)
- **Issue:** Plan code specified `import toml` with `toml.loads`/`toml.dumps`; `toml` package not installed
- **Fix:** Used `tomllib` (Python 3.11+ stdlib) for reading, installed and used `tomli-w` for writing; added tomli-w to pyproject.toml dependencies
- **Files modified:** src/cli/commands/config_cmd.py, pyproject.toml
- **Verification:** 5 tests pass including set-writes-value and set-creates-nested-key
- **Committed in:** b146f2b

---

**Total deviations:** 3 auto-fixed (1 missing method interface, 2 blocking issues)
**Impact on plan:** All auto-fixes required for correctness. No scope creep — the service interface mismatch was adapted to the actual v3.0 SQLite-direct architecture.

## Issues Encountered
None beyond the auto-fixed deviations above.

## Known Stubs
None — both commands are fully wired to real data sources (SQLite DB and ~/.recall/config.toml).

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- `recall search <query>` fully functional against indexed knowledge graphs
- `recall search --semantic` requires `[embeddings]` section in config and indexed embeddings table
- `recall config show/get/set` fully functional
- CLI surface complete: all 6 commands (init, sync, search, health, config, ui) implemented
- Phase 30 (MCP server) can proceed — search logic is in pure functions callable from MCP tools

## Self-Check

### Files exist:
- src/cli/commands/search_cmd.py: FOUND
- src/cli/commands/config_cmd.py: FOUND
- tests/cli/__init__.py: FOUND
- tests/cli/test_search_cmd.py: FOUND
- tests/cli/test_config_cmd.py: FOUND

### Commits exist:
- 4f5f1db: FOUND (feat(29-02): implement search_cmd.py with --semantic and --related flags)
- b146f2b: FOUND (feat(29-02): implement config_cmd.py with show, get, set subcommands)

## Self-Check: PASSED

---
*Phase: 29-cli-commands*
*Completed: 2026-04-20*
