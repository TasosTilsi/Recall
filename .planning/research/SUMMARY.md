# Project Research Summary

**Project:** graphiti-knowledge-graph v1.1 Advanced Features
**Domain:** Local-first knowledge graph CLI — developer productivity tool
**Researched:** 2026-03-01
**Confidence:** HIGH (architecture and pitfalls), MEDIUM-HIGH (features), MEDIUM (some version pinning)

## Executive Summary

The graphiti-knowledge-graph v1.1 milestone extends a shipped v1.0 MVP with four independent but interrelated feature areas: smart retention (TTL + reinforcement scoring), configurable capture modes (decisions-only vs. decisions-and-patterns), a localhost graph visualization UI, and multi-provider LLM support. The recommended approach treats each feature as an additive extension to the existing architecture rather than a refactor — the v1.0 service layer, CLI, and adapters are preserved intact, with new capabilities added via new modules (`src/retention/`, `src/llm/providers/`) and targeted modifications to existing files (`service.py`, `summarizer.py`, `client.py`). The ordering is dictated by dependency complexity: retention and capture modes are low-risk additions with no breaking changes, the UI is a new surface that avoids existing code paths, and multi-provider LLM is the highest-regression-risk change due to its refactoring of the core `client.py` provider chain.

The key architectural constraint that runs across all four features is the graphiti-core `EntityNode` schema limitation: nodes have no `last_accessed_at`, `access_count`, or TTL fields. This means retention metadata must live in a SQLite sidecar (`~/.graphiti/retention.db`), not in the graph database. Similarly, Kuzu's archived status (KuzuDB archived October 2025) means the `graphiti-core[kuzu]==0.28.1` pin must be held firm throughout v1.1; dependency resolver conflicts during the multi-provider phase are the most likely way this pin gets accidentally broken. Both of these architectural facts must be treated as non-negotiable constraints, not implementation details to revisit.

The most critical risk across the milestone is the interaction between the TTL retention sweep and the background queue: a retention run that deletes an entity while a queued capture job references it will produce dangling episodic nodes. The mitigation is a pessimistic deletion window (subtract `queue_item_ttl_hours` from the cutoff date), implemented from day one in Phase 9. A secondary risk is security regression if capture mode selection is implemented before sanitization rather than after — the existing security gate must remain unconditional regardless of capture mode.

## Key Findings

### Recommended Stack

The v1.0 stack is unchanged. v1.1 adds five packages across three optional dependency groups, keeping the core install lean for existing users. The most important decision is to reject LiteLLM (170MB+, 40+ transitive deps, proxy-server architecture) in favor of the `openai` Python SDK 2.x with `base_url` overrides — this single package covers OpenAI, Groq, LM Studio, vLLM, and any OpenAI-compatible endpoint. A critical pre-Phase-12 step is verifying whether graphiti-core 0.28.1 already pins an incompatible `openai` version internally; if it pins openai 1.x, `openai>=1.50.0,<2.0.0` must be used instead.

For the graph UI, the research recommends a hybrid: use the official `kuzudb/explorer` Docker image for graph visualization (zero custom UI code, launches with one `docker run` command) and defer a custom FastAPI/Streamlit dashboard to Phase 12. APScheduler 3.x (pinned `<4.0`) handles periodic retention sweeps in-process; the 3.x-to-4.x API break is a documented incompatibility that requires an explicit version pin.

**Core technologies (new additions for v1.1):**
- `apscheduler>=3.10.4,<4.0` (core dep): In-process scheduler for TTL sweeps — lightweight, uses existing asyncio event loop, no broker required. Pin strictly to `<4.0`; the v4 API is a complete rewrite.
- `pyvis==0.3.2` + `networkx>=3.3` + `streamlit>=1.42.0` (optional `[ui]` group): pyvis wraps vis.js for graph HTML, streamlit serves it — simpler than FastAPI + Dash for a developer tool.
- `openai>=2.0.0` (optional `[providers]` group): covers OpenAI, Groq, and OpenAI-compatible endpoints via `base_url`. CRITICAL: verify compatibility with graphiti-core's internal openai pin before adding.

