# Phase 10: Configurable Capture Modes - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Named capture modes configurable via `llm.toml [capture]` section. Two modes: `decisions-only` (default, narrow) and `decisions-and-patterns` (broad). Active mode visible in `graphiti config show`. Security sanitization runs before any mode-based filtering — unconditional invariant regardless of mode.

</domain>

<decisions>
## Implementation Decisions

### What each mode captures

Mode controls the EXTRACT categories section of `BATCH_SUMMARIZATION_PROMPT` in `summarizer.py` — prompt-only approach, single injection point, no post-LLM filtering.

- **`decisions-only`** (default): EXTRACT only — Decisions & Rationale + Architecture & Patterns
- **`decisions-and-patterns`**: EXTRACT all 4 categories — Decisions & Rationale + Architecture & Patterns + Bug Fixes & Root Causes + Dependencies & Config
- EXCLUDE section is identical in both modes: raw code snippets, routine operations, WIP/scratch content — no relaxation in either mode
- Security gate (sanitize_content) runs before the prompt is built, unconditional

### Mode scope — what it applies to

Mode applies to any pipeline that goes through `summarizer.py`:
- Git post-commit hook captures
- Claude Code conversation hook captures
- MCP `graphiti_capture` tool
- `graphiti index` (git history re-indexing)

Mode does NOT apply to:
- `graphiti add <text>` — manual add stores verbatim, unfiltered, no summarization stage

### Config display in `graphiti config show`

- New **"Capture Settings"** section added to the Rich table with `capture.mode` row
- Phase 10 also adds a **"Retention Settings"** section for `retention_days` (fixing Phase 9 omission where it was added to `LLMConfig` but never surfaced in `config show`)
- `graphiti config --set capture.mode=decisions-and-patterns` works — `capture.mode` added to `VALID_CONFIG_KEYS` with enum validation; users can set via CLI or edit `llm.toml` directly

### Invalid mode handling

- **`config --set` with invalid value**: rejected at set time with clear error — "Valid values: decisions-only, decisions-and-patterns"
- **`llm.toml` with invalid value**: structlog warning at load time + fall back to `decisions-only` (same pattern as `retention_days` minimum enforcement)
- **No `[capture]` section in `llm.toml`**: default to `decisions-only` — existing users get same behavior without touching their config

### Claude's Discretion

- Exact prompt wording for the two EXTRACT sections
- Whether to expose prompts as constants vs inline strings
- How to thread `capture_mode` through the call chain from `load_config()` to `summarize_batch()`

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `src/capture/summarizer.py` — `BATCH_SUMMARIZATION_PROMPT` with EXTRACT/EXCLUDE structure; mode splits into two prompt templates or a conditional EXTRACT block. `summarize_batch()` is the single injection point.
- `src/llm/config.py` — `LLMConfig` frozen dataclass; `load_config()` reads TOML sections. Add `capture_mode: str = "decisions-only"` and parse `[capture]` section with validation (same pattern as `retention_days` minimum check).
- `src/cli/commands/config.py` — `VALID_CONFIG_KEYS` dict drives `config --set` validation; `config_command()` builds the Rich table. Add `capture.mode` to keys, add Capture + Retention sections to the table display.
- `src/cli/utils.py` — no changes needed

### Established Patterns

- `[section]` TOML structure for config areas (Phase 9: `[retention]`); `[capture]` follows same pattern
- `LLMConfig` frozen dataclass extension: add field with default, parse in `load_config()` under new section key
- Invalid config value handling: structlog warning + fall back to safe default (Phase 9: `retention_days` < 30)
- `VALID_CONFIG_KEYS` enum-style validation: add `capture.mode` with `"type": str` and allowed values list

### Integration Points

- `summarize_batch()` in `summarizer.py` needs `capture_mode` parameter (or reads from `load_config()`)
- `summarize_and_store()` is the call site in the hook/index pipeline — needs to pass mode through
- `config show` table in `config.py` — add two new section groups (Capture + Retention)
- No hook installer changes needed; mode is read inside the summarization layer

</code_context>

<specifics>
## Specific Ideas

- The key insight from discussion: the existing 4-category prompt is NOT decisions-only — it already captures bugs and deps. Phase 10 makes this explicit by splitting into two distinct prompt variants.
- Decisions-only = high-signal mode: only "why X was chosen" and "system structure" — no operational noise
- Decisions-and-patterns = current full behavior, now named and opt-in

</specifics>

<deferred>
## Deferred Ideas

- Per-scope capture mode (independent global vs. project config) — noted as CAPT-04 in REQUIREMENTS.md v2+ backlog
- `--mode` flag on individual commands to override config per-call — mentioned in discussion, deferred; config-level mode is sufficient for v1.1

</deferred>

---

*Phase: 10-configurable-capture-modes*
*Context gathered: 2026-03-06*
