# Stack Research — v1.1 Advanced Features

**Domain:** Knowledge graph CLI — Smart retention, graph UI, multi-provider LLM
**Researched:** 2026-03-01
**Confidence:** HIGH (core decisions), MEDIUM (version pinning for new packages)
**Scope:** ADDITIONS ONLY — documents new packages needed for v1.1 features, not the existing v1.0 stack

---

## Existing v1.0 Stack (reference only, do not change)

| Technology | Version | Notes |
|------------|---------|-------|
| Python | 3.12 | Runtime — do not change |
| kuzu | 0.11.3 | Graph DB — pinned |
| graphiti-core[kuzu] | 0.28.1 | KG framework — pinned |
| ollama | 0.6.1 | Ollama SDK — pinned |
| mcp[cli] | >=1.26.0,<2.0.0 | FastMCP — pinned range |
| typer | >=0.15.0 | CLI — keep |
| httpx | >=0.28.0 | HTTP client — keep |
| structlog | >=25.5.0 | Logging — keep |
| tenacity | 9.1.4 | Retry — keep |
| persist-queue | 1.1.0 | SQLiteAckQueue — keep |
| python-toon | >=0.1.3 | TOON encoding — keep |
| detect-secrets | >=1.5.0 | Secret scanning — keep |
| GitPython | >=3.1.0 | Git integration — keep |

---

## New Stack Additions for v1.1

### Feature 1: Smart Retention (TTL + Reinforcement Scoring)

**Approach: Pure Python + Kuzu Cypher — no new library needed.**

TTL-based expiry and access-frequency reinforcement are implemented as:
1. New Kuzu node properties: `last_accessed_at TIMESTAMP`, `access_count INT64`, `reinforcement_score FLOAT`
2. Python-level scheduled cleanup: query Kuzu with `WHERE last_accessed_at < $cutoff` + `DELETE`
3. Scoring: Python computes `score = (access_count * recency_weight) + base_score` and writes it back

Kuzu's Cypher `DELETE` and `MATCH ... WHERE timestamp < $cutoff` already supports this pattern. No additional database scheduler library is required for a single-process local tool.

**If a background scheduler is needed for periodic cleanup:**

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `apscheduler` | `>=3.10.4` | In-process job scheduler for TTL sweeps | Lightweight cron-style scheduler with no external broker; runs in same Python process; APScheduler 3.x is stable on Python 3.12 with `AsyncIOScheduler`. Alternative to a cron job that would require OS-level setup. |

APScheduler 3.x (not 4.x — see pitfalls) is the right choice: it runs inside the existing async event loop via `AsyncIOScheduler`, has no daemon or broker dependency, and integrates cleanly with the existing `BackgroundWorker` pattern.

**Installation:**
```bash
pip install "apscheduler>=3.10.4,<4.0"
```

**Do NOT use APScheduler 4.x:** It was released in 2024 with a completely different API (no `AsyncIOScheduler`, no `add_job`). The 3.x → 4.x migration is a full rewrite. Pin to `<4.0` in pyproject.toml.

---

### Feature 2: Configurable Capture Modes (decisions-only vs. decisions-and-patterns)

**No new library needed.** This is a configuration change + filtering logic in Python:
- `llm.toml` gets a new `[capture]` section with `mode = "decisions"` or `mode = "patterns"`
- The existing `LLMConfig` dataclass gains a `capture_mode: str` field
- Filtering logic in `src/capture/summarizer.py` applies mode-specific prompts

No external dependency required.

---

### Feature 3: Localhost Graph Visualization (`graphiti ui`)

**Recommended stack: `pyvis` for graph rendering + `streamlit` as the app server.**

#### Graph Rendering: pyvis

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `pyvis` | `0.3.2` | Interactive graph HTML generation | Renders entity nodes + relationship edges as interactive HTML via vis.js. Pure Python wrapper around vis.js — no JavaScript required. `Network.from_nx()` accepts NetworkX graphs directly. Output is a self-contained HTML file that opens in any browser. |
| `networkx` | `>=3.3` | Graph data structure intermediate | pyvis accepts NetworkX `Graph` objects natively. The existing system uses Kuzu Cypher for queries — NetworkX is the bridge between Kuzu query results and pyvis. NetworkX 3.x is Python 3.12 compatible and actively maintained. |