**Do NOT add:** LiteLLM, APScheduler 4.x, Dash/Plotly, Celery, `anthropic` SDK (openai SDK reaches Anthropic via compatibility endpoint), `groq` SDK (openai SDK + Groq `base_url` is sufficient).

See `.planning/research/STACK.md` for full version matrix and compatibility verification steps.

### Expected Features

The four v1.1 feature areas each have a minimum viable surface that makes them usable, plus a set of "add after core works" enhancements. All P1 features are required for the v1.1 milestone; P2 are post-milestone additions; P3 are deferred to v2+.

**Must have (P1, v1.1 core):**
- Retention: TTL sweep (`graphiti compact --expire`), pin command (`graphiti pin <uuid>`), stale preview (`graphiti stale`) — users will not trust automated deletion without preview and pin
- Retention: configurable `retention_days` in `llm.toml` (default 90) — hardcoded TTL is not acceptable
- Capture modes: two named modes (`decisions-only`, `decisions-and-patterns`) selectable via `llm.toml [capture] mode` — existing full-capture behavior becomes `decisions-and-patterns`; new narrower mode is `decisions-only`
- UI: node + edge browser via `graphiti ui` (Docker Kuzu Explorer), launched from CLI with browser auto-open
- Multi-provider: OpenAI-compatible adapter via `[provider]` section in `llm.toml`; backward compatibility with existing Ollama config guaranteed (no `[provider]` section = Ollama default unchanged)

**Should have (P2, add once P1 is stable):**
- Retention: access-frequency scoring (sidecar `access_count` + `last_accessed_at` per search hit)
- UI: monitoring dashboard tab (capture stats, queue depth, entity count over time)
- UI: scope selector (global vs. project view without restart)
- Multi-provider: N-provider failover chain (ordered fallback list)

**Defer to v2+:**
- Retention: RL-based importance scoring (requires 6+ months of access pattern data to train)
- Capture modes: per-scope mode config (global vs. project mode independently configurable)
- UI: real-time streaming updates (WebSocket complexity without proportional value)
- Multi-provider: cost-aware routing (requires per-task cost modeling; premature for v1.1)

**Anti-features to reject explicitly:**
- Silent automatic deletion without logging or preview (users lose trust when knowledge disappears)
- Force-directed graph layout as default (unreadable above ~80 nodes; use hierarchical layout)
- Inline graph editing from UI (bypasses CLI security layer; UI must be strictly read-only)
- LiteLLM as a dependency (170MB+, 800+ open issues, proxy-server model, overkill for local tool)
- Third "silent" capture mode (indistinguishable from broken hooks; `hooks_enabled = false` already handles this)

See `.planning/research/FEATURES.md` for full prioritization matrix and feature dependency graph.

### Architecture Approach

v1.1 is an additive extension, not a redesign. The existing five-layer architecture (Interface → Service → Capture → LLM → Storage) gains new implementations at each layer but the layer boundaries and calling conventions are preserved. The two new storage concerns (SQLite retention sidecar alongside Kuzu) establish a pattern: application-level metadata that graphiti-core does not own lives in a parallel SQLite file, keyed by entity UUID, co-located with the Kuzu DB for each scope.

**Major new components:**
1. `src/retention/` — three files: `store.py` (SQLite sidecar CRUD keyed by entity UUID), `policy.py` (TTL scoring and expiry decisions), `sweeper.py` (background scan + delete). `GraphService` gains an `expire()` method and access-tracking hooks in `search()` and `get_entity()`.
2. `src/llm/providers/` — provider factory pattern: `base.py` (Protocol definition), `ollama.py` (extracted from existing `client.py`), `openai_compat.py` (new — covers OpenAI, Groq, compatible endpoints), `anthropic.py` (new — Anthropic SDK adapter). `client.py` becomes a thin factory. `adapters.py` is NOT changed.
3. `src/cli/commands/ui.py` — new Typer command that spawns Docker Kuzu Explorer (Phase 11) or Uvicorn FastAPI server (Phase 12) as a subprocess. Never inline with MCP server — always a separate process.
4. Capture mode changes are pure parameterization: `summarizer.py` gains two prompt constants and a `mode` parameter; `relevance.py` gains `filter_for_mode()`; no new modules needed.

