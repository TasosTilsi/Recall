# Pitfalls Research

**Domain:** Python CLI knowledge graph tool — v2.0 DB backend migration (KuzuDB replacement)
**Researched:** 2026-03-09
**Confidence:** HIGH — all pitfalls verified against codebase inspection, graphiti-core 0.28.1 source, upstream GitHub issues, and current package state

---

## Critical Pitfalls

### Pitfall 1: Three Application-Layer Kuzu Calls Will Not Port Transparently

**What goes wrong:**
`src/graph/service.py` contains three methods that bypass graphiti-core entirely and call Kuzu's Python API directly:
- `list_edges_readonly()` (line 1143) — opens `kuzu.Database(path, read_only=True)` and executes `MATCH (a:Entity)-[:RELATES_TO]->(rel:RelatesToNode_)-[:RELATES_TO]->(b:Entity)` raw Cypher.
- `list_entities_readonly()` (line 1185) — same pattern, different query.
- `get_entity_by_uuid_readonly()` (line 1247) — same pattern for single-entity fetch.

These methods import `kuzu` directly, open their own database handle, and use Kuzu-specific result iteration (`result.has_next()`, `result.get_next()`). After migration:
- `kuzu.Database` and `kuzu.Connection` do not exist for Neo4j or FalkorDB.
- The `RelatesToNode_` intermediate node pattern is Kuzu-only. In Neo4j/FalkorDB, `RELATES_TO` is a direct relationship between Entity nodes — this query returns nothing.
- The result iteration API (`has_next()`, `get_next()`) is Kuzu-specific; Neo4j returns `Result` objects; FalkorDB returns its own record format.

**Why it happens:**
These methods were added as a performance bypass for the UI server — they avoid the overhead of initializing a full Graphiti instance just to read nodes for visualization. The bypass trades correctness guarantees for speed but creates hard Kuzu dependencies invisible to tests (tests mock `_get_graphiti()` and never exercise these paths with a real DB).

**How to avoid:**
Before choosing a replacement backend, audit every direct `import kuzu` call. These three methods must be rewritten to either:
(a) use graphiti-core's official query interface (`driver.execute_query()` or the operations interfaces), or
(b) abstract the read-only query into a `GraphDriver` method on the new driver.
Write integration tests that exercise `list_edges_readonly()` and `list_entities_readonly()` against a live database — these will fail immediately after migration if not fixed.

**Warning signs:**
- `grep -rn "import kuzu" src/` returns results outside `storage/graph_manager.py`.
- UI server visualization returns empty graph after backend switch.
- No test in `tests/` exercises `list_edges_readonly()` with a real database handle.

**Phase to address:** DB Migration Phase — cannot mark migration complete until all three methods are rewritten and integration-tested against the new backend.

---

### Pitfall 2: graphiti-core Has 50+ Kuzu-Specific Branches That Are Automatically Bypassed by Driver Swap — But Not All Are

**What goes wrong:**
graphiti-core 0.28.1 contains over 50 `if driver.provider == GraphProvider.KUZU:` branches across `search_utils.py`, `nodes.py`, `edges.py`, `edge_db_queries.py`, `node_db_queries.py`, `bulk_utils.py`, `graph_data_operations.py`, and `community_operations.py`. When you replace `KuzuDriver` with `Neo4jDriver` or `FalkorDriver`, graphiti-core automatically routes all these branches to the Neo4j/FalkorDB code paths — that part works correctly because `driver.provider` changes.

The critical exception: `src/storage/graph_manager.py` manually calls `get_fulltext_indices(GraphProvider.KUZU)` in `_create_fts_indices()`. This call is hardcoded to `GraphProvider.KUZU`, not to `driver.provider`. After migration, `_create_fts_indices()` will generate Kuzu FTS DDL and attempt to execute it against Neo4j or FalkorDB, which do not understand Kuzu's `CALL db.index.fulltext.createNodeIndex(...)` syntax. The error will surface as `DatabaseError` at startup, before any data is written.

**Why it happens:**
The `_create_fts_indices()` method was a workaround specific to `KuzuDriver.build_indices_and_constraints()` being a no-op. Neo4j and FalkorDB both implement `build_indices_and_constraints()` properly — the entire `_create_fts_indices()` method and its call sites become dead code after migration, but it fails before the driver can tell it to stop.