pyvis is the right choice over Plotly/Dash because:
- **Zero JavaScript**: generates self-contained HTML with embedded vis.js
- **Minimal dependencies**: networkx is the only required dep; no React, no webpack
- **For tool scale**: this tool has hundreds of nodes max, not millions — pyvis handles this easily
- **Fast iteration**: `net.show("graph.html")` is 5 lines of code; Dash equivalent is 60+

pyvis last release was January 2025 (v0.3.2). It is in maintenance mode but stable. The vis.js rendering is battle-tested. For a developer tool with dozens to hundreds of nodes, this is not a concern.

#### App Server: streamlit

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `streamlit` | `>=1.42.0` | Localhost web app framework | Turns a Python script into a web app with `streamlit run src/ui/app.py`. Handles HTTP serving, browser launch, and live reload. 10x less code than Dash for the same result. Python 3.12 supported (verified). Latest stable: 1.52.2 (Jan 2026). |

Streamlit is the right choice over Dash because:
- **Simplicity**: the UI is a dev tool, not a production dashboard. Streamlit's script-rerun model is perfect — each user interaction reruns the script from the codebase.
- **No routing/layout boilerplate**: Dash requires defining layout, callbacks, and running a server app object. Streamlit is a script.
- **Fast development**: `st.components.v1.html(pyvis_html_content)` embeds the pyvis graph directly.
- **Already supports Python 3.12**: verified (3.9, 3.10, 3.11, 3.12, 3.13 all supported).

Streamlit brings notable dependencies (tornado, watchdog, etc.) but they are non-conflicting with the existing stack. The `[ui]` optional dependency group isolates this to users who run `graphiti ui`.

**Installation (optional group):**
```bash
pip install "graphiti-knowledge-graph[ui]"
# Which installs: pyvis==0.3.2 networkx>=3.3 streamlit>=1.42.0
```

In `pyproject.toml`:
```toml
[project.optional-dependencies]
ui = [
    "pyvis==0.3.2",
    "networkx>=3.3",
    "streamlit>=1.42.0",
]
```

---

### Feature 4: Multi-Provider LLM Support

**Recommended approach: openai Python SDK 2.x with `base_url` overrides — NOT litellm.**

#### Why NOT litellm

litellm is the obvious choice but it is wrong for this project:

1. **Dependency explosion**: litellm 1.81+ requires `aiohttp`, `azure-identity`, `grpcio`, `mlflow`, `polars`, `redisvl`, `semantic-router`, `tiktoken`, `tokenizers`, `uvloop`, and many more. This is a massive transitive dependency tree for a local developer tool.
2. **Version conflicts**: litellm pins `openai>=1.99.5` (in recent versions), which conflicts with other packages pinning older openai. The existing `httpx>=0.28.0` and graphiti-core's own OpenAI dependency may conflict.
3. **Overkill**: litellm is designed for production AI gateways with load balancing, cost tracking, and logging at scale. This project needs provider switching for a single local user.
4. **Stability**: As of Jan 2026, litellm has 800+ open issues; one release caused OOM on deployments.

#### The Right Approach: openai SDK 2.x + anthropic SDK + groq SDK

All major providers support the OpenAI-compatible API via `base_url`. The architecture is:

1. **`openai>=2.0.0`** — handles OpenAI, Groq, and any OpenAI-compatible endpoint (via `base_url`)
2. **`anthropic>=0.84.0`** — handles Anthropic natively (Claude models)
3. **`groq>=0.33.0`** — optional; Groq is already reachable via openai SDK with `base_url="https://api.groq.com/openai/v1"`

The existing `OllamaClient` pattern (provider-specific client, config-driven) is replicated for a new `ProviderClient` abstraction. The `llm.toml` gains a `[provider]` section:

```toml
[provider]
type = "openai"          # "openai" | "anthropic" | "groq" | "openai-compatible"
api_key = "sk-..."       # or set PROVIDER_API_KEY env var
base_url = ""            # override for openai-compatible endpoints
models = ["gpt-4o-mini"] # models to use
```

The graphiti-core `LLMClient` interface requires `chat()` and `generate()` methods. The new `ProviderClient` implements those using whichever SDK matches the configured provider type.

