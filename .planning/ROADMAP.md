# Roadmap: Graphiti Knowledge Graph

## Milestones

- [x] **v1.0 MVP** — Phases 1–8.9 (shipped 2026-03-01) — see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- [x] **v1.1 Advanced Features** — Phases 9–11.1 (shipped 2026-03-09) — see [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- [ ] **v2.0 Rebuild** — Phases 12–16 (in progress): replace KuzuDB with maintained embedded backend, multi-provider LLM, 4-hook Claude Code memory system with Option C context injection and incremental git indexing, CLI rename to `recall` with 9-command consolidated surface, shadcn/ui graph UI redesign. Execution order: 12 → 13 → 15 → 16 → 14

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

- [x] **Phase 12: DB Migration** — LadybugDB embedded default replaces KuzuDB; Neo4j opt-in via Docker Compose; all 3 Kuzu workarounds removed (completed 2026-03-17)
- [x] **Phase 13: Multi-Provider LLM** — Users can switch LLM providers by editing `llm.toml`; backward compatible with Ollama (completed 2026-03-18)
- [ ] **Phase 14: Graph UI Redesign** — shadcn/ui dual-view table + graph replacing react-force-graph-2d; reads via driver-agnostic API
- [x] **Phase 15: Local Memory System** — 4 Claude Code hook scripts (pure Python), Option C context injection, incremental git indexing; executed before Phase 16 (completed 2026-03-20)
- [x] **Phase 16: Rename & CLI Consolidation** — rename `graphiti` → `recall` (alias `rc`), 9-command public surface, all plumbing hidden; executed after Phase 15, before Phase 14 (completed 2026-03-20)
- [x] **Phase 17: Fix Stale Binary References** — `_GRAPHITI_CLI` → `_RECALL_CLI` in worker.py + mcp_server; MEM-03 docs corrected; test skip reason fixed [Gap Closure] (completed 2026-03-21)
- [x] **Phase 18: Formal Verification — Phases 14 & 16** — produce VERIFICATION.md for P14 and P16; upgrades 11 partial requirements to satisfied [Gap Closure] (completed 2026-03-21)
- [ ] **Phase 19: Wire UI-03 Retention Filter** — add retention_status to API + Entities.tsx filter dropdown [Gap Closure]

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

**Plans**: 5 plans

Plans:
- [ ] 12-01-PLAN.md — Spike + test infrastructure (install real-ladybug, resolve 3 spike questions, rewrite test_storage.py, create stub test files)
- [ ] 12-02-PLAN.md — LadybugDriver + GraphManager + paths + pyproject.toml (vendor driver, delete 3 workarounds, rename .kuzu→.lbdb, swap deps)
- [ ] 12-03-PLAN.md — service.py readonly rewrites (3 import kuzu methods → driver.execute_query())
- [ ] 12-04-PLAN.md — BackendConfig + Neo4j opt-in + health Backend row + Docker Compose + first-run detection
- [ ] 12-05-PLAN.md — Cleanup + integration tests + full suite + human smoke test

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

**Plans**: 3 plans

Plans:
- [ ] 13-01-PLAN.md — [llm] config fields + ProviderClient (LLMConfig llm_* fields, _detect_sdk, validate_provider_startup)
- [ ] 13-02-PLAN.md — Adapter factories + GraphService wiring (make_llm_client, make_embedder)
- [ ] 13-03-PLAN.md — Health rows + CLI startup validation (_check_provider, startup hook, human verify)

---

### Phase 14: Graph UI Redesign

**Goal**: The browser UI displays entities in a dual-view shadcn/ui layout (table + graph), reads data through the driver-agnostic service API, and preserves scope toggle and retention filters from v1.1.
**Depends on**: Phase 12 (service.py read methods must use new backend API before UI can consume them correctly). Executes after Phase 15 in practice — independent of memory system, can run in parallel if capacity allows
**Requirements**: UI-01, UI-02, UI-03, UI-04
**Success Criteria** (what must be TRUE):
  1. User can open `graphiti ui` and switch between a table view (browsable entity list with columns) and a graph view (interactive node/edge visualization) without reloading the page
  2. User can toggle between project scope and global scope in the redesigned UI — entity list and graph update to reflect the selected scope
  3. User can filter the entity list and graph by retention status (pinned, archived, stale) using UI controls — the filter state persists within the session
  4. The UI backend reads all entity data via `GraphService` methods (no direct DB driver calls) — swapping the underlying backend in Phase 12 requires zero UI code changes

**Research flag**: Research complete — see 14-RESEARCH.md and 14-UI-SPEC.md.
**Plans**: 7 plans

Plans:
- [ ] 14-01-PLAN.md — Directory rename .graphiti → .recall + LLMConfig ui_port cleanup (~20 files)
- [ ] 14-02-PLAN.md — New GraphService read-only methods (list_episodes, get_episode_detail, get_time_series_counts, get_top_connected_entities, get_retention_summary)
- [ ] 14-03-PLAN.md — API routes rewrite (4 endpoints) + app.py CORS + tests
- [ ] 14-04-PLAN.md — Vite scaffold + shadcn init + shell layout + route stubs
- [ ] 14-05-PLAN.md — Dashboard tab (9 charts) + Graph tab (Sigma.js WebGL)
- [ ] 14-06-PLAN.md — Entities/Relations/Episodes tabs + DetailPanel (breadcrumb, 3 modes)
- [ ] 14-07-PLAN.md — Search tab + final build + human smoke test

---

### Phase 15: Local Memory System

**Goal**: Four Claude Code hook scripts (pure Python, calling GraphService directly) automatically capture tool call context and inject temporally-aware knowledge before every prompt — entirely local, never blocking the development workflow. Distill CLI (stateless SDK sessions sharing the same DB) is a stretch goal.
**Depends on**: Phase 12 (FTS/vector quality validated on new backend), Phase 13 (Ollama-primary LLM abstraction must be in place for hook path)
**Requirements**: MEM-01, MEM-02, MEM-03, MEM-04, MEM-05
**Success Criteria** (what must be TRUE):
  1. Four hooks fire within their timeout budgets: SessionStart ≤5s (includes `graphiti sync`), UserPromptSubmit ≤6s (hybrid search + context format), PostToolUse fire-and-forget via async queue, PreCompact ≤30s (urgent queue flush before compaction destroys context)
  2. PostToolUse captures Write/Edit/Bash/WebFetch tool calls as graph episodes via the existing async write queue — Ollama entity extraction runs in background, tool execution never blocked
  3. UserPromptSubmit injects context in Option C format: `<session_context>` block containing `<continuity>` (previous session summary) + `<relevant_history>` (temporally-current facts from BM25+semantic+graph retrieval, ≤4000 token budget, priority: recent session facts → recent git facts → older session facts → older git facts)
  4. SessionStart triggers `graphiti sync` (incremental git indexing since last synced commit hash) — skips gracefully if no git repo; registers session in graph
  5. Hooks installed via `graphiti hooks install` — additive only, existing `~/.graphiti/` installs continue working unchanged

**Research flag**: Low — architecture fully designed, context injection format resolved (Option C), hook timeout budgets confirmed. Pure Python hook scripts, no TypeScript or bridge process.
**Plans**: 5 plans

Plans:
- [ ] 15-01-PLAN.md — graphiti sync command + install_global_hooks() foundation (Wave 1)
- [ ] 15-02-PLAN.md — session_start.py + inject_context.py read-path hooks (Wave 2)
- [ ] 15-03-PLAN.md — capture_entry.py + session_stop.py + BackgroundWorker capture_tool_use (Wave 2)
- [ ] 15-04-PLAN.md — graphiti hooks install wiring + graphiti memory search CLI (Wave 3)
- [ ] 15-05-PLAN.md — integration tests + E2E human verification (Wave 4)

---

### Phase 16: Rename & CLI Consolidation

**Goal**: Users interact with the tool as `recall` (alias `rc`) through a clean 10-command public surface — internal plumbing is hidden, the entrypoint communicates what the tool actually does (local developer memory), and every command is maintainable without ripple effects across 18 entrypoints.
**Depends on**: Phase 15 (hook scripts call `graphiti` commands — rename updates them all consistently)
**Requirements**: CLI-01, CLI-02, CLI-03
**Success Criteria** (what must be TRUE):
  1. `recall --help` shows exactly 10 commands: `init`, `search`, `list`, `delete`, `pin`, `unpin`, `health`, `config`, `ui`, `note` — no plumbing commands visible
  2. `recall search "query"` auto-syncs git history (incremental if indexed, full if not) before searching — one command, always works
  3. `recall list <name>` shows entity detail (replaces `show`); `recall list --stale` previews TTL candidates (replaces `stale`)
  4. `recall init` installs hooks globally, registers MCP, runs initial git index, and generates config if missing — one command to set up everything
  5. All hook scripts, MCP server, and internal references updated from `graphiti` → `recall`; alias `rc` works identically

**Research flag**: Low — scope is mechanical renaming + command consolidation; no new architecture.
**Plans**: 4 plans

Plans:
- [ ] 16-01-PLAN.md — Rename entrypoints (recall/rc) + app restructure (10 commands) + init_cmd + note_cmd
- [ ] 16-02-PLAN.md — Expand list command (--stale/--compact/--queue/name) + search auto-sync (CLI-03)
- [ ] 16-03-PLAN.md — Delete 12 removed command files + update hook scripts to use recall binary
- [ ] 16-04-PLAN.md — Phase 16 test suite + human verification checkpoint

---

### Phase 17: Fix Stale Binary References
**Goal:** All `_GRAPHITI_CLI` / `graphiti` binary references updated to `recall`/`_RECALL_CLI` — queue CLI replay unblocked, MCP server runtime restored, Phase 15 verification docs corrected, stale test skip reason removed.
**Requirements:** MEM-02, MEM-03
**Gap Closure:** Closes gaps from audit — Gap 2 (worker.py), Gap 3 (mcp_server), MEM-03 doc, test_backend_config skip

Plans:
- [ ] 17-01-PLAN.md — Fix `_GRAPHITI_CLI` → `_RECALL_CLI` in worker.py + mcp_server/tools.py + mcp_server/context.py; update graphiti_capture to call `note` command
- [ ] 17-02-PLAN.md — Update Phase 15 VERIFICATION.md MEM-03 reference (`graphiti memory search` → `recall search`); fix stale skip reason in test_backend_config.py

---

### Phase 18: Formal Verification — Phases 14 & 16
**Goal:** Produce VERIFICATION.md for Phase 14 (Graph UI Redesign) and Phase 16 (Rename & CLI Consolidation), upgrading 11 requirements from partial to satisfied and clearing the audit blockers.
**Requirements:** UI-01, UI-02, UI-04, CLI-01, CLI-02, CLI-03
**Gap Closure:** Closes audit Gap 1 — missing VERIFICATION.md for phases 14 and 16

Plans:
- [ ] 18-01-PLAN.md — Create scripts/verify_phase_14.py + Phase 14 VERIFICATION.md (UI-01, UI-02, UI-04)
- [ ] 18-02-PLAN.md — Run verify_phase_16.py + produce Phase 16 VERIFICATION.md (CLI-01, CLI-02, CLI-03)

---

### Phase 19: Wire UI-03 Retention Filter
**Goal:** The redesigned Entities view allows users to filter by retention status (pinned/archived/stale) — `retention_status` field added to API response and filter dropdown added to Entities.tsx.
**Requirements:** UI-03
**Gap Closure:** Closes audit Gap 4 — UI-03 partial → satisfied

Plans:
- [x] 19-01-PLAN.md — Add `retention_status` field to `GraphService.list_entities_readonly()` response + `/api/graph` node shape
- [ ] 19-02-PLAN.md — Add retention filter dropdown to `Entities.tsx`; wire filter state to entity list and graph view
- [ ] 19-03-PLAN.md — Integration tests + human smoke test

---

## v2.0 Strategic Direction (updated 2026-03-19)

- **graphiti-core stays.** Entity resolution across time, typed relationship edges (A *caused* B, X *depends on* Y), bi-temporal model, multi-hop graph traversal — these are what make the system genuinely valuable for developers working on long-lived projects.
- **KuzuDB replaced.** Archived Oct 2025. All 3 workarounds in `graph_manager.py` are Kuzu-specific bugs — they disappear with the backend swap.
- **Two-tier backend model.** Embedded default (zero container requirement) + containerized power path (opt-in).
- **Four-hook Claude Code memory system** (Phase 15) — SessionStart (≤5s, incremental git sync), UserPromptSubmit (≤6s, inject context), PostToolUse (fire-and-forget async queue), PreCompact (≤30s urgent flush). Pure Python scripts calling GraphService directly. No TypeScript, no bridge process.
- **Option C context injection format** (Phase 15) — `<session_context>` block: `<continuity>` (previous session summary) + `<relevant_history>` (temporally-current facts via BM25+semantic+graph retrieval). Token budget ≤4000. Priority when tight: recent session facts → recent git facts → older session facts → older git facts.
- **Incremental git indexing** (Phase 15) — `graphiti init` full history, `graphiti sync` delta on SessionStart. Episodes fed oldest-first for correct bi-temporal ordering. Gracefully skips non-git directories.
- **Execution order: 12 → 13 → 15 → 16 → 14** — memory hooks (Phase 15) need LLM abstraction (Phase 13); rename (Phase 16) needs Phase 15 hook scripts to exist before updating them; UI (Phase 14) launches with the final `recall` entrypoint.
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

- **Phase 12 first** — storage layer is the lowest dependency; removing KuzuDB validates FTS/vector quality that Phase 15 memory hooks depend on and fixes `service.py` read methods that Phase 14 UI consumes.
- **Phase 13 second** — zero storage dependency; decoupled from DB; the Ollama-primary LLM abstraction must be in place before Phase 15 hook scripts can be built against it.
- **Phase 15 third** — depends on Phase 12 (FTS quality) and Phase 13 (LLM abstraction); architecture fully designed, low research needed, expected to be fastest phase to execute.
- **Phase 16 fourth** — depends on Phase 15 (hook scripts must exist to be updated); mechanical rename + consolidation; low risk, fast execution.
- **Phase 14 last** — depends on Phase 12 `service.py` rewrites and Phase 16 rename (UI launches with `recall` entrypoint); independent of memory system otherwise.

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
| 12. DB Migration | 5/5 | Complete    | 2026-03-17 | — |
| 13. Multi-Provider LLM | 3/3 | Complete    | 2026-03-18 | — |
| 14. Graph UI Redesign | 6/7 | In Progress|  | — |
| 15. Local Memory System | 5/5 | Complete    | 2026-03-20 | — |
| 16. Rename & CLI Consolidation | 4/4 | Complete   | 2026-03-20 | — |
| 17. Fix Stale Binary References | 2/2 | Complete    | 2026-03-21 | — |
| 18. Formal Verification — Phases 14 & 16 | 2/2 | Complete    | 2026-03-21 | — |
| 19. Wire UI-03 Retention Filter | 0/3 | 1/3 | In Progress|  |
