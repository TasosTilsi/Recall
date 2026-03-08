# Roadmap: Graphiti Knowledge Graph

## Milestones

- [x] **v1.0 MVP** — Phases 1–8.9 (shipped 2026-03-01) — see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- [ ] **v1.1 Advanced Features** — Phases 9–11 (in progress)
- [ ] **v2.0 Rebuild** — After v1.1 complete: keep graphiti-core (graph engine justified by enterprise use case), replace KuzuDB with maintained backend, add claude-mem-inspired live capture and UX layer

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

### v1.1 Advanced Features (Phases 9–11)

- [x] **Phase 9: Smart Retention** — TTL-based expiry with access-frequency reinforcement scoring, pin/unpin protection, stale preview before deletion (completed 2026-03-06)
- [x] **Phase 10: Configurable Capture Modes** — Named capture modes (decisions-only vs decisions-and-patterns) selectable via llm.toml with unconditional security gate (completed 2026-03-08)
- [ ] **Phase 11: Graph UI** — `graphiti ui` command for localhost graph visualization with scope selection (visualization approach TBD — discuss before planning)

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
**Plans**: 4 plans

Plans:
- [ ] 10-01-PLAN.md — Test scaffold (failing stubs for all CAPT-01/02/03 test cases)
- [ ] 10-02-PLAN.md — Core: LLMConfig.capture_mode + dual prompt constants + summarizer param threading
- [ ] 10-03-PLAN.md — Wire: CLI config display + call site wiring in git_worker + conversation
- [ ] 10-04-PLAN.md — Wire: indexer extraction pipeline — mode-aware FREE_FORM_EXTRACTION_PROMPT in extraction.py + capture_mode threading through GitIndexer.run()

### Phase 11: Graph UI
**Goal**: Users can visually explore their knowledge graph in a browser — seeing entity nodes and relationship edges — launched from the CLI with scope selection.
**Depends on**: Phase 10 (stable capture pipeline before exposing visualization)
**Requirements**: UI-01, UI-02, UI-03
**Success Criteria** (what must be TRUE):
  1. User can run `graphiti ui` and visit `http://localhost:8765` to see the project-scope knowledge graph (FastAPI + Next.js static export, no Docker)
  2. The Kuzu database is opened read-only — the UI cannot modify graph content
  3. User can run `graphiti ui --global` to visualize the global scope graph instead of the project scope; in-UI scope toggle switches without restarting
  4. `graphiti ui` fails with a clear error message if the port is already in use or if `ui/out/` static files are missing
**Plans**: 5 plans

Plans:
- [ ] 11-01-PLAN.md — RED test scaffold: tests/test_ui_command.py + tests/test_ui_server.py (8 failing tests)
- [ ] 11-02-PLAN.md — Python backend: LLMConfig [ui] section + GraphService.list_edges() + src/ui_server/ package
- [ ] 11-03-PLAN.md — Next.js frontend: ui/ directory with react-force-graph-2d, static build committed to git
- [ ] 11-04-PLAN.md — Wire: src/cli/commands/ui.py + CLI registration + pyproject.toml deps (turns 8 tests GREEN)
- [ ] 11-05-PLAN.md — Human checkpoint: live browser verification of graph rendering, scope toggle, sidebar

---

## v2.0 Rebuild (After v1.1 Complete)

**Goal:** Keep graphiti-core's graph engine — entity resolution, typed relationship edges, multi-hop traversal. These capabilities are the system's ceiling for enterprise and legacy codebase use cases and justify the dependency. Replace only KuzuDB (archived Oct 2025) with a maintained backend. Add a claude-mem-inspired live capture and UX layer on top of the same graph core.

**Trigger:** Begin planning only after Phase 11 (Graph UI) is verified complete.

**Strategic direction (locked 2026-03-08):**

- **graphiti-core stays.** Entity resolution across time, typed relationship edges (A *caused* B, X *depends on* Y), bi-temporal model, multi-hop graph traversal — these are what make the system genuinely valuable for teams working on legacy codebases, not just solo developers. The graph model enables questions flat vector search cannot answer.
- **KuzuDB replaced.** Archived Oct 2025. All 3 workarounds in `graph_manager.py` are Kuzu-specific bugs — they disappear with the backend swap.
- **Two-tier backend model.** Embedded default (zero container requirement) + containerized power path (opt-in). Most users get a zero-infrastructure install; power users and teams get Neo4j via Docker Compose.
- **claude-mem-inspired UX layer.** PostToolUse hook for real-time capture, progressive disclosure MCP search (3-layer: index → timeline → full entity), web viewer for live graph introspection.
- **Async pipeline preserved.** LLM calls and graph writes stay async. The latency lives in Ollama, not the DB layer. No change to the concurrency model.
- **Git history bootstrap stays.** `graphiti index` is the unique differentiator — no other tool in this space builds a knowledge scaffold from commit history. Non-negotiable.

