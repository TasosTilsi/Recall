# Architecture Research: DB Backend Migration (v2.0)

**Domain:** Embedded graph database backend migration for graphiti-knowledge-graph
**Researched:** 2026-03-09
**Confidence:** HIGH (all integration points verified from installed source code at
`/home/tasostilsi/.local/lib/python3.12/site-packages/graphiti_core/`)

---

## Context: Why Migration Is Needed

KuzuDB was archived by its creator Kùzu Inc in October 2025 following an acquisition by Apple.
The project is unmaintained, receives no security reviews, and is written in C++ with a large
third-party dependency surface. The installed version (kuzu 0.11.3, graphiti-core 0.28.1) still
works but carries growing security and longevity risk.

**graphiti-core 0.28.1 is the latest PyPI release as of 2026-03-09.** There is no newer release.
This means no new backend drivers (LadybugDB, FalkorLiteDriver) are available via pip yet —
they exist only in the upstream GitHub main branch.

---

## Standard Architecture: The Driver Abstraction

### GraphProvider Enum (verified from installed source)

```python
# graphiti_core/driver/driver.py  (installed 0.28.1)
class GraphProvider(Enum):
    NEO4J    = 'neo4j'
    FALKORDB = 'falkordb'
    KUZU     = 'kuzu'
    NEPTUNE  = 'neptune'
```

### GraphDriver Abstract Base Class

`GraphDriver(QueryExecutor, ABC)` defines the interface all backends must implement:

| Method | Purpose |
|--------|---------|
| `execute_query(cypher, **kwargs)` | Run a Cypher query, return `(records, header, summary)` |
| `session(database)` | Return a `GraphDriverSession` context manager |
| `close()` | Async teardown |
| `delete_all_indexes()` | Drop all indices |
| `build_indices_and_constraints(delete_existing)` | Create schema + FTS indices |
| `transaction()` | Async context manager yielding a `Transaction` |

The base class also has typed operation property slots (`entity_node_ops`, `search_ops`, etc.)
that each backend wires to provider-specific implementations.

### Available Drivers in graphiti-core 0.28.1 (verified)

| Driver Class | Module | Backend | Embedded? | Dual-scope strategy |
|---|---|---|---|---|
| `KuzuDriver` | `driver/kuzu_driver.py` | KuzuDB (archived) | Yes — file path | Two `KuzuDriver(db=<path>)` instances |
| `FalkorDriver` | `driver/falkordb_driver.py` | FalkorDB | No — Redis server | `driver.clone(database=<name>)` |
| `Neo4jDriver` | `driver/neo4j_driver.py` | Neo4j | No — Bolt server | Two drivers or `_database` swap |
| `NeptuneDriver` | `driver/neptune_driver.py` | Amazon Neptune | No — cloud | N/A |

`FalkorLiteDriver` (truly embedded FalkorDB) and a `LadybugDriver` both exist in the upstream
GitHub main branch but are **not in any PyPI release**. Installing either requires either a
pre-release or vendoring a driver locally.

### How Graphiti() Accepts a Driver (verified from graphiti.py lines 204–209)

```python
if graph_driver:
    self.driver = graph_driver          # use the provided driver directly
else:
    self.driver = Neo4jDriver(uri, user, password)  # default fallback
```

The driver is passed as `graph_driver=<instance>` — a clean, tested injection point. This
project already uses it correctly in `src/graph/service.py` line 188–193.

---

## Current Integration Architecture

```
CLI commands
    |
    v
src/graph/service.py (GraphService)
    |
    +-- _get_graphiti(scope, project_root)
    |       |
    |       v
    |   src/storage/graph_manager.py (GraphManager)
    |       |-- _get_global_driver()
    |       |       KuzuDriver(db=str(GLOBAL_DB_PATH))
    |       |       driver._database = str(GLOBAL_DB_PATH)   [workaround 1: missing attr]
    |       |       _create_fts_indices(driver.db)           [workaround 2: FTS no-op bug]
    |       |
    |       +-- _get_project_driver(project_root)
    |               KuzuDriver(db=str(project_db_path))
    |               driver._database = str(project_db_path)  [workaround 1]
    |               _create_fts_indices(driver.db)            [workaround 2]
    |
    +-- list_edges_readonly()        line ~1143: import kuzu; kuzu.Database(read_only=True)
    +-- list_entities_readonly()     line ~1185: import kuzu; kuzu.Database(read_only=True)
    +-- get_entity_by_uuid()         line ~1247: import kuzu; kuzu.Database(read_only=True)
    |   [these 3 bypass the driver abstraction and call kuzu directly]
    |
    +-- src/graph/adapters.py        [unchanged for any backend migration]
    +-- src/config/paths.py          GLOBAL_DB_PATH = ~/.graphiti/global/graphiti.kuzu
                                     PROJECT_DB_NAME = "graphiti.kuzu"
```

