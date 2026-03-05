# Requirements: Graphiti Knowledge Graph

**Defined:** 2026-03-01
**Core Value:** Context continuity without repetition — Claude remembers your preferences, decisions, and project architecture across all sessions without you stating them again, while sensitive data stays out of git through strict security filtering.

## v1.1 Requirements

Requirements for the v1.1 Advanced Features milestone. Each maps to roadmap phases 9–12.

### Smart Retention

- [ ] **RETN-01**: User can run `graphiti compact --expire` to delete nodes older than the configured `retention_days` (default 90 days)
- [ ] **RETN-02**: User can run `graphiti stale` to preview which nodes would be deleted by a retention sweep before committing to deletion
- [x] **RETN-03**: User can set `[retention] retention_days` in `llm.toml` to configure the TTL for knowledge expiry
- [ ] **RETN-04**: User can run `graphiti pin <uuid>` to protect a node from TTL expiry indefinitely
- [ ] **RETN-05**: User can run `graphiti unpin <uuid>` to remove expiry protection from a pinned node
- [x] **RETN-06**: Retention sweep tracks `last_accessed_at` and `access_count` via SQLite sidecar; frequently-accessed nodes receive extended effective TTL (reinforcement scoring)

### Capture Modes

- [ ] **CAPT-01**: User can set `[capture] mode = "decisions-only"` in `llm.toml` to capture only decisions and architectural choices (narrow — current implicit default behavior)
- [ ] **CAPT-02**: User can set `[capture] mode = "decisions-and-patterns"` in `llm.toml` to capture broader patterns, bugs, and dependencies alongside decisions
- [ ] **CAPT-03**: User can see the active capture mode in `graphiti config show` output

### Graph UI

- [ ] **UI-01**: User can run `graphiti ui` to launch a localhost graph browser (Docker Kuzu Explorer at `http://localhost:8000`)
- [ ] **UI-02**: `graphiti ui` mounts the scope-appropriate Kuzu DB read-only and opens the browser automatically on launch
- [ ] **UI-03**: User can choose global vs. project scope when launching `graphiti ui`

### Multi-Provider LLM

- [ ] **PROV-01**: User can set a `[provider]` section in `llm.toml` to switch to OpenAI, Groq, or any OpenAI-compatible endpoint without code changes
- [ ] **PROV-02**: Existing Ollama config works unchanged when no `[provider]` section is present (backward compatibility guaranteed)
- [ ] **PROV-03**: `graphiti health` shows the active provider name and its reachability status
- [ ] **PROV-04**: Provider API key is validated at startup (not at first use), with a clear error message if the provider is unreachable

## v2+ Requirements

Deferred — acknowledged but not in the current roadmap.

### Retention

- **RETN-07**: RL-based importance scoring (needs 6+ months of access pattern data to train on)
- **RETN-08**: Per-scope retention policy (independent `retention_days` for global vs. project graphs)

### Capture

- **CAPT-04**: Per-scope capture mode config (global vs. project mode independently configurable)

### UI

- **UI-04**: Monitoring dashboard tab with capture stats, queue depth, entity count over time (Streamlit)
- **UI-05**: Real-time streaming updates in the UI (WebSocket — complexity without proportional value at this scale)

### Multi-Provider

- **PROV-05**: N-provider failover chain (ordered fallback list: try OpenAI, fall back to Groq, fall back to local)
- **PROV-06**: Cost-aware provider routing (requires per-task cost modeling — premature for v1.1)
- **PROV-07**: Anthropic native SDK adapter (Anthropic is reachable via OpenAI SDK `base_url` compatibility for v1.1; native SDK deferred)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Inline graph editing from UI | UI must be strictly read-only — editing bypasses the CLI security layer |
| Silent automatic deletion without preview | Users lose trust when knowledge disappears without warning; `graphiti stale` preview is required |
| LiteLLM dependency | 170MB+, 800+ open issues, proxy-server architecture — disproportionate for a local dev tool |
| Third "silent" capture mode | Indistinguishable from broken hooks; `hooks_enabled = false` already handles silent capture |
| Force-directed graph layout as default | Unreadable above ~80 nodes; hierarchical layout required |
| graphiti-core upgrade beyond 0.28.1 | Three existing workarounds in adapters.py and graph_manager.py are version-specific; KuzuDB archived October 2025 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| RETN-01 | Phase 9 | Pending |
| RETN-02 | Phase 9 | Pending |
| RETN-03 | Phase 9 | Complete |
| RETN-04 | Phase 9 | Pending |
| RETN-05 | Phase 9 | Pending |
| RETN-06 | Phase 9 | Complete |
| CAPT-01 | Phase 10 | Pending |
| CAPT-02 | Phase 10 | Pending |
| CAPT-03 | Phase 10 | Pending |
| UI-01 | Phase 11 | Pending |
| UI-02 | Phase 11 | Pending |
| UI-03 | Phase 11 | Pending |
| PROV-01 | Phase 12 | Pending |
| PROV-02 | Phase 12 | Pending |
| PROV-03 | Phase 12 | Pending |
| PROV-04 | Phase 12 | Pending |

**Coverage:**
- v1.1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0

---
*Requirements defined: 2026-03-01*
*Last updated: 2026-03-01 — roadmap phases 9–12 created with success criteria*