### Phase 12: Multi-Provider LLM (moved from v1.1)
**Goal**: Users can switch LLM providers (OpenAI, Groq, any OpenAI-compatible endpoint) by editing `llm.toml` — no code changes required — with clear startup feedback on provider reachability.
**Depends on**: v1.1 complete
**Requirements**: PROV-01, PROV-02, PROV-03, PROV-04
**Success Criteria** (what must be TRUE):
  1. User can add a `[provider]` section to `llm.toml` specifying `type = "openai"`, `base_url`, and `api_key`, and all graph operations use that provider without restarting
  2. An existing `llm.toml` without a `[provider]` section continues to work with Ollama exactly as before (backward compatibility guaranteed)
  3. `graphiti health` shows the active provider name and whether it is reachable
  4. If the configured provider API key is invalid or the endpoint is unreachable, `graphiti health` reports the error at startup rather than failing silently at first use
**Plans**: TBD

### Backend options

#### Default path — LadybugDB (embedded, no container)
Community-driven fork of KuzuDB by ex-Facebook/Google engineers. Same Cypher dialect, same embedded columnar architecture. Near drop-in replacement for our `KuzuDriver` — swapping it removes all 3 Kuzu workarounds.
- **Embedded**: yes — in-process, no server
- **graphiti-core compatible**: yes — slots into the existing Kuzu provider path
- **Maintenance**: active, community-funded
- **Migration cost**: low — swap driver, delete workarounds
- **Risk**: needs a spike to confirm no new workarounds surface
- **Source**: [github.com/LadybugDB/ladybug](https://github.com/LadybugDB/ladybug)

#### Power path — Neo4j via Docker/Podman (opt-in, containerized)
graphiti-core's primary and best-tested backend. Richest Cypher support, native vector search (5.23+), mature tooling. Requires container runtime — appropriate as opt-in for teams and enterprise users.
- **Embedded**: no — Docker Compose, single `docker compose up`
- **graphiti-core compatible**: yes — native/primary backend, zero workarounds
- **Maintenance**: commercial, indefinitely stable
- **Migration cost**: medium — requires container runtime on target machine
- **Best for**: teams, enterprise, users who want full Cypher + APOC plugins
- **Source**: [neo4j.com](https://neo4j.com)

#### Watch — FalkorDB Lite
Embedded Python graph DB with full Cypher. Open issue in graphiti-core ([#1240](https://github.com/getzep/graphiti/issues/1240)) to add it as a backend. If merged before v2.0 planning, migration cost drops to near-zero and it becomes a strong default path candidate.

### New features for v2.0

**PostToolUse hook capture** — observe every significant tool call (file writes, bash runs, test results) in real time, not just at session end. Fire-and-forget, async, non-blocking. Richer signal than conversation-only capture.

**Progressive disclosure MCP search** — 3-layer pattern:
1. `search` → compact entity index (~50–100 tokens)
2. `timeline` → chronological context for filtered results
3. `get_entity` → full detail only for final targets (~500–1000 tokens)

**Web viewer** — `graphiti ui` launches a localhost browser view of the live knowledge graph with scope selection. Read-only. (Phase 11 may deliver this — coordinate at planning time.)

**Docker Compose** — single-file `docker-compose.yml` for the Neo4j power path. `docker compose up` brings the full stack. Default embedded path needs zero containers.

### What stays regardless

- CLI entrypoints (`graphiti` / `gk`)
- graphiti-core graph engine (entity resolution, typed edges, bi-temporal model)
- Git post-commit hook + Claude Code conversation hook
- `graphiti index` — git history bootstrap (unique differentiator)
- MCP server and all existing tools
- Security filtering layer (non-negotiable, runs before everything)
- Dual-scope graphs (global + per-project)
- Async pipeline for LLM calls and graph writes

### Strategic questions to answer at v2.0 planning kickoff

- What from v1.1 proved genuinely useful in daily practice vs theoretically useful?
- LadybugDB spike: does it slot into graphiti-core's Kuzu provider without new workarounds?
- FalkorDB Lite graphiti-core #1240: merged yet? If so, evaluate as default path.
- Is the async queue + retention system worth its complexity, or can it be simplified?

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
| 9. Smart Retention | v1.1 | 5/5 | Complete | 2026-03-06 |
| 10. Configurable Capture Modes | v1.1 | 4/4 | Complete | 2026-03-08 |
| 11. Graph UI | 4/5 | In Progress|  | — |
| 12. Multi-Provider LLM | v2.0 | 0/TBD | Not started | — |
