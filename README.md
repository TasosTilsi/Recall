# recall

> **Your project's engineering knowledge graph.** Index your entire git history into a searchable, interconnected knowledge graph — every decision, bug fix, pattern, and architectural change, linked by backlinks and queryable in seconds.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![SQLite](https://img.shields.io/badge/Database-SQLite-blue.svg)](https://sqlite.org/)

---

## What It Does

recall indexes your git history and builds a knowledge graph you can query:

- **"What decisions were made about the auth module?"**
- **"Show me all bug fixes related to the queue worker."**
- **"What patterns were introduced in Q1?"**
- **"Which files always change together?"**

Every commit is analyzed by an LLM and broken into typed entities (decisions, bug fixes, patterns, files, tech debt) with bidirectional backlinks connecting them across time.

---

## Install

### As a CLI tool

```bash
pipx install recall-kg
```

### As a Claude plugin

```bash
claude plugin install https://github.com/TasosTilsi/recall-kg
```

The plugin registers two slash commands and a read-only MCP server into your Claude settings automatically.

---

## Quick Start

```bash
# Configure your LLM provider
recall config init

# Index your repo (full, first time)
recall init

# Search the knowledge graph
recall search "why was the auth middleware changed"
recall search "database migration decisions"

# Open the visual graph explorer
recall ui
```

Or from inside Claude, after installing the plugin:

```
/recall-setup    → guided config + first index
/recall-index    → sync new commits into the graph
```

---

## Commands

| Command | Description |
|---------|-------------|
| `recall init` | Full index — wipes and rebuilds the graph from entire git history |
| `recall sync` | Incremental — indexes only new commits since last sync (auto-inits if no DB) |
| `recall search <query>` | Keyword search (FTS); add `--semantic` for vector similarity |
| `recall health` | Verify LLM provider + database status |
| `recall config` | View and edit `~/.recall/config.toml` |
| `recall ui` | Open graph explorer at `http://localhost:8765` |

Short alias: `rc` works everywhere `recall` does.

---

## Knowledge Graph

Each commit is extracted into typed entities connected by backlinks:

| Entity Type | What it captures |
|-------------|-----------------|
| `decision` | Architectural choices, "why we chose X over Y", trade-offs |
| `bug_fix` | What broke, root cause, how it was fixed, symptom |
| `pattern` | Conventions introduced or changed ("all hooks use structlog") |
| `file` | File-level change history and co-change relationships |
| `concept` | Domain concepts, abstractions, named components |
| `tech_debt` | Known burdens, deferred work, "why this exists" context |

**Backlinks** connect everything bidirectionally — a decision links to every commit that implemented it; a file links to every bug fix that touched it.

---

## Configuration

Config lives at `~/.recall/config.toml`:

```toml
# Use Claude (via claude-code subscription — no API key needed)
[llm]
provider = "claude"
model = "claude-sonnet-4-6"

# Or Ollama (local)
# [llm]
# provider = "ollama"
# base_url = "http://localhost:11434"
# model = "gemma2:9b"

# Or OpenAI / OpenRouter / any compatible endpoint
# [llm]
# provider = "openai"
# base_url = "https://openrouter.ai/api/v1"
# api_key = "sk-..."
# model = "anthropic/claude-3.5-sonnet"

# Optional: enable semantic (vector) search
# [embeddings]
# provider = "ollama"
# base_url = "http://localhost:11434"
# model = "nomic-embed-text"

[indexer]
batch_size = 10        # commits per LLM extraction call
```

One provider. No fallbacks. Clear failure when misconfigured.

---

## Architecture

```
src/
├── db/
│   ├── schema.py       # SQLite table definitions (commits, entities, backlinks, fts_index)
│   ├── queries.py      # Named SQL queries
│   └── backlinks.py    # Bidirectional traversal helpers
├── extractor/
│   ├── git.py          # GitPython: walk commits, extract diffs
│   ├── llm.py          # Single provider client (claude / ollama / openai)
│   └── parser.py       # LLM output → structured entities + backlinks
├── indexer/
│   └── indexer.py      # init (full rebuild) + sync (incremental)
├── cli/
│   └── commands/       # init, sync, search, health, config, ui
├── mcp_server/         # Read-only MCP tools (stdio, stderr-only logging)
├── ui_server/          # FastAPI + pre-built React frontend
└── config.py           # load_config() from ~/.recall/config.toml

ui/                     # Vite + React + Sigma.js + shadcn/ui
└── out/                # Pre-built static bundle (committed)

.claude/
└── skills/
    ├── recall-setup/   # /recall-setup Claude skill
    └── recall-index/   # /recall-index Claude skill
```

---

## Graph UI

```bash
recall ui
```

Opens at `http://localhost:8765`:

- **Graph** — Sigma.js WebGL view; nodes = entities, edges = backlinks; colored by type
- **Search** — full-text search with type filter
- **Detail panel** — click any node to see content, source commit, and all backlinks
- **Filter** — narrow to decisions / bug_fixes / patterns / files / tech_debt

---

## MCP Server

When installed as a Claude plugin, the read-only MCP server is registered automatically. Tools available to Claude:

| Tool | Description |
|------|-------------|
| `search_knowledge` | FTS search across all entities |
| `get_entity` | Get entity by id or name |
| `get_backlinks` | Traverse backlinks from an entity |
| `get_decisions` | List all decision entities |
| `get_bugs` | List all bug_fix entities |
| `get_patterns` | List all pattern entities |

---

## Development

```bash
git clone https://github.com/TasosTilsi/recall-kg
cd recall-kg

python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

recall health          # verify provider + DB
recall search "test"   # smoke test
pytest tests/ -x -q    # run test suite
```

---

## License

MIT License — see LICENSE file for details.

---

## Resources

- **SQLite FTS5**: [sqlite.org/fts5](https://sqlite.org/fts5.html)
- **sqlite-vec**: [github.com/asg017/sqlite-vec](https://github.com/asg017/sqlite-vec)
- **Ollama**: [ollama.ai](https://ollama.ai/)
- **Claude Code**: [claude.com/claude-code](https://claude.com/claude-code)