**Architecture phase sequencing (recommended in ARCHITECTURE.md):**
- Phase 9: Smart retention (standalone new module, minimal existing code changes)
- Phase 10: Configurable capture modes (prompt parameterization, low-risk)
- Phase 11: Graph UI — Docker Kuzu Explorer CLI wrapper (zero new UI code)
- Phase 12: Multi-provider LLM (highest regression risk — `client.py` decomposition)

### Critical Pitfalls

1. **Orphaned RelatesToNode_ after entity deletion** — Kuzu uses reified edges (`RelatesToNode_`) that are NOT cascade-deleted when their entity nodes are deleted. TTL deletion must issue `DETACH DELETE` on edge nodes first, then delete entity nodes, then sweep for zero-MENTIONS orphans. Wrap both steps in a Kuzu transaction. Prevention: two-step deletion query built into the sweeper from day one. Verify with `MATCH (e:RelatesToNode_) WHERE NOT (()-[:RELATES_TO]->(e)) RETURN count(e)` returning 0 after every retention run.

2. **TTL sweep deletes nodes with pending background queue items** — The retention sweeper and `BackgroundWorker` run independently. If an entity's TTL expires while a queued capture job references it, the episode is stored but cannot link to the deleted entity, producing dangling episodic nodes. Prevention: subtract `queue_item_ttl_hours` (default 24h) from the TTL cutoff window. Only delete nodes with `last_accessed < now - 90days - 24hours`. Verify by checking dead letter queue is empty after a retention run.

3. **Capture mode selection bypasses security sanitization** — If mode-based filtering is implemented as "filter before sanitize" to avoid wasting sanitizer cycles, a bug in the mode filter could allow raw content with secrets to bypass the security gate. The order `sanitize_content() → filter_for_mode()` is a security invariant. Prevention: comment this invariant explicitly in `summarizer.py`; gate Phase 10 ship on test `test_capture_modes_always_sanitize_before_filter()` passing.

4. **MCP stdio protocol corrupted by UI server stdout** — `graphiti ui` must NEVER start the web server in the same process as `graphiti mcp serve`. Uvicorn's startup banner and access logs write to stdout by default, corrupting the JSON-RPC stdio transport. Prevention: `graphiti ui` uses `subprocess.Popen(..., stdout=subprocess.DEVNULL, start_new_session=True)` — the UI server is always a separate process.

5. **graphiti-core version drift when adding new dependencies** — Adding `openai>=2.0.0` or other new packages triggers the dependency resolver, which may opportunistically upgrade graphiti-core if it sees a compatible newer version. Three existing workarounds in `graph_manager.py` and `adapters.py` are version-specific and break silently on upgrades. Prevention: pin `graphiti-core[kuzu]==0.28.1` hard in `pyproject.toml`; add `assert graphiti_core.__version__ == "0.28.1"` to the test suite before Phase 12 begins.

6. **OllamaLLMClient structured output logic does not transfer to other providers** — `_strip_schema_suffix()`, `_inject_example()`, and `format=` kwarg injection are calibrated exclusively for Ollama behavior. OpenAI uses `response_format={"type": "json_schema", ...}`; Anthropic uses tool-use JSON extraction. New provider adapters must implement their own structured output pattern. Prevention: new adapters inherit from graphiti-core's `LLMClient` ABC directly, NOT from `OllamaLLMClient`. Verify with graphiti-core's structured output integration test suite.

## Implications for Roadmap

Based on research, the suggested phase structure for v1.1 is four phases ordered by dependency complexity and regression risk:

### Phase 9: Smart Retention

**Rationale:** The retention module is a new, standalone addition with minimal risk to existing code paths (two hook points in `service.py` and a new `expire()` method). Building retention first establishes the SQLite sidecar pattern that other features reference (UI monitoring stats, retention health in `graphiti health`).