**How to avoid:**
The migration diff for `graph_manager.py` should be exactly:
1. Remove `import kuzu`, `from graphiti_core.driver.kuzu_driver import KuzuDriver, GraphProvider`, and `from graphiti_core.graph_queries import get_fulltext_indices`.
2. Delete `_create_fts_indices()` entirely.
3. Remove the two `self._create_fts_indices(self._global_driver.db)` call sites.
4. Remove the `self._global_driver._database = str(GLOBAL_DB_PATH)` workaround (Neo4j/FalkorDB set `_database` in their constructors).
5. Replace `KuzuDriver(db=str(GLOBAL_DB_PATH))` with the new driver constructor.

The `build_indices_and_constraints()` method on the new driver is called by `_get_graphiti()` via `await graphiti.build_indices_and_constraints()` — this already works correctly in `service.py`. No additional FTS creation code is needed.

**Warning signs:**
- Import errors at startup: `ImportError: No module named 'kuzu'` if kuzu is uninstalled before `graph_manager.py` is updated.
- `DatabaseError` with "CALL db.index.fulltext.createNodeIndex" in traceback — FTS DDL being sent to the wrong backend.
- `AttributeError: 'Neo4jDriver' object has no attribute 'db'` — the `_create_fts_indices(self._global_driver.db)` call treats the driver as a KuzuDriver.

**Phase to address:** DB Migration Phase — `graph_manager.py` must be the first file touched. Rewrite it completely before testing any other component.

---

### Pitfall 3: The "Rebuild From Git History" Migration Strategy Loses Pinned Entities, Retention Metadata, and Access History

**What goes wrong:**
The planned migration strategy is: delete old Kuzu files, run `graphiti index` to re-populate the graph from git history. This strategy recovers:
- Entities and facts extracted from git commits (anything in git history).

This strategy irrecoverably loses:
- **All manually added episodes** (`graphiti add --content "..."`) not associated with a git commit. These live only in the Kuzu database, not in any recoverable source.
- **All pinned entities** (`graphiti pin <uuid>`). Pin state is stored in `~/.graphiti/retention.db` (SQLite sidecar, unaffected by migration). However, the UUIDs in `retention.db` will not match new UUIDs after reindexing — graphiti generates UUIDs deterministically from content, but if the entity resolution produces different merge results on a fresh run (due to different LLM outputs), UUIDs diverge. Old pins become orphaned references.
- **All access history and staleness scores** in `retention.db`. The SQLite sidecar persists, but the UUIDs it references no longer exist.
- **Community clusters** computed by `graphiti compact`. These are expensive to recompute and not guaranteed to produce the same clustering on the same data (LLM-dependent).

**Why it happens:**
Graph data has two tiers:
1. Content derived from source material (git history) — recoverable by reindexing.
2. Metadata and manually-added content — not stored in any source, only in the Kuzu files being deleted.

The reindex strategy treats the graph as a cache of source material, but it is not: it accumulates knowledge that has no other home.

**How to avoid:**
Do not use the rebuild strategy as the default migration path. Instead, treat it as a fallback. The primary path should be data export/import:
1. Before deleting Kuzu files, export all entities and episodes to JSON using `graphiti list --format json` and `graphiti search --all`.
2. After installing the new backend, reimport using `graphiti add` for each exported episode.
3. If the export volume is too large for manual reimport, implement a one-shot migration script: open the old Kuzu database (still installable as `kuzu==0.11.3` even if deprecated), read all nodes/edges, write them to the new backend via graphiti-core's standard `add_episode()`.

For users who cannot preserve data, be explicit: document in release notes that v2.0 requires a data reset and list exactly what is lost.

**Warning signs:**
- Migration guide says "run `graphiti index`" without mentioning what is lost.
- `retention.db` still contains UUIDs after reindex — stale references will silently fail PIN checks.
- `graphiti list` after reindex returns fewer entities than before — unrecovered content.

**Phase to address:** DB Migration Phase — the migration documentation must be written before the code. Identify the data loss surface before shipping.

---

### Pitfall 4: Neo4j Requires Docker; "Docker Not Running" Is a Hard Failure With No Fallback

