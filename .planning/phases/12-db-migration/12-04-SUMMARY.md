---
phase: 12-db-migration
plan: "04"
subsystem: database
tags: [backend-config, neo4j-opt-in, ladybugdb, health, docker-compose, config-init]

requires:
  - "12-02 (LadybugDriver vendored, GraphManager rewritten)"
  - "12-03 (service.py migrated to driver abstraction)"
provides:
  - "src/llm/config.py — LLMConfig.backend_type and LLMConfig.backend_uri fields + [backend] TOML parsing"
  - "src/storage/graph_manager.py — parse_bolt_uri(), _make_driver(), _clear_stale_v1_data(), first v2.0 run detection"
  - "src/cli/commands/health.py — _check_backend() function, Backend row in health output"
  - "src/cli/commands/config.py — init_command generating llm.toml with commented [backend] block"
  - "docker-compose.neo4j.yml — Neo4j 5.24-community opt-in Docker Compose file in project root"
affects:
  - "DB-01 requirement: complete (LadybugDriver is default, wired through _make_driver)"
  - "DB-02 requirement: complete (Neo4j opt-in path: set [backend] type=neo4j in llm.toml)"
  - "Phase 13 (Multi-Provider LLM): backend_type/backend_uri pattern established for provider config"

tech-stack:
  added:
    - "neo4j Python driver (graphiti-core[neo4j] dep already present from Plan 02)"
  patterns:
    - "config_app sub-typer pattern: allows graphiti config (view) and graphiti config init (generate) from same sub-app"
    - "fail-fast reachability check: asyncio.run(_check_neo4j_reachable()) in _make_driver() before creating driver"
    - "schema version stamp (~/.graphiti/version.json): detects first v2.0 run for stale data clearing"

key-files:
  created:
    - "docker-compose.neo4j.yml — Neo4j 5.24-community, APOC plugin, volumes, healthcheck"
  modified:
    - "src/llm/config.py — backend_type (default 'ladybug') and backend_uri (default None) on LLMConfig"
    - "src/storage/graph_manager.py — parse_bolt_uri(), _check_neo4j_reachable(), _make_driver(), _clear_stale_v1_data(), _is_first_v2_run(), _mark_v2_initialized()"
    - "src/cli/commands/health.py — _check_backend() helper, Backend row appended before Quota"
    - "src/cli/commands/config.py — init_command + config_app sub-typer with callback for default view behavior"
    - "src/cli/__init__.py — config registered as sub-app (config_app), init subcommand wired"
    - "tests/test_backend_config.py — skip decorators removed from test_bolt_uri_parsed_correctly"

key-decisions:
  - "config sub-app pattern: converted config from simple command to Typer sub-app with callback so both 'graphiti config' (view) and 'graphiti config init' (generate) work"
  - "fail-fast with sys.exit(1): Neo4j configured but unreachable → any graphiti command exits immediately with named URI message"
  - "schema version stamp at ~/.graphiti/version.json: simplest first-run detection; cleared retention.db and queue on v2.0 first run"
  - "test_neo4j_unreachable_raises_on_init left skipped: requires live Docker Neo4j; integration test infrastructure out of scope"

requirements-completed: [DB-01, DB-02]

duration: 7min
completed: "2026-03-17"
---

# Phase 12 Plan 04: Backend Config, Neo4j Opt-in, Health Row, Docker Compose Summary

**BackendConfig fields (backend_type/backend_uri) added to LLMConfig; _make_driver() routes to LadybugDriver or Neo4jDriver; fail-fast Neo4j check; Backend row in health output; docker-compose.neo4j.yml created; graphiti config init generates llm.toml with commented [backend] block**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-17T16:46:24Z
- **Completed:** 2026-03-17T16:53:10Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `backend_type` (default `"ladybug"`) and `backend_uri` (default `None`) to `LLMConfig` dataclass
- Parsing of `[backend]` section from `llm.toml` in `load_config()` with validation + fallback
- `parse_bolt_uri()` extracts `(clean_uri, user, password)` from bolt://user:pass@host:port URI
- `_check_neo4j_reachable()` async helper pings bolt endpoint for fail-fast check
- `_make_driver()` in `GraphManager` routes to `LadybugDriver` (default) or `Neo4jDriver` (neo4j type)
- Fail-fast: if Neo4j configured but unreachable, prints named URI message and `sys.exit(1)`
- First v2.0 run detection via `~/.graphiti/version.json` schema version stamp
- `_clear_stale_v1_data()` removes `retention.db` and `queue/` on first v2.0 run
- `_check_backend()` health check helper with ladybug/neo4j status rows
- Backend row added to `graphiti health` output (before Quota row)
- `docker-compose.neo4j.yml` with Neo4j 5.24-community, APOC plugin, memory settings, named volumes
- `init_command` generates `~/.graphiti/llm.toml` with commented `[backend]` block hint
- `config` converted to Typer sub-app so `graphiti config` (view) and `graphiti config init` both work
- Unskipped `test_bolt_uri_parsed_correctly` — 3/4 tests in test_backend_config.py pass (1 skipped: Docker-dependent)