**Delivers:** TTL-based entity expiry with configurable `retention_days`, access-frequency tracking sidecar (`last_accessed_at`, `access_count`), `graphiti stale` preview command, `graphiti pin <uuid>` to protect nodes from expiry, `graphiti compact --with-expiry` combined operation. Deletion safety: orphan edge cleanup, queue-aware TTL window, Kuzu transaction wrapping.

**Addresses:** All P1 retention features from FEATURES.md. Foundation for P2 access-frequency scoring.

**Avoids:** Pitfall 1 (orphaned RelatesToNode_ edges — built into sweeper from day one). Pitfall 4 (queue race condition — pessimistic TTL window required).

**Stack:** `apscheduler>=3.10.4,<4.0` added to core dependencies. New `src/retention/` module with three files.

**Research flag:** Standard patterns. No `/gsd:research-phase` needed. SQLite sidecar, APScheduler 3.x AsyncIOScheduler, and Kuzu DETACH DELETE are all well-documented. Architecture decisions fully specified in ARCHITECTURE.md.

---

### Phase 10: Configurable Capture Modes

**Rationale:** Pure parameterization of existing code — no new dependencies, no new modules, no risk to the security layer if the sanitize-then-filter invariant is enforced. The phase is fast and low-risk, making it appropriate before the higher-complexity UI and multi-provider phases.

**Delivers:** `decisions-only` and `decisions-and-patterns` modes selectable in `llm.toml [capture] mode`. Active mode visible in `graphiti config show`. Security gate verified unconditional via mandatory integration test.

**Addresses:** All P1 capture mode features from FEATURES.md.

**Avoids:** Pitfall 6 (security bypass via mode pre-filter). The phase gates on `test_capture_modes_always_sanitize_before_filter()` passing before ship.

**Stack:** No new dependencies. Changes to `summarizer.py`, `relevance.py`, `config.py`, `git_worker.py`, `conversation.py`.

**Research flag:** No research needed. ARCHITECTURE.md specifies the exact files to modify and the two prompt constants to add.

---

### Phase 11: Graph UI (Docker Kuzu Explorer)

**Rationale:** Implementing `graphiti ui` as a Docker launcher for `kuzudb/explorer` delivers a working graph visualization command with zero custom UI code. The Docker image mounts the Kuzu database read-only, avoiding the Kuzu single-writer constraint. This approach has no Python dependency changes, so it cannot trigger the graphiti-core version conflict that multi-provider carries.

**Delivers:** `graphiti ui` command checks Docker availability, resolves the scope-appropriate Kuzu DB path, mounts it read-only, and opens the browser to `http://localhost:8000`. Graph visualization of entity nodes and relationship edges. Kuzu Explorer's built-in Cypher query interface enables ad-hoc graph exploration.

**Addresses:** P1 UI features (node + edge browser, CLI launch). Full text search integration (graphiti search syntax) is deferred to Phase 12.

**Avoids:** Pitfall 5 (MCP stdio corruption — subprocess launch with stdout isolation is the only acceptable design).

**Stack:** No new Python dependencies. Docker required (document as prerequisite). `src/cli/commands/ui.py` new file.

**Research flag:** Needs a targeted check during planning — verify that the `kuzudb/explorer` Docker image version compatible with Kuzu 0.11.3 schema is available on Docker Hub. One verification step, not a full research phase.

---

### Phase 12: Multi-Provider LLM Support

**Rationale:** The highest regression risk of the four v1.1 features. Refactoring `client.py` into a provider factory touches the core LLM dispatch chain used by every graph operation. This phase is done last so that retention, capture modes, and UI are stable before the LLM layer is restructured.

**Delivers:** `[provider]` section in `llm.toml` enabling OpenAI, Groq, and any OpenAI-compatible endpoint. `OllamaLLMClient` and `OllamaEmbedder` remain unchanged (embeddings always local). Backward compatibility: no `[provider]` section = Ollama default. `graphiti health` shows active provider and reachability. Provider API key validated at startup, not at first use.

