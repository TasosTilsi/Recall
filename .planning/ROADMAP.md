# Roadmap: Graphiti Knowledge Graph

## Milestones

- [x] **v1.0 MVP** — Phases 1–8.9 (shipped 2026-03-01) — see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- [ ] **v1.1 Advanced Features** — Phases 9–12 (in progress)
- [ ] **v2.0 Simplification** — After v1.1 complete: storage migration (sqlite-vec replaces KuzuDB + graphiti-core), complexity audit, cut what doesn't earn its keep

## Phases

<details>
<summary>v1.0 MVP (Phases 1–8.9) — SHIPPED 2026-03-01</summary>

- [x] Phase 1: Storage Foundation (3/3 plans) — completed 2026-02-03
- [x] Phase 2: Security Filtering (5/5 plans) — completed 2026-02-04
- [x] Phase 3: LLM Integration (5/5 plans) — completed 2026-02-08
- [x] Phase 4: CLI Interface (11/11 plans) — completed 2026-02-12
- [x] Phase 5: Background Queue (3/3 plans) — completed 2026-02-13
- [x] Phase 6: Automatic Capture (4/4 plans) — completed 2026-02-13
- [x] Phase 7: Git Integration (5/5 plans) — completed 2026-02-20
- [x] Phase 7.1: Git Indexing Pivot [INSERTED] (4/4 plans) — completed 2026-02-20
- [x] Phase 8: MCP Server (4/4 plans) — completed 2026-02-27
- [x] Phase 8.1: Gap Closure — Verification Files [INSERTED] (2/2 plans) — completed 2026-02-24
- [x] Phase 8.2: Gap Closure — MCP Server Bugs [INSERTED] (2/2 plans) — completed 2026-02-24
- [x] Phase 8.3: Gap Closure — Queue Dispatch [INSERTED] (2/2 plans) — completed 2026-02-24
- [x] Phase 8.4: Gap Closure — Documentation Traceability [INSERTED] (1/1 plan) — completed 2026-02-24
- [x] Phase 8.5: Gap Closure — Human Runtime Verification [INSERTED] (2/2 plans) — completed 2026-02-24
- [x] Phase 8.6: Gap Closure — Runtime Bug Fixes [INSERTED] (2/2 plans) — completed 2026-02-27
- [x] Phase 8.7: Gap Closure — Hook Security Gaps [INSERTED] (3/3 plans) — completed 2026-02-27
- [x] Phase 8.8: Gap Closure — Verification Documentation [INSERTED] (2/2 plans) — completed 2026-03-01
- [x] Phase 8.9: Gap Closure — Integration Wiring Fixes [INSERTED] (2/2 plans) — completed 2026-03-01

See [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) for full phase details.

</details>

### v1.1 Advanced Features (Phases 9–12)

- [x] **Phase 9: Smart Retention** — TTL-based expiry with access-frequency reinforcement scoring, pin/unpin protection, stale preview before deletion (completed 2026-03-06)
- [ ] **Phase 10: Configurable Capture Modes** — Named capture modes (decisions-only vs decisions-and-patterns) selectable via llm.toml with unconditional security gate
- [ ] **Phase 11: Graph UI** — `graphiti ui` command for localhost graph visualization with scope selection (visualization approach TBD — discuss before planning)
- [ ] **Phase 12: Multi-Provider LLM** — Provider factory pattern enabling OpenAI, Groq, and any OpenAI-compatible endpoint via llm.toml without code changes
  > Phases 11 & 12 have zero code overlap — can run in parallel after Phase 10

## Phase Details

### Phase 9: Smart Retention
**Goal**: Users can manage knowledge freshness — stale knowledge expires automatically, frequently-accessed knowledge persists longer, and critical knowledge is pinned permanently.
**Depends on**: Phase 8 (graph service and CLI foundation)
**Requirements**: RETN-01, RETN-02, RETN-03, RETN-04, RETN-05, RETN-06
**Success Criteria** (what must be TRUE):
  1. User can run `graphiti stale` to see a list of nodes that would be deleted before any deletion occurs
  2. User can run `graphiti compact --expire` to delete nodes older than `retention_days` (default 90) with no dangling edges left behind
  3. User can set `[retention] retention_days = N` in `llm.toml` and the next retention sweep respects that value
  4. User can run `graphiti pin <uuid>` to protect a node — it does not appear in `graphiti stale` output and is not deleted by `compact --expire`
  5. User can run `graphiti unpin <uuid>` to remove pin protection — the node becomes eligible for TTL expiry again
**Plans**: 5 plans

Plans:
- [ ] 09-01-PLAN.md — RetentionManager module + LLMConfig retention_days
- [ ] 09-02-PLAN.md — GraphService: list_stale, archive_nodes, record_access
- [ ] 09-03-PLAN.md — stale command + compact --expire flag
- [ ] 09-04-PLAN.md — pin/unpin commands + MCP stale tool
- [ ] 09-05-PLAN.md — CLI wiring, show access hook, integration tests + human checkpoint

