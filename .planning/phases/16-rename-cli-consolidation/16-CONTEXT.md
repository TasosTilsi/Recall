# Phase 16: Rename & CLI Consolidation - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Rename entrypoints (`graphiti` → `recall`, `gk` → `rc`), expose exactly 10 public commands, remove all plumbing commands from the codebase. No new capabilities — only reorganization of the existing surface.

</domain>

<decisions>
## Implementation Decisions

### Public Command Surface (10 commands)

The public surface exposed in `recall --help`:

| Command | What it does | Absorbs |
|---------|-------------|---------|
| `init` | Install hooks + full git index + write static llm.toml template | `hooks`, `index` |
| `search` | Search knowledge graph (auto-syncs git first) | — |
| `list` | Browse entities; detail/stale/compact/queue via flags | `show`, `stale`, `compact`, `queue` |
| `delete` | Delete entity by name/UUID | — |
| `pin` | Protect node from TTL archiving | — |
| `unpin` | Remove TTL protection | — |
| `health` | System status | — |
| `config` | View/modify llm.toml | — |
| `ui` | Launch graph visualization | — |
| `note` | Manually add a memory | `add` |

**`recall list` flags:**
- `recall list <name>` — entity detail (replaces `show`)
- `recall list --stale` — preview TTL candidates (replaces `stale`)
- `recall list --compact` — expire stale nodes (replaces `compact`)
- `recall list --queue` — show background queue status (replaces `queue`)

### Hidden Command: recall index

`recall index` is a hidden command (not shown in `--help`) for power users and hook scripts:

- `recall index` (no flags) — incremental indexing (new commits only, skips if within 5-min cooldown)
- `recall index --force` — wipe existing index and re-index entire history from scratch (replaces old `--full`)
- Hidden registration: `app.command(name="index", hidden=True)`
- `index.py` is NOT deleted — it is updated (`--full` → `--force`) and kept

### Removed Commands (fully deleted from codebase)

All of the following are fully removed — not hidden, not deprecated, deleted:
`add`, `capture`, `compact`, `hooks`, `memory`, `mcp`, `queue`, `show`, `stale`, `summarize`, `sync`

**sync is truly deleted** — no `recall sync` command exists anywhere. The sync logic lives inside:
- `recall search` (auto-syncs incrementally before every query, via `_auto_sync()`)
- `recall index` (full or incremental indexing)
- `session_start.py` (calls `GitIndexer` directly in Python — no subprocess)

Note: `mcp` functionality (serving the MCP server) is internal — the MCP server is started by Claude Desktop via config, not by users directly. The `mcp install` subcommand logic moves into `recall init`.

### recall init scope

Bundles into a single idempotent command:
1. Install 4 Claude Code hook scripts to `~/.claude/settings.json` (additive, no data changes)
2. Run full git history index (bootstrap the graph from git log)
3. Write `~/.graphiti/llm.toml` **static template** if missing — no interactive prompts
4. Register MCP server in Claude Desktop config (same as current `hooks install` does)

**Config setup:** `recall init` writes a static TOML template to `~/.graphiti/llm.toml` if the file does not exist (or always if `--force`). The user edits the file to customize provider, model, and API key. No interactive prompting.

**Failure mode:** Warn on each skipped/failed step, continue with remaining steps. Idempotent — safe to re-run.

**No git repo:** Warn "No git repo found — skipping git history index". Continue with hooks + config.

**Hooks already installed:** Warn "Hooks already installed — skipping". Continue.

### Old Entrypoints

- `graphiti` and `gk` **hard removed** from `pyproject.toml` — no shim, no deprecation warning
- Clean break: users who haven't upgraded get shell "command not found"
- All Phase 15 hook scripts (`session_start.py`, `capture_entry.py`, `session_stop.py`, `inject_context.py`) updated to call `recall` instead of `graphiti`

### session_start.py hook

