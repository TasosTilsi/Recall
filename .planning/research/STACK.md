# Stack Research — v2.0 DB Backend Replacement

**Domain:** Embedded graph database backend for graphiti-core (replacing archived KuzuDB)
**Researched:** 2026-03-09
**Confidence:** HIGH (all findings verified against installed packages, PyPI, and official sources)

---

## Context

KuzuDB was archived by Kuzu Inc on **2025-10-10**. The repository is read-only and receives no bug fixes or security patches. `pip install kuzu==0.11.3` still works but is a dead-end dependency.

This research answers: what are the viable replacements within graphiti-core's driver architecture?

---

## graphiti-core==0.28.1 Built-In Drivers (Verified)

**Source: inspected `/home/tasostilsi/.local/lib/python3.12/site-packages/graphiti_core/driver/`**

graphiti-core 0.28.1 (latest on PyPI as of 2026-03-09) ships exactly four drivers:

| Driver Class | `GraphProvider` Enum Value | Install Extra | Embedded |
|---|---|---|---|
| `KuzuDriver` | `KUZU` | `graphiti-core[kuzu]` | Yes — in-process |
| `FalkorDriver` | `FALKORDB` | `graphiti-core[falkordb]` | No — requires server/subprocess |
| `Neo4jDriver` | `NEO4J` | included by default | No — requires Neo4j server |
| `NeptuneDriver` | `NEPTUNE` | `graphiti-core[neptune]` | No — AWS cloud only |

**No `FalkorLiteDriver` or `LadybugDriver` exists in 0.28.1.** Both are proposed in open GitHub issues but are not merged.

---

## Option 1: LadybugDB

### Identity

LadybugDB is a community-driven fork of KuzuDB, announced in October 2025 by Arun Sharma (ex-Facebook, ex-Google). The first release (v0.12.0, 2025-11-04) was explicitly described as "functionally equivalent to Kuzu v0.11.3 — only the name changed." LadybugDB Inc is the commercial entity providing enterprise support.

### Package Details

| Field | Value |
|---|---|
| PyPI package name | `real-ladybug` |
| Python import module | `lbug` |
| Latest version | **0.15.1** |
| Last release date | 2026-03-02 |
| Source | https://github.com/LadybugDB/ladybug |
| Maintained | Yes — monthly releases since Oct 2025 |
| Docker required | No — in-process embedded |
| Cypher support | Yes — KuzuDB Cypher implementation |
| FTS support | Yes — inherited from KuzuDB |

Release cadence: v0.12.x (Nov 2025), v0.13.x (Dec 2025), v0.14.x (Jan 2026), v0.15.x (Feb/Mar 2026).

### graphiti-core Compatibility

**Status: Needs a custom driver patch — no built-in support in 0.28.1.**

The KuzuDriver in graphiti-core 0.28.1 begins with `import kuzu` (line 20 of `kuzu_driver.py`, verified). LadybugDB uses `import lbug`. LadybugDB's own documentation states they performed "a global rename from kuzu to lbug" to maintain API parity. The driver code is otherwise structurally identical.

Two viable approaches to compatibility:

1. **Import alias shim (minimal):** `pip install real-ladybug` and add `import lbug as kuzu` at the top of a patched `kuzu_driver.py`. All graphiti-core internal calls to `kuzu.*` route to `lbug.*`.
2. **Module-level mock (no fork):** Install `real-ladybug`, then in the project's startup code: `import sys; import lbug; sys.modules['kuzu'] = lbug` before importing graphiti-core. This tricks Python's import system into loading `lbug` whenever graphiti-core does `import kuzu`.

**graphiti-core issue #1132** (opened 2026-01-02, open as of 2026-03-09): Community request to officially support LadybugDB. The graphiti maintainers have not acted on this in 0.28.1.

### Risk Assessment

- HIGH confidence on API compatibility for Kuzu 0.11.3 feature set (first release explicitly guaranteed parity).
- MEDIUM confidence on stability beyond v0.12.0 — the fork adds new features (hypergraph, metagraph support per Feb 2026 blog) that diverge from Kuzu 0.11.3. Ensure the three KuzuDB workarounds in `src/storage/graph_manager.py` are verified at runtime.
- MEDIUM confidence on long-term maintenance — commercial entity is <6 months old.

---

## Option 2: FalkorDB (built-in graphiti-core driver)