### Phase 10: Configurable Capture Modes
**Goal**: Users can control what the capture system records — narrow (decisions and architecture only) or broad (decisions, patterns, bugs, dependencies) — and see the active mode at a glance.
**Depends on**: Phase 9 (stable retention infrastructure before adding capture parameterization)
**Requirements**: CAPT-01, CAPT-02, CAPT-03
**Success Criteria** (what must be TRUE):
  1. User can set `[capture] mode = "decisions-only"` in `llm.toml` and subsequent captures record only decisions and architectural choices
  2. User can set `[capture] mode = "decisions-and-patterns"` in `llm.toml` and subsequent captures also record bugs, patterns, and dependencies
  3. User can run `graphiti config show` and see the active capture mode clearly labeled in the output
  4. Security sanitization runs before any mode-based filtering regardless of which mode is active (secrets are never captured in any mode)
**Plans**: 3 plans

Plans:
- [ ] 10-01-PLAN.md — Test scaffold (failing stubs for all CAPT-01/02/03 test cases)
- [ ] 10-02-PLAN.md — Core: LLMConfig.capture_mode + dual prompt constants + summarizer param threading
- [ ] 10-03-PLAN.md — Wire: CLI config display + call site wiring in git_worker + conversation

### Phase 11: Graph UI
**Goal**: Users can visually explore their knowledge graph in a browser — seeing entity nodes and relationship edges — launched from the CLI with scope selection.
**Depends on**: Phase 10 (stable capture pipeline before exposing visualization)
**Requirements**: UI-01, UI-02, UI-03
**Success Criteria** (what must be TRUE):
  1. User can run `graphiti ui` and a browser opens to `http://localhost:8000` showing the project-scope knowledge graph
  2. The Kuzu database is mounted read-only — the UI cannot modify graph content
  3. User can run `graphiti ui --global` to visualize the global scope graph instead of the project scope
  4. `graphiti ui` fails with a clear error message if required dependencies are missing, rather than hanging silently
**Plans**: TBD

### Phase 12: Multi-Provider LLM
**Goal**: Users can switch LLM providers (OpenAI, Groq, any OpenAI-compatible endpoint) by editing `llm.toml` — no code changes required — with clear startup feedback on provider reachability.
**Depends on**: Phase 10 (no code overlap with Phase 11 — can run in parallel)
**Requirements**: PROV-01, PROV-02, PROV-03, PROV-04
**Success Criteria** (what must be TRUE):
  1. User can add a `[provider]` section to `llm.toml` specifying `type = "openai"`, `base_url`, and `api_key`, and all graph operations use that provider without restarting
  2. An existing `llm.toml` without a `[provider]` section continues to work with Ollama exactly as before (backward compatibility guaranteed)
  3. `graphiti health` shows the active provider name and whether it is reachable
  4. If the configured provider API key is invalid or the endpoint is unreachable, `graphiti health` reports the error at startup rather than failing silently at first use
**Plans**: TBD

---

## v2.0 Simplification (After v1.1 Complete)

**Goal:** Reassess what earned its complexity after shipping v1.1. Replace the archived KuzuDB + graphiti-core stack with a maintained, minimal alternative. Keep what is genuinely valuable; cut what is infrastructure serving infrastructure.

**Trigger:** Begin planning only after Phase 12 (Multi-Provider LLM) is verified complete.

### Strategic questions to answer at planning time

- What from v1.1 proved genuinely useful in daily use vs theoretically useful?
- Is the async queue + retention system worth maintaining, or is simpler fire-and-forget enough?
- Does multi-provider LLM (Phase 12) justify its complexity once used in practice?

### Likely scope (TBD — audit v1.1 first)

- **Storage migration**: replace `graphiti-core` + KuzuDB (archived Oct 2025) with a maintained alternative (see options below). Eliminates all 6 existing workarounds.
- **Simplification audit**: identify and remove over-engineered subsystems that don't justify their maintenance cost
- **Optional (containerized path)**: Neo4j via Podman for users who want richer Cypher queries — opt-in, not the default

### Database options evaluated