### The Dual-Scope Design

KuzuDB is file-path-based: each scope gets its own directory on disk and `GraphManager` holds
two separate `KuzuDriver` instances. The replacement backend must fit this pattern or require
an alternative scoping mechanism.

| Backend | Dual-Scope Mechanism |
|---------|---------------------|
| KuzuDB (current) | Two separate `KuzuDriver(db=<path>)` instances |
| LadybugDB | Same as KuzuDB — file-path constructor, two instances |
| FalkorDB server | `FalkorDriver.clone(database=<name>)` — one Redis connection, two graph names |
| FalkorLiteDriver (not in PyPI) | File-path based (same as KuzuDB) — two instances |
| Neo4j | Two `Neo4jDriver` instances with different `_database` values, or group_id only |

---

## Option A: LadybugDB (Recommended Embedded Path)

### What It Is

LadybugDB is a community fork of KuzuDB started in October 2025 immediately after the Apple
acquisition. It is designed and marketed as a drop-in replacement for KuzuDB, with active
development, enterprise support, and the same Cypher dialect.

### graphiti-core Support Status

PR #1296 in the upstream graphiti repo proposes replacing `KuzuDriver` with `LadybugDriver`.
The PR is open as of 2026-03-09 (not merged). The upstream team requested keeping Kuzu until
a major version bump. **No `LadybugDriver` exists in any PyPI release of graphiti-core.**

### API Compatibility

