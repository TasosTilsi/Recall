# Feature Research — v1.1 Advanced Features

**Domain:** Knowledge Graph Developer Tools (CLI + Hooks + MCP) — v1.1 extension
**Researched:** 2026-03-01
**Confidence:** MEDIUM-HIGH

## Scope

This document covers only the **four new feature areas** targeted for v1.1. v1.0 features
(16+ CLI commands, MCP server, dual-scope storage, security filtering, git hooks, background
queue, context injection) are shipped and not re-researched here.

**v1.1 targets:**
1. Smart retention — TTL + reinforcement scoring for knowledge freshness
2. Configurable capture modes — what gets captured and at what detail level
3. Localhost graph visualization UI — node/edge browser + monitoring dashboard
4. Multi-provider LLM support — switch providers via `llm.toml` without code changes

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in each category. Missing these makes the feature feel incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Retention: configurable TTL value** | Users expect to control when nodes expire, not just get a hardcoded 90-day default | LOW | Single `retention_days` field in `llm.toml`. Already has `queue_item_ttl_hours` pattern to follow. |
| **Retention: dry-run before purge** | Users will not trust automatic deletion without being able to preview what gets removed | LOW | `graphiti compact --dry-run` pattern; list nodes scheduled for deletion |
| **Retention: manual keep/pin** | Users need to mark knowledge that should never auto-expire (personal preferences, stable decisions) | LOW | `graphiti pin <uuid>` — sets `pinned=True` on entity, exempts from TTL sweep |
| **Capture modes: named modes, not just flags** | Users expect `--mode decisions` or `--mode full`, not arbitrary flag combinations | LOW | Config field + CLI override. Two modes sufficient: `decisions` (default) and `full`. |
| **Capture modes: security must stay stricter in decisions mode** | Decisions-only mode must filter harder, not just capture less. Users expect this is the safe default. | LOW | Already implicit in summarizer prompt. Make it explicit in mode config. |
| **Capture modes: mode visible in `graphiti config`** | Users expect `graphiti config show` to display the active capture mode | LOW | Extend existing `config` command output |
| **UI: nodes and edges browsable** | The minimum viable graph UI must show entities and their relationships, not just a node list | MEDIUM | Pyvis/Vis.js renders both. No UI that shows only nodes is acceptable. |
| **UI: search from browser** | Users expect to type a query in the UI and see matching nodes highlighted | MEDIUM | FastAPI endpoint for search; JS frontend calls it and highlights results |
| **UI: launch via CLI command** | `graphiti ui` starts the server and opens the browser | LOW | `typer` command + `webbrowser.open()` |
| **Multi-provider: no code change to switch** | Switching from Ollama to OpenAI must require only `llm.toml` edits | MEDIUM | Provider abstraction layer in `src/llm/client.py`. OpenAI SDK covers most providers. |
| **Multi-provider: Ollama remains default** | Existing users must not have their config broken by v1.1 update | LOW | Backward-compatible: if no `[provider]` section, use Ollama as before |
| **Multi-provider: health check shows active provider** | `graphiti health` must show which provider is configured and reachable | LOW | Extend existing health command |

### Differentiators (Competitive Advantage)