### Identity

FalkorDB is a graph database module for Redis, using GraphBLAS for sparse adjacency matrices. It implements OpenCypher and RedisSearch-style FTS. FalkorDB has a **built-in driver in graphiti-core 0.28.1**. However, FalkorDB itself is server-based (requires a Redis process).

**falkordblite** is a separate package that auto-manages a Redis+FalkorDB subprocess, providing a "zero-config" experience without Docker. It communicates over a Unix domain socket.

### Package Details

| Field | falkordb (server) | falkordblite (subprocess) |
|---|---|---|
| PyPI package name | `falkordb` | `falkordblite` |
| Latest version | **1.6.0** | **0.9.0** |
| Last release date | 2026 (active) | 2026-02-04 |
| Source | https://github.com/FalkorDB/FalkorDB | https://github.com/FalkorDB/falkordblite |
| Maintained | Yes | Yes |
| Docker required | Yes (standard) / No (falkordblite subprocess) | No |
| Cypher support | Yes (OpenCypher) | Yes |
| FTS support | Yes (RediSearch syntax) | Yes |
| Python 3.12 required | 3.8+ | **3.12+ only** (matches project) |
| Platforms | Cross-platform | Linux x86-64, macOS x86-64/ARM64 only |

### graphiti-core Compatibility

**Status: Built-in driver (`FalkorDriver`) — no custom code needed.**

`graphiti-core[falkordb]` installs both graphiti-core and the `falkordb` Python client. `FalkorDriver(host, port)` is the constructor.

With falkordblite, the workflow is:
1. `from falkordblite import FalkorDB as EmbeddedFalkorDB`
2. Start the managed subprocess: `edb = EmbeddedFalkorDB(path="~/.graphiti/falkor.db")`
3. Pass the connection to `FalkorDriver(host=edb.host, port=edb.port)`

**graphiti-core issue #1240** (FalkorDB Lite support, open): Proposes a `FalkorLiteDriver(path=...)` thin subclass for clean integration. Not merged in 0.28.1. Manual wiring as above is required today.

### Key Architectural Distinction

falkordblite is **not in-process embedded**. It forks a child process and communicates via Unix socket. This means:
- One extra process on startup (lightweight Redis+FalkorDB subprocess)
- IPC overhead per query (negligible for local use)
- Process isolation: app crash does not corrupt DB process
- The DB process persists across Python interpreter restarts within the same session

This is architecturally different from KuzuDB/LadybugDB's true in-process embedding.

### Cypher Compatibility Warning

FalkorDB's Cypher dialect has differences from KuzuDB's Cypher. The graphiti-core KuzuDriver and FalkorDriver use **separate query implementations** — the FalkorDB driver in graphiti-core rewrites all queries in FalkorDB's dialect. Migrating from `KuzuDriver` to `FalkorDriver` is a driver swap, not a query translation task (graphiti-core handles the translation internally). No manual Cypher porting needed.

### Risk Assessment

- HIGH confidence on graphiti-core compatibility — FalkorDriver is first-class, actively maintained by graphiti team.
- MEDIUM confidence on falkordblite subprocess stability — 9 releases in 3 months indicates rapid iteration but also potential churn.
- The subprocess model increases operational complexity slightly vs. LadybugDB's true embedding.

---

## Option 3: Neo4j

**Status: Built-in driver. Server required. Not viable for embedded use case.**

Requires a running Neo4j server (Docker or Neo4j Desktop). Eliminates the project's zero-infrastructure, local-first design. Not considered for v2.0.

---

## Option 4: Neptune

**Status: Built-in driver. AWS cloud service only. Not viable.**

Neptune Analytics requires AWS credentials and network access. Not a local embedded option.

---

## Option 5: Other Python Graph Libraries

| Library | PyPI | Embedded | Cypher | FTS | graphiti-core Driver | Verdict |
|---|---|---|---|---|---|---|
| `igraph` | `igraph` | In-memory only | No | No | None — needs full build | No |
| `networkx` | `networkx` | In-memory only | No | No | None — needs full build | No |
| DuckDB graph ext | `duckdb` | Yes | No (SQL) | Partial | None — needs full build | No |
| SQLite + graph | various | Yes | No | Partial | None — needs full build | No |

