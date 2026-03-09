# Roadmap: Graphiti Knowledge Graph

## Milestones

- [x] **v1.0 MVP** — Phases 1–8.9 (shipped 2026-03-01) — see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- [x] **v1.1 Advanced Features** — Phases 9–11.1 (shipped 2026-03-09) — see [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- [ ] **v2.0 Rebuild** — Phases 12–15 (in progress): replace KuzuDB with maintained embedded backend, multi-provider LLM, shadcn/ui graph UI redesign, full Claude Code hook lifecycle with session-start context injection and progressive disclosure MCP search

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
- [x] Phase 8.1–8.9: Gap Closures [INSERTED] (16/16 plans) — completed 2026-03-01

See [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) for full phase details.

</details>

<details>
<summary>v1.1 Advanced Features (Phases 9–11.1) — SHIPPED 2026-03-09</summary>

- [x] Phase 9: Smart Retention (5/5 plans) — completed 2026-03-06
- [x] Phase 10: Configurable Capture Modes (4/4 plans) — completed 2026-03-08
- [x] Phase 11: Graph UI (5/5 plans) — completed 2026-03-08
- [x] Phase 11.1: Gap Closure — Graph UI Retention Wiring [INSERTED] (commits-only) — completed 2026-03-09

See [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md) for full phase details.

</details>

### v2.0 Rebuild (Phases 12–15)

- [ ] **Phase 12: DB Migration** — LadybugDB embedded default replaces KuzuDB; Neo4j opt-in via Docker Compose; all 3 Kuzu workarounds removed
- [ ] **Phase 13: Multi-Provider LLM** — Users can switch LLM providers by editing `llm.toml`; backward compatible with Ollama
- [ ] **Phase 14: Graph UI Redesign** — shadcn/ui dual-view table + graph replacing react-force-graph-2d; reads via driver-agnostic API
- [ ] **Phase 15: Local Memory System** — 6-hook Claude Code lifecycle, session-start context injection, Ollama summarization, progressive disclosure MCP search

## Phase Details

### Phase 12: DB Migration

**Goal**: The system runs on a maintained embedded graph backend (LadybugDB default, Neo4j opt-in) — KuzuDB removed, all 3 workarounds gone, all existing features work identically.
**Depends on**: v1.1 complete
**Requirements**: DB-01, DB-02
**Success Criteria** (what must be TRUE):
  1. User can run `graphiti add`, `graphiti search`, and `graphiti index` with no Docker or external process — LadybugDB stores data at the same dual-scope paths (`.graphiti/` and `~/.graphiti/global/`)
  2. User can opt in to Neo4j by setting `[backend] type = "neo4j"` in `llm.toml` and running `docker compose up` — all graph operations route to Neo4j without code changes
  3. The three Kuzu-specific workarounds in `graph_manager.py` (`_database` attr patch, `_create_fts_indices()` call, `create_batch()` loop) are deleted — no workaround comments remain
  4. FTS entity deduplication works correctly with the new backend — adding the same entity twice in `graphiti add` resolves to one node, not two
  5. All existing integration tests pass and new backend-specific integration tests cover add/search/delete/FTS against a real (non-mocked) DB instance

**Research flag**: Phase plan MUST start with a spike — install `real-ladybug==0.15.1`, check PR #1296 status, verify 3 workarounds against LadybugDB. Backend choice resolves during planning, not execution.
**Plans**: TBD

---

### Phase 13: Multi-Provider LLM

**Goal**: Users can switch LLM providers (OpenAI, Groq, any OpenAI-compatible endpoint) by editing `llm.toml` — no code changes required — with clear startup feedback on provider reachability.
**Depends on**: Phase 12
**Requirements**: PROV-01, PROV-02, PROV-03, PROV-04
**Success Criteria** (what must be TRUE):
  1. User can add a `[provider]` section to `llm.toml` specifying `type`, `base_url`, and `api_key`, and all graph operations use that provider without restarting
  2. An existing `llm.toml` without a `[provider]` section continues to work with Ollama exactly as before — no migration step required
  3. `graphiti health` shows the active provider name (e.g., "openai via api.openai.com" or "ollama local") and whether the endpoint is reachable
  4. If the configured provider API key is invalid or the endpoint is unreachable, `graphiti` reports the error at startup — not silently at the time of first graph operation

**Plans**: TBD

---

### Phase 14: Graph UI Redesign

**Goal**: The browser UI displays entities in a dual-view shadcn/ui layout (table + graph), reads data through the driver-agnostic service API, and preserves scope toggle and retention filters from v1.1.
**Depends on**: Phase 12 (service.py read methods must use new backend API before UI can consume them correctly)
**Requirements**: UI-01, UI-02, UI-03, UI-04
**Success Criteria** (what must be TRUE):
  1. User can open `graphiti ui` and switch between a table view (browsable entity list with columns) and a graph view (interactive node/edge visualization) without reloading the page
  2. User can toggle between project scope and global scope in the redesigned UI — entity list and graph update to reflect the selected scope
  3. User can filter the entity list and graph by retention status (pinned, archived, stale) using UI controls — the filter state persists within the session
  4. The UI backend reads all entity data via `GraphService` methods (no direct DB driver calls) — swapping the underlying backend in Phase 12 requires zero UI code changes

**Research flag**: Medium research needed — shadcn/ui integration with Next.js static export, SSR guards for graph libraries, and query patterns against the new backend API.
**Plans**: TBD

---

### Phase 15: Local Memory System

**Goal**: Claude Code captures all 6 hook lifecycle events into a local observation store, compresses them with Ollama, and injects relevant past context at session start — entirely local, never blocking the development workflow.
**Depends on**: Phase 12 (observation store uses the chosen DB backend's FTS/vector APIs; FTS quality validated in Phase 12 integration tests)
**Requirements**: MEM-01, MEM-02, MEM-03, MEM-04, MEM-05
**Success Criteria** (what must be TRUE):
  1. All 6 Claude Code hooks (SessionStart, SessionResume, UserPromptSubmit, PostToolUse, Notification, SessionEnd) fire and return within 100ms — no hook blocks on storage, LLM calls, or network
  2. Tool observations are compressed by local Ollama into structured summaries (request / investigated / learned / completed / next_steps fields) and stored in the chosen DB backend
  3. `graphiti memory search <query>` returns relevant results via 3-layer progressive disclosure: compact index first (`memory_search`), chronological context on demand (`memory_timeline`), full observation by ID (`memory_details`)
  4. When a new Claude Code session starts, the SessionStart hook injects up to 8K tokens of relevant past observations via `additionalContext` — Claude arrives with project context without the user repeating it
  5. An existing `~/.graphiti/` install with no memory data continues working unchanged — memory features add new paths, never modify existing ones

**Research flag**: Medium research needed — observation store schema design, 3-layer MCP progressive disclosure implementation patterns, SessionStart `additionalContext` format constraints.
**Plans**: TBD

---

## v2.0 Strategic Direction (locked 2026-03-09)

- **graphiti-core stays.** Entity resolution across time, typed relationship edges (A *caused* B, X *depends on* Y), bi-temporal model, multi-hop graph traversal — these are what make the system genuinely valuable for developers working on long-lived projects.
- **KuzuDB replaced.** Archived Oct 2025. All 3 workarounds in `graph_manager.py` are Kuzu-specific bugs — they disappear with the backend swap.
- **Two-tier backend model.** Embedded default (zero container requirement) + containerized power path (opt-in).
- **Full Claude Code hook lifecycle.** All 6 hooks with fire-and-forget queue pattern. SessionStart injects relevant past memories via `additionalContext`. Non-blocking; hooks must return in <100ms.
- **Local observation storage + Ollama summarization** (Phase 15) — tool observations compressed into structured summaries by local Ollama. Stored in a backend-agnostic memory layer (uses the DB backend chosen in Phase 12).
- **Progressive disclosure MCP search** (Phase 15) — 3-layer pattern: `memory_search` → compact index, `memory_timeline` → chronological context, `memory_details` → full observation by ID.
- **Web viewer redesign** — `graphiti ui` redesigned in Phase 14 with shadcn/ui dual-view replacing react-force-graph-2d.
- **Docker Compose** — single-file for Neo4j power path (Phase 12 opt-in).
- **Git history bootstrap stays.** `graphiti index` is the unique differentiator. Non-negotiable.

### Backend Options

#### Default — LadybugDB (embedded, no container)
Community-driven KuzuDB fork. Same Cypher dialect. Near drop-in for `KuzuDriver` — swapping removes all 3 workarounds.
- **Risk**: spike needed to confirm no new workarounds surface at v0.15.1
- **Source**: [github.com/LadybugDB/ladybug](https://github.com/LadybugDB/ladybug)
- **graphiti-core PR**: #1296 (open as of 2026-03-09 — vendor locally if unmerged)

#### Power path — Neo4j via Docker/Podman (opt-in)
graphiti-core's primary backend. Richest Cypher, native vector search (5.23+). Requires container runtime.
- **Best for**: teams, enterprise, users who want full Cypher + APOC plugins

#### Watch — FalkorDB Lite
Embedded Python graph DB with full Cypher. graphiti-core #1240 open. FTS/vector in embedded mode unverified. Not targeted for v2.0.

### Build Order Rationale

- **Phase 12 first** — storage layer is the lowest dependency; removing KuzuDB unblocks the `service.py` read methods that Phase 14 UI consumes and validates FTS quality that Phase 15 memory depends on.
- **Phase 13 second** — zero storage dependency; decoupled from DB; high user value; proceeds immediately after DB stabilizes.
- **Phase 14 third** — depends on Phase 12 `service.py` rewrites; UI reads via the fixed driver-agnostic methods.
- **Phase 15 last** — most complex; depends on FTS quality (Phase 12) and backend choice finalized.

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
| 11. Graph UI | v1.1 | 5/5 | Complete | 2026-03-08 |
| 11.1. Gap Closure — Graph UI Retention Wiring | v1.1 | commits-only | Complete | 2026-03-09 |
| 12. DB Migration | v2.0 | 0/TBD | Not started | — |
| 13. Multi-Provider LLM | v2.0 | 0/TBD | Not started | — |
| 14. Graph UI Redesign | v2.0 | 0/TBD | Not started | — |
| 15. Local Memory System | v2.0 | 0/TBD | Not started | — |
