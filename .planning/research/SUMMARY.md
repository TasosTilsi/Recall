# Research Summary — v2.0 DB Backend Migration

**Project:** graphiti-knowledge-graph
**Domain:** Embedded graph database backend replacement (KuzuDB → maintained alternative)
**Researched:** 2026-03-09
**Confidence:** HIGH (architecture and pitfalls), MEDIUM (LadybugDB v0.15.x API parity), LOW (FalkorDB Lite FTS/vector)

## Executive Summary

KuzuDB was archived by Kùzu Inc in October 2025 (acquired by Apple). `kuzu==0.11.3` still installs but receives no security patches or bug fixes. graphiti-core 0.28.1 ships exactly four built-in drivers — KuzuDB, FalkorDB (server), Neo4j, and Neptune — with no embedded maintained alternative available on PyPI today.

**Two viable migration paths exist:** LadybugDB (`real-ladybug==0.15.1`) is a community-driven KuzuDB fork with near-identical API — the lowest-effort embedded path, but graphiti-core's PR #1296 is not yet merged, requiring a vendored ~280-line `LadybugDriver` locally. FalkorDB server mode has a first-class built-in driver and works today, but introduces a Docker/server dependency that breaks the project's zero-infrastructure design. FalkorDB Lite (embedded subprocess) is architecturally attractive but FTS/vector support in embedded mode is unverified, and its graphiti-core driver (PR #1250) is also unmerged.

**The migration is not a one-commit swap.** Three methods in `service.py` bypass the driver abstraction with direct `import kuzu` calls. `_create_fts_indices()` in `graph_manager.py` is hardcoded to `GraphProvider.KUZU` and will crash at startup after migration. Data loss is real: rebuild-from-git does not recover manually-added episodes, pin state, or retention access history. The DB migration phase must be the first v2.0 phase — it unblocks Graph UI Redesign (which reads via the broken kuzu-direct methods) and Local Memory (which depends on correct FTS for entity resolution quality).

## Key Findings

### Recommended Stack

**Primary path — LadybugDB:**
Vendor a ~280-line `LadybugDriver` in `src/storage/ladybug_driver.py` (copied from KuzuDB driver with `import lbug` substitution). Swap `real-ladybug>=0.15.1` for `kuzu>=0.11.3` in `pyproject.toml`. File-path based: same dual-scope design as today. Removes all 3 Kuzu workarounds (pending verification — LadybugDB may have fixed the `_database` bug and FTS no-op bug). Monitor graphiti-core PR #1296 to replace the vendored driver with the official one when released.

**Fallback path — FalkorDB server (if LadybugDB fails):**
Drop-in driver swap (`FalkorDriver` ships in graphiti-core 0.28.1). Adds Docker dependency but eliminates all risks. Requires full rewrite of `graph_manager.py` (host/port instead of file paths), and the three `service.py` read-only blocks must migrate to `driver.execute_query()` (actually cleaner architecture). Schema simplification bonus: FalkorDB supports native relationship FTS, eliminating the `RelatesToNode_` intermediate node workaround.

**Core technologies:**
- `real-ladybug>=0.15.1`: embedded DB, file-path based, KuzuDB fork — lowest-effort embedded migration
- `graphiti-core==0.28.1`: stays unchanged; entity resolution, typed edges, bi-temporal model non-negotiable
- `graphiti-core[falkordb]` + Docker: fallback only if LadybugDB fails verification

**Do NOT use:** Neo4j as primary (server+JVM overhead disproportionate for a CLI tool), FalkorDB Lite before PR #1250 merges + FTS/vector verified, Apache AGE (no driver, server required), LanceDB (not a graph database).

### Required Capabilities (All Must Be Satisfied)

**Table stakes — replacement backend must support all of these:**
- **Cypher query execution** — all graphiti-core ops use Cypher strings
- **FTS on 4 labels** (Entity, Community, Episodic, RelatesToNode_) — called inside `add_episode()` for entity deduplication; missing FTS creates duplicate entities on every add
- **Vector cosine similarity** — used by all 3 `*_similarity_search()` operations
- **Variable-depth graph traversal** — BFS patterns like `RELATES_TO*2..{depth*2}`
- **Embedded / no server** — project design invariant; file paths, no daemon
- **Dual-scope isolation** — two separate DB instances (global + project) open simultaneously
- **Python async API** — graphiti-core is fully async
- **Active maintenance** — non-negotiable given KuzuDB's fate

**Differentiators available in FalkorDB (if fallback chosen):**
- Native relationship FTS → eliminates `RelatesToNode_` intermediate node workaround
- UNWIND support → eliminates per-UUID loop workarounds in reranker queries
- ACID transactions → safer concurrent writes

### Architecture Approach

The `Graphiti(graph_driver=<instance>)` injection point in `graphiti.py` is clean and already used correctly in `src/graph/service.py` line 188. Swapping backends does not touch the `Graphiti` class at all. The migration scope is contained to 5 files + 1 new vendored driver.

**Migration touchpoints:**

| File | Change | Risk |
|------|--------|------|
| `src/storage/ladybug_driver.py` (NEW) | Vendored ~280-line LadybugDriver (copy KuzuDriver + `import lbug`) | LOW |
| `src/storage/graph_manager.py` | Replace `KuzuDriver`, remove 3 workarounds, delete `_create_fts_indices()` | HIGH — most changes |
| `src/graph/service.py` (~L1143, L1185, L1247) | Replace 3 direct `import kuzu` read-only blocks with `driver.execute_query()` | HIGH — invisible to mock tests |
| `src/config/paths.py` | Rename `.kuzu` → `.db` (backend-agnostic); add stale-data startup detection | MEDIUM |
| `pyproject.toml` | Swap kuzu packages | LOW |

**Data migration strategy:** graphiti-core has zero export/import API (`migrations/` is empty). Episodic nodes are the source of truth — entities are derived and re-extracted. Project scope: users can re-run `graphiti index`. Global scope + manually-added episodes: implement `graphiti migrate --from kuzu` CLI command (read Episodic nodes from old Kuzu DB, replay via `add_episode()`). Must ship before the migration removes Kuzu support.

**Build order confirmed:** DB Migration → Multi-Provider LLM → Graph UI Redesign → Local Memory. Storage layer is the lowest dependency; changing it requires re-testing everything above. Stabilize it first.

### Critical Pitfalls

1. **Three direct `import kuzu` calls in `service.py`** — `list_edges_readonly()`, `list_entities_readonly()`, `get_entity_by_uuid_readonly()` bypass the driver abstraction and use Kuzu-specific result iteration (`has_next()`, `get_next()`). The `RelatesToNode_` query pattern is also Kuzu-only (Neo4j/FalkorDB use direct `RELATES_TO` relationships). These are invisible to the mock-based test suite. **Fix: rewrite to `driver.execute_query()` and write integration tests against live DB.**

2. **`_create_fts_indices()` hardcoded to `GraphProvider.KUZU`** — sends Kuzu FTS DDL to the new backend at startup, causing `DatabaseError`. The entire method is dead code after migration. **Fix: delete `_create_fts_indices()` and all call sites as the first change to `graph_manager.py`.**

3. **Rebuild-from-git loses irrecoverable data** — manually-added episodes, pinned entities, access history, and retention scores cannot be recovered. `retention.db` UUID references become orphaned. **Fix: ship `graphiti migrate --from kuzu` before removing Kuzu support; document data loss in release notes.**

4. **Mock-based tests pass but provide zero migration coverage** — `pytest tests/` will pass 100% after migration while `graphiti add "test"` crashes. **Fix: write integration tests with a real backend before changing any application code.**

5. **LadybugDB pre-production + unmerged graphiti-core PR** — v0.15.1 is 5 months old with potential API drift from Kuzu 0.11.3 post-v0.12.0. PR #1296 not merged. If API has diverged silently, tests may pass while queries return wrong data. **Fix: verify the 3 Kuzu workarounds against LadybugDB before committing; fall back to FalkorDB server if PR #1296 not merged when phase starts.**

## Implications for Roadmap

### Phase 12: DB Migration (NEW — must be first)

**Rationale:** All other v2.0 phases depend on a stable storage layer. The three `service.py` kuzu-direct methods break the Graph UI (Phase 14). Local Memory entity resolution depends on FTS quality (Phase 15). LLM Provider work (Phase 13) is fully decoupled from storage and can follow immediately after.

**Delivers:**
- Replace `kuzu==0.11.3` with `real-ladybug>=0.15.1` (or FalkorDB server as fallback)
- All 3 KuzuDB workarounds removed from `graph_manager.py`
- All 3 direct `import kuzu` blocks in `service.py` rewritten to driver-agnostic API
- `graphiti migrate --from kuzu` CLI command for data preservation
- Integration tests against real backend (FTS + vector + add/search/delete)
- Startup warning when stale `graphiti.kuzu` files detected

**Avoids:** Direct kuzu bypass crash (Pitfall 1), FTS DDL startup crash (Pitfall 2), silent data loss (Pitfall 3), mock-test false confidence (Pitfall 4)

**Research flag:** Requires spike at plan start before writing any plan tasks:
1. Check graphiti-core PR #1296 status (merged+released → use official driver; not merged → vendor locally)
2. Install `real-ladybug==0.15.1`; verify 3 KuzuDB workarounds still needed/fixed
3. If LadybugDB fails verification → pivot to FalkorDB server path
Do not write Phase 12 plan tasks until spike resolves the backend choice.

---

### Phase 13: Multi-Provider LLM (renumbered from current 12)

**Rationale:** Fully decoupled from storage layer — `OllamaLLMClient` and adapters do not touch the DB. Can proceed immediately after DB migration is stable. Low regression risk from DB changes.

**Delivers:** `[provider]` section in `llm.toml` for OpenAI/Groq/any OpenAI-compatible endpoint; backward-compatible Ollama; `graphiti health` shows provider + reachability.

**Uses:** openai SDK `base_url` overrides (decided in v1.1 research); PROV-01–04 requirements.

**Research flag:** Standard patterns (decision already locked from v1.1 research). No research-phase needed.

---

### Phase 14: Graph UI Redesign (renumbered from current 13)

**Rationale:** Depends on DB migration completing cleanly — the three `service.py` read-only methods powering the UI are being rewritten in Phase 12. Must come after Phase 12. Medium research need for shadcn/ui + Next.js static export integration patterns.

**Delivers:** shadcn/ui dual-view table + graph replacing react-force-graph-2d.

**Research flag:** Medium research needed — shadcn/ui integration with Next.js static export, SSR guards, and query patterns for the visualization methods against the new backend.

---

### Phase 15: Local Memory System (renumbered from current 14)

**Rationale:** Depends on FTS quality being validated by DB migration (entity deduplication quality is FTS-dependent). The original phase plan explicitly states "Plan 02 implementation must be rewritten for the DB backend chosen in Phase 12" — confirmed dependency on Phase 12 completing first.

**Delivers:** All 6 Claude Code hooks, Ollama summarization, 3-layer progressive disclosure MCP search, SessionStart context injection. MEM-01–05 requirements.

**Research flag:** Medium research needed for observation store schema design and 3-layer MCP progressive disclosure implementation.

---

### Phase Ordering Rationale

- **DB Migration first** — lowest layer; changing it requires re-testing every feature above it. Clearing it early avoids double-testing after each subsequent phase. Also removes the unmaintained KuzuDB C++ dependency (security risk) as early as possible.
- **LLM Provider second** — zero storage dependency; high user value; proceeds unblocked immediately after DB migration stabilizes.
- **Graph UI third** — reads via the service.py methods being fixed in Phase 12; cannot ship correctly until those methods use the new backend's API.
- **Local Memory last** — most complex; depends on FTS quality validated by Phase 12 and DB backend choice finalized.

### Research Flags

Requires spike before planning (not a full research-phase, but mandatory pre-work):
- **Phase 12 (DB Migration):** Spike required: install LadybugDB, check PR #1296, verify workarounds. Backend choice must be resolved before any plan tasks are written.

Needs targeted research-phase before planning:
- **Phase 14 (Graph UI):** shadcn/ui + Next.js static export patterns for the new backend
- **Phase 15 (Local Memory):** Observation store schema, 3-layer MCP progressive disclosure, SessionStart `additionalContext` format

Standard patterns — skip research-phase:
- **Phase 13 (Multi-Provider LLM):** Decision locked from v1.1 research; openai SDK `base_url` overrides are well-documented.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack (package names, versions, availability) | HIGH | Verified against PyPI, installed packages, GitHub issues |
| graphiti-core driver requirements | HIGH | Derived from direct source inspection of installed 0.28.1 |
| LadybugDB API compatibility at v0.15.x | MEDIUM | v0.12.0 guaranteed Kuzu 0.11.3 parity; v0.15.1 may have diverged |
| FalkorDB server mode | HIGH | Built-in driver in 0.28.1; official docs; production-tested |
| FalkorDB Lite FTS/vector in embedded mode | LOW | Unverified; requires empirical spike |
| Architecture integration points | HIGH | All touchpoints verified from installed source code |
| Data migration strategy | HIGH | Confirmed no upstream API; Episodic replay pattern is standard |
| Pitfalls | HIGH | All verified against actual codebase inspection |

**Overall confidence:** HIGH for architecture and pitfalls; MEDIUM for backend selection pending LadybugDB verification spike.

### Gaps to Address

- **LadybugDB PR #1296 status**: Check at Phase 12 planning start. If merged+released: use official driver. If not: vendor locally.
- **LadybugDB workaround parity at v0.15.1**: Empirically verify all 3 workarounds against `real-ladybug==0.15.1` before committing.
- **FalkorDB Lite FTS/vector**: Not verified for embedded mode — if targeted in future milestone, run spike before planning.
- **retention.db UUID remapping**: After migration, old pin UUIDs will not match new entity UUIDs. Either clear `retention.db` at migration time or implement a UUID remapping pass.

## Sources

### Primary (HIGH confidence)
- Installed graphiti-core 0.28.1 at `.venv/lib/python3.12/site-packages/graphiti_core/` — driver inventory, FTS call sites, 50+ provider branches
- Project source: `src/storage/graph_manager.py`, `src/graph/service.py`, `src/config/paths.py` — all integration points verified
- `pip index versions real-ladybug` — v0.15.1 confirmed on PyPI (2026-03-02)
- `pip index versions falkordblite` — v0.9.0 confirmed on PyPI (2026-02-04)
- `pip index versions graphiti-core` — 0.28.1 is latest on PyPI (2026-03-09)

### Secondary (MEDIUM confidence)
- [KuzuDB archived — The Register](https://www.theregister.com/2025/10/14/kuzudb_abandoned/)
- [graphiti issue #1132](https://github.com/getzep/graphiti/issues/1132) — Kuzu archived, LadybugDB request (open 2026-03-09)
- [graphiti issue #1240](https://github.com/getzep/graphiti/issues/1240) — FalkorDB Lite driver (draft PR #1250, open 2026-03-09)
- [graphiti PR #1296](https://github.com/getzep/graphiti/pull/1296) — LadybugDB migration (open 2026-03-09)
- [LadybugDB v0.12.0 release](https://blog.ladybugdb.com/post/ladybug-release/) — "functionally equivalent to Kuzu v0.11.3"
- [FalkorDB FTS docs](https://docs.falkordb.com/cypher/indexing/fulltext-index.html) — native relationship FTS confirmed

### Tertiary (LOW confidence)
- [FalkorDB KuzuDB migration guide](https://www.falkordb.com/blog/kuzudb-to-falkordb-migration/) — migration pattern reference
- [falkordblite GitHub](https://github.com/FalkorDB/falkordblite) — embedded mode architecture (subprocess + Unix socket)

---
*Research completed: 2026-03-09*
*Ready for roadmap: yes — pending LadybugDB verification spike at Phase 12 plan creation*