LadybugDB's Python API mirrors KuzuDB structurally:
- `lb.Database("path.lbug")` vs `kuzu.Database("path")`
- `lb.AsyncConnection(db)` vs `kuzu.AsyncConnection(db)`
- Same Cypher dialect (KuzuDB's SCHEMA_QUERIES in `kuzu_driver.py` are compatible)

The file extension changes: `.kuzu` (a directory) → `.lbug`.

### Implementation Strategy

**Option A1 (recommended): Write a thin LadybugDriver locally and vendor it.**

`KuzuDriver` in graphiti-core is ~280 lines. It wraps `kuzu.Database` and `kuzu.AsyncConnection`.
A `LadybugDriver` can be written by copying `KuzuDriver` and substituting `ladybug` for `kuzu`
imports, keeping `provider = GraphProvider.KUZU` to reuse all Kuzu-dialect query builders
already in graphiti-core. This creates a ~280-line vendored file in `src/storage/`.

Verify two things before removing existing workarounds:
1. Does LadybugDB's `__init__` set `_database`? If yes, drop workaround 1.
2. Does `build_indices_and_constraints()` in LadybugDB actually create FTS indices? If yes,
   drop workaround 2. If no (same bug as KuzuDB), keep `_create_fts_indices()` unchanged.

**Option A2: Wait for upstream graphiti-core to publish LadybugDB support.**

Risk: unknown timeline. The upstream PR was open as of 2026-03-09.

### Confidence

MEDIUM — API compatibility is structurally consistent with Kuzu but not formally documented
as "100% drop-in." The upstream PR author states "all queries are backward compatible."
No Cypher dialect breaking changes found in community posts.

---

## Option B: FalkorDB Server Mode

### What It Is

FalkorDB is a Redis-based graph database with a full, well-tested driver in graphiti-core
0.28.1. It is the most mature alternative available on PyPI today.

### Initialization (verified from falkordb_driver.py)

```python
from graphiti_core.driver.falkordb_driver import FalkorDriver

driver = FalkorDriver(
    host='localhost',
    port=6379,
    username=None,
    password=None,
    database='global_db',
)
# For dual scope — clone reuses the same connection:
project_driver = driver.clone(database='project_my_project')
```

Connection: `host` + `port` as separate params (not a URI). Default: `localhost:6379`.

### Architecture Change: Graph Names Replace File Paths

FalkorDB is multi-tenant: one Redis server hosts multiple named graphs. Dual-scope becomes two
graph names instead of two file paths. The `FalkorDriver.clone()` method returns a copy with
a different `_database` (graph name), sharing the same underlying Redis connection.

`default_group_id = '\\_'` on `FalkorDriver` (vs `''` on Neo4jDriver/KuzuDriver) — means
graphiti-core uses a different default tenant separator. Verify this does not conflict with
the group_id strings the project currently uses (`"global"`, project path hashes).

### FalkorDB Embedded Mode (FalkorLiteDriver) — Not Available in 0.28.1

`FalkorLiteDriver` wraps a Redis subprocess. It is file-path based and spawns an OS process.
It exists in the upstream graphiti-core GitHub main but is not in any PyPI release. Platform
support when it is released: Linux x86-64, macOS x86-64/ARM64 only.

### Confidence

HIGH for server-mode `FalkorDriver` (code is in 0.28.1, production-tested, recommended by
FalkorDB's own KuzuDB migration guide).
LOW for `FalkorLiteDriver` availability (not in any PyPI release as of 2026-03-09).

---

## Option C: Neo4j

### Initialization (verified from neo4j_driver.py)

```python
from graphiti_core.driver.neo4j_driver import Neo4jDriver

driver = Neo4jDriver(
    uri='bolt://localhost:7687',   # or neo4j://localhost:7687
    user='neo4j',
    password='password',
    database='neo4j',
)
```

The driver is the reference implementation — most tested, full operations support.

### Dual-Scope with Neo4j

Neo4j Community Edition supports one database per server instance. Options:

1. **Two named databases** — requires Neo4j Enterprise Edition or Neo4j 5.x+ Community.
2. **group_id filtering only** — use one database, rely on `group_id` (which graphiti-core
   already does for all queries). This means global and project data coexist in one DB with
   different group_id values. Adequate for single-user local tools.

### Embedded Mode

No Python-embedded mode exists. The `neo4j-contrib/python-embedded` project is archived and
used JPype (unworkable). Neo4j always requires a running server process (Docker or Neo4j Desktop).
This is a regression for the "zero-external-services" UX this project has always had.

### Confidence

HIGH — fully supported, but poor fit for embedded local tooling.

---

## Files That Must Change Per Backend

### LadybugDB Migration

| File | Change | Lines of Work |
|------|--------|--------------|
| `src/storage/graph_manager.py` | Replace `KuzuDriver` import with `LadybugDriver`; update `_create_fts_indices` to use `lb.Database`/`lb.Connection`; verify and possibly remove workarounds 1 and 2 | ~30 lines changed |
| `src/graph/service.py` | Replace 3 `import kuzu` blocks (~lines 1143, 1185, 1247); replace `kuzu.Database(read_only=True)` and `kuzu.Connection` with `ladybug` equivalents | ~15 lines changed |
| `src/config/paths.py` | Rename db file extension from `.kuzu` to `.lbug` (or use neutral `.db`) | 2 lines changed |
| `pyproject.toml` | Replace `graphiti-core[kuzu]==0.28.1` and `kuzu==0.11.3` with appropriate new packages | 2 lines changed |
| `CLAUDE.md` | Update architecture section and known workarounds | — |
| **New file:** `src/storage/ladybug_driver.py` | Vendored LadybugDriver (~280 lines, copied from KuzuDriver with import substitution) | 280 lines new |

### FalkorDB Server Migration

| File | Change | Lines of Work |
|------|--------|--------------|
| `src/storage/graph_manager.py` | Full rewrite — `FalkorDriver` uses host/port not file paths; remove all 3 KuzuDB workarounds; dual-scope via `driver.clone()`; new `FalkorManager` class | ~135 lines, full rewrite |
| `src/graph/service.py` | Remove 3 `import kuzu` read-only blocks; replace with `driver.execute_query()` calls through the GraphDriver interface; remove `_resolve_db_path()` method | ~80 lines changed |
| `src/config/paths.py` | Add FalkorDB connection config (host, port, graph names); remove `.kuzu` path constants | ~10 lines changed |
| `pyproject.toml` | Replace `graphiti-core[kuzu]` → `graphiti-core[falkordb]`; remove `kuzu==0.11.3`; add `falkordb` package | 3 lines changed |
| `src/cli/commands/ui.py` | Point graph visualization at FalkorDB browser instead of Kuzu Explorer | Moderate |
| `CLAUDE.md` | Major architecture update | — |

### Neo4j Migration

| File | Change | Lines of Work |
|------|--------|--------------|
| `src/storage/graph_manager.py` | Rewrite for `Neo4jDriver(uri, user, password, database)`; handle dual-scope via `_database` field swap or two drivers; add config loading | ~135 lines, full rewrite |
| `src/graph/service.py` | Same as FalkorDB — remove 3 `import kuzu` blocks; `_resolve_db_path()` no longer applies | ~80 lines changed |
| `src/config/paths.py` | Add Neo4j connection config; remove file path constants | ~10 lines changed |
| `pyproject.toml` | Replace `graphiti-core[kuzu]` → `graphiti-core` (Neo4j driver bundled by default via `neo4j` in Requires); remove `kuzu==0.11.3` | 2 lines changed |
| `CLAUDE.md` | Update | — |

---

## The Three Read-Only Kuzu Blocks (Critical Migration Touchpoints)

`src/graph/service.py` has three methods that bypass the `GraphDriver` abstraction and open
raw Kuzu connections for read-only queries. These are the hardest migration points.

```
list_edges_readonly()       line ~1143
list_entities_readonly()    line ~1185
get_entity_by_uuid()        line ~1247
```

All three follow the pattern:
```python
import kuzu
db = kuzu.Database(str(db_path), read_only=True)
conn = kuzu.Connection(db)
result = conn.execute(query, params)
```

These exist because KuzuDB's `read_only=True` flag prevents write contention with the active
writer connection (Kuzu allows only one writer at a time).

**Migration per backend:**

| Backend | Strategy for 3 Read-Only Blocks |
|---------|--------------------------------|
| LadybugDB | Replace `import kuzu` with `import ladybug as lb`; same `lb.Database(path, read_only=True)` pattern; minimal change |
| FalkorDB server | Delete file-path logic entirely; replace with `driver.execute_query()` via the existing `GraphDriver` interface; FalkorDB has no single-writer contention issue |
| Neo4j | Delete file-path logic; replace with `driver.execute_query()`; Neo4j handles concurrent reads natively |

The FalkorDB/Neo4j version is actually cleaner architecture — it removes the bypass entirely.
For LadybugDB it stays as a pragmatic short-term fix.

---

## Data Migration Strategy

### graphiti-core Has No Export/Import API (verified)

`graphiti_core/migrations/__init__.py` is empty (1 line). There is no `dump()`, `restore()`,
`export()`, or cross-backend migration utility in graphiti-core 0.28.1.

### The Key Insight: Episodes Are the Source of Truth

graphiti-core stores two types of data:
- **Episodic nodes** — the raw source episodes (text, git commits) that were fed in
- **Entity nodes + edges** — derived via LLM extraction from episodic content

Only `Episodic` nodes need to be migrated. Entity nodes and edges will be reconstructed
automatically when episodes are replayed through `graphiti.add_episode()`.

### Practical Migration Options

**Option 1: Re-index from git history (recommended for project scope)**

The project already has `graphiti index` which reads git history and calls `add_episode()`.
Any user who has only indexed local git repos can rebuild fully:

```bash
graphiti index --rebuild   # existing functionality, project scope
```

Global scope data (manually added episodes via `graphiti add`) cannot be rebuilt this way.

**Option 2: One-time migration script (for global scope and manual episodes)**

A `graphiti migrate` CLI command that:
1. Opens the old KuzuDB with `read_only=True`
2. Reads all `Episodic` nodes (raw episodes, not derived entities)
3. Feeds them back through `graphiti.add_episode()` on the new backend

Only ~1 hour of implementation. Covers all user scenarios, including global scope.

**Option 3: Accept loss, rebuild**

For users with only small/recent project-scope data, wiping and rebuilding from git is trivial.
Most developer use-cases fall here. Offer this as the default path with an explicit warning.

### Recommendation

Build `graphiti migrate --from kuzu` as a phase deliverable. Detect old-format databases
(`graphiti.kuzu` directory present) and warn at startup before the old driver is removed.

---

## Build Order Recommendation

### Phase 1: Backend Migration (DB Migration Milestone)

Must precede any LLM provider expansion work because:

1. The `import kuzu` read-only bypass in `service.py` creates three code paths that will need
   maintenance after every new feature that reads the graph. Cleaning this up first reduces
   the surface area for LLM provider work.
2. The driver interface is the lowest layer in the stack. Changing it requires re-testing
   every feature above it. Getting this stable before adding multi-provider LLM avoids
   re-testing twice.
3. Security: KuzuDB's unmaintained C++ codebase is the highest-risk component. Migrating first
   removes it from the dependency tree before adding new provider dependencies.

### Phase 2: LLM Provider Expansion (after migration is stable)

Touches `src/llm/` and `src/graph/adapters.py`. Has zero dependency on which graph backend is
running. Can be developed immediately after the new backend passes the test suite.

**Recommended build order:**

```
Step 1.1  Upgrade graphiti-core if new version available with LadybugDriver
          OR vendor a LadybugDriver in src/storage/ladybug_driver.py

Step 1.2  Rewrite src/storage/graph_manager.py
          - New driver, remove 3 KuzuDB workarounds
          - Verify FTS index creation (keep _create_fts_indices or remove)

Step 1.3  Replace 3 read-only kuzu blocks in src/graph/service.py

Step 1.4  Update src/config/paths.py constants

Step 1.5  Update pyproject.toml dependencies

Step 1.6  Write and run data migration command
          (detect old graphiti.kuzu directories, migrate Episodic nodes)

Step 1.7  Run full test suite + smoke test all graph operations:
          add, search, list, get, delete, compact, index

Step 2.1+ LLM provider expansion (independent, no storage dependency)
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Replicating the Direct-Kuzu-Bypass in the New Backend

**What happens:** The three read-only methods in `service.py` do `import kuzu` directly,
bypassing the `GraphDriver` abstraction. Tempting to do the same for the new backend.

**Why it is wrong:** Two code paths per backend. Doubles maintenance surface. Any new query
needs to be added in both `driver.execute_query()` and the direct-access block.

**Do instead:** For FalkorDB/Neo4j migrations, replace the three blocks with
`driver.execute_query()` calls. For LadybugDB, keep the direct-access pattern temporarily
(same API, minimal friction) but mark it as technical debt to be cleaned up.

### Anti-Pattern 2: Upgrading graphiti-core Without Auditing Breaking Changes

**What happens:** Bumping from 0.28.1 to get LadybugDriver support without checking what
else changed in the intermediate versions.

**Why it is wrong:** graphiti-core has changed its driver operations pattern significantly
across minor versions (the typed `_entity_node_ops` property pattern was introduced relatively
recently). The 3 existing workarounds in this project were found by reading installed source.
Future upgrades may introduce new ones silently.

**Do instead:** Read the changelog for every graphiti-core version between 0.28.1 and target.
Run the full test suite against the new version in isolation before merging. Check if any of
the 3 workarounds are now fixed upstream (they may be, especially the `_database` attr bug).

### Anti-Pattern 3: Dropping Old Databases Without a Migration Warning

**What happens:** Migration is deployed and the old `graphiti.kuzu` directories are simply
ignored by the new backend. Users lose their knowledge graph data silently.

**Why it is wrong:** Users may have months of manually-added global-scope episodes that cannot
be recovered from git history.

**Do instead:** At startup, detect `graphiti.kuzu` directories in standard locations. Warn
the user and direct them to run `graphiti migrate`. Only suppress the warning once migration
has completed or the user explicitly acknowledges data loss.

### Anti-Pattern 4: Using FalkorDB or Neo4j for a "Local First" Tool Without Documenting Server Requirements

**What happens:** Backend is switched to server-mode FalkorDB or Neo4j. New users run
`graphiti add` and get `ConnectionRefusedError: localhost:6379` with no helpful message.

**Why it is wrong:** The current tool has zero external service dependencies. Silently adding
a server requirement breaks the install-and-run experience.

**Do instead:** If server-mode backend is chosen, add a `graphiti doctor` check for server
connectivity at startup, and document the prerequisite prominently in the README.

---

## Integration Points Summary (for Phase Planning)

| Integration Point | File | Backend-Specific? | Change for LadybugDB | Change for FalkorDB |
|---|---|---|---|---|
| Driver instantiation | `src/storage/graph_manager.py` | Yes | Import `LadybugDriver` (vendored) | Import `FalkorDriver`; full rewrite |
| FTS index workaround | `src/storage/graph_manager.py` | Yes (Kuzu bug) | Verify if still needed | Not needed |
| `_database` attr workaround | `src/storage/graph_manager.py` | Yes (Kuzu bug) | Verify if fixed in LadybugDB | Not needed |
| Graphiti() driver injection | `src/graph/service.py` line 188 | No | No change | No change |
| `build_indices_and_constraints()` call | `src/graph/service.py` line 197 | No | No change | No change |
| Read-only edges query | `src/graph/service.py` ~1143 | Yes (kuzu import) | `import ladybug as lb` | Use `driver.execute_query()` |
| Read-only entities query | `src/graph/service.py` ~1185 | Yes (kuzu import) | `import ladybug as lb` | Use `driver.execute_query()` |
| Read-only entity-by-uuid | `src/graph/service.py` ~1247 | Yes (kuzu import) | `import ladybug as lb` | Use `driver.execute_query()` |
| DB path constants | `src/config/paths.py` | Yes (file extension) | Change `.kuzu` to `.lbug` | Remove file path constants |
| Dependencies | `pyproject.toml` | Yes | Replace kuzu package | Replace with falkordb |
| LLM/embedding adapters | `src/graph/adapters.py` | No | No change | No change |
| Data migration | New CLI command | Both need | Episodic node replay | Episodic node replay |

---

## Sources

- Installed graphiti-core 0.28.1 source (read directly):
  - `graphiti_core/driver/driver.py` — `GraphProvider` enum, `GraphDriver` ABC
  - `graphiti_core/driver/kuzu_driver.py` — `KuzuDriver` implementation (~280 lines)
  - `graphiti_core/driver/neo4j_driver.py` — `Neo4jDriver` with `Neo4jDriver(uri, user, password, database)`
  - `graphiti_core/driver/falkordb_driver.py` — `FalkorDriver` with `clone()` and `default_group_id`
  - `graphiti_core/graphiti.py` lines 134–233 — `Graphiti.__init__` driver injection point
  - `graphiti_core/migrations/__init__.py` — confirmed empty (no migration API)
- Project source (read directly):
  - `src/storage/graph_manager.py` — all 3 KuzuDB workarounds, dual-scope pattern
  - `src/graph/service.py` — `_get_graphiti()`, 3 read-only kuzu blocks (lines ~1143/1185/1247)
  - `src/config/paths.py` — `GLOBAL_DB_PATH`, `PROJECT_DB_NAME` constants
- `pip index versions graphiti-core` — confirmed 0.28.1 is latest on PyPI, 2026-03-09
- [KuzuDB archived — The Register, Oct 2025](https://www.theregister.com/2025/10/14/kuzudb_abandoned/)
- [Kuzu is archived — graphiti issue #1132](https://github.com/getzep/graphiti/issues/1132)
- [LadybugDB migration PR #1296 (open)](https://github.com/getzep/graphiti/pull/1296)
- [FalkorDBLite issue #1240](https://github.com/getzep/graphiti/issues/1240) — FalkorLiteDriver not in PyPI yet
- [LadybugDB Python API docs](https://docs.ladybugdb.com/client-apis/python/) — API structure reviewed
- [FalkorDBLite GitHub](https://github.com/FalkorDB/falkordblite) — embedded mode confirmed; not in graphiti-core PyPI

---

*Architecture research for: graphiti-knowledge-graph v2.0 DB backend migration*
*Researched: 2026-03-09*
