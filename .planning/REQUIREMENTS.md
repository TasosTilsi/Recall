# Requirements — v3.0 Engineering Knowledge Graph

**Milestone:** v3.0 Engineering Knowledge Graph
**Status:** Active
**Created:** 2026-04-14

---

## v3.0 Requirements

### ARCH — Architecture Cleanup

- [x] **ARCH-01**: All session-capture components are removed — hooks directory, queue worker, retention manager, global graph, and all related CLI commands (`note`, `list --stale`, `pin`, `unpin`, `delete`)
- [x] **ARCH-02**: graphiti-core and real-ladybug dependencies are removed from pyproject.toml and all imports; vendored LadybugDriver deleted
- [ ] **ARCH-03**: Codebase is restructured to the new layout: `src/db/`, `src/extractor/`, `src/indexer/`, `src/cli/`, `src/mcp_server/`, `src/ui_server/`, `src/config.py` — no legacy module names remain

### KG — Knowledge Graph Schema

- [ ] **KG-01**: SQLite database has four tables: `commits` (sha, message, author, date, files_changed), `entities` (id, type, name, content, commit_sha, tags, created_at), `backlinks` (from_id, to_id, relationship, context), and `metadata` (key, value)
- [ ] **KG-02**: Entity `type` field supports exactly six values: `decision`, `bug_fix`, `pattern`, `file`, `concept`, `tech_debt`
- [ ] **KG-03**: Every backlink is stored bidirectionally — inserting a relationship `A → B` also creates `B → A` with an inverse label; each backlink stores a `context` snippet from the commit
- [ ] **KG-04**: An FTS5 virtual table indexes `entities.name` and `entities.content` and supports ranked keyword search
- [ ] **KG-05**: An optional `embeddings` table stores `(entity_id, vector BLOB)` using sqlite-vec; the table is created only when `[embeddings]` is present in config

### IDX — Indexer

- [x] **IDX-01**: `recall init` rebuilds the knowledge graph from scratch — deletes and recreates the SQLite database, then walks entire git history oldest-first
- [x] **IDX-02**: `recall sync` processes only commits since `last_indexed_sha` stored in the `metadata` table; if no database exists, `recall sync` runs a full init automatically and silently
- [x] **IDX-03**: Commits are processed in configurable batches (default 10 per LLM call); the batch size is set via `[indexer] batch_size` in config
- [ ] **IDX-04**: Each LLM extraction call receives a batch of commit messages + diffs and returns structured JSON with: decisions + rationale, bug fixes + root cause + symptom, patterns + conventions, files changed + co-change pairs, tech debt items with "why this burden exists" context
- [ ] **IDX-05**: Entity names are normalized before insertion (lowercase, stripped) to collapse duplicates across commits — same file path or concept name maps to the same entity row via upsert

### LLM — Provider Configuration

- [ ] **LLM-01**: Exactly one LLM provider is active at a time — `provider` field in `[llm]` accepts `claude`, `ollama`, or `openai`; there are no fallback chains; if the provider is unreachable, the command fails with a clear error
- [ ] **LLM-02**: `[llm]` section in `~/.recall/config.toml` has fields: `provider`, `model`, `base_url` (optional for claude), `api_key` (optional for ollama); all OpenRouter/OpenAI-compatible endpoints work via `provider = "openai"` + custom `base_url`
- [ ] **LLM-03**: `[embeddings]` section is optional; when present it has: `provider`, `model`, `base_url`; when absent, semantic search is disabled and sqlite-vec table is not created
- [ ] **LLM-04**: `recall health` reports: provider name, model, reachability (OK / UNREACHABLE), and whether embeddings are configured

### CLI — Commands

- [ ] **CLI-01**: `recall` exposes exactly six public commands: `init`, `sync`, `search`, `health`, `config`, `ui`; `recall mcp serve` is a hidden sub-command
- [ ] **CLI-02**: `recall search <query>` performs FTS keyword search by default; `--semantic` flag enables vector similarity search (requires `[embeddings]` config); results show entity type, name, content snippet, commit sha, and date
- [ ] **CLI-03**: `recall search` output optionally includes related entities via backlink traversal when `--related` flag is passed, showing one hop of backlinks with relationship labels

### MCP — Read-Only Server

- [ ] **MCP-01**: `recall mcp serve` starts a stdio MCP server with six read-only tools: `search_knowledge` (FTS query), `get_entity` (by id or name), `get_backlinks` (traverse one or more hops), `get_decisions` (filter type=decision), `get_bugs` (filter type=bug_fix), `get_patterns` (filter type=pattern)
- [ ] **MCP-02**: The MCP server never writes to stdout outside the MCP protocol — all logging goes to stderr; tool responses are JSON

