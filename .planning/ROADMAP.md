# Roadmap: Graphiti Knowledge Graph

## Milestones

- [x] **v1.0 MVP** — Phases 1–8.9 (shipped 2026-03-01) — see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- [x] **v1.1 Advanced Features** — Phases 9–11.1 (shipped 2026-03-09) — see [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- [x] **v2.0 Rebuild** — Phases 12–24 (completed 2026-04-07): replace KuzuDB with maintained embedded backend, multi-provider LLM, 4-hook Claude Code memory system with Option C context injection and incremental git indexing, CLI rename to `recall` with 9-command consolidated surface, shadcn/ui graph UI redesign. Gap closure: Phases 22–24.
- [ ] **v3.0 Engineering Knowledge Graph** — Phases 25–33 (in progress): major pivot — remove graphiti-core/LadybugDB/hooks/queue/retention; rebuild on SQLite + FTS5 + backlinks; single LLM provider; Claude plugin + two skills; clean 6-command CLI surface.

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

<details>
<summary>✅ v2.0 Rebuild (Phases 12–24) — SHIPPED 2026-04-07</summary>

- [x] Phase 12: DB Migration (5/5 plans) — completed 2026-03-17
- [x] Phase 13: Multi-Provider LLM (3/3 plans) — completed 2026-03-18
- [x] Phase 14: Graph UI Redesign (7/7 plans) — completed 2026-03-21
- [x] Phase 15: Local Memory System (5/5 plans) — completed 2026-03-20
- [x] Phase 16: Rename & CLI Consolidation (4/4 plans) — completed 2026-03-20
- [x] Phase 17: Fix Stale Binary References [Gap Closure] (2/2 plans) — completed 2026-03-21
- [x] Phase 18: Formal Verification — Phases 14 & 16 [Gap Closure] (2/2 plans) — completed 2026-03-21
- [x] Phase 19: Wire UI-03 Retention Filter [Gap Closure] (3/3 plans) — completed 2026-03-28
- [x] Phase 20: Fast Indexing via Claude CLI + Batch + FTS (5/5 plans) — completed 2026-04-02
- [x] Phase 21: Knowledge Quality Uplift (3/3 plans) — completed 2026-04-03
- [x] Phase 22: Complete UI-03 — EntityPanel + P19 Verification [Gap Closure] (3/3 plans) — completed 2026-04-03
- [x] Phase 23: Nyquist Compliance Sweep [Gap Closure] (3/3 plans) — completed 2026-04-05
- [x] Phase 24: v2.0 Audit Gap Closure [Gap Closure] (3/3 plans) — completed 2026-04-07

See [milestones/v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md) for full phase details.

</details>

<details open>
<summary>v3.0 Engineering Knowledge Graph (Phases 25–33) — IN PROGRESS</summary>

- [ ] **Phase 25: Teardown** - Remove all legacy components and restructure to the new module layout
- [ ] **Phase 26: DB Schema** - SQLite schema with FTS5, backlinks table, and optional embeddings table
- [ ] **Phase 27: LLM Provider** - Single-provider LLM client with claude/ollama/openai support and health reporting
- [ ] **Phase 28: Git Extractor + Indexer** - Batch LLM extraction from git history with init and sync modes
- [ ] **Phase 29: CLI Commands** - Six-command CLI surface wired to the new stack
- [ ] **Phase 30: MCP Server** - Read-only stdio MCP server with six knowledge tools
- [ ] **Phase 31: UI Adaptation** - Update graph explorer to the new SQLite-backed API and six entity types
- [ ] **Phase 32: Claude Plugin + Skills** - Plugin manifest, skill definitions, and installation mechanism
- [ ] **Phase 33: Integration + Packaging** - pipx packaging, end-to-end smoke test, and final polish

</details>

## Phase Details

### Phase 25: Teardown
**Goal**: The legacy codebase is gone and the new module layout is in place — no imports of removed code compile
**Depends on**: Nothing (first phase of v3.0)
**Requirements**: ARCH-01, ARCH-02, ARCH-03
**Success Criteria** (what must be TRUE):
  1. Running `python -c "import src"` produces no import errors from hooks, queue, retention, or ladybug modules
  2. `pyproject.toml` has no `graphiti-core` or `real-ladybug` entries; `pip install -e .` succeeds cleanly
  3. Directory tree shows exactly: `src/db/`, `src/extractor/`, `src/indexer/`, `src/cli/`, `src/mcp_server/`, `src/ui_server/`, `src/config.py` — no other legacy top-level modules
  4. `recall --help` loads without errors (even if subcommands are stubs)
**Plans**: TBD

### Phase 26: DB Schema
**Goal**: The SQLite database schema is fully defined and tested — all tables, indexes, constraints, and the optional embeddings table are in place and accept real data
**Depends on**: Phase 25
**Requirements**: KG-01, KG-02, KG-03, KG-04, KG-05
**Success Criteria** (what must be TRUE):
  1. A freshly created database contains tables: `commits`, `entities`, `backlinks`, `metadata`; inserting a row in each succeeds without error
  2. Inserting an entity with an invalid `type` (e.g. `"unknown"`) raises a constraint error; all six valid types (`decision`, `bug_fix`, `pattern`, `file`, `concept`, `tech_debt`) insert without error
  3. Inserting backlink `A → B` automatically creates the inverse `B → A` row with an inverse label; querying backlinks of `B` returns the inserted relationship
  4. `SELECT * FROM entities_fts WHERE entities_fts MATCH 'authentication'` returns ranked rows matching text in `name` or `content`
  5. When `[embeddings]` is present in config the `embeddings` table exists after DB init; when absent the table is not created
**Plans**: TBD

### Phase 27: LLM Provider
**Goal**: The LLM client reads a single provider from config, sends requests, and reports health — no fallback logic exists anywhere in the codebase
**Depends on**: Phase 26
**Requirements**: LLM-01, LLM-02, LLM-03, LLM-04
**Success Criteria** (what must be TRUE):
  1. Setting `provider = "claude"`, `"ollama"`, or `"openai"` in `~/.recall/config.toml` routes all LLM calls through that provider only; switching provider requires only a config edit
  2. When the configured provider is unreachable, the failing command exits with an error message naming the provider and URL — no silent fallback or retry occurs
  3. `recall health` prints provider name, model, and either `OK` or `UNREACHABLE` within 5 seconds
  4. `recall health` prints a separate line reporting whether embeddings are configured and reachable (or `not configured`)
**Plans**: TBD

### Phase 28: Git Extractor + Indexer
**Goal**: Running `recall init` or `recall sync` fully populates the database with structured knowledge extracted from git history via batched LLM calls
**Depends on**: Phase 26, Phase 27
**Requirements**: IDX-01, IDX-02, IDX-03, IDX-04, IDX-05
**Success Criteria** (what must be TRUE):
  1. `recall init` on a repo with 50+ commits deletes and repopulates the database; re-running `recall init` produces the same entity count (deterministic upsert)
  2. `recall sync` on a previously indexed repo processes only commits newer than `last_indexed_sha`; running it twice with no new commits prints "0 commits to process"
  3. `recall sync` on a repo with no existing database automatically runs a full init and completes without prompting the user
  4. After indexing a real repo, the `entities` table contains rows covering all six types; no entity `name` value has leading/trailing whitespace or uppercase letters
  5. Indexing progress logs show batch boundaries (e.g. "Processing commits 1–10 of 200"); the process completes without crash on a 200-commit repo
**Plans**: TBD

### Phase 29: CLI Commands
**Goal**: All six public CLI commands are wired to the new stack and produce correct output for both normal operation and error cases
**Depends on**: Phase 26, Phase 27, Phase 28
**Requirements**: CLI-01, CLI-02, CLI-03
**Success Criteria** (what must be TRUE):
  1. `recall --help` lists exactly six commands: `init`, `sync`, `search`, `health`, `config`, `ui`; legacy commands (`note`, `pin`, `unpin`, `delete`, `list`) do not appear
  2. `recall search "authentication"` returns results showing entity type, name, content snippet, commit sha, and date; `recall search "authentication" --semantic` returns vector results when embeddings are configured and prints an actionable error when they are not
  3. `recall search "authentication" --related` outputs one hop of backlinked entities below each primary result, each labeled with the relationship type
**Plans**: TBD

### Phase 30: MCP Server
**Goal**: `recall mcp serve` starts a fully working stdio MCP server that Claude can query with all six read-only knowledge tools
**Depends on**: Phase 26, Phase 28, Phase 29
**Requirements**: MCP-01, MCP-02
**Success Criteria** (what must be TRUE):
  1. A Claude session with the MCP server configured can successfully call all six tools (`search_knowledge`, `get_entity`, `get_backlinks`, `get_decisions`, `get_bugs`, `get_patterns`) and receive valid JSON responses
  2. Running `recall mcp serve` and sending it input produces no output on stdout except valid MCP protocol frames; all diagnostic log lines appear only on stderr
**Plans**: TBD

### Phase 31: UI Adaptation
**Goal**: The graph explorer loads against the new SQLite-backed API, renders all six entity types with distinct colors, and the detail panel shows backlink context
**Depends on**: Phase 26, Phase 28, Phase 29
**Requirements**: UI-01, UI-02, UI-03, UI-04
**Success Criteria** (what must be TRUE):
  1. `recall ui` opens the graph explorer in a browser with no console errors referencing `episodes`, `edge_count`, or `retention_status`
  2. Nodes in the graph view are colored by entity type; all six types appear in the legend with distinct colors
  3. Selecting one or more types in the entity type filter hides all nodes of unselected types from the graph view
  4. Clicking any node opens a detail panel showing: name, type, tags, source commit sha, content, and all backlinks with relationship label and context snippet
**Plans**: TBD
**UI hint**: yes

### Phase 32: Claude Plugin + Skills
**Goal**: Installing the plugin registers the MCP server and both skills in Claude; skills guide a user through setup and indexing from scratch
**Depends on**: Phase 27, Phase 28, Phase 29, Phase 30
**Requirements**: SKILL-01, SKILL-02, INST-02, INST-03
**Success Criteria** (what must be TRUE):
  1. After plugin install, typing `/recall-setup` in Claude launches an interactive walkthrough that writes `~/.recall/config.toml` and confirms `recall health` passes
  2. After plugin install, typing `/recall-index` in Claude runs `recall sync` (or `recall init` if no DB exists), then reports commit count processed and entity type breakdown
  3. Plugin install writes the MCP server entry (`recall mcp serve`) into `~/.claude/settings.json` under `mcpServers`
  4. Plugin install creates `~/.recall/` directory if it does not exist; an existing `~/.recall/config.toml` is left unchanged
**Plans**: TBD

### Phase 33: Integration + Packaging
**Goal**: `pipx install recall-kg` works on a clean machine and the full init → search → serve workflow passes end-to-end
**Depends on**: Phase 25, Phase 26, Phase 27, Phase 28, Phase 29, Phase 30, Phase 31, Phase 32
**Requirements**: INST-01
**Success Criteria** (what must be TRUE):
  1. On a machine with only Python and pipx, `pipx install recall-kg` completes without error and `recall --help` prints the six-command help text
  2. `pip install -e .` in a fresh venv installs all required dependencies without conflicts; `pytest tests/` passes with no failures
  3. Running `recall init`, then `recall search "fix"`, then `recall mcp serve` (10-second smoke test) all succeed sequentially in a single terminal session
**Plans**: TBD

---

## Progress

| Milestone | Phases | Plans | Status |
|-----------|--------|-------|--------|
| v1.0 MVP | 1–8.9 | 60 | ✅ Shipped 2026-03-01 |
| v1.1 Advanced Features | 9–11.1 | 14 | ✅ Shipped 2026-03-09 |
| v2.0 Rebuild | 12–24 | 48 | ✅ Shipped 2026-04-07 |
| v3.0 Engineering Knowledge Graph | 25–33 | TBD | In progress |

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 25. Teardown | 0/? | Not started | - |
| 26. DB Schema | 0/? | Not started | - |
| 27. LLM Provider | 0/? | Not started | - |
| 28. Git Extractor + Indexer | 0/? | Not started | - |
| 29. CLI Commands | 0/? | Not started | - |
| 30. MCP Server | 0/? | Not started | - |
| 31. UI Adaptation | 0/? | Not started | - |
| 32. Claude Plugin + Skills | 0/? | Not started | - |
| 33. Integration + Packaging | 0/? | Not started | - |

*Full phase details for each milestone: see `.planning/milestones/`*
