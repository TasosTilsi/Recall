# Requirements: Graphiti Knowledge Graph

**Defined:** 2026-03-09
**Core Value:** Context continuity without repetition — Claude remembers preferences, decisions, and project architecture across all sessions without repetition, while sensitive data stays out of git through strict security filtering.

## v2.0 Requirements

Requirements for the v2.0 Rebuild milestone. Each maps to a roadmap phase.

### DB Migration

- [x] **DB-01**: User can run `graphiti` with LadybugDB as the embedded default backend (no Docker required) — replaces KuzuDB, removes all 3 `graph_manager.py` workarounds
- [x] **DB-02**: User can opt in to Neo4j via Docker Compose for teams and power users

### Multi-Provider LLM

- [x] **PROV-01**: User can set a `[provider]` section in `llm.toml` to switch to OpenAI, Groq, or any OpenAI-compatible endpoint without code changes
- [x] **PROV-02**: Existing Ollama config works unchanged when no `[provider]` section is present (backward compatibility guaranteed)
- [x] **PROV-03**: `graphiti health` shows the active provider name and reachability status
- [x] **PROV-04**: Provider API key is validated at startup with a clear error if unreachable (not at first use)

### Memory System

- [x] **MEM-01**: All 6 Claude Code hooks (SessionStart, SessionResume, UserPromptSubmit, PostToolUse, Notification, SessionEnd) fire and return within 100ms (fire-and-forget)
- [x] **MEM-02**: Tool observations are compressed by local Ollama into structured summaries and stored in the chosen DB backend
- [x] **MEM-03**: `graphiti memory search <query>` returns results via 3-layer progressive disclosure MCP tools
- [x] **MEM-04**: SessionStart hook injects up to 8K tokens of relevant past observations via `additionalContext`
- [x] **MEM-05**: Memory features are additive — existing installs with no memory data continue working unchanged

### Rename & CLI Consolidation

- [x] **CLI-01**: Tool is invocable as `recall` (primary) and `rc` (alias) — `graphiti` and `gk` entrypoints removed
- [x] **CLI-02**: `recall --help` shows exactly 10 commands: `init`, `search`, `list`, `delete`, `pin`, `unpin`, `health`, `config`, `ui`, `note` — no plumbing commands in public help
- [x] **CLI-03**: `recall search` auto-syncs git history (incremental if previously indexed, full if not) before returning results — works without prior `init`

### Graph UI Redesign

- [x] **UI-01**: User can view entities in a dual-view layout (table view + graph view) — replaces react-force-graph-2d
- [x] **UI-02**: User can toggle between project and global scope in the redesigned UI
- [ ] **UI-03**: User can filter entities by retention status (pinned/archived/stale) in the redesigned UI
- [x] **UI-04**: UI reads entity data via driver-agnostic API (no direct Kuzu reads) — works with any v2.0 backend

## Future Requirements

Features acknowledged but deferred beyond v2.0.

### DB Migration

- **DB-03**: `graphiti migrate --from kuzu` command to export and replay existing Kuzu data — deferred; no real users on KuzuDB to migrate
- **DB-04**: Startup detection of stale `graphiti.kuzu` files with actionable warning — deferred with DB-03

### Multi-Provider LLM

- **PROV-05**: N-provider failover chain (ordered fallback list beyond cloud/local)

### Memory System

- **MEM-06**: Memory deduplication by session_id + content_hash

### Graph UI

- **UI-05**: Real-time streaming updates in the UI (WebSocket)
- **UI-06**: Per-scope retention filter configuration

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-time collaboration | Async git-based sharing; not a multi-user tool |
| Multi-user authentication | Personal developer tool; team sharing through git |
| GraphQL API | MCP protocol is the standard interface |
| Distributed deployment | Local-only; runs on dev machine |
| Mobile apps | Desktop/CLI only |
| Cloud-native architecture | Local-first always |
| LiteLLM abstraction layer | openai SDK `base_url` overrides cover all needed providers with less complexity |
| Data migration tooling (v2.0) | No real users on KuzuDB yet; fresh start acceptable |
| FalkorDB Lite as default backend | FTS/vector in embedded mode unverified; graphiti-core PR #1250 not merged |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DB-01 | Phase 12 | Complete |
| DB-02 | Phase 12 | Complete |
| PROV-01 | Phase 13 | Complete |
| PROV-02 | Phase 13 | Complete |
| PROV-03 | Phase 13 | Complete |
| PROV-04 | Phase 13 | Complete |
| UI-01 | Phase 18 (gap closure) | Pending |
| UI-02 | Phase 18 (gap closure) | Pending |
| UI-03 | Phase 19 (gap closure) | Pending |
| UI-04 | Phase 18 (gap closure) | Pending |
| MEM-01 | Phase 15 | Complete |
| MEM-02 | Phase 17 (gap closure) | Complete |
| MEM-03 | Phase 17 (gap closure) | Complete |
| MEM-04 | Phase 15 | Complete |
| MEM-05 | Phase 15 | Complete |
| CLI-01 | Phase 18 (gap closure) | Pending |
| CLI-02 | Phase 18 (gap closure) | Pending |
| CLI-03 | Phase 18 (gap closure) | Pending |

**Coverage:**
- v2.0 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓
- Pending (gap closure): MEM-02, MEM-03 (Phase 17), UI-01, UI-02, UI-04, CLI-01, CLI-02, CLI-03 (Phase 18), UI-03 (Phase 19)

---
*Requirements defined: 2026-03-09*
*Last updated: 2026-03-21 — Gap closure phases 17–19 assigned; MEM-02, MEM-03, UI-03 reset to Pending; UI-01/02/04, CLI-01/02/03 traceability updated to Phase 18*