Features that go beyond expectations. Not required, but high value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Retention: access-frequency scoring** | Frequently-searched nodes get their TTL extended automatically; unused nodes expire faster | MEDIUM | Requires tracking `last_accessed_at` + `access_count` in a sidecar store (EntityNode schema in graphiti-core 0.26.3 has no `last_accessed` field — must be tracked externally in SQLite or a metadata JSON file) |
| **Retention: importance tiers** | Nodes tagged `pinned`, `reinforced`, or `expiring` visible in `graphiti list` with age indicators | LOW | Adds value to browsing; implementation is just metadata annotation on existing display |
| **Retention: stale preview command** | `graphiti stale` lists nodes within 7 days of expiry so user can pin or prune intentionally | LOW | High usefulness for low complexity. Output: table of node name, age, last search hit |
| **Capture modes: per-scope mode config** | Global captures in `decisions` mode, project captures optionally in `full` mode | MEDIUM | Separate config key per scope: `capture.global_mode` and `capture.project_mode` |
| **Capture modes: token budget enforcement** | `full` mode sets a max token limit per capture event to prevent runaway LLM costs | MEDIUM | Add `capture_max_tokens` config field; truncate input before LLM call |
| **UI: scope selector** | Switch between global and per-project graph views without restarting the server | MEDIUM | Dropdown in UI that changes the active graph endpoint; FastAPI route parameter |
| **UI: monitoring dashboard tab** | Capture stats: last N captures, queue depth, error count, node count over time | MEDIUM | Separate `/dashboard` route; reads from SQLiteAckQueue stats + graph node count |
| **UI: node detail panel** | Click a node to see its full content, tags, age, access count, and linked edges | MEDIUM | Side panel in Pyvis via JS click callback + FastAPI `/node/<uuid>` endpoint |
| **Multi-provider: embeddings provider separation** | Embeddings always use a separate provider config (local Ollama) even when chat switches to OpenAI | LOW | Already architecturally correct (embeddings always local); just expose in config explicitly |
| **Multi-provider: failover chain** | Configure a fallback chain: `[openai, groq, local_ollama]` — tried in order | MEDIUM | Extend existing cloud/local failover logic to support N-provider chain |
| **Multi-provider: cost-aware routing** | Route cheap/fast tasks (classify, summarize) to Groq; complex tasks (entity extraction) to OpenAI | HIGH | DEFER — not v1.1 scope. Requires per-task cost modeling. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Retention: automatic silent deletion** | "Just clean it up without asking" | Users lose trust when knowledge disappears without notice. Debugging broken context injection becomes impossible. | Always log deletions to a retention log; `graphiti stale` previews before any sweep runs. |
| **UI: force-directed graph as default** | Looks impressive in demos | Force-directed layouts become unreadable above ~80 nodes. Dev knowledge graphs routinely exceed 200 nodes after one month. | Hierarchical or cluster layout by default; force-directed as an opt-in toggle. |
| **UI: real-time streaming updates** | "Show new nodes as they're captured" | WebSocket complexity for marginal value. Capture happens async; user is coding, not watching the UI. | Manual refresh button + auto-refresh on 60s interval. No sockets needed. |
| **UI: edit nodes inline** | "Fix a wrong label from the UI" | Two write paths (CLI + UI) diverge. UI edits bypass security filtering and audit logging. | CLI is the single write path. UI is read-only. |
| **Capture modes: third "silent" mode** | "I want hooks to run but nothing gets stored" | Silent mode is indistinguishable from broken hooks. Creates debugging confusion. | `hooks_enabled = false` in config already handles this. No third mode needed. |
| **Capture modes: per-file capture rules** | "Only capture decisions from src/, ignore tests/" | Rule complexity grows unbounded. File exclusions already handle secrets; capture-level file routing is premature optimization. | `decisions` mode's LLM prompt already filters out test/scaffolding content implicitly. |
| **Multi-provider: LiteLLM as dependency** | "One library handles all providers" | LiteLLM has >500µs overhead per call, 3+ second cold start (import time), memory leaks at scale, and 40+ transitive dependencies. For a CLI tool calling ~5 LLM ops per session, this is disproportionate weight. | Direct OpenAI SDK (`openai` package covers OpenAI, Anthropic via compatibility, Groq, any OpenAI-compatible base_url). Thin provider adapter per provider. |
| **Multi-provider: provider marketplace UI** | "Let me browse and switch providers in the browser UI" | Provider config is a one-time setup, not a runtime choice. A UI for it adds maintenance with no value. | `llm.toml` with clear documentation. `graphiti health` shows active provider. |
| **Retention: ML-based importance scoring** | "Train a model on my access patterns" | Training data cold start problem — no signal on day 1. Model needs retraining. Storage overhead. | Simple heuristics: pinned > access_count > age. Good enough for 95% of cases. Implement RL scoring in v2 if needed. |
| **UI: graph editing (add/delete nodes)** | "I want to curate my graph visually" | Bypasses CLI security layer, creates dual write paths, breaks audit trail | `graphiti add`, `graphiti delete` — CLI is already fast and scriptable |

---

## Feature Dependencies