## Task Commits

1. **Task 1: BackendConfig fields in LLMConfig** - `eb949b0` (feat)
2. **Task 2: _make_driver, health Backend row, config init, docker-compose** - `a55a73e` (feat)

## Files Created/Modified

- `src/llm/config.py` — `backend_type` and `backend_uri` fields; `[backend]` TOML parsing; validation with fallback
- `src/storage/graph_manager.py` — `parse_bolt_uri()`, `_check_neo4j_reachable()`, `_make_driver()`, `_clear_stale_v1_data()`, `_is_first_v2_run()`, `_mark_v2_initialized()`; updated `_get_global_driver()` and `_get_project_driver()` to call `_make_driver()`
- `src/cli/commands/health.py` — `_check_backend()` function; `checks.append(_check_backend())` before quota
- `src/cli/commands/config.py` — `init_command`; `config_app` sub-typer with `invoke_without_command=True` callback
- `src/cli/__init__.py` — `config` command converted to sub-app; `init` subcommand registered
- `docker-compose.neo4j.yml` — new file in project root
- `tests/test_backend_config.py` — skip removed from `test_bolt_uri_parsed_correctly`

## Verification Results

```
$ python3 -c "from src.llm.config import load_config; c = load_config(); print(c.backend_type, c.backend_uri)"
ladybug None

$ graphiti health | grep Backend
│ Backend            │ ✓      │ ladybug (embedded)

$ graphiti config init --path /tmp/test_gk.toml --force && grep '# \[backend\]' /tmp/test_gk.toml
✓ Created /tmp/test_gk.toml
# [backend]

$ pytest tests/test_backend_config.py -v
3 passed, 1 skipped in 0.58s

$ pytest tests/ -x -q
298 passed, 3 skipped in 7.46s
```

## Decisions Made

- **config sub-app pattern**: Typer doesn't support a simple command and a sub-app with the same name. Solution: convert `config` to a `typer.Typer` sub-app with `invoke_without_command=True` and a callback that runs the view/set logic when no subcommand is given. This preserves backward compatibility for `graphiti config` while enabling `graphiti config init`.
- **test_neo4j_unreachable_raises_on_init stays skipped**: The test requires a live Docker container (or a patched asyncio.run). Adding mock-based testing is out of scope for this plan; integration test infrastructure is Phase 15 concern.
- **First-run detection via schema version stamp**: Simplest reliable detection — `~/.graphiti/version.json` with `{"schema_version": "2.0"}`. Absent file = first run; wrong version = upgrade run. Clears `retention.db` and `queue/` to avoid UUID mismatch with v1.1 KuzuDB entities.

## Deviations from Plan

### Auto-fixed Issues

None - plan executed exactly as written, with one minor implementation variation:

**[Implementation decision] config_app sub-app approach instead of separate config-init command**

- **Found during:** Task 2, registering init_command
- **Issue:** Plan said "register init_command in the Typer app" but adding both `app.command(name="config")` (simple) and `app.add_typer(config_app, name="config")` (sub-app) causes the sub-app to win, breaking `graphiti config` view mode.
- **Fix:** Added `@config_app.callback(invoke_without_command=True)` that calls `config_command()` when no subcommand is given. This preserves both `graphiti config` (view) and `graphiti config init` (generate) behaviors under a single sub-app registration.
- **Files modified:** `src/cli/commands/config.py`, `src/cli/__init__.py`
- **Result:** Both commands work correctly; full test suite passes.

---

**Total deviations:** 1 implementation-level fix (not a bug; plan underspecified registration method)

## Issues Encountered

None.

## User Setup Required

None for LadybugDB default. To use Neo4j opt-in:
1. Add to `~/.graphiti/llm.toml`:
   ```toml
   [backend]
   type = "neo4j"
   uri  = "bolt://neo4j:changeme@localhost:7687"
   ```
2. `docker compose -f docker-compose.neo4j.yml up -d`

## Next Phase Readiness

- **Phase 12 complete**: All 4 plans done. LadybugDB default + Neo4j opt-in wired. Zero Kuzu workarounds remain. Full test suite passes.
- **Phase 13 (Multi-Provider LLM)**: Unblocked. `backend_type/backend_uri` pattern in `LLMConfig` establishes the config extension model for adding `[provider]` section in Phase 13.
- **Phase 15 (Local Memory)**: Unblocked. Git post-commit hook removal decision locked in CONTEXT.md — Phase 15 removes the hook installer call.

---
*Phase: 12-db-migration*
*Completed: 2026-03-17*

## Self-Check: PASSED

- FOUND: .planning/phases/12-db-migration/12-04-SUMMARY.md
- FOUND: docker-compose.neo4j.yml
- FOUND: commit eb949b0 (Task 1: BackendConfig fields)
- FOUND: commit a55a73e (Task 2: _make_driver, health row, config init, docker-compose)
- VERIFIED: 298 passed, 3 skipped in full test suite
- VERIFIED: graphiti config shows config table
- VERIFIED: graphiti config init generates llm.toml with commented [backend] block
- VERIFIED: graphiti health includes Backend row with "ladybug (embedded)"