**What goes wrong:**
Unlike KuzuDB (embedded, zero startup dependency), Neo4j requires a running server process — typically via Docker. If `graphiti add "..."` is run and Docker is not running, or the Neo4j container is not started, the Neo4j Python driver throws `ServiceUnavailable: Failed to establish connection to ('127.0.0.1', 7687)` immediately. There is no retry, no fallback, and no clear error message from graphiti-core — the exception propagates through `run_graph_operation()` as a generic exception, and the CLI prints a cryptic traceback.

Specific failure modes:
- Docker daemon not running: `socket.error: [Errno 111] Connection refused` — driver instantiation fails.
- Container not started: same error, same UX.
- Container still initializing (race condition on Docker startup): `ServiceUnavailable` raised during `build_indices_and_constraints()`, before any data operation.
- Wrong password: `AuthError: The client is unauthorized` — confusable with connection failure.
- `Neo4jDriver.__init__()` schedules `build_indices_and_constraints()` as an `asyncio.loop.create_task()` — the connection error surfaces asynchronously, not at construction time, making it harder to catch at startup.

**Why it happens:**
The embedded model of KuzuDB set user expectations: the database just works. Neo4j is a client/server database designed for always-on server environments. Its Python driver was not designed for environments where the server may not be running at all.

**How to avoid:**
- Implement a `neo4j_health_check()` function that calls `driver.verify_connectivity()` with a 5-second timeout before any graph operation. Run this in `graphiti health` and surface a clear error: "Neo4j is not reachable at bolt://localhost:7687. Is Docker running? Run: docker compose up -d neo4j".
- Add a `docker-compose.yml` to the repository with a pre-configured Neo4j service. Users should never manually configure Neo4j.
- In `GraphManager._get_global_driver()`, catch `ServiceUnavailable` and raise a custom `BackendUnavailableError` with a user-facing message, not a raw traceback.
- The `Neo4jDriver` constructor schedules `build_indices_and_constraints()` async — test that this failure propagates correctly and does not get silently swallowed by the background task.

**Warning signs:**
- `graphiti add "test"` raises an unhandled exception with a bolt:// URI in the traceback.
- `graphiti health` passes but `graphiti add` fails — health check is not actually testing the connection.
- Docker container restarts and graphiti CLI starts getting `ServiceUnavailable` mid-session — no reconnect logic.

**Phase to address:** DB Migration Phase — the health check and fallback error handling must be implemented before any other feature that uses the new backend.

---

### Pitfall 5: FalkorDB (falkordblite Embedded) Is Not Yet Supported by graphiti-core 0.28.1

**What goes wrong:**
FalkorDB is an attractive replacement because `falkordblite` is embedded (like Kuzu), requiring no Docker. However, as of 2026-03-09, the `FalkorLiteDriver` that wraps falkordblite is not yet merged into graphiti-core — it exists as draft PR #1250 in the graphiti repo. The existing `FalkorDriver` in graphiti-core 0.28.1 requires a running FalkorDB server (Redis-based, client/server protocol), which defeats the embedded advantage.

If the team assumes falkordblite "just works" with the existing `FalkorDriver`, they will discover that:
- `FalkorDriver.__init__(host="localhost", port=6379)` connects via Redis protocol to a TCP socket — falkordblite uses Unix domain sockets internally and is not accessible via host/port.
- falkordblite requires Python 3.12+ and is unavailable on Windows entirely.
- falkordblite spawns a subprocess on import — incompatible with the MCP server's stdio process model (subprocess stdout may interfere).

**Why it happens:**
FalkorDB markets falkordblite as an embedded, zero-config option, which creates the impression that dropping it in as a Kuzu replacement is straightforward. The graphiti-core driver gap is not obvious until you try to wire it up.

**How to avoid:**
- Do not plan the migration around falkordblite unless PR #1250 has merged and been released in a stable graphiti-core version.
- If falkordblite is desired as the target backend, the migration must be sequenced as: (a) implement the LadybugDB or Neo4j migration first to remove Kuzu dependency, then (b) revisit falkordblite once the graphiti-core driver exists.
- Verify falkordblite's subprocess-spawning behavior does not conflict with MCP stdio transport before committing to this option.