```
[Smart Retention]
    └──requires──> [EntityNode metadata sidecar]  (no last_accessed in graphiti-core schema)
    └──requires──> [search() instrumentation]     (must track access on every search call)
    └──enables──>  [graphiti stale]               (depends on access metadata being present)
    └──enables──>  [graphiti pin]                 (depends on sidecar metadata store)
    └──conflicts-> [graphiti compact]             (both modify entity lifecycle — must coordinate)

[Configurable Capture Modes]
    └──requires──> [existing summarizer.py]       (already exists — extend, don't replace)
    └──requires──> [LLMConfig extension]          (add capture_mode field to llm.toml)
    └──enables──>  [per-scope mode config]        (global_mode vs project_mode)
    └──enhances--> [security filtering]           (decisions mode requires stricter LLM prompt)

[Localhost Graph UI]
    └──requires──> [FastAPI or similar web server]     (new dependency)
    └──requires──> [Pyvis or Cytoscape.js]             (new dependency)
    └──requires──> [graphiti search() as API endpoint] (expose existing search via HTTP)
    └──enhances--> [Smart Retention]                   (UI can show stale/pinned node status)
    └──conflicts-> [MCP stdio transport]               (UI server must NOT share process with MCP server)

[Multi-Provider LLM]
    └──requires──> [openai SDK]                   (new dependency — covers OpenAI, Groq, Anthropic-compat)
    └──requires──> [LLMConfig extension]          (add [provider] section to llm.toml)
    └──requires──> [LLMClient refactor]           (src/llm/client.py dispatcher by provider type)
    └──enhances--> [health command]               (show active provider + reachability)
    └──conflicts-> [ollama SDK hardcoding]        (existing ollama.Client() calls must be behind adapter)
```

### Dependency Notes

- **Retention metadata is the key unknown:** graphiti-core 0.26.3 `EntityNode` has only `created_at` on nodes (`expired_at`, `valid_at`, `invalid_at` are on edges only). To track `last_accessed_at` and `access_count`, a sidecar SQLite or JSON store is required. This must be designed before implementing retention scoring.
- **UI must be a separate process/port:** The MCP server uses stdio transport and cannot share a process with an HTTP server. `graphiti ui` spawns a separate FastAPI process.
- **Multi-provider does not touch embeddings:** Embeddings always use local Ollama (`nomic-embed-text`). Cloud providers are chat/generate only. This constraint is already established in v1.0.
- **Capture modes extend, not replace:** The existing `summarizer.py` `BATCH_SUMMARIZATION_PROMPT` already captures decisions. Mode config changes the prompt strictness and optionally increases token budget in `full` mode.
- **LLMConfig is the integration point for both capture modes and multi-provider:** Both features add fields to `llm.toml` and `LLMConfig`. Coordinate their additions to avoid schema conflicts.

---

## MVP Definition for v1.1

### Must Ship (v1.1 core)

The minimum set that makes each feature area usable.

- [ ] **Retention: TTL sweep** — `graphiti compact` prunes nodes older than `retention_days` (default: 90) from configured date. Log all deletions. MEDIUM complexity.
- [ ] **Retention: pin command** — `graphiti pin <uuid>` exempts a node from TTL sweep. LOW complexity.
- [ ] **Retention: stale command** — `graphiti stale` lists nodes within 7 days of TTL expiry. LOW complexity.
- [ ] **Capture modes: two modes** — `decisions` (current behavior, stricter prompt) and `full` (captures patterns + code rationale). `capture_mode` field in `llm.toml`. LOW complexity.
- [ ] **UI: node + edge browser** — Pyvis-rendered graph served by FastAPI at `localhost:7474`. `graphiti ui` launches. MEDIUM complexity.
- [ ] **UI: text search** — Search box queries existing `graphiti search` and highlights matching nodes. MEDIUM complexity.
- [ ] **Multi-provider: OpenAI-compatible adapter** — `[provider] type = "openai"` in `llm.toml` routes chat through `openai.OpenAI(base_url=..., api_key=...)`. Groq and Anthropic-compatible endpoints work with same adapter. MEDIUM complexity.
- [ ] **Multi-provider: backward compat** — No `[provider]` section means existing Ollama behavior unchanged. LOW complexity.

### Add After Core Works (v1.1.x)

- [ ] **Retention: access-frequency scoring** — Track `last_accessed_at` per search hit in sidecar store; extend TTL on access. Trigger: retention sweep works correctly.
- [ ] **UI: monitoring dashboard** — Capture stats tab. Trigger: UI core is stable.
- [ ] **UI: scope selector** — Switch global vs project graph. Trigger: UI core is stable.
- [ ] **Multi-provider: N-provider failover chain** — Configure ordered fallback list. Trigger: single provider works.

