# Phase 32: Claude Plugin + Skills - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Source:** Pre-planning discussion

<domain>
## Phase Boundary

Create the Claude plugin: manifest, two skill definitions (`/recall-setup`, `/recall-index`), and the installation mechanism that writes to `~/.claude/settings.json`. Skills guide users through setup and indexing.

</domain>

<decisions>
## Implementation Decisions

### Installation writes to ~/.claude/settings.json
- Plugin install adds MCP server entry under `mcpServers`:
  ```json
  {
    "mcpServers": {
      "recall": {
        "command": "recall",
        "args": ["mcp", "serve"]
      }
    }
  }
  ```
- Creates `~/.recall/` if not present
- Leaves existing `~/.recall/config.toml` unchanged if already present

### `/recall-setup` skill
- Interactive walkthrough: asks provider, model, sets `~/.recall/config.toml`
- Ends by running `recall health` and confirming it passes

### `/recall-index` skill
- Runs `recall sync` (or `recall init` if no DB exists)
- Reports: commit count processed, entity type breakdown

### LLM for skills: subprocess
- Skills that invoke `recall` commands use `claude -p` subprocess pattern (same as Phase 27)

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
- Plugin manifest format details
- Skill SKILL.md content/structure

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — Phase 32 success criteria
- `.planning/REQUIREMENTS.md` — SKILL-01, SKILL-02, INST-02, INST-03
- `~/.claude/settings.json` — target file for MCP registration (read structure before writing)
- `CLAUDE.md` — project skill conventions if .claude/skills/ exists

</canonical_refs>

<deferred>
## Deferred Ideas

- Auto-update mechanism for plugin — Phase 33 polish or future milestone

</deferred>

---
*Phase: 32-claude-plugin-skills*
*Context gathered: 2026-04-14 via pre-planning discussion*