#### Option A — LadybugDB (recommended starting point)
Community-driven fork of KuzuDB by ex-Facebook/Google engineers. Direct 1:1 drop-in replacement for Kuzu — same Cypher dialect, same embedded columnar architecture. Migration cost would be lowest: swap the driver, remove our 3 KuzuDB workarounds.
- **Embedded**: yes — lives in-process, no server
- **Vector search**: yes — inherited from Kuzu architecture
- **Graph semantics**: full property graph, typed tables
- **Maintenance**: active, community-funded, investor interest confirmed
- **Migration cost**: low — near drop-in for our KuzuDriver
- **Source**: [github.com/LadybugDB/ladybug](https://github.com/LadybugDB/ladybug)

#### Option B — FalkorDBLite
Embedded Python graph DB running as an isolated subprocess (Unix socket, no network overhead). Actively maintained — v0.8.0 released Feb 2026. Requires Python 3.12+. Full Cypher support. There is already an open issue in graphiti-core to add FalkorDB Lite as a backend ([#1240](https://github.com/getzep/graphiti/issues/1240)) — if that lands, migration could be nearly zero-cost.
- **Embedded**: yes — isolated subprocess, Unix socket
- **Vector search**: yes — via parent FalkorDB
- **Graph semantics**: full property graph + Cypher
- **Maintenance**: active (FalkorDB team, commercial backing)
- **Migration cost**: low-medium — depends on graphiti-core issue #1240 landing
- **Source**: [github.com/FalkorDB/falkordblite](https://github.com/FalkorDB/falkordblite)

#### Option C — sqlite-vec + custom graph tables
Replace the graph DB entirely. Store entity nodes and relationship edges as plain SQLite tables; use sqlite-vec extension for vector similarity (KNN, SIMD-accelerated, pure C, zero dependencies). Requires reimplementing the graph query layer ourselves — more work but eliminates graphiti-core dependency entirely.
- **Embedded**: yes — SQLite is already our sidecar DB
- **Vector search**: yes — sqlite-vec, production-ready, runs anywhere SQLite runs
- **Graph semantics**: manual — SQL tables for nodes/edges, Python for traversal
- **Maintenance**: sqlite-vec is actively maintained; SQLite itself is indefinitely stable
- **Migration cost**: high — must replace graphiti-core graph operations
- **Best if**: v2.0 simplification audit concludes graphiti-core adds more complexity than value
- **Source**: [github.com/asg017/sqlite-vec](https://github.com/asg017/sqlite-vec)

#### Option D — Neo4j via Podman (containerized, opt-in)
Full production-grade graph DB. Richest Cypher support, mature Python SDK (`neo4j-graphrag-python`), best tooling. Requires Podman or Docker runtime — not zero-dependency. Appropriate as an opt-in for power users, not the default.
- **Embedded**: no — runs as a container (Podman/Docker)
- **Vector search**: yes — native in Neo4j 5.23+
- **Graph semantics**: best-in-class, full Cypher, APOC plugins
- **Maintenance**: commercial, indefinitely stable
- **Migration cost**: medium — Python SDK is clean, but requires container runtime on target machine
- **Best if**: user explicitly wants richer graph queries and is comfortable with containers
- **Source**: [neo4j.com](https://neo4j.com) / `podman pull neo4j:latest`

### Decision framework for v2.0

| Priority | Recommendation |
|----------|---------------|
| Lowest migration cost | Option A (LadybugDB) — near drop-in for KuzuDriver |
| Zero new dependencies | Option C (sqlite-vec) — but requires reimplementing graph layer |
| Best graph semantics, containerized | Option D (Neo4j + Podman) — opt-in only |
| Watch closely | Option B (FalkorDBLite) — if graphiti-core #1240 merges before v2.0 planning |

### What stays regardless

- CLI entrypoints (`graphiti` / `gk`)
- Git post-commit hook + Claude Code conversation hook
- MCP server (11 tools — core value delivery mechanism)
- Security filtering layer (non-negotiable)
- Dual-scope graphs (global + per-project)

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Storage Foundation | v1.0 | 3/3 | Complete | 2026-02-03 |
| 2. Security Filtering | v1.0 | 5/5 | Complete | 2026-02-04 |
| 3. LLM Integration | v1.0 | 5/5 | Complete | 2026-02-08 |
| 4. CLI Interface | v1.0 | 11/11 | Complete | 2026-02-12 |
| 5. Background Queue | v1.0 | 3/3 | Complete | 2026-02-13 |
| 6. Automatic Capture | v1.0 | 4/4 | Complete | 2026-02-13 |
| 7. Git Integration | v1.0 | 5/5 | Complete | 2026-02-20 |
| 7.1. Git Indexing Pivot | v1.0 | 4/4 | Complete | 2026-02-20 |
| 8. MCP Server | v1.0 | 4/4 | Complete | 2026-02-27 |
| 8.1–8.9. Gap Closures | v1.0 | 16/16 | Complete | 2026-03-01 |
| 9. Smart Retention | 5/5 | Complete   | 2026-03-06 | — |
| 10. Configurable Capture Modes | v1.1 | 0/3 | Planned | — |
| 11. Graph UI | v1.1 | 0/TBD | Not started | — |
| 12. Multi-Provider LLM | v1.1 | 0/TBD | Not started | — |