### Defer to v2+

- [ ] **Retention: RL-based importance scoring** — Needs access pattern training data that doesn't exist until 6+ months of usage.
- [ ] **Capture modes: per-scope mode config** — Adds config complexity before simpler global mode is validated.
- [ ] **UI: real-time streaming** — WebSocket complexity without proportional value.
- [ ] **Multi-provider: cost-aware routing** — Requires per-task cost modeling; premature for v1.1.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Retention: TTL sweep + log | HIGH | MEDIUM | P1 |
| Retention: pin command | HIGH | LOW | P1 |
| Retention: stale preview | HIGH | LOW | P1 |
| Capture modes: decisions vs full | MEDIUM | LOW | P1 |
| Multi-provider: OpenAI-compat adapter | HIGH | MEDIUM | P1 |
| Multi-provider: backward compat | HIGH | LOW | P1 |
| UI: node + edge browser | MEDIUM | MEDIUM | P1 |
| UI: text search in browser | MEDIUM | MEDIUM | P1 |
| Retention: access-frequency scoring | MEDIUM | MEDIUM | P2 |
| Capture modes: per-scope config | LOW | MEDIUM | P2 |
| UI: monitoring dashboard tab | MEDIUM | MEDIUM | P2 |
| UI: scope selector | MEDIUM | MEDIUM | P2 |
| Multi-provider: N-provider failover | MEDIUM | MEDIUM | P2 |
| Retention: RL scoring | LOW | HIGH | P3 |
| UI: real-time streaming | LOW | HIGH | P3 |
| Multi-provider: cost routing | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v1.1 milestone
- P2: Should have, add once P1 is stable
- P3: Defer to v2+

---

## Implementation Notes by Feature

### Smart Retention

**Key constraint:** graphiti-core 0.26.3 `EntityNode` schema: `{uuid, name, group_id, labels, created_at, name_embedding, summary, attributes}`. There is no `last_accessed_at`, `access_count`, or `pinned` field. These must live in a sidecar store.

**Recommended sidecar:** A single SQLite table `~/.graphiti/retention.db`:
```sql
CREATE TABLE node_metadata (
    uuid TEXT PRIMARY KEY,
    scope TEXT,
    project_path TEXT,
    last_accessed_at DATETIME,
    access_count INTEGER DEFAULT 0,
    pinned BOOLEAN DEFAULT 0
);
```

**TTL sweep logic:** `created_at < now - retention_days AND pinned = 0 AND access_count = 0 OR last_accessed_at < now - retention_days`. Use existing `graphiti.remove_episode()` or direct KuzuDriver `execute_query()` for deletion.

**Integration point:** `GraphService.search()` must write to retention.db after every successful search. Non-blocking write (separate thread or fire-and-forget coroutine).

### Configurable Capture Modes

**Simple approach:** Two named prompt templates in `summarizer.py`:
- `DECISIONS_PROMPT` — current `BATCH_SUMMARIZATION_PROMPT` (extracts decisions, rationale, architecture, bug fixes)
- `FULL_PROMPT` — adds "Patterns & Idioms" and "Code Structure Changes" sections to extracted content

**Config field addition to `LLMConfig`:**
```toml
[capture]
mode = "decisions"          # "decisions" | "full"
max_tokens = 4096           # cap input tokens per capture event
```

**No new code paths needed:** `summarize_batch()` selects prompt template based on config. Security filtering runs identically in both modes (SECURITY GATE is non-negotiable, per CLAUDE.md).

### Localhost Graph UI

**Stack recommendation:** FastAPI (already in transitive deps via MCP) + Pyvis (new dep, ~200KB, pure Python wrapper over vis.js).

**Architecture:**
- `graphiti ui` Typer command spawns `uvicorn` on port 7474, opens browser
- `/` route serves interactive Pyvis HTML (generated from KuzuDriver query)
- `/api/search?q=<query>` proxies to existing `GraphService.search()`
- `/api/node/<uuid>` returns full node detail JSON
- UI is **read-only** — no write routes

**Port 7474:** Convention borrowed from Neo4j Browser (7474). Recognizable to graph developers.

**Node limit for rendering:** Cap at 500 nodes for Pyvis performance. Show "Showing top 500 nodes by recency" notice. Force-directed layout fails above ~300 nodes in browser — use hierarchical layout by default.

