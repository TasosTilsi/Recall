# Phase 26: DB Schema - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Source:** Pre-planning discussion

<domain>
## Phase Boundary

Create the SQLite database module at `src/db/`. Implement schema with FTS5, backlinks with auto-inverse, optional embeddings table, and a clean Python API for all DB operations. This is the data foundation all subsequent phases build on.

</domain>

<decisions>
## Implementation Decisions

### Database location
- DB path is **project-local**: `.recall/recall.db` relative to the git repo root (not `~/.recall/`)
- The `[db]` section in `~/.recall/config.toml` can override this default
- `src/db/` module must auto-detect the project root (walk up from CWD to find `.git/`) to place the DB correctly

### Config file format (canonical — all phases use this)
```toml
[llm]
provider = "claude"                    # claude | ollama | openai
model = "claude-haiku-4-5-20251001"   # default for claude
url = ""                               # ollama/openai only
api_key = ""                           # openai or ollama cloud

[embeddings]                           # optional — omit to disable embeddings table
provider = "ollama"
model = "nomic-embed-text"
url = "http://localhost:11434"
api_key = ""                           # ollama cloud

[db]                                   # optional — omit for project-local default
path = ".recall/recall.db"
```

### Schema tables
Required: `commits`, `entities`, `backlinks`, `metadata`
- `entities` must enforce six valid types via CHECK constraint: `decision`, `bug_fix`, `pattern`, `file`, `concept`, `tech_debt`
- `backlinks` must auto-create inverse row via TRIGGER (insert A→B creates B→A with inverse label)
- `entities_fts` FTS5 virtual table indexes `name` and `content` columns of `entities`
- `embeddings` table only created when `[embeddings]` section present in config

### Claude's Discretion
- Exact column names and types (follow success criteria as spec)
- Migration strategy (simple CREATE IF NOT EXISTS for v3.0 — no alembic)
- Python API surface for DB operations (keep minimal: init, insert, query)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — Phase 26 success criteria (authoritative spec)
- `.planning/REQUIREMENTS.md` — KG-01 through KG-05
- `CLAUDE.md` — project coding standards (structlog, async patterns)

</canonical_refs>

<deferred>
## Deferred Ideas

- Full migration system (alembic/yoyo) — not needed for v3.0 single-schema release
- Multi-database support — single SQLite file per project only

</deferred>

---
*Phase: 26-db-schema*
*Context gathered: 2026-04-14 via pre-planning discussion*