**Note on Anthropic:** Anthropic exposes an OpenAI-compatible endpoint at `https://api.anthropic.com/v1/` (documented officially). This means `openai` SDK + `base_url="https://api.anthropic.com/v1/"` works for basic use. The native `anthropic` SDK is only needed for Anthropic-specific features (extended thinking, PDF processing, prompt caching). For v1.1, use the openai SDK for Anthropic too — simpler, one less dependency.

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `openai` | `>=2.0.0` | OpenAI + OpenAI-compatible provider client | Official SDK, Python 3.9+. Latest: 2.24.0 (Feb 2026). Supports `base_url` override for Groq, Anthropic-compatible, LM Studio, vLLM, etc. Already transitively pulled by graphiti-core in some versions — check for conflicts. |
| `groq` | `>=0.33.0` | Groq provider — OPTIONAL | Only needed if users want native Groq SDK features. In practice, Groq is fully reachable via openai SDK with `base_url="https://api.groq.com/openai/v1"`. Add to `[provider]` optional group, not core. |

**Installation (optional group):**
```bash
pip install "graphiti-knowledge-graph[providers]"
# Which installs: openai>=2.0.0
```

```toml
[project.optional-dependencies]
providers = [
    "openai>=2.0.0",
]
```

**IMPORTANT — Compatibility check with graphiti-core 0.28.1:**
graphiti-core may already import `openai` internally (it supports OpenAI and Azure OpenAI backends). Before adding `openai>=2.0.0`, run `pip show graphiti-core | grep -i openai` to verify there is no pinned openai version that conflicts. If graphiti-core pins to openai 1.x, use `openai>=1.50.0,<2.0.0` instead. This MUST be verified during Phase 9 plan creation.

---

## Summary: What to Add vs. What to Skip

### Add (as optional groups)

| Package | Version | Group | Feature |
|---------|---------|-------|---------|
| `apscheduler` | `>=3.10.4,<4.0` | core | Smart retention periodic cleanup |
| `pyvis` | `==0.3.2` | `[ui]` | Graph visualization HTML |
| `networkx` | `>=3.3` | `[ui]` | Graph data bridge for pyvis |
| `streamlit` | `>=1.42.0` | `[ui]` | Localhost web app server |
| `openai` | `>=2.0.0` | `[providers]` | Multi-provider LLM |

### Do NOT Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `litellm` | 100+ transitive deps, version conflicts, overkill for local tool | openai SDK with `base_url` overrides |
| `anthropic` | Not needed for v1.1 — openai SDK reaches Anthropic via compatible endpoint | openai SDK + `base_url="https://api.anthropic.com/v1/"` |
| `apscheduler>=4.0` | Completely different API from 3.x, migration is a rewrite | `apscheduler>=3.10.4,<4.0` |
| `dash` + `plotly` | 10x more code than streamlit for same result, requires layout/callback/server boilerplate | streamlit |
| `celery` | Requires Redis/RabbitMQ broker, distributed task system, massive overkill | apscheduler in-process |
| `neo4j-python-driver` | TTL is Python-level; no Neo4j | native Kuzu Cypher DELETE |
| `aiocron` | Less maintained, less features than apscheduler | `apscheduler>=3.10.4,<4.0` |

---

## Version Compatibility Matrix

| New Package | Existing Package | Status | Notes |
|-------------|-----------------|--------|-------|
| `apscheduler>=3.10.4,<4.0` | Python 3.12 | COMPATIBLE | APScheduler 3.10.4 supports Python 3.9+ |
| `apscheduler>=3.10.4,<4.0` | asyncio (existing) | COMPATIBLE | `AsyncIOScheduler` uses the existing event loop |
| `pyvis==0.3.2` | networkx>=3.3 | COMPATIBLE | pyvis 0.3.2 uses networkx 3.x API |
| `pyvis==0.3.2` | Python 3.12 | COMPATIBLE | pure Python, no compiled extensions |
| `streamlit>=1.42.0` | Python 3.12 | COMPATIBLE | Verified 3.12 support in Streamlit docs |
| `streamlit>=1.42.0` | httpx>=0.28.0 | VERIFY | Streamlit may pin httpx; check with `pip install --dry-run` |
| `openai>=2.0.0` | graphiti-core 0.28.1 | VERIFY CRITICAL | graphiti-core may pin openai 1.x internally |
| `openai>=2.0.0` | httpx>=0.28.0 | COMPATIBLE | openai SDK 2.x uses httpx |

**CRITICAL verify step for Phase 9:** Before adding `openai>=2.0.0`, inspect graphiti-core's requirements:
```bash
pip show graphiti-core
cat .venv/lib/python3.12/site-packages/graphiti_core-*.dist-info/METADATA | grep -i openai
```

---

## Updated pyproject.toml Structure

