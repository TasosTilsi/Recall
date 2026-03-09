# Feature Research — v2.0 DB Backend Selection

**Domain:** Embedded Graph Database Backend for graphiti-core — replacing KuzuDB (archived Oct 2025)
**Researched:** 2026-03-09
**Confidence:** HIGH (graphiti-core driver interface derived from direct source inspection; backend capabilities verified against official docs and GitHub issues)

---

## Context

KuzuDB was archived by Kùzu Inc on October 10, 2025. The company announced "We will no longer be actively supporting KuzuDB." The GitHub repo is read-only. No new releases will be published. This project currently depends on `kuzu==0.11.3` and `graphiti-core[kuzu]==0.28.1`.

The replacement backend must satisfy every capability that graphiti-core's KuzuDriver currently provides, without requiring the application code to change its GraphService or adapter layers.

Sources: [The Register](https://www.theregister.com/2025/10/14/kuzudb_abandoned/), [graphiti issue #1132](https://github.com/getzep/graphiti/issues/1132)

---

## What graphiti-core Requires From a Backend Driver

This section is derived from direct inspection of the installed graphiti-core 0.28.1 source at `.venv/lib/python3.12/site-packages/graphiti_core/`.

### 1. The GraphDriver ABC

Every backend must subclass `GraphDriver` (in `driver/driver.py`) and implement:

| Method | Required | Notes |
|--------|----------|-------|
| `execute_query(cypher, **kwargs)` | YES | Core async query method. Returns `(list[dict], None, None)`. |
| `session(database)` | YES | Returns a `GraphDriverSession` context manager |
| `close()` | YES | Async cleanup |
| `delete_all_indexes()` | YES | Index teardown |
| `build_indices_and_constraints()` | YES | Called on startup. For Kuzu this is a no-op (see workarounds below). |
| `_database: str` | YES | String attribute. Kuzu never sets this — the project patches it manually. |

Plus all the operation-specific property accessors:
`entity_node_ops`, `episode_node_ops`, `community_node_ops`, `saga_node_ops`, `entity_edge_ops`, `episodic_edge_ops`, `community_edge_ops`, `has_episode_edge_ops`, `next_episode_edge_ops`, `search_ops`, `graph_ops`.

Each returns a typed operations class instance. For a new driver, every operations class must be implemented (currently ~11 operation classes for Kuzu, same count for Neo4j and FalkorDB).

### 2. Schema Requirements

Kuzu's schema defines node and relationship tables. The equivalent must exist in any replacement:

**Nodes:** `Episodic`, `Entity`, `Community`, `RelatesToNode_`, `Saga`

**Relationships:** `RELATES_TO`, `MENTIONS`, `HAS_MEMBER`, `HAS_EPISODE`, `NEXT_EPISODE`

**Embedding columns:** `Entity.name_embedding FLOAT[]`, `Community.name_embedding FLOAT[]`, `RelatesToNode_.fact_embedding FLOAT[]`

Note: `RelatesToNode_` exists because Kuzu cannot create FTS indices on relationship properties directly. This is a Kuzu-specific workaround. A backend with native relationship FTS could store edges as actual relationships.

### 3. Full-Text Search (FTS) Requirements

**This is the hardest requirement to satisfy.** graphiti-core's Kuzu search operations call FTS indices on 4 labels:

| Index Name | Label | Fields Indexed | Query Mechanism |
|------------|-------|----------------|-----------------|
| `node_name_and_summary` | `Entity` | `name`, `summary` | `CALL QUERY_FTS_INDEX('Entity', 'node_name_and_summary', $query, TOP := $limit)` |
| `community_name` | `Community` | `name` | same pattern |
| `episode_content` | `Episodic` | `content`, `source`, `source_description` | same pattern |
| `edge_name_and_fact` | `RelatesToNode_` | `name`, `fact` | same pattern |

FTS is called from `search_ops`:
- `node_fulltext_search()` — entity search by name/summary
- `edge_fulltext_search()` — relationship search by fact text
- `episode_fulltext_search()` — episode search by content
- `community_fulltext_search()` — community search by name

**What breaks without FTS:** All search operations return empty results. `graphiti search <query>` stops working. Entity deduplication during `add_episode()` also calls FTS to find existing matching entities. Without FTS, every re-add creates duplicate entities.

### 4. Vector (Embedding) Similarity Search Requirements

Used in `search_ops` via `array_cosine_similarity(n.name_embedding, CAST($vec AS FLOAT[N]))`:
- `node_similarity_search()` — cosine similarity on `Entity.name_embedding`
- `edge_similarity_search()` — cosine similarity on `RelatesToNode_.fact_embedding`
- `community_similarity_search()` — cosine similarity on `Community.name_embedding`

The vector dimension is dynamic (determined at query time from the embedding length). Kuzu uses `CAST($search_vector AS FLOAT[{len(search_vector)}])` inline in the query — the dimension is baked into the query string.

**What breaks without vector search:** Semantic search stops working. The system falls back to FTS-only results, which are lower quality. Entity deduplication quality degrades significantly.

### 5. Graph Traversal Requirements

BFS traversal queries used in `node_bfs_search()` and `edge_bfs_search()`:
- Variable-length relationship patterns: `RELATES_TO*2..{depth*2}`
- Cross-label traversal: `Episodic → MENTIONS → Entity → RELATES_TO → RelatesToNode_ → Entity`
- Kuzu-specific: each logical graph hop is 2 physical hops because edges are materialized as `RelatesToNode_` intermediate nodes

### 6. Transaction Support

Kuzu has no real transaction support. `GraphDriver.transaction()` falls back to a `_SessionTransaction` wrapper that executes queries immediately. ACID transactions are not required — graphiti-core is designed to work without them.

### 7. Cypher Dialect

graphiti-core's Kuzu driver uses Cypher with Kuzu-specific extensions:
- `CALL QUERY_FTS_INDEX(...)` — Kuzu FTS syntax
- `CALL CREATE_FTS_INDEX(...)` — Kuzu FTS creation syntax
- `array_cosine_similarity(vec1, vec2)` — Kuzu vector cosine function
- `CAST($vec AS FLOAT[N])` — typed vector cast
- No `UNWIND` support (Kuzu limitation, worked around with per-UUID loops)
- No relationship FTS (workaround: `RelatesToNode_` intermediate node)

A replacement backend must either: (a) support the same Kuzu Cypher dialect, or (b) have its own driver implementation with operations classes rewritten for the new dialect.

---

## Feature Landscape

### Table Stakes (Required Capabilities)

Features the replacement backend must support to maintain existing functionality.

| Capability | Why Required | Complexity to Implement | Evidence |
|------------|--------------|------------------------|---------|
| **Cypher query execution** | All graphiti-core ops use Cypher strings | LOW if backend supports Cypher natively; HIGH if not | Source: `driver/driver.py` `execute_query()` abstract method |
| **FTS on 4 node/edge labels** | Required by all 4 `*_fulltext_search()` operations | HIGH — not all graph DBs support this natively | Source: `driver/kuzu/operations/search_ops.py` |
| **Vector cosine similarity** | Required by all 3 `*_similarity_search()` operations | MEDIUM — widely supported now | Source: `graph_queries.py` `get_vector_cosine_func_query()` |
| **Variable-depth graph traversal** | BFS search for related entities | LOW with Cypher, HIGH without | Source: `search_ops.py` `node_bfs_search()` |
| **Embedded operation (no server)** | Project requirement: `~/.graphiti/` file path, no daemon | HIGH — eliminates most graph DBs | Milestone context |
| **Dual-scope isolation** | Two separate DB instances per session (global + project) | MEDIUM — must support multiple open DBs simultaneously | Source: `graph_manager.py` |
| **Python async API** | graphiti-core is fully async | MEDIUM | Source: `kuzu.AsyncConnection` usage |
| **Schema management** | Node/relationship table creation on first run | LOW with Cypher DDL | Source: `kuzu_driver.py` `SCHEMA_QUERIES` |
| **Active maintenance** | Security patches, Python version support | LOW to verify | Non-negotiable requirement given Kuzu's fate |

### Differentiators (Capability Improvements Over KuzuDB)

Capabilities that would improve the system beyond what Kuzu provided.

| Capability | Value | Complexity | Notes |
|------------|-------|------------|-------|
| **Native relationship FTS** | Eliminates `RelatesToNode_` workaround; simplifies schema | HIGH (requires driver rewrite) | Kuzu had no rel FTS; this was the root cause of the intermediate node pattern |
| **ACID transactions** | Safer concurrent writes from multiple CLI invocations | LOW (transparent to app) | Neo4j supports; FalkorDB partial; Kuzu had none |
| **UNWIND support** | Eliminates per-UUID loop workarounds in reranker queries | LOW (transparent to app) | Kuzu lacked UNWIND; Neo4j and FalkorDB support it |
| **Built-in vector index (HNSW)** | Faster approximate nearest-neighbor vs exact cosine scan | MEDIUM (query rewrite needed) | Kuzu used exact scan; Neo4j/FalkorDB have vector indexes |
| **Official graphiti-core driver** | No custom driver maintenance burden for this project | HIGH (waiting for FalkorDB Lite) | FalkorDB Lite driver proposed in graphiti issue #1240 (draft PR) |
| **Graph UI compatibility** | Visual inspection without custom UI | LOW | FalkorDB has browser UI; Neo4j has Neo4j Browser |

### Anti-Features (What to Explicitly Avoid)

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| **Server-mode graph DB (Docker required)** | "Neo4j is mature and well-supported" | Breaks the embedded use case. Users cannot install Docker just to use a CLI tool. MCP clients would need Docker compose to start. | Use FalkorDB Lite (embedded subprocess) or wait for another embedded Cypher DB. Neo4j is server-only. |
| **Custom Python graph library (e.g., NetworkX)** | "Simple, no server" | No Cypher support. Would require complete rewrite of all 11 operation classes + query translator. FTS and vector search would need separate integrations. | Not viable for this scope. |
| **LanceDB as graph backend** | "It's embedded and has vector search" | LanceDB is a vector database, not a graph database. No Cypher, no relationship traversal, no FTS on graph nodes. Used alongside Kuzu in some stacks, not as a replacement for it. | LanceDB does not implement GraphDriver ABC and cannot without a full graph layer above it. |
| **Apache AGE (PostgreSQL extension)** | "PostgreSQL is mature" | Requires PostgreSQL server running. Not embedded. Python client requires `psycopg2` + PostgreSQL installation. No graphiti-core driver exists. | Server requirement eliminates it for the embedded use case. |
| **Forking KuzuDB** | "We know the codebase" | The community fork (LadybugDB/bighorn) has unknown stability and no graphiti-core driver commitment. Maintains the same risks Kuzu had. | Wait for FalkorDB Lite or migrate to Neo4j for the server case. |
| **Dual-engine approach (FTS via SQLite FTS5, graph via custom store)** | "Mix best-of-breed" | Would require writing a GraphDriver that proxies two separate stores. Every search operation becomes a cross-store join. Maintenance nightmare. | A single DB that supports both graph traversal and FTS is the correct solution. |

---

## Candidate Backend Comparison

### Backend 1: FalkorDB (server mode)

| Criterion | Status | Evidence |
|-----------|--------|---------|
| graphiti-core driver | YES — `FalkorDriver` shipped in 0.28.1 | Source: `.venv/.../falkordb_driver.py` |
| FTS support | YES — `db.idx.fulltext.createNodeIndex()`, RediSearch syntax | [FalkorDB FTS docs](https://docs.falkordb.com/cypher/indexing/fulltext-index.html) |
| FTS on relationships | YES — `CREATE FULLTEXT INDEX FOR ()-[e:RELATES_TO]-() ON (e.name, e.fact)` | Source: `graph_queries.py` line 119; removes need for `RelatesToNode_` workaround |
| Vector search | YES — `vec.cosineDistance()`, vector indexes | [FalkorDB Vector Index](https://docs.falkordb.com/cypher/indexing/vector-index.html) |
| Embedded (no server) | NO — Redis-based, requires server process | Source: `falkordb.com`, Docker requirement |
| Active maintenance | YES — last commit within days, commercial backing | [FalkorDB GitHub](https://github.com/FalkorDB/FalkorDB) |
| Cypher compatibility | YES — OpenCypher with FalkorDB extensions | Confirmed in graphiti-core driver |
| Driver migration effort | LOW — drop-in swap of `KuzuDriver` → `FalkorDriver` | graphiti-core already ships this driver |
| Known issues | Edge FTS causes full graph scan (O(n×m)), reported in [#1272](https://github.com/getzep/graphiti/issues/1272) | MEDIUM confidence |

**Verdict:** Fully capable, officially supported, but requires Docker/server. Not embedded.

### Backend 2: FalkorDB Lite (`falkordblite`)

| Criterion | Status | Evidence |
|-----------|--------|---------|
| graphiti-core driver | NOT YET — draft PR #1250 exists, not merged as of 2026-03-09 | [graphiti issue #1240](https://github.com/getzep/graphiti/issues/1240) |
| FTS support | UNVERIFIED — "requires validation against embedded engine" | Issue #1240 text; falkordblite README does not document FTS |
| Vector search | UNVERIFIED — same caveat as FTS | Issue #1240 text |
| Embedded (no server) | YES — subprocess with Unix socket, file-based storage | [falkordblite repo](https://github.com/FalkorDB/falkordblite) |
| Platform support | Linux x86-64, macOS x86-64 + ARM64 ONLY | falkordblite README |
| Active maintenance | YES — v0.8.0 released Feb 4, 2026 | PyPI release history |
| Python requirement | 3.12+ (matches this project) | falkordblite README |
| Driver migration effort | LOW once driver ships — same FalkorDriver subclass | Issue #1240: "thin subclass of existing FalkorDriver" |
| Risk | HIGH — FTS/vector unverified, driver not merged | LOW confidence on search capabilities |

**Verdict:** Ideal embedded solution but NOT ready. FTS and vector search support unverified. No graphiti-core driver merged. Requires monitoring for v0.28.x+ driver support.

### Backend 3: Neo4j Community Edition

| Criterion | Status | Evidence |
|-----------|--------|---------|
| graphiti-core driver | YES — `Neo4jDriver` is the primary/reference driver in 0.28.1 | Source: `.venv/.../neo4j_driver.py` |
| FTS support | YES — `CREATE FULLTEXT INDEX ... FOR ()-[e:RELATES_TO]-() ON EACH [e.name, e.fact]` — native rel FTS | Source: `graph_queries.py` lines 132-139 |
| Vector search | YES — `vector.similarity.cosine()`, ANN indexes available in Neo4j 5.x | Official Neo4j docs |
| Embedded (no server) | NO — JVM process required, no pure-Python embedded mode | Neo4j docs; confirmed no Python embedded option |
| Active maintenance | YES — Neo4j 5.x actively maintained, commercial company | neo4j.com |
| Cypher compatibility | YES — Neo4j created Cypher; fullest implementation | Official |
| ACID transactions | YES — full ACID with `async with driver.transaction()` | Neo4j Driver ABC in graphiti-core |
| Driver migration effort | LOW — reference implementation, most complete | graphiti-core's Neo4j driver is the primary target |
| Docker requirement | YES — `docker run neo4j` or install Neo4j locally | neo4j.com |
| graphiti-core issue count | Fewest open bugs vs FalkorDB | GitHub issues comparison |

**Verdict:** Most capable and best-tested driver in graphiti-core. Server-only. Acceptable for developer workflow (Docker once, stays running). Not truly embedded.

### Backend 4: Apache AGE (PostgreSQL extension)

| Criterion | Status | Evidence |
|-----------|--------|---------|
| graphiti-core driver | NO — no driver exists | PyPI, GitHub search |
| FTS support | YES — via PostgreSQL `pg_trgm` or `tsvector` | PostgreSQL docs |
| Vector search | YES — via `pgvector` extension | pgvector |
| Embedded (no server) | NO — requires PostgreSQL server | Architecture requirement |
| Active maintenance | YES — Apache Top Level Project | apache/age GitHub |
| Cypher compatibility | PARTIAL — openCypher via PostgreSQL paths | Apache AGE docs |
| Driver migration effort | VERY HIGH — full driver + operations classes from scratch | No existing driver |

**Verdict:** No driver exists. Server-only. Not a viable migration path without months of custom driver work.

### Backend 5: LanceDB

| Criterion | Status | Evidence |
|-----------|--------|---------|
| graphiti-core driver | NO — not a graph database | Architecture |
| Graph traversal | NO — vector store only, no relationship model | LanceDB docs |
| FTS support | YES — BM25 full-text search | [LanceDB FTS docs](https://docs.lancedb.com/search/full-text-search) |
| Vector search | YES — primary feature | LanceDB |
| Embedded (no server) | YES — file-based, embedded | LanceDB |
| Active maintenance | YES — active development 2025-2026 | LanceDB GitHub |
| Role in ecosystem | Used as vector layer alongside Kuzu, not a Kuzu replacement | kuzudb/graph-rag-workshop README |

**Verdict:** Not a graph database. Cannot replace KuzuDB for graphiti-core. LanceDB + a graph DB is a complementary architecture, not a replacement.

---

## Capability Requirements Matrix

Required capabilities to maintain all existing features, mapped to each candidate:

| Capability | FalkorDB (server) | FalkorDB Lite | Neo4j | Apache AGE | LanceDB |
|------------|:-----------------:|:-------------:|:-----:|:----------:|:-------:|
| GraphDriver ABC implementation | YES | NOT YET | YES | NO | NO |
| FTS on node labels | YES | UNVERIFIED | YES | YES (via pg) | YES |
| FTS on relationship properties | YES | UNVERIFIED | YES | YES (via pg) | N/A |
| Vector cosine similarity | YES | UNVERIFIED | YES | YES (pgvector) | YES |
| Variable-depth graph traversal | YES | UNVERIFIED | YES | PARTIAL | NO |
| Embedded / no server | NO | YES | NO | NO | YES |
| Dual-scope (multiple open DBs) | YES (multi-graph) | YES | YES (multi-db) | YES | YES |
| Python async API | YES | YES | YES | NO driver | YES |
| Active maintenance (2026) | YES | YES | YES | YES | YES |
| Drop-in swap (no app code change) | YES | YES (future) | YES | NO | NO |

**Key insight:** Only Neo4j and FalkorDB (server mode) satisfy ALL requirements today. FalkorDB Lite satisfies them architecturally but is not yet proven for FTS + vector in embedded mode.

---

## Feature Dependencies

```
[Embedded operation]
    └──conflicts──> [Neo4j]          (server only)
    └──conflicts──> [FalkorDB server] (server only)
    └──compatible─> [FalkorDB Lite]  (embedded subprocess)

[FTS on 4 labels]
    └──requires──> [Backend native FTS] OR [custom FTS implementation]
    └──enables──>  [node_fulltext_search]
    └──enables──>  [edge_fulltext_search]
    └──enables──>  [episode_fulltext_search]
    └──enables──>  [community_fulltext_search]
    └──if missing──> [entity dedup breaks] + [graphiti search stops working]

[Vector similarity search]
    └──requires──> [Backend cosine similarity] OR [external vector store]
    └──enables──>  [node_similarity_search]
    └──enables──>  [edge_similarity_search]
    └──enables──>  [community_similarity_search]
    └──if missing──> [semantic search degrades to FTS-only]

[graphiti-core driver]
    └──requires──> [11 operations classes implemented]
    └──requires──> [FTS integration]
    └──requires──> [vector similarity integration]
    └──requires──> [Cypher dialect support]
```

### Dependency Notes

- **FTS is the hardest dependency:** It is called inside `add_episode()` for entity deduplication, not just in search. Missing FTS causes data corruption (duplicate entities), not just degraded search.
- **FalkorDB Lite FTS is the critical unknown:** The entire case for an embedded migration rests on whether FalkorDB Lite supports `db.idx.fulltext.createNodeIndex()` inside its embedded subprocess. This must be empirically verified.
- **The `RelatesToNode_` workaround disappears with FalkorDB:** FalkorDB supports `CREATE FULLTEXT INDEX FOR ()-[e:RELATES_TO]-() ON EACH [e.name, e.fact]`. A FalkorDB migration could simplify the schema by replacing `RelatesToNode_` with a real relationship. This is a driver-level change, not an application-level change.
- **Neo4j removes ALL Kuzu workarounds:** The Neo4j driver in graphiti-core is the reference implementation. It has real ACID, real relationship FTS, UNWIND support. None of the three `graph_manager.py` workarounds are needed.

---

## Migration Risk Matrix

| Migration Path | FTS Risk | Vector Risk | Schema Risk | Driver Risk | Embedded Risk | Overall Risk |
|----------------|----------|-------------|-------------|-------------|---------------|--------------|
| Kuzu → FalkorDB (server) | LOW | LOW | MEDIUM (RelatesToNode_ → real edge) | LOW (driver ships) | HIGH (breaks embedded) | MEDIUM |
| Kuzu → FalkorDB Lite | HIGH (unverified FTS) | HIGH (unverified) | MEDIUM | HIGH (driver not merged) | LOW | HIGH |
| Kuzu → Neo4j | LOW | LOW | MEDIUM (schema dialect changes) | LOW (reference impl) | HIGH (breaks embedded) | MEDIUM |
| Kuzu → Apache AGE | HIGH (no driver) | MEDIUM | HIGH | VERY HIGH | HIGH | VERY HIGH |
| Kuzu → LanceDB | BLOCKER (not a graph DB) | N/A | BLOCKER | BLOCKER | LOW | BLOCKER |

---

## MVP Definition for v2.0 Backend Migration

### Launch With (v2.0 — minimum to restore all v1.1 capabilities)

- [ ] **Backend choice confirmed** — empirically verify FalkorDB Lite FTS + vector in embedded mode. If passes: FalkorDB Lite. If fails: Neo4j with Docker.
- [ ] **Driver swap** — replace `KuzuDriver` with the chosen backend driver in `graph_manager.py`. Remove three Kuzu-specific workarounds from `graph_manager.py`.
- [ ] **Schema migration** — export existing Kuzu graphs and import to new backend. FalkorDB has a [KuzuDB migration guide](https://www.falkordb.com/blog/kuzudb-to-falkordb-migration/).
- [ ] **FTS validation** — confirm all 4 FTS indices are created on first run and queries return results.
- [ ] **Vector validation** — confirm cosine similarity queries work with Ollama embedding dimensions.
- [ ] **Dual-scope validation** — global and project graphs operate independently.
- [ ] **Update pyproject.toml** — remove `kuzu==0.11.3` and `graphiti-core[kuzu]`, add chosen backend dep.

### Add After Validation (v2.0.x)

- [ ] **Schema simplification (FalkorDB path only)** — if on FalkorDB, replace `RelatesToNode_` with real RELATES_TO edges. Requires driver-level change to `search_ops.py`. Improves query performance and removes a confusing schema artifact.
- [ ] **Migration tooling** — `graphiti migrate` command to export existing Kuzu graph and re-import to new backend for users upgrading from v1.1.

### Future Consideration (v2.1+)

- [ ] **FalkorDB Lite (if not ready for v2.0)** — revisit when graphiti-core FalkorLiteDriver is merged and FTS/vector are confirmed in embedded mode.
- [ ] **HNSW vector index** — replace exact cosine scan with approximate nearest-neighbor index for better performance on large graphs.

---

## Feature Prioritization Matrix

| Feature/Capability | User Value | Implementation Cost | Priority |
|--------------------|------------|---------------------|----------|
| Confirm FTS works in chosen backend | HIGH | LOW (1-day spike) | P1 |
| Drop-in driver swap in graph_manager.py | HIGH | LOW (if driver ships) | P1 |
| Remove Kuzu workarounds | HIGH | LOW (3 patches, all in graph_manager.py) | P1 |
| Schema migration tool | HIGH | MEDIUM | P1 |
| Validate all search operations end-to-end | HIGH | LOW (existing test suite) | P1 |
| FalkorDB Lite FTS/vector spike | HIGH | LOW (experimental branch) | P1 |
| RelatesToNode_ removal (FalkorDB) | MEDIUM | HIGH (driver rewrite) | P2 |
| HNSW vector index | LOW | MEDIUM | P3 |

---

## Recommendation

**Primary path (if FalkorDB Lite FTS/vector verified):** Migrate to FalkorDB Lite.
- Preserves embedded operation
- graphiti-core FalkorDriver is a thin subclass (expected low effort once driver merges)
- FalkorDB is actively maintained with commercial backing focused on LLM/GraphRAG use cases
- Same Cypher dialect as FalkorDB server; if embedded limits appear, drop-in swap to FalkorDB server

**Fallback path (if FalkorDB Lite FTS/vector fails):** Migrate to FalkorDB (server mode).
- Adds Docker dependency but eliminates all other risks
- Driver ships with graphiti-core 0.28.1 today
- Preferred over Neo4j because FalkorDB is the embedded-first direction the graphiti team is pursuing

**Do not use:** Neo4j as primary path (server + JVM overhead for a CLI tool is disproportionate), Apache AGE (no driver, server required), LanceDB (not a graph DB).

**Critical pre-condition before v2.0 planning:** Run a FalkorDB Lite spike test — create an FTS index and execute a `db.idx.fulltext.queryNodes()` call inside falkordblite. If it raises an error or returns empty results, switch immediately to the FalkorDB server fallback path. Do not design the v2.0 roadmap around FalkorDB Lite without this confirmation.

---

## Sources

- Direct source inspection: `graphiti-core==0.28.1` installed at `.venv/lib/python3.12/site-packages/graphiti_core/` (HIGH confidence)
- [KuzuDB archived — The Register](https://www.theregister.com/2025/10/14/kuzudb_abandoned/) (HIGH confidence)
- [graphiti issue #1132 — Kuzu is archived](https://github.com/getzep/graphiti/issues/1132) (HIGH confidence)
- [graphiti issue #1240 — FalkorDB Lite support proposal](https://github.com/getzep/graphiti/issues/1240) (HIGH confidence — Feb 18, 2026, draft PR)
- [graphiti issue #1272 — FalkorDB edge FTS full scan bug](https://github.com/getzep/graphiti/issues/1272) (MEDIUM confidence)
- [falkordblite GitHub](https://github.com/FalkorDB/falkordblite) — v0.8.0 released Feb 4, 2026 (HIGH confidence)
- [FalkorDB FTS documentation](https://docs.falkordb.com/cypher/indexing/fulltext-index.html) (HIGH confidence, official docs)
- [FalkorDB Vector Index documentation](https://docs.falkordb.com/cypher/indexing/vector-index.html) (HIGH confidence, official docs)
- [FalkorDB KuzuDB migration guide](https://www.falkordb.com/blog/kuzudb-to-falkordb-migration/) (MEDIUM confidence)
- `graphiti_core/graph_queries.py` — FTS index creation strings for all three backends (HIGH confidence, direct source)
- `graphiti_core/driver/kuzu/operations/search_ops.py` — FTS and vector query patterns (HIGH confidence, direct source)
- `graphiti_core/driver/kuzu_driver.py` — SCHEMA_QUERIES, operations class registration (HIGH confidence, direct source)

---

*Feature research for: v2.0 DB Backend Selection — KuzuDB replacement*
*Researched: 2026-03-09*
*Confidence: HIGH for graphiti-core requirements (source-derived); MEDIUM for FalkorDB Lite capabilities (FTS/vector unverified in embedded mode)*