**Addresses:** All P1 multi-provider features from FEATURES.md.

**Avoids:** Pitfall 3 (OllamaLLMClient coupling — new adapters are additions, not modifications). Pitfall 5 (graphiti-core version drift — assert version pin in test suite before adding openai dep).

**Stack:** `openai>=2.0.0` added as optional `[providers]` group. New `src/llm/providers/` directory. CRITICAL pre-work: verify graphiti-core 0.28.1 internal openai version pin before writing the phase plan.

**Research flag:** Needs `/gsd:research-phase` before planning. Two unknowns require resolution: (1) graphiti-core 0.28.1's internal openai version pin — run `pip show graphiti-core` and inspect METADATA before writing plan; (2) the exact structured output API differences between Ollama `format=`, OpenAI `response_format=`, and Anthropic tool-use that each new adapter must handle correctly.

---

### Phase Ordering Rationale

- **Retention before capture modes:** Retention requires new sidecar infrastructure. Capture modes are a simpler prompt parameterization that does not block other phases. Starting with retention establishes the sidecar pattern referenced by later features.
- **Capture modes before UI:** The UI monitoring dashboard reads capture stats tagged by mode. Mode labeling should be in place before the dashboard displays mode-tagged events.
- **UI (Docker, Phase 11) before multi-provider:** The Docker-based UI has zero Python dependency changes — it cannot trigger the graphiti-core version conflict that multi-provider carries. Do the safe phase before the risky one.
- **Multi-provider last:** Highest regression risk. Restructures the LLM dispatch chain used by every graph operation. Do last to avoid blocking earlier phases or introducing regressions that affect all features.

### Research Flags

Needs `/gsd:research-phase` before planning:
- **Phase 12 (Multi-Provider):** Two unknowns — graphiti-core's internal openai version pin, and provider-specific structured output API differences between Ollama, OpenAI, and Anthropic. Research is mandatory before writing the phase plan.

Needs targeted check during plan creation (not a full research phase):
- **Phase 11 (Graph UI):** Verify `kuzudb/explorer` Docker image version matches Kuzu 0.11.3 schema. One `docker pull` and schema check, not full research.