```toml
[project]
dependencies = [
    # existing v1.0 deps unchanged
    "detect-secrets>=1.5.0",
    "GitPython>=3.1.0",
    "graphiti-core[kuzu]==0.28.1",
    "httpx>=0.28.0",
    "kuzu==0.11.3",
    "mcp[cli]>=1.26.0,<2.0.0",
    "ollama==0.6.1",
    "persist-queue==1.1.0",
    "python-toon>=0.1.3",
    "structlog>=25.5.0",
    "tenacity==9.1.4",
    "typer>=0.15.0",
    # v1.1 additions (core — no optional group)
    "apscheduler>=3.10.4,<4.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
]
reranking = [
    "sentence-transformers>=2.0.0",
]
ui = [
    "pyvis==0.3.2",
    "networkx>=3.3",
    "streamlit>=1.42.0",
]
providers = [
    "openai>=2.0.0",
]
```

---

## Installation Commands

```bash
# Core v1.1 (includes apscheduler for retention)
pip install -e "."

# With graph UI
pip install -e ".[ui]"

# With multi-provider LLM support
pip install -e ".[providers]"

# All optional features
pip install -e ".[ui,providers,reranking]"

# Dev
pip install -e ".[dev]"
```

---

## Architecture Integration Notes

### Retention: where to hook in

The TTL sweep belongs in `src/graph/service.py` as a new `expire_stale_nodes(cutoff_days: int)` method. It runs:
1. On `graphiti ui` startup (sweep before displaying)
2. Via `apscheduler AsyncIOScheduler` triggered from `BackgroundWorker` startup
3. On-demand via `graphiti compact --expire`

No new module needed — extend `GraphService`.

### Graph UI: new module

```
src/
  ui/
    __init__.py
    app.py          # streamlit app: queries Kuzu, builds pyvis graph, st.components.v1.html()
    graph_builder.py # Kuzu → networkx → pyvis conversion
```

The `graphiti ui` CLI command calls `subprocess.run(["streamlit", "run", str(ui_app_path)])`.

### Multi-provider LLM: extend existing pattern

The existing `OllamaClient` in `src/llm/client.py` is not replaced. It remains for Ollama (cloud + local). A new `ProviderClient` class in `src/llm/provider_client.py` handles OpenAI-compatible providers. `load_config()` reads the `[provider]` section and returns a discriminated union: either `OllamaClient` or `ProviderClient`. The graphiti-core adapters (`OllamaLLMClient`, `OllamaEmbedder`) remain unchanged — they wrap whichever client is active.

---

## Sources

- [litellm PyPI](https://pypi.org/project/litellm/) — dependency list, latest version 1.81.x (Feb 2026) — MEDIUM confidence
- [litellm GitHub releases](https://github.com/BerriAI/litellm/releases) — version history — MEDIUM confidence
- [LiteLLM Review 2026](https://www.truefoundry.com/blog/a-detailed-litellm-review-features-pricing-pros-and-cons-2026) — stability concerns, 800+ open issues — MEDIUM confidence
- [openai PyPI](https://pypi.org/project/openai/) — latest 2.24.0 (Feb 2026) — HIGH confidence
- [anthropic PyPI](https://pypi.org/project/anthropic/) — latest 0.84.0 (Feb 2026) — HIGH confidence
- [groq PyPI](https://pypi.org/project/groq/) — latest 0.33.0 — HIGH confidence
- [Anthropic OpenAI SDK compatibility docs](https://docs.anthropic.com/en/api/openai-sdk) — verified openai SDK works with Anthropic endpoint — HIGH confidence
- [pyvis PyPI](https://pypi.org/project/pyvis/) — latest 0.3.2 (Jan 2025) — HIGH confidence
- [pyvis GitHub](https://github.com/WestHealth/pyvis) — maintenance status — MEDIUM confidence
- [streamlit PyPI](https://pypi.org/project/streamlit/) — latest 1.52.2 (Jan 2026), Python 3.12 supported — HIGH confidence
- [APScheduler PyPI](https://pypi.org/project/APScheduler/) — 3.10.4 stable, 4.x different API — HIGH confidence
- [Kuzu DELETE docs](https://docs.kuzudb.com/cypher/data-manipulation-clauses/delete/) — native DELETE WHERE timestamp support — HIGH confidence

---
*Stack research for: Graphiti Knowledge Graph v1.1 Advanced Features*
*Researched: 2026-03-01*
*Confidence: HIGH for approach decisions, MEDIUM for exact version pinning of new packages*