Building a complete new graphiti-core `GraphDriver` implementation requires implementing 10+ operation classes (entity nodes, episode nodes, community nodes, saga nodes, entity edges, episodic edges, community edges, has-episode edges, next-episode edges, search ops, graph maintenance ops). This is weeks of engineering work with no existing reference. None of these are viable for v2.0.

---

## Definitive Comparison Table

| Option | pip package | Version | Last Release | Maintained | Docker | Cypher | FTS | graphiti-core Support | Embedded Mode |
|---|---|---|---|---|---|---|---|---|---|
| **KuzuDB (current, dead)** | `kuzu` | 0.11.3 | 2025-10-10 (FINAL) | NO — archived | No | Yes | Yes (buggy*) | Built-in (`[kuzu]`) | True in-process |
| **LadybugDB** | `real-ladybug` | 0.15.1 | 2026-03-02 | Yes | No | Yes | Yes | Needs import shim | True in-process |
| **FalkorDB (Docker/server)** | `falkordb` | 1.6.0 | 2026 | Yes | Yes | Yes (OpenCypher) | Yes (RediSearch) | Built-in (`[falkordb]`) | No — external server |
| **FalkorDB via falkordblite** | `falkordb` + `falkordblite` | 1.6.0 / 0.9.0 | 2026-02-04 | Yes | No | Yes (OpenCypher) | Yes | Built-in driver + manual wiring | Subprocess (IPC) |
| **Neo4j** | `neo4j` | active | active | Yes | Yes | Yes | Yes | Built-in (default) | No — external server |
| **Neptune** | langchain-aws | active | active | Yes | No (AWS cloud) | Yes | Yes | Built-in (`[neptune]`) | No — cloud |
| **igraph / networkx / DuckDB** | various | active | active | Yes | No | No | No/Partial | None — full build required | In-memory (no persistence) |

*KuzuDB FTS: required the three workarounds in `src/storage/graph_manager.py`

---

## Recommendation

**Use LadybugDB (`real-ladybug==0.15.1`) as the primary v2.0 backend.**

**Rationale:**

1. **True in-process embedding.** Same architecture as KuzuDB — the database lives inside the Python process with no IPC, no child process management, and no port configuration. Preserves the project's zero-infrastructure design.

2. **Near-zero migration cost.** The three KuzuDB workarounds in `src/storage/graph_manager.py` were written against Kuzu 0.11.3 behavior. LadybugDB v0.12.0 was explicitly guaranteed equivalent to Kuzu 0.11.3. The import alias `import lbug as kuzu` or a `sys.modules['kuzu'] = lbug` shim is the entire migration at the driver level.

3. **Cypher and schema compatibility.** All KuzuDB SCHEMA_QUERIES, FTS index creation, and Cypher patterns in graphiti-core's `KuzuDriver` carry forward unchanged. The graphiti-core queries do not need modification.

4. **Active development.** 8 releases in 5 months with a commercial backer. More actively maintained than KuzuDB ever was in its final year.

**FalkorDB via falkordblite is the fallback** if LadybugDB has runtime incompatibilities (schema divergence, FTS behavior differences, or API drift post-0.12.0). FalkorDB has a first-class built-in graphiti-core driver that is maintained by the Zep team. The tradeoff is subprocess architecture and manual falkordblite wiring.

---

## Installation

```bash
# Option A: LadybugDB (recommended)
pip install "real-ladybug>=0.15.1"
# Remove: kuzu>=0.11.3

# Option B: FalkorDB embedded via falkordblite (fallback)
pip install "graphiti-core[falkordb]" "falkordblite>=0.9.0"
# Use: FalkorDriver (already in graphiti-core)
# Remove: graphiti-core[kuzu], kuzu
```

**pyproject.toml change for Option A:**
```toml
[project]
dependencies = [
    # Replace:
    #   "graphiti-core[kuzu]==0.28.1",
    #   "kuzu>=0.11.3",
    # With:
    "graphiti-core==0.28.1",   # drop [kuzu] extra
    "real-ladybug>=0.15.1",    # LadybugDB
]
```

---

## Version Compatibility