**Warning signs:**
- `pip install graphiti-core[falkordb]` succeeds but importing `FalkorLiteDriver` raises `ImportError`.
- `FalkorDriver(host="localhost")` raises `ConnectionRefusedError` when falkordblite is the only FalkorDB running.
- MCP server stdio produces garbled output after falkordblite import (subprocess startup noise).

**Phase to address:** DB Migration Phase — verify the chosen backend has a working graphiti-core driver before writing any migration code. Run the graphiti-core example notebooks locally with the target driver.

---

### Pitfall 6: LadybugDB Is the Closest Drop-in but Is Version 0.11.x — Pre-Production Maturity

**What goes wrong:**
LadybugDB is a Kuzu fork positioned as a direct replacement: "the only change is to rename kuzu to the correct package name." In practice, the `ladybug` Python package wraps the same core database engine as Kuzu 0.11.3, so the graphiti-core `KuzuDriver` should work with it by swapping the import. However:
- LadybugDB version history is very short (first stable release early 2026). It has not been battle-tested at scale.
- graphiti-core 0.28.1 does not formally support LadybugDB — the Migrate kuzu → ladybug PR (#1296) is open but not yet merged as of research date.
- If LadybugDB diverges from the Kuzu 0.11.3 API (renamed classes, changed query syntax), the `KuzuDriver` in graphiti-core will silently fail or produce wrong results — not raise import errors.
- The migration strategy of `import ladybug as kuzu` (aliasing) will work for the driver module but will fail for any code that calls `kuzu.Database`, `kuzu.Connection`, or `kuzu.AsyncConnection` directly — which includes three methods in `service.py`.

**Why it happens:**
The "rename the import" story is compelling but incomplete. LadybugDB may expose an identical API for the happy path while having subtle differences in error handling, connection lifecycle, or transaction behavior that only surface under load or with specific queries.

**How to avoid:**
- Treat LadybugDB as a provisional target, not a final one. Run the full test suite against LadybugDB before committing.
- Check the graphiti-core issue #1296 — only proceed with LadybugDB as the backend if this PR has merged into graphiti-core and been released.
- Specifically test: FTS index creation, vector cosine similarity queries, `DETACH DELETE`, and the `RelatesToNode_` intermediate node pattern — the four areas where Kuzu required workarounds.
- Do not assume the three `service.py` Kuzu-direct methods will "just work" with LadybugDB even if the API matches — write explicit integration tests.

**Warning signs:**
- `import ladybug` succeeds but `ladybug.Database` raises `AttributeError`.
- FTS index creation raises a different error from LadybugDB than expected.
- graphiti-core PR #1296 is still open or reverted — upstream hasn't blessed the migration.

**Phase to address:** DB Migration Phase (pre-implementation) — verify PR #1296 status before writing any code. If not merged, use Neo4j as the primary target.

---

### Pitfall 7: `graphiti.kuzu` File Extension in paths.py Will Confuse Users and Tooling

**What goes wrong:**
`src/config/paths.py` sets `GLOBAL_DB_PATH = GLOBAL_DB_DIR / "graphiti.kuzu"` and `PROJECT_DB_NAME = "graphiti.kuzu"`. After migration:
- Existing user installations have `~/.graphiti/global/graphiti.kuzu` directories.
- New installations will have (e.g.) `~/.graphiti/global/graphiti.db` or `neo4j/`.
- Both the old and new paths may exist simultaneously on a user's machine, causing confusion about which is the active database.
- `graphiti health` may report the old Kuzu path as "not found" while simultaneously showing the new backend as healthy — masking the fact that all old data was abandoned.

**Why it happens:**
The `.kuzu` suffix was chosen to make the database type obvious. But it now becomes a migration artifact: the file extension outlasts the database it named.

**How to avoid:**
- Rename the database path to a backend-agnostic name at migration time: `graphiti.db` for embedded backends, or remove the path constant entirely for client/server backends (Neo4j has no local file path).
- Add migration detection: at startup, check if `~/.graphiti/global/graphiti.kuzu` exists but the new path does not — print a clear warning: "Found legacy KuzuDB data at ~/.graphiti/global/graphiti.kuzu. This data is not accessible with the current backend. Run `graphiti migrate` to export it or `graphiti reset` to start fresh."
- Update `.gitignore` patterns in newly initialized project repositories: the current pattern likely ignores `.graphiti/*.kuzu`.

**Warning signs:**
- `GLOBAL_DB_PATH` still ends in `.kuzu` in `paths.py` after migration.
- `os.path.exists(GLOBAL_DB_PATH)` returns True on old installs pointing to a Kuzu database the new driver cannot open.
- `.gitignore` in new projects excludes `.graphiti/graphiti.kuzu` but not `.graphiti/graphiti.db`.

**Phase to address:** DB Migration Phase — update `paths.py` as part of the driver swap. Add startup migration detection before writing any new data.

---

### Pitfall 8: Tests Mock KuzuDriver — They Will Pass After Migration But Provide No Coverage

**What goes wrong:**
The existing test suite mocks `_get_graphiti()` using `MagicMock()` and patches `GraphService._graph_manager`. Tests in `test_graph_service_retention.py` never touch a real database. `test_storage.py` imports `kuzu` directly and creates real Kuzu databases in temp directories. After migration:
- Tests that mock the driver will continue to pass regardless of whether the new backend works — they prove nothing about the migration.
- `test_storage.py` will fail immediately on `import kuzu` if the kuzu package is uninstalled as part of migration.
- There are zero integration tests that exercise the full path: CLI command → GraphService → Driver → actual database query → result assertion.

A common mistake is to declare migration complete because the mock-based test suite still passes. The graph does not actually work until tested against a live database.

**Why it happens:**
Mock-based testing was appropriate during initial development when a real Kuzu database was heavy to set up. But over time the mocks accumulated until they cover all database interaction, making the test suite provide no migration safety net.

**How to avoid:**
- Add a test fixture (`conftest.py`) that starts a real database instance for the chosen backend:
  - LadybugDB/KuzuDB: create a temp directory, initialize `KuzuDriver(db=tmpdir)` — already done in `test_storage.py`.
  - Neo4j: use `testcontainers-python` to start a Neo4j Docker container in the test session.
  - FalkorDB server: use `testcontainers-python` for FalkorDB.
- Write one integration test per critical operation: `add_episode()`, `search()`, `list_entities()`, `delete_entities()`. These must run against the real backend, not a mock.
- Tag these as `@pytest.mark.integration` and ensure CI runs them on every PR.
- Before declaring migration complete, the following must pass against a live backend: FTS search returns results, vector similarity search returns results, entity deletion cascades correctly.

**Warning signs:**
- `pytest tests/` passes with 100% success rate but `graphiti add "test"` crashes.
- No `conftest.py` fixture provides a database connection — all fixtures return `MagicMock()`.
- CI pipeline has no Docker service configured — Neo4j tests cannot run in CI.

**Phase to address:** DB Migration Phase — write integration tests first, before changing any application code. Red tests confirm what is broken; green tests confirm migration is done.

---

### Pitfall 9: CI Without the New Backend Service — Migration "Works" Locally But Breaks in CI

**What goes wrong:**
If Neo4j is chosen as the backend, CI must run a Neo4j container as a service alongside the test runner. GitHub Actions and similar CI platforms support this via `services:` blocks. A common mistake: the migration is developed locally with Docker running, tests pass, the PR is merged, and then CI starts failing on every subsequent push because the CI pipeline has no Neo4j service configured.

For embedded backends (LadybugDB, falkordblite), this is less of a concern — the database starts in-process. But falkordblite spawns a subprocess, which may fail in CI environments with restricted process namespaces.

**Why it happens:**
CI configuration is treated as a secondary concern and updated after the code is merged. Developers verify locally and assume CI will match.

**How to avoid:**
- Update CI configuration (`.github/workflows/`) as part of the migration PR, not after.
- For Neo4j: add the services block:
  ```yaml
  services:
    neo4j:
      image: neo4j:5.26
      env:
        NEO4J_AUTH: neo4j/test
      ports:
        - 7687:7687
      options: >-
        --health-cmd "cypher-shell -u neo4j -p test 'RETURN 1'"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
  ```
- For embedded backends: no service needed, but verify the CI runner has write access to the temp directory used by the database.
- Add a CI-specific environment variable `GRAPHITI_TEST_BACKEND=neo4j|ladybug` and use it in `conftest.py` to pick the right driver.

**Warning signs:**
- CI workflow YAML has no `services:` section after migration.
- Integration tests are marked `@pytest.mark.skip("requires Neo4j")` — they are excluded from CI, defeating their purpose.
- Local `pytest` passes, remote CI fails with `ConnectionRefusedError` on bolt://localhost:7687.

**Phase to address:** DB Migration Phase — update CI in the same commit as the driver swap. Do not merge a migration PR with a broken CI pipeline.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `kuzu.Database(path, read_only=True)` in `service.py` directly | Avoids full Graphiti initialization for read-heavy UI queries | Hard Kuzu dependency outside the driver layer; breaks on any backend swap | Never — move to driver interface methods |
| Aliasing `import ladybug as kuzu` | Zero code changes to import statements | Silent failures if LadybugDB API diverges; confusing for future readers | Never for production code; only as a temporary spike |
| Keeping `graphiti.kuzu` file extension after migration | No user migration needed | Confuses tooling, masks stale data, breaks `.gitignore` patterns | Never — rename at migration time |
| Skipping data export and using rebuild-from-git as migration | Fast migration | Irrecoverable loss of manually-added episodes, pins, and access history | Only if user explicitly consents to data loss |
| Mocking the driver in all tests after migration | Fast tests | Zero confidence in actual backend behavior | Never for critical paths like `add`, `search`, `delete` |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Neo4j FTS | Assuming Neo4j uses Lucene syntax like `name:"foo*"` — it does, but the query must be wrapped in `CALL db.index.fulltext.queryNodes(...)` not the Kuzu `QUERY_FTS_INDEX` form | Use `Neo4jSearchOperations` from graphiti-core; do not hand-write fulltext queries |
| Neo4j RELATES_TO schema | Querying `(Entity)-[:RELATES_TO]->(RelatesToNode_)-[:RELATES_TO]->(Entity)` — Neo4j stores `RELATES_TO` as a direct relationship, no intermediate node | The three `service.py` read-only methods must use `(n:Entity)-[e:RELATES_TO]->(m:Entity)` for Neo4j |
| FalkorDB build_indices_and_constraints | FalkorDB's implementation schedules index creation as a background asyncio task in `__init__()` — if the event loop is not running yet, the task is silently dropped | Call `await graphiti.build_indices_and_constraints()` explicitly, like the current Graphiti init flow does |
| Neo4j driver lazy connection | `Neo4jDriver.__init__()` schedules `build_indices_and_constraints()` as `loop.create_task()` — if called from sync context (e.g., during app startup before asyncio.run()), the task never executes | Ensure `Neo4jDriver` is always created inside an async context; use `await graphiti.build_indices_and_constraints()` explicitly |
| retention.db UUID references | SQLite sidecar stores entity UUIDs from the Kuzu database — after migration and reindex, new UUIDs will not match old pin/access records | Clear `retention.db` at migration time or implement a UUID remapping pass |
| `asyncio.run()` in `GraphManager` | `GraphManager.reset_project()` and `close_all()` call `asyncio.run(driver.close())` — this works for KuzuDriver (whose `close()` is a no-op) but Neo4jDriver's `close()` actually closes connections and raises if called from within an event loop | Replace with `asyncio.get_event_loop().run_until_complete()` or make callers async |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Neo4j connection pool exhausted by dual-scope GraphManager | Two KuzuDriver instances (global + project) are cheap — two Neo4j connection pools are not | Configure Neo4j driver with `max_connection_pool_size=5` per scope; or share a single driver with `with_database()` for scope switching | From first use — Neo4j default pool size is 100 connections |
| Full-graph load for UI visualization against Neo4j | Query returning all nodes/edges performs a full scan with no index on `group_id` | Add a range index on `group_id` — Neo4j's `build_indices_and_constraints()` already does this; verify it ran | At 100+ nodes |
| LadybugDB/Kuzu single-file access contention | LadybugDB (like Kuzu) allows only one writer at a time — if two CLI invocations open the database concurrently, the second blocks or errors | The existing `GraphManager` singleton pattern prevents this within a process; add a lockfile check for multi-process access | Two simultaneous `graphiti add` invocations |
| Neo4j container cold start | `graphiti add` fails if executed immediately after `docker compose up` — Neo4j takes 10-30 seconds to fully initialize | Implement a startup health-check retry loop (5 retries, 2s sleep) in `GraphManager` for Neo4j only | Every time Docker is restarted |
| falkordblite subprocess spawning in test | Each test that imports falkordblite spawns a subprocess, adding 1-3s overhead per test | Use a session-scoped fixture for falkordblite initialization; do not re-initialize per test | When test suite has 50+ tests |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing Neo4j credentials in `llm.toml` in plaintext | `llm.toml` may be committed to git or world-readable | Use environment variables `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`; check file permissions at startup |
| Neo4j default password `neo4j` in docker-compose.yml | Committed `docker-compose.yml` with hardcoded credentials exposes defaults | Use `NEO4J_AUTH: none` for local-only dev or environment variable substitution |
| falkordblite database file in project directory | Embedded database file in `.graphiti/graphiti.db` may be committed to project git | Ensure `.gitignore` patterns cover both `.graphiti/*.kuzu` and `.graphiti/*.db` |
| Multi-process access to embedded database | Two processes writing to LadybugDB/Kuzu simultaneously cause corruption | Add PID lockfile at `~/.graphiti/global/graphiti.lock`; error if lock is held |

---

## v2.0 Phase Regression Risk Assessment

Which phases have highest regression risk from a DB backend change:

| Phase | Risk | Why | Mitigation |
|-------|------|-----|------------|
| DB Migration | CRITICAL | This is the change itself | Integration tests against live DB before shipping |
| Graph UI Redesign | HIGH | UI server uses three Kuzu-direct read methods in `service.py` — these break immediately | Fix all three methods as part of DB migration, before UI redesign phase |
| LLM Provider (Multi-Provider) | LOW | LLM adapters are fully decoupled from the graph driver — `OllamaLLMClient` and `OllamaEmbedder` do not touch the DB | No DB-related regression expected |
| Local Memory | MEDIUM | Entity persistence depends on correct FTS and vector indexing — if the new backend's FTS is not wired correctly, entity resolution quality degrades silently | Validate FTS and vector search return expected results after migration before Local Memory work begins |

**Recommended phase ordering:** DB Migration must land before Graph UI Redesign (the UI reads break), and before Local Memory (depends on FTS quality). It can be sequenced before or after LLM Provider work with no coupling.

---

## "Looks Done But Isn't" Checklist

- [ ] **Driver swap:** `import kuzu` no longer appears in any file under `src/` — verify with `grep -rn "import kuzu" src/`.
- [ ] **Workarounds removed:** `_create_fts_indices()` deleted from `graph_manager.py` — verify method does not exist.
- [ ] **Workarounds removed:** `driver._database = str(db_path)` hack removed — new driver sets `_database` in its constructor.
- [ ] **Readonly methods:** `list_edges_readonly()`, `list_entities_readonly()`, `get_entity_by_uuid_readonly()` rewritten to use driver-agnostic API — verify UI visualization shows correct data.
- [ ] **File paths:** `GLOBAL_DB_PATH` no longer ends in `.kuzu` — verify `paths.py`.
- [ ] **Schema migration detected:** Startup warns if old `graphiti.kuzu` files exist alongside new database — verify warning appears on a machine with old data.
- [ ] **retention.db cleared or remapped:** Old UUID references do not cause silent pin failures — verify `graphiti pin` and `graphiti stale` still function correctly.
- [ ] **Integration tests:** At least one test in `tests/` opens a real database connection and performs `add_episode()` + `search()` — verify `grep -n "real_db\|live_backend\|testcontainers" tests/`.
- [ ] **CI configured:** `.github/workflows/` service block matches the chosen backend — verify CI passes on a fresh branch.
- [ ] **FTS working:** `graphiti search "test entity"` returns results for a known entity — verify after migration with a smoke test.
- [ ] **Vector search working:** `graphiti search --semantic "concept"` returns results — verify cosine similarity index is active.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Kuzu-direct calls in `service.py` return empty after migration | MEDIUM | Identify which of the three methods is failing; rewrite to use driver's `execute_query()` with backend-appropriate Cypher |
| FTS indices not created (wrong DDL sent to new backend) | LOW | Call `await graphiti.build_indices_and_constraints()` manually; check `Neo4jDriver` or `FalkorDriver` implementation of this method |
| Neo4j not reachable at startup | LOW | `docker compose up -d neo4j`; wait 30 seconds; retry |
| Data loss from rebuild strategy | HIGH | Reindex from git history gets project knowledge back; manually-added knowledge cannot be recovered |
| retention.db UUID mismatch after migration | MEDIUM | Delete `~/.graphiti/retention.db`; access history and pin state are reset; rebuild from user actions |
| CI failing due to missing backend service | LOW | Add `services:` block to CI YAML; push a fix commit |
| LadybugDB API divergence from Kuzu | HIGH | Revert to Kuzu 0.11.3 while LadybugDB stabilizes, or switch to Neo4j; do not patch around API differences |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Three Kuzu-direct calls in service.py | DB Migration Phase (day 1) | `grep -rn "import kuzu" src/` returns zero results |
| 50+ graphiti-core Kuzu branches + hardcoded `_create_fts_indices` | DB Migration Phase (day 1) | `_create_fts_indices` method deleted; startup creates indices via `build_indices_and_constraints()` |
| Data loss from rebuild strategy | DB Migration Phase (pre-code) | Migration guide documents exactly what is lost; export script available |
| Neo4j Docker not running = hard failure | DB Migration Phase | `graphiti health` prints clear, actionable error when Neo4j unreachable |
| falkordblite not yet supported in graphiti-core | DB Migration Phase (backend selection) | Chosen backend has a merged, released graphiti-core driver |
| LadybugDB pre-production maturity | DB Migration Phase (backend selection) | PR #1296 merged into graphiti-core before LadybugDB is chosen |
| `graphiti.kuzu` path naming | DB Migration Phase | `paths.py` uses backend-agnostic name; startup detects stale `.kuzu` files |
| Mocked tests provide no coverage | DB Migration Phase | Integration test with real backend exists; CI runs it |
| CI misconfigured for new backend | DB Migration Phase | CI passes on a fresh branch without local Docker |
| Graph UI Redesign breaks on service.py methods | DB Migration Phase (prerequisite to UI) | UI endpoints return correct data from new backend |

---

## Sources

- Codebase inspection: `src/graph/service.py` (lines 1143, 1185, 1247 — direct Kuzu calls), `src/storage/graph_manager.py` (all three workarounds), `src/config/paths.py` (`.kuzu` extension)
- graphiti-core 0.28.1 source inspection: `driver/kuzu_driver.py` (schema, no `_database` set), `driver/neo4j_driver.py` (constructor, `build_indices_and_constraints()`), `search/search_utils.py` (50+ KUZU branches), `driver/falkordb_driver.py` (server-only, host/port constructor)
- graphiti-core GitHub issue #1132: Kuzu is archived — https://github.com/getzep/graphiti/issues/1132
- graphiti-core GitHub issue #1240: FalkorDB Lite (embedded) support — https://github.com/getzep/graphiti/issues/1240 (PR #1250 in draft as of 2026-03-09)
- graphiti-core GitHub PR #1296: Migrate kuzu → ladybug (open, not yet merged as of 2026-03-09)
- KuzuDB archived October 2025 — https://www.theregister.com/2025/10/14/kuzudb_abandoned/
- LadybugDB v0.12.0: "functionality is equivalent to kuzu v0.11.3" — https://blog.ladybugdb.com/post/ladybug-release/
- falkordblite PyPI: Python 3.12+ only, Linux x86-64 + macOS x86-64/ARM64, no Windows — https://pypi.org/project/falkordblite/
- falkordblite docs: libomp.dylib required on macOS — https://docs.falkordb.com/operations/falkordblite/falkordblite-py.html
- Neo4j Python driver: `verify_connectivity()` usage, `ServiceUnavailable` exception — https://neo4j.com/docs/python-manual/current/connect/
- Neo4j Docker startup race condition — https://github.com/neo4j/neo4j/issues/12908

---
*Pitfalls research for: graphiti-knowledge-graph v2.0 — DB backend migration (KuzuDB replacement)*
*Researched: 2026-03-09*