`session_start.py` calls `GitIndexer` directly in Python rather than via a subprocess to any binary. Rationale:
- There is no `recall sync` command (sync is deleted)
- Direct Python call is more robust in hook context (no PATH issues, no binary name dependency, no subprocess timeout management)
- `GitIndexer.run(full=False)` has its own built-in 5-minute cooldown

### recall note

- Writes a JSON line to `.graphiti/pending_tool_captures.jsonl` matching the `capture_entry.py` format
- Processed by `session_stop.py` on next PreCompact — same pipeline as PostToolUse hook
- Argument-only: `recall note "decision: use JWT auth"` — no stdin piping
- Fail-open: any exception exits 0 (consistent with hook script behavior)

</decisions>

<canonical_refs>
## Canonical References

No external specs — requirements fully captured in decisions above.

### Requirements
- `CLI-01`: `recall` + `rc` entrypoints, `graphiti`/`gk` removed
- `CLI-02`: `recall --help` shows exactly 10 commands (updated to 10 with `note`)
- `CLI-03`: `recall search` auto-syncs before returning results

### Key source files to read before planning
- `src/cli/__init__.py` — current command registration (20 commands)
- `src/cli/commands/hooks.py` — current hooks CLI (install logic moves into init)
- `src/cli/commands/index.py` — current index command (kept hidden; --full renamed to --force)
- `src/hooks/installer.py` — `install_global_hooks()` called by recall init
- `src/hooks/session_start.py`, `src/hooks/capture_entry.py`, `src/hooks/session_stop.py`, `src/hooks/inject_context.py` — must be updated from `graphiti` → `recall`
- `pyproject.toml` — entrypoints to update

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/hooks/installer.py` — `install_global_hooks()` + `is_global_hooks_installed()` already exist (Phase 15-01)
- `src/indexer.GitIndexer` — `GitIndexer(project_root=root).run(full=False)` for incremental; `reset_full()` + `run()` for full
- `src/cli/commands/config.py` — `init_command` exists but recall init writes its own static template directly
- `src/cli/commands/list_cmd.py` — add `--stale`, `--compact`, `--queue` flags here
- `src/cli/commands/search.py` — add auto-sync call at entry (CLI-03)

### Integration Points
- `pyproject.toml` `[project.scripts]` — change `graphiti`/`gk` → `recall`/`rc`; add `cli_entry` function alias
- `src/cli/__init__.py` — remove 11 command registrations, rename app, update help text, add hidden `index`
- Hook scripts — string replace `graphiti` → `recall` in subprocess calls; session_start replaces subprocess with direct GitIndexer call

### Patterns
- Typer app with `add_typer()` for sub-apps — existing pattern for `config`, `hooks`, `mcp`, `queue`
- Commands that wrap other commands: `recall init` orchestrates installer + indexer + config gen
- Hidden Typer commands: `app.command(name="index", hidden=True)` — callable but not shown in --help

</code_context>

<specifics>
## Specific Ideas

- User wants this project to eventually become a Claude Code plugin (registry-based distribution, auto-setup on install). Not Phase 16 scope — captured in deferred.
- `recall note` writes to the same `.graphiti/pending_tool_captures.jsonl` queue as the PostToolUse hook — no separate processing path needed.

</specifics>

<deferred>
## Deferred Ideas

- **Claude Code plugin distribution model** — Convert `recall` into a proper Claude Code plugin so it can be installed/updated/distributed via the plugin registry. Auto-installs hooks, MCP, and skills on install. Future milestone.
- **`/recall-setup` Claude Code skill** — Conversational config helper skill for first-time setup. Future phase.
- **`graphiti`/`gk` deprecation shim** — User chose hard remove. If needed later, a shim can be added as a patch.
- **Interactive `recall init` config prompts** — User chose static template approach. Interactive prompting deferred to future phase if needed.

</deferred>

---

*Phase: 16-rename-cli-consolidation*
*Context gathered: 2026-03-20*
*Decisions updated: 2026-03-20 (sync deleted, index hidden with --force, init writes static template)*