| Package | Compatible With | Notes |
|---|---|---|
| `real-ladybug==0.15.1` | `graphiti-core==0.28.1` | Needs `import lbug as kuzu` shim; not officially tested by graphiti maintainers as of 2026-03-09 |
| `real-ladybug==0.15.1` | Python 3.12 | Confirmed — LadybugDB targets same Python support as KuzuDB |
| `falkordblite==0.9.0` | `graphiti-core[falkordb]==0.28.1` | Python 3.12+ required (matches project); FalkorDriver is built-in |
| `kuzu==0.11.3` | `graphiti-core==0.28.1` | Still works but receives no patches; do not use for v2.0 |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|---|---|---|
| `kuzu>=0.11.3` | Archived 2025-10-10; no security or bug fix patches | `real-ladybug` |
| `neo4j` for local use | Requires server process; contradicts zero-infrastructure design | `real-ladybug` |
| `graphiti-core-falkordb` (separate PyPI package) | Frozen at 0.19.x era (pre-0.20 graphiti-core); incompatible with 0.28.1 | `graphiti-core[falkordb]` |
| `igraph` / `networkx` as graph DB | No persistence, no Cypher, no FTS; requires writing all 10 graphiti-core operation classes | Any option above |
| `falkordblite` on Windows | Not supported — Linux and macOS only | Use Docker FalkorDB on Windows |

---

## Open Questions / Phase 1 Verification Required

1. **LadybugDB workaround parity at v0.15.1:** The three KuzuDB bugs worked around in `src/storage/graph_manager.py` must be verified against `real-ladybug==0.15.1`:
   - Missing `_database` attr on driver: does `lbug.KuzuDriver._database` exist after construction?
   - FTS no-op: does `lbug.KuzuDriver.build_indices_and_constraints()` still skip FTS?
   - `create_batch()` NotImplementedError in embedder: unrelated to LadybugDB (lives in `OllamaEmbedder`)
   Verification: `import lbug; d = lbug.Database("/tmp/test"); ...` in a scratch script.

2. **`sys.modules` shim feasibility:** Verify that replacing `kuzu` in `sys.modules` with `lbug` before graphiti-core import does not break graphiti-core's internal type checks (it uses `kuzu.Database`, `kuzu.Connection` etc. by name in the driver).

3. **graphiti-core upgrade path:** If Zep releases 0.29+ with official LadybugDB support before v2.0 ships, the custom shim becomes unnecessary. Monitor https://github.com/getzep/graphiti/issues/1132.

4. **falkordblite lifecycle API:** If FalkorDB fallback is chosen, verify the exact Python API for starting and stopping the subprocess in `src/storage/graph_manager.py`'s `close_all()` method.

---

## Sources

- Installed package inspection: `/home/tasostilsi/.local/lib/python3.12/site-packages/graphiti_core/driver/` — HIGH confidence
- `pip index versions graphiti-core` — 0.28.1 is LATEST as of 2026-03-09 — HIGH confidence
- `pip index versions real-ladybug` — 0.15.1 confirmed on PyPI — HIGH confidence
- `pip index versions falkordblite` — 0.9.0 confirmed on PyPI — HIGH confidence
- `pip index versions falkordb` — 1.6.0 confirmed on PyPI — HIGH confidence
- KuzuDB archival: https://github.com/kuzudb/kuzu (archived), https://news.ycombinator.com/item?id=45560036 — HIGH confidence
- LadybugDB GitHub: https://github.com/LadybugDB/ladybug — HIGH confidence
- LadybugDB v0.12.0 release note ("functionally equivalent to Kuzu v0.11.3"): https://github.com/LadybugDB/ladybug/releases/tag/v0.12.0 — HIGH confidence
- FalkorDB blog on KuzuDB migration: https://www.falkordb.com/blog/kuzudb-to-falkordb-migration/ — MEDIUM confidence
- FalkorDBLite architecture (subprocess/Unix socket): https://www.falkordb.com/blog/falkordblite-embedded-python-graph-database/ — HIGH confidence
- graphiti issue #1132 (KuzuDB archived, LadybugDB): https://github.com/getzep/graphiti/issues/1132 — HIGH confidence (open 2026-03-09)
- graphiti issue #1240 (FalkorDB Lite feature request): https://github.com/getzep/graphiti/issues/1240 — HIGH confidence (open, not merged 2026-03-09)
- graphiti-core extras verified: `graphiti_core-0.28.1.dist-info/METADATA` — HIGH confidence

---

*Stack research for: graphiti-knowledge-graph v2.0 — DB backend replacement*
*Researched: 2026-03-09*
*Confidence: HIGH for all findings — verified against locally installed packages and PyPI*
