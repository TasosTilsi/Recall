# recall

> **Never repeat context again.** A local developer memory system that automatically captures tool call context and injects relevant knowledge before every Claude Code prompt — entirely local, never blocking your workflow.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![LadybugDB](https://img.shields.io/badge/Database-LadybugDB-green.svg)](https://github.com/bwJoint/ladybugdb)

---

## The Problem

You're working in Claude Code. You explain your tech stack, coding style, and project architecture. Next session? You explain it again. And again. Context is lost between sessions.

**recall solves this:**
- Automatically captures decisions and architecture from every session
- Injects relevant past knowledge before every prompt via Claude Code hooks
- Keeps sensitive data (secrets, PII) completely out of the graph
- Project knowledge stays in your git repo — shareable with your team
- Runs locally, never blocks your workflow

---

## Quick Start

### Installation

```bash
git clone git@github.com:TasosTilsi/Graphiti-Knowledge-Graph.git
cd Graphiti-Knowledge-Graph

python3.12 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
```

### One-command setup

```bash
recall init          # installs hooks, creates config, indexes git history
```

This installs 5 Claude Code hooks into `~/.claude/settings.json` and sets up your local knowledge graph at `~/.recall/global/` and `.recall/` in your project.

---

## Commands

| Command | Description |
|---------|-------------|
| `recall init` | One-command setup: install hooks, create config, index git history |
| `recall search <query>` | Natural language search (auto-syncs git before results) |
| `recall list` | List stored knowledge (`--stale`, `--compact`, `--queue` flags) |
| `recall delete <id>` | Remove an entry from the graph |
| `recall pin <id>` | Pin an entry (exempt from retention cleanup) |
| `recall unpin <id>` | Unpin an entry |
| `recall health` | System health check: backend, LLM provider, hooks status |
| `recall config` | View and edit configuration |
| `recall ui` | Open the graph browser UI at localhost:8765 |
| `recall note <text>` | Manually add a memory entry |

Short alias: `rc` works everywhere `recall` does.

---

## How It Works

Four Claude Code hook scripts run automatically during your sessions:

| Hook | Trigger | Action |
|------|---------|--------|
| `session_start.py` | `SessionStart` | Writes session UUID, runs incremental git index |
| `inject_context.py` | `UserPromptSubmit` | Searches graph, injects `<session_context>` block (≤4000 tokens) |
| `capture_entry.py` | `PostToolUse` | Appends tool call data to queue (fire-and-forget, <1s) |
| `session_stop.py` | `Stop` / `PreCompact` | Drains queue, generates session summary episode |

No manual steps. Just work — `recall` remembers.

---

## Architecture

```
~/.recall/global/          # Global preferences (cross-project)
.recall/                   # Project knowledge (git-safe)
~/.recall/llm.toml         # LLM provider config

src/
├── cli/                   # Typer CLI (recall/rc entrypoints)
│   └── commands/          # init, search, list, delete, pin, unpin,
│                          # health, config, ui, note
├── hooks/                 # Claude Code hook scripts
│   ├── session_start.py   # SessionStart: UUID + git sync
│   ├── inject_context.py  # UserPromptSubmit: context injection
│   ├── capture_entry.py   # PostToolUse: queue append
│   └── session_stop.py    # Stop/PreCompact: drain + summarize
├── graph/
│   ├── service.py         # GraphService — all graph operations
│   └── adapters.py        # LLM client + embedder factories
├── storage/
│   ├── graph_manager.py   # Backend routing (LadybugDB / Neo4j)
│   └── ladybug_driver.py  # LadybugDB driver
├── llm/
│   ├── config.py          # LLMConfig dataclass, load_config()
│   └── provider.py        # OpenAI-compatible provider client
├── queue/
│   └── worker.py          # BackgroundWorker for async capture
└── ui_server/             # FastAPI server + Vite frontend

ui/                        # Vite + React + Sigma.js + shadcn/ui
└── out/                   # Pre-built frontend (committed)
```

---

## Configuration

Config lives at `~/.recall/llm.toml`:

```toml
# Local Ollama (default)
[local]
models = ["gemma2:9b"]

[embeddings]
models = ["nomic-embed-text"]

# Optional: switch to any OpenAI-compatible provider
# [llm]
# primary_url = "https://api.openai.com/v1"
# primary_api_key = "sk-..."
# primary_models = ["gpt-4o-mini"]
# embed_url = "http://localhost:11434"
# embed_models = ["nomic-embed-text"]

# Optional: Neo4j backend (default is embedded LadybugDB)
# [backend]
# type = "neo4j"
# uri = "bolt://localhost:7687"
```

---

## Storage Backends

| Backend | Default | Use case |
|---------|---------|----------|
| **LadybugDB** | Yes | Embedded, no Docker, zero config |
| **Neo4j** | No (opt-in) | Teams, power users, Docker Compose |

For Neo4j: `docker compose -f docker-compose.neo4j.yml up -d`

---

## Graph UI

```bash
recall ui
```

Opens at `http://localhost:8765`. Features:
- **Dashboard** — entity stats, activity heatmap, retention breakdown
- **Graph** — interactive Sigma.js WebGL view with FA2 physics
- **Entities / Relations / Episodes** — sortable tables with detail panel
- **Search** — full-text search across all graph data
- Scope toggle (project / global), retention filters (pinned / stale / archived)

---

## Security

All content is sanitized before storage:
- Pattern detection for API keys, tokens, credentials
- Entropy analysis for high-entropy strings
- `detect-secrets` integration for industry-standard scanning

What gets captured: decisions, architecture patterns, technology choices, coding conventions.

What gets filtered: API keys, database passwords, private keys, `.env` contents, PII.

---

## Testing

```bash
pytest tests/                    # full suite
pytest tests/ -m "not integration"  # skip Ollama-dependent tests
pytest tests/test_cli_rename.py  # CLI surface tests
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `graphiti-core[neo4j]==0.28.1` | Knowledge graph engine |
| `real-ladybug==0.15.1` | Embedded graph database |
| `ollama==0.6.1` | Local LLM + embeddings client |
| `sentence-transformers` | Semantic embeddings |
| `typer` | CLI framework |
| `fastapi` + `uvicorn` | UI server |
| `detect-secrets` | Secret scanning |
| `persist-queue` | Async capture queue |
| `structlog` | Structured logging |
| `mcp[cli]` | MCP server protocol |

Optional: `pip install -e ".[reranking]"` enables BGE cross-encoder reranking (heavier sentence-transformers usage).

---

## Development

```bash
pip install -e ".[dev]"

recall health               # verify everything is wired
recall search "test query"  # end-to-end smoke test
pytest tests/ -x -q         # run test suite
```

---

## License

MIT License — see LICENSE file for details.

---

## Resources

- **graphiti-core**: [github.com/getzep/graphiti](https://github.com/getzep/graphiti)
- **LadybugDB**: embedded graph backend
- **Ollama**: [ollama.ai](https://ollama.ai/)
- **Claude Code**: [claude.com/claude-code](https://claude.com/claude-code)
