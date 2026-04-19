# Phase 29: CLI Commands - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Source:** Pre-planning discussion

<domain>
## Phase Boundary

Wire all six CLI commands to the new stack. Replace the Phase 25 stubs with real implementations. Commands: `init`, `sync`, `search`, `health`, `config`, `ui`.

</domain>

<decisions>
## Implementation Decisions

### `recall config` — three subcommands
- `recall config show` — prints full `~/.recall/config.toml` to stdout (or message if not found)
- `recall config get <key>` — prints value for a dotted key (e.g. `recall config get llm.provider`)
- `recall config set <key> <value>` — sets a dotted key value and writes back to file

### Six commands only
- Exactly: `init`, `sync`, `search`, `health`, `config`, `ui`
- Legacy commands (`note`, `pin`, `unpin`, `delete`, `list`) must NOT appear in `--help`

### `recall search` flags
- `recall search "<query>"` — FTS5 keyword search
- `recall search "<query>" --semantic` — vector search (requires `[embeddings]` in config; actionable error if not configured)
- `recall search "<query>" --related` — includes one hop of backlinked entities below each result, labeled with relationship type

### `recall ui`
- Starts the FastAPI UI server (existing `src/ui_server/`)
- Opens browser automatically (or prints URL)

### `recall health`
- Calls Phase 27 health check logic
- Prints: provider name, model, status (OK | UNREACHABLE)
- Prints separate line for embeddings: configured+reachable | not configured
- Must complete within 5 seconds

### `recall init` / `recall sync`
- Thin wrappers over Phase 28 indexer
- `recall init` — full reindex
- `recall sync` — incremental; auto-runs init if no DB exists

### Config file format (canonical)
```toml
[llm]
provider = "claude"
model = "claude-haiku-4-5-20251001"
url = ""
api_key = ""

[embeddings]
provider = "ollama"
model = "nomic-embed-text"
url = "http://localhost:11434"
api_key = ""

[db]
path = ".recall/recall.db"
```

### Claude's Discretion
- Error message wording for missing config
- Output formatting for `recall search` results

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — Phase 29 success criteria
- `.planning/REQUIREMENTS.md` — CLI-01, CLI-02, CLI-03
- `src/cli/__init__.py` — Phase 25 stub (shows stub command list to replace)
- `CLAUDE.md` — typer usage, structlog

</canonical_refs>

<deferred>
## Deferred Ideas

- Shell completion (`recall --install-completion`) — Phase 33 polish
- `recall config edit` (open in $EDITOR) — deferred, get/set/show covers the use case

</deferred>

---
*Phase: 29-cli-commands*
*Context gathered: 2026-04-14 via pre-planning discussion*