Standard patterns — skip research-phase:
- **Phase 9 (Retention):** SQLite sidecar, APScheduler 3.x, Kuzu DETACH DELETE — all well-documented with clear official sources. Architecture decisions fully specified in ARCHITECTURE.md.
- **Phase 10 (Capture Modes):** Pure code parameterization. All context is in the existing codebase and research files. No external unknowns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH (approach), MEDIUM (version pinning) | LiteLLM rejection is HIGH confidence (multiple sources, documented issues). openai 2.x compatibility with graphiti-core is MEDIUM — requires runtime verification at Phase 12 start. APScheduler 3.x vs 4.x distinction is HIGH (documented API break). pyvis maintenance-mode status is MEDIUM (last release Jan 2025). |
| Features | MEDIUM-HIGH | P1 features are well-defined with clear implementation paths. `EntityNode` schema constraints verified via direct codebase inspection (HIGH). Competitor analysis (Zep, Mem0, MemGPT) is MEDIUM confidence — single source for some comparisons. |
| Architecture | HIGH | Analysis grounded in actual v1.0 source code (`service.py`, `adapters.py`, `client.py`, `config.py`, `summarizer.py`, `relevance.py`). Component boundaries and data flows are specified at implementation level. SQLite sidecar decision verified against graphiti-core schema limitations (direct codebase inspection). |
| Pitfalls | HIGH | All 6 critical pitfalls verified against codebase inspection, graphiti-core GitHub issues (#1083 orphaned entities, #1132 Kuzu archived), Kuzu documentation, and KuzuDB deprecation news. Orphaned edge pitfall is a confirmed upstream bug. Version drift risk is confirmed via KuzuDB archived status. |

**Overall confidence:** HIGH for Phases 9 and 10. MEDIUM-HIGH for Phase 11 (Docker compatibility check needed). MEDIUM for Phase 12 (openai version pin unknown until runtime verification).

### Gaps to Address

- **openai SDK vs. graphiti-core version conflict (Phase 12 blocker):** Must run `pip show graphiti-core` and inspect METADATA for openai version constraints before Phase 12 plan is written. If graphiti-core pins openai 1.x, the provider approach remains valid but the version range changes to `openai>=1.50.0,<2.0.0`. Handle during Phase 12 research.

- **Kuzu Explorer Docker image compatibility (Phase 11 pre-check):** Must verify the `kuzudb/explorer` Docker image supports the Kuzu 0.11.3 schema. The explorer image version must match the pinned Kuzu library version. Check on Docker Hub before writing Phase 11 plan.

- **Retention scoring decay formula (Phase 9 design decision):** Research specifies `score = (access_count * recency_weight) + base_score` as a placeholder. The exact decay function (linear, exponential, step-function) is not specified and should be decided during Phase 9 plan creation. Exponential decay with a half-life of 30 days is the standard approach for content freshness scoring and is a reasonable default to propose.

- **graphiti-core installed version mismatch (pre-Phase-9 check):** FEATURES.md noted `graphiti-core==0.26.3` installed vs `==0.28.1` in `pyproject.toml`. This must be confirmed with `pip show graphiti-core` before Phase 9 begins — retention behavior depends on the `EntityNode` schema, which may differ between versions. Resolve before any Phase 9 work starts.

## Sources

### Primary (HIGH confidence)
- graphiti-core source (direct inspection): `.venv/lib/python3.12/site-packages/graphiti_core/nodes.py` — EntityNode fields confirmed, no TTL fields on EntityNode
- graphiti-core edges.py (direct inspection) — `expired_at`, `valid_at`, `invalid_at` confirmed on EdgeNode only
- graphiti-core GitHub issue #1083 — orphaned entity bug confirmed, PR #1130 unmerged as of 2026-03-01
- graphiti-core GitHub issue #1132 — Kuzu archived discussion, FalkorDB migration guide referenced
- KuzuDB archived October 2025 — The Register report (theregister.com)
- Kuzu DELETE docs (docs.kuzudb.com/cypher/data-manipulation-clauses/delete/) — DETACH DELETE pattern confirmed
- openai PyPI (pypi.org/project/openai) — latest 2.24.0 (Feb 2026), Python 3.9+ supported
- APScheduler PyPI — 3.10.4 stable, 4.x API break documented and confirmed
- streamlit PyPI — 1.52.2 (Jan 2026), Python 3.12 verified
- Anthropic OpenAI SDK compatibility docs — openai SDK reaches Anthropic via `base_url` override confirmed
- Codebase inspection: `service.py`, `adapters.py`, `client.py`, `config.py`, `summarizer.py`, `relevance.py`, `graph_manager.py`, `queue/worker.py`

### Secondary (MEDIUM confidence)
- pyvis PyPI + GitHub — 0.3.2 (Jan 2025), maintenance mode but stable for hundreds-of-nodes scale
- LiteLLM review 2026 (TrueFoundry) — 800+ open issues, dependency explosion documented
- graphiti-core EntityNode schema (help.getzep.com) — web-verified `created_at` on nodes, edge-only temporal fields
- Knowledge graph visualization comparison (Memgraph blog) — Pyvis/vis.js suitable up to ~300 nodes; hierarchical layout recommended above ~80 nodes
- Kuzu Explorer Docker (hub.docker.com/r/kuzudb/explorer + docs.kuzudb.com/visualization) — read-only volume mount pattern confirmed
- graphiti-core DeepWiki provider configuration — third-party source used for multi-provider background

### Tertiary (LOW confidence, validate before use)
- FalkorDB KuzuDB migration guide — contingency only if graphiti-core drops Kuzu support; not relevant to v1.1
- LiteLLM OpenAI-compatible endpoint docs — referenced only to confirm the openai SDK `base_url` approach is the correct alternative

---
*Research completed: 2026-03-01*
*Ready for roadmap: yes*
