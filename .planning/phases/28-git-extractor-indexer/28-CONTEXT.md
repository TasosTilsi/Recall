# Phase 28: Git Extractor + Indexer - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Source:** Pre-planning discussion

<domain>
## Phase Boundary

Implement `src/extractor/` and wire `src/indexer/` — batch LLM extraction from git history with `recall init` (full) and `recall sync` (incremental) modes. Populates the SQLite DB (Phase 26) using the LLM client (Phase 27).

</domain>

<decisions>
## Implementation Decisions

### Init vs Sync modes
- `recall init`: deletes and repopulates DB — deterministic upsert so re-running produces same entity count
- `recall sync`: processes only commits newer than `last_indexed_sha` stored in `metadata` table
- `recall sync` with no existing DB: automatically runs full init without prompting

### Batch size
- Planner decides optimal batch size (v2.0 used 10 commits per LLM call as reference)
- Progress must be logged at batch boundaries: "Processing commits 1–10 of 200"

### Entity extraction
- Six entity types: `decision`, `bug_fix`, `pattern`, `file`, `concept`, `tech_debt`
- Entity `name` values must be lowercase, trimmed (no leading/trailing whitespace)
- Extraction via `claude -p` subprocess (Phase 27 LLM client)
- Planner decides exact prompt/schema format

### DB path
- Project-local: `.recall/recall.db` relative to git repo root
- Use `src/db/` module from Phase 26 for all DB operations

### Config file format (canonical)
```toml
[llm]
provider = "claude"
model = "claude-haiku-4-5-20251001"
url = ""
api_key = ""

[embeddings]                           # optional
provider = "ollama"
model = "nomic-embed-text"
url = "http://localhost:11434"
api_key = ""

[db]
path = ".recall/recall.db"
```

### Claude's Discretion
- Exact batch size (optimize for cost vs. speed)
- Extraction prompt design
- Concurrency/semaphore settings

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — Phase 28 success criteria
- `.planning/REQUIREMENTS.md` — IDX-01 through IDX-05
- `src/indexer/indexer.py` — v2.0 GitIndexer (reference for git walk logic, will be updated)
- `src/indexer/extraction.py` — v2.0 extraction (reference, will be replaced)
- `CLAUDE.md` — async patterns, structlog usage

</canonical_refs>

<deferred>
## Deferred Ideas

- Webhook-triggered sync — not needed for v3.0
- Parallel per-commit extraction — may cause LLM rate limits; batch sequential is safer

</deferred>

---
*Phase: 28-git-extractor-indexer*
*Context gathered: 2026-04-14 via pre-planning discussion*