### UI — Graph Explorer

- [ ] **UI-01**: The existing shadcn/Sigma.js UI is adapted to query the new SQLite-backed REST API; all references to graphiti-core data shapes (episodes, edge_count, retention_status) are removed
- [ ] **UI-02**: Graph view renders entities as nodes and backlinks as directed edges; node color encodes entity type using the six-type palette
- [ ] **UI-03**: Entity type filter (multi-select) in the graph toolbar narrows visible nodes to selected types
- [ ] **UI-04**: Clicking any node opens a detail panel showing: entity name, type, tags, source commit, content, and all backlinks with relationship labels and context snippets

### INST — Installation

- [ ] **INST-01**: `pipx install recall-kg` (or `pip install -e .`) installs the `recall` CLI globally and makes `recall --help` work
- [ ] **INST-02**: The repository includes a `claude-plugin.json` manifest (or equivalent) that, when installed as a Claude plugin, registers the two skills and the MCP server (`recall mcp serve`) in `~/.claude/settings.json`
- [ ] **INST-03**: Plugin install creates `~/.recall/` directory structure if it does not exist; it does not overwrite an existing `config.toml`

### SKILL — Claude Skills

- [ ] **SKILL-01**: `/recall-setup` skill guides the user through: choosing an LLM provider, entering credentials, writing `~/.recall/config.toml`, running `recall health` to verify, and optionally running `recall init` on the current repo
- [ ] **SKILL-02**: `/recall-index` skill runs `recall sync` on the current repo (or `recall init` if no DB exists), reports how many commits were processed, and summarizes what types of entities were extracted

---

## Future Requirements (deferred)

- Multi-repo aggregation — single graph spanning multiple repos
- PR/issue body extraction — pull decisions from PR descriptions and issue comments
- Branch awareness — tag entities with branch name at extraction time
- Team sharing — shared SQLite via git LFS or sync service
- Incremental re-extraction — re-run extraction on existing commits when extraction prompt is updated
- BGE reranking — cross-encoder reranking for higher-quality semantic results

---

## Out of Scope

- **Session capture** — hooks, queue, context injection: claude-mem handles this; recall does not
- **Global graph (~/.recall/global/)** — removed; per-project only
- **Retention / TTL / pin-unpin** — not needed without session capture
- **Neo4j backend** — removed; SQLite is the only backend
- **Fallback LLM chains** — single provider per config; no automatic failover
- **Real-time capture** — git history only; no live session recording
- **GraphQL API** — MCP protocol is the interface standard
- **Mobile / cloud deployment** — local CLI tool, always

---

## Traceability

<!-- Filled by roadmapper -->

| REQ-ID | Phase | Status |
|--------|-------|--------|
| ARCH-01 | Phase 25 | Complete (25-01) |
| ARCH-02 | Phase 25 | Complete (25-01) |
| ARCH-03 | Phase 25 | Pending |
| KG-01 | Phase 26 | Pending |
| KG-02 | Phase 26 | Pending |
| KG-03 | Phase 26 | Pending |
| KG-04 | Phase 26 | Pending |
| KG-05 | Phase 26 | Pending |
| IDX-01 | Phase 28 | Complete |
| IDX-02 | Phase 28 | Complete |
| IDX-03 | Phase 28 | Complete |
| IDX-04 | Phase 28 | Pending |
| IDX-05 | Phase 28 | Pending |
| LLM-01 | Phase 27 | Pending |
| LLM-02 | Phase 27 | Pending |
| LLM-03 | Phase 27 | Pending |
| LLM-04 | Phase 27 | Pending |
| CLI-01 | Phase 29 | Pending |
| CLI-02 | Phase 29 | Pending |
| CLI-03 | Phase 29 | Pending |
| MCP-01 | Phase 30 | Pending |
| MCP-02 | Phase 30 | Pending |
| UI-01 | Phase 31 | Pending |
| UI-02 | Phase 31 | Pending |
| UI-03 | Phase 31 | Pending |
| UI-04 | Phase 31 | Pending |
| INST-01 | Phase 33 | Pending |
| INST-02 | Phase 32 | Pending |
| INST-03 | Phase 32 | Pending |
| SKILL-01 | Phase 32 | Pending |
| SKILL-02 | Phase 32 | Pending |