### Multi-Provider LLM

**Provider abstraction pattern:** Replace `ollama.Client()` instantiation in `src/llm/client.py` with a factory:

```toml
# llm.toml — new [provider] section
[provider]
type = "openai"              # "ollama" (default) | "openai" | "groq" | "openai_compatible"
api_key = "sk-..."          # or set OPENAI_API_KEY env var
base_url = "https://api.openai.com/v1"   # for openai_compatible, point to any endpoint
models = ["gpt-4o-mini"]
```

**Implementation:** `openai` Python SDK supports any OpenAI-compatible endpoint via `base_url`. Groq uses `https://api.groq.com/openai/v1`. This means a single `openai.OpenAI(base_url=..., api_key=...)` adapter covers OpenAI, Groq, LM Studio, vLLM, and most self-hosted options.

**Anthropic:** Not OpenAI-compatible natively. Requires separate `anthropic` SDK adapter. Defer to v1.1.x if no demand.

**Embeddings stay local:** `_is_cloud_available("embed")` pattern from v1.0 is preserved. Embeddings always use local Ollama. New provider section only controls chat/generate routing.

---

## Competitor Feature Analysis

| Feature Area | Zep (graphiti-core's parent) | Mem0 | MemGPT/Letta | Our Approach |
|--------------|------------------------------|------|---------------|--------------|
| **Retention** | Bi-temporal model, manual expiry | Per-user TTL | Archival tiers | TTL + access scoring, automatic sweep |
| **Capture modes** | Manual add only | Structured memory types | Memory compiler | Decisions-only default, full mode opt-in |
| **Visualization** | No built-in UI | No UI | Web UI (complex) | Minimal Pyvis browser, read-only |
| **Multi-provider** | OpenAI + Anthropic hardcoded | OpenAI + Anthropic | Any via LiteLLM | Config-driven, OpenAI-compat covers most |

**Key differentiation vs Zep/Mem0:** Those are cloud-hosted services with per-user billing. This project is a local-first personal developer tool — no server, no billing, no data leaving the machine.

---

## Sources

- [graphiti-core EntityNode schema](https://help.getzep.com/graphiti/core-concepts/custom-entity-and-edge-types) — confirmed `created_at` on nodes, `expired_at`/`valid_at`/`invalid_at` on edges only (MEDIUM confidence, web verified)
- [Neo4j APOC TTL documentation](https://neo4j.com/labs/apoc/4.1/graph-updates/ttl/) — TTL pattern using node property + index (MEDIUM confidence, official docs)
- [LiteLLM performance analysis](https://www.truefoundry.com/blog/litellm-alternatives) — 500µs overhead, 3s cold start, memory leak concerns (MEDIUM confidence, multiple sources agree)
- [Pyvis GitHub](https://github.com/WestHealth/pyvis) — Python wrapper over vis.js, outputs interactive HTML (HIGH confidence, official source)
- [LiteLLM OpenAI-compatible endpoint docs](https://docs.litellm.ai/docs/providers/openai_compatible) — `openai/` prefix pattern for any compatible endpoint (HIGH confidence, official docs)
- [OpenAI Python SDK base_url pattern](https://platform.openai.com/docs/api-reference/introduction) — `openai.OpenAI(base_url=..., api_key=...)` enables any compatible endpoint (HIGH confidence, official)
- [Knowledge graph visualization libraries comparison](https://memgraph.com/blog/you-want-a-fast-easy-to-use-and-popular-graph-visualization-tool) — Pyvis/vis.js suitable up to ~300 nodes, Cytoscape.js for larger graphs (MEDIUM confidence, single source)
- [Content freshness and knowledge lifecycle](https://kminsider.com/blog/knowledge-lifecycle/) — Retire criteria: unused 24+ months, superseded (MEDIUM confidence, domain expertise)
- Local codebase inspection: `graphiti-core==0.26.3` installed (not 0.28.1 as in pyproject.toml — version mismatch to watch), `EntityNode.model_fields` confirmed via `python3 -c` (HIGH confidence, direct inspection)

---

*Feature research for: v1.1 Advanced Features — Smart Retention, Capture Modes, Graph UI, Multi-Provider LLM*
*Researched: 2026-03-01*
*Confidence: MEDIUM-HIGH (critical schema facts verified via direct codebase inspection; visualization and LLM provider patterns verified via official docs)*
