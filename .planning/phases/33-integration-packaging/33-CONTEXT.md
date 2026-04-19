# Phase 33: Integration + Packaging - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Source:** Pre-planning discussion

<domain>
## Phase Boundary

Final integration: `pipx install recall-kg` works on a clean machine. End-to-end smoke test (`recall init` → `recall search` → `recall mcp serve`). Ensure `pytest tests/` passes (tests added by Phases 26–32).

</domain>

<decisions>
## Implementation Decisions

### Package name: recall-kg
- `pyproject.toml` already renamed to `recall-kg` in Phase 25
- Verify `pipx install recall-kg` installs correctly (may require PyPI publish or local wheel test)
- Entry points: `recall` and `rc` both point to `src.cli:cli_entry`

### Test suite
- `pytest tests/` must pass — each upstream phase (26–32) adds its own tests
- Phase 33 adds the end-to-end integration test only (not unit tests for earlier phases)
- E2E test: `recall init` → `recall search "fix"` → `recall mcp serve` (10-second smoke)

### Smoke test sequence
1. `pip install -e .` in fresh venv — succeeds without conflicts
2. `recall init` — indexes current repo
3. `recall search "fix"` — returns results
4. `recall mcp serve` — starts, receives a test MCP call, exits cleanly (10s timeout)

### DB path: project-local
- Smoke test uses `.recall/recall.db` in the test repo

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
- Wheel build vs. local path install for smoke test
- Test isolation strategy for E2E (temp dirs, cleanup)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — Phase 33 success criteria
- `.planning/REQUIREMENTS.md` — INST-01
- `pyproject.toml` — packaging config (primary modification target)
- `CLAUDE.md` — project standards

</canonical_refs>

<deferred>
## Deferred Ideas

- PyPI publish automation — manual publish for v3.0, automate later
- CI/CD pipeline — out of scope for v3.0

</deferred>

---
*Phase: 33-integration-packaging*
*Context gathered: 2026-04-14 via pre-planning discussion*
