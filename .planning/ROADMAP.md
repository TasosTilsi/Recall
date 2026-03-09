# Roadmap: Graphiti Knowledge Graph

## Milestones

- [x] **v1.0 MVP** — Phases 1–8.9 (shipped 2026-03-01) — see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- [x] **v1.1 Advanced Features** — Phases 9–11.1 (shipped 2026-03-09) — see [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- [ ] **v2.0 Rebuild** — Phases 12–14 (planning): keep graphiti-core, replace KuzuDB with maintained backend, full Claude Code hook lifecycle with session-start context injection, progressive disclosure MCP search

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

### v2.0 Rebuild (Phases 12–14)

- [ ] **Phase 12: Multi-Provider LLM** — Users can switch LLM providers by editing `llm.toml`; backward compatible with Ollama
- [ ] **Phase 13: Graph UI Redesign** — shadcn/ui dual-view table + graph replacing react-force-graph-2d
- [ ] **Phase 14: Local Memory System** — 6-hook Claude Code lifecycle, session-start context injection, Ollama summarization, progressive disclosure MCP search

## Phase Details

### Phase 12: Multi-Provider LLM
**Goal**: Users can switch LLM providers (OpenAI, Groq, any OpenAI-compatible endpoint) by editing `llm.toml` — no code changes required — with clear startup feedback on provider reachability.
**Depends on**: v1.1 complete
**Requirements**: PROV-01, PROV-02, PROV-03, PROV-04
**Success Criteria** (what must be TRUE):
  1. User can add a `[provider]` section to `llm.toml` specifying `type = "openai"`, `base_url`, and `api_key`, and all graph operations use that provider without restarting
  2. An existing `llm.toml` without a `[provider]` section continues to work with Ollama exactly as before (backward compatibility guaranteed)
  3. `graphiti health` shows the active provider name and whether it is reachable
  4. If the configured provider API key is invalid or the endpoint is unreachable, `graphiti health` reports the error at startup rather than failing silently at first use
**Plans**: TBD

### Phase 13: Graph UI Redesign — shadcn/ui dual-view table and graph

**Goal:** Replace react-force-graph-2d with a shadcn/ui dual-view layout: table view for browsing entities and graph view for visualizing relationships. Scope toggle and retention filters carry over from v1.1.
**Requirements**: TBD
**Depends on:** Phase 12
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 13 to break down)

---

### Phase 14: Local Memory System

**Goal:** Users get persistent session memory — Claude Code captures every hook event (tool use, session start/end, prompts) into a local observation store and automatically injects relevant past context at session start. No external APIs; 100% local Ollama processing.
**Depends on:** Phase 12 (DB backend decided — memory storage layer must use the chosen backend's search APIs, not Kuzu-specific FTS/HNSW)
**Requirements**: MEM-01, MEM-02, MEM-03, MEM-04, MEM-05
**Success Criteria** (what must be TRUE):
  1. All 6 Claude Code hooks fire and return within 100ms (fire-and-forget — hook never blocks on storage or LLM)
  2. Tool observations are compressed by local Ollama into structured summaries (request / investigated / learned / completed / next_steps) and stored in the chosen DB backend
  3. `graphiti memory search <query>` returns results using the 3-layer progressive disclosure pattern via MCP tools
  4. When a new Claude Code session starts, the SessionStart hook injects up to 8K tokens of relevant past observations via `additionalContext` so Claude arrives with project context
  5. An existing `~/.graphiti/` install with no memory data continues to work — memory features are additive, not breaking
**Source plans:** Adapted from `10-local-memory` ghost phase (planned but never wired into roadmap). Plan 02 implementation must be rewritten for the DB backend chosen in Phase 12.
**Plans:** 5 plans

Plans:
- [ ] 14-01-PLAN.md — Expand Claude Code hook infrastructure: all 6 lifecycle handlers + observation queue (fire-and-forget, <100ms)
- [ ] 14-02-PLAN.md — Backend-agnostic observation store + search: FTS keyword, semantic vector, 3-layer progressive disclosure (implement for chosen Phase 12 backend)
- [ ] 14-03-PLAN.md — Ollama local summarization: structured XML prompt → observation summary → store (no external API calls)
- [ ] 14-04-PLAN.md — SessionStart context injection: load relevant observations + format as `additionalContext` JSON + MCP `memory_get_context` tool
- [ ] 14-05-PLAN.md — Integration tests + human verification: full lifecycle from hook fire → queue → store → search → injection

---

## v2.0 Strategic Direction (locked 2026-03-08)

- **graphiti-core stays.** Entity resolution across time, typed relationship edges (A *caused* B, X *depends on* Y), bi-temporal model, multi-hop graph traversal — these are what make the system genuinely valuable for teams working on legacy codebases.
- **KuzuDB replaced.** Archived Oct 2025. All 3 workarounds in `graph_manager.py` are Kuzu-specific bugs — they disappear with the backend swap.
- **Two-tier backend model.** Embedded default (zero container requirement) + containerized power path (opt-in).
- **Full Claude Code hook lifecycle.** All 6 hooks with fire-and-forget queue pattern. SessionStart injects relevant past memories via `additionalContext`. Non-blocking; hooks must return in <100ms.
- **Local observation storage + Ollama summarization** (Phase 14) — tool observations compressed into structured summaries by local Ollama. Stored in a backend-agnostic memory layer (uses the DB backend chosen in Phase 12). Deduplication by session_id + content_hash.
- **Progressive disclosure MCP search** (Phase 14) — 3-layer pattern: `memory_search` → compact index, `memory_timeline` → chronological context, `memory_details` → full observation by ID.
- **Web viewer** — `graphiti ui` launched in Phase 11. ✓
- **Docker Compose** — single-file for Neo4j power path.
- **Git history bootstrap stays.** `graphiti index` is the unique differentiator. Non-negotiable.

### Backend Options

#### Default — LadybugDB (embedded, no container)
Community-driven KuzuDB fork. Same Cypher dialect. Near drop-in for `KuzuDriver` — swapping removes all 3 workarounds.
- **Risk**: spike needed to confirm no new workarounds surface
- **Source**: [github.com/LadybugDB/ladybug](https://github.com/LadybugDB/ladybug)

#### Power path — Neo4j via Docker/Podman (opt-in)
graphiti-core's primary backend. Richest Cypher, native vector search (5.23+). Requires container runtime.
- **Best for**: teams, enterprise, users who want full Cypher + APOC plugins

#### Watch — FalkorDB Lite
Embedded Python graph DB with full Cypher. graphiti-core #1240 open. If merged, becomes strong default path candidate.

### Strategic Questions for v2.0 Planning Kickoff

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
| 11. Graph UI | v1.1 | 5/5 | Complete | 2026-03-08 |
| 11.1. Gap Closure — Graph UI Retention Wiring | v1.1 | commits-only | Complete | 2026-03-09 |
| 12. Multi-Provider LLM | v2.0 | 0/TBD | Not started | — |
| 13. Graph UI Redesign | v2.0 | 0/TBD | Not started | — |
| 14. Local Memory System | v2.0 | 0/5 | Not started | — |
