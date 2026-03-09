# Phase 10: Configurable Capture Modes - Research

**Researched:** 2026-03-06
**Domain:** Prompt template parameterization, config extension, CLI display
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Mode semantics:**
- `decisions-only` (default): EXTRACT only Decisions & Rationale + Architecture & Patterns
- `decisions-and-patterns`: EXTRACT all 4 categories — Decisions & Rationale + Architecture & Patterns + Bug Fixes & Root Causes + Dependencies & Config
- EXCLUDE section is identical in both modes (raw code, routine ops, WIP/scratch) — no relaxation
- Security gate (`sanitize_content`) runs BEFORE the prompt is built, unconditional in all cases

**Mode scope:**
- Applies to every pipeline that calls `summarizer.py`: git post-commit hook, conversation hook, MCP `graphiti_capture`, `graphiti index`
- Does NOT apply to `graphiti add <text>` — manual add is verbatim, no summarization

**Config display:**
- New "Capture Settings" section in the Rich table showing `capture.mode`
- New "Retention Settings" section for `retention_days` (fixing Phase 9 omission)
- `graphiti config --set capture.mode=decisions-and-patterns` works — `capture.mode` added to `VALID_CONFIG_KEYS` with enum validation

**Invalid mode handling:**
- `--set` with invalid value: rejected at set-time with "Valid values: decisions-only, decisions-and-patterns"
- `llm.toml` with invalid value: structlog warning + fall back to `decisions-only`
- No `[capture]` section: default to `decisions-only`

### Claude's Discretion

- Exact prompt wording for the two EXTRACT sections
- Whether to expose prompts as constants vs inline strings
- How to thread `capture_mode` through the call chain from `load_config()` to `summarize_batch()`

### Deferred Ideas (OUT OF SCOPE)

- Per-scope capture mode (independent global vs. project config) — CAPT-04 v2+ backlog
- `--mode` flag on individual commands to override config per-call
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CAPT-01 | User can set `[capture] mode = "decisions-only"` in `llm.toml` to capture only decisions and architectural choices | New `[capture]` TOML section parsed in `load_config()`; `capture_mode` field on `LLMConfig`; separate prompt constant for narrow mode |
| CAPT-02 | User can set `[capture] mode = "decisions-and-patterns"` in `llm.toml` to also capture bugs and dependencies | Same config extension; broad prompt constant includes all 4 EXTRACT categories; threaded into `summarize_batch()` |
| CAPT-03 | User can see the active capture mode in `graphiti config show` output | New "Capture Settings" section added to Rich table; `capture.mode` row; also add "Retention Settings" section for `retention_days` |
</phase_requirements>

---

## Summary

Phase 10 is a focused parameterization of the existing prompt-only summarization pipeline. The implementation surface is narrow and well-bounded: one new config field, two prompt constants, a single injection point, and a CLI display addition. No new dependencies, no new modules, no schema changes.

The key architectural insight (from CONTEXT.md) is that the current `BATCH_SUMMARIZATION_PROMPT` already captures all 4 categories. Phase 10 makes this explicit: `decisions-only` becomes the new default (narrow, high-signal), and `decisions-and-patterns` is the opt-in broad mode that matches the current implicit behavior. Security sanitization (`sanitize_content`) is an unconditional gate that precedes any mode-based prompt selection — this invariant must never be inverted.

Threading `capture_mode` through the call chain is Claude's discretion. The two viable approaches are: (A) read `load_config()` inside `summarize_batch()` directly, or (B) pass `capture_mode` as a parameter through `summarize_and_store` → `summarize_batch`. Option B is more testable and explicit; option A keeps the signature stable. The planner should choose based on test isolation preference.

**Primary recommendation:** Implement as two named prompt constants (`BATCH_SUMMARIZATION_PROMPT_NARROW` and `BATCH_SUMMARIZATION_PROMPT_BROAD`), pass `capture_mode: str = "decisions-only"` as a parameter to `summarize_batch()` and `summarize_and_store()`, and load the value from `load_config()` at the call sites in `git_worker.py` and `conversation.py`.

---

## Standard Stack

### Core (all existing — no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `tomllib` | stdlib | Parse `[capture]` TOML section | Already used in `load_config()` |
| `dataclasses` | stdlib | Add `capture_mode` field to `LLMConfig` | Frozen dataclass pattern already established |
| `rich.table` | existing dep | Add Capture/Retention sections to config show | Already used in `config_command()` |
| `structlog` | existing dep | Warning log on invalid mode value | Already used throughout |

### No New Dependencies
Phase 10 requires zero new packages. All functionality is prompt string switching and config field extension.

---

## Architecture Patterns

### Recommended Project Structure

No new files required. All changes are confined to existing files:

```
src/
  capture/
    summarizer.py       # Add 2 prompt constants + capture_mode param
  llm/
    config.py           # Add capture_mode field + [capture] section parsing
  cli/
    commands/config.py  # Add VALID_CONFIG_KEYS entry + 2 table sections
tests/
  test_capture_modes.py   # NEW — unit tests for CAPT-01, CAPT-02, CAPT-03
```

### Pattern 1: Two Prompt Constants (NOT dynamic string building)

**What:** Define `BATCH_SUMMARIZATION_PROMPT_NARROW` and `BATCH_SUMMARIZATION_PROMPT_BROAD` as module-level string constants. Select in `summarize_batch()` based on `capture_mode` parameter.

**When to use:** Always. Avoids runtime string concatenation bugs; makes both prompts independently reviewable; constants can be imported in tests.

**Example:**
```python
# src/capture/summarizer.py
BATCH_SUMMARIZATION_PROMPT_NARROW = """You are summarizing a development session from {source}.

INPUT: {count} {items} with full context below.

EXTRACT ONLY:
1. **Decisions & Rationale**: Why something was chosen over alternatives
2. **Architecture & Patterns**: System structure, component relationships, design patterns

EXCLUDE:
- Raw code snippets (store WHAT/WHY, not HOW)
- Routine operations ("ran tests", "formatted code")
- WIP/scratch content (fixup commits, debugging traces)

SPECIAL NOTE - Merge commit deduplication:
- If merge commit content overlaps with individual commits in this batch, skip redundant information
- Focus on unique knowledge not already covered by constituent commits

OUTPUT: Single cohesive session summary as a knowledge graph entity.
Focus on knowledge that helps understand the system's evolution and design decisions.

---
{content}
---

Summarize the session:"""

BATCH_SUMMARIZATION_PROMPT_BROAD = """You are summarizing a development session from {source}.

INPUT: {count} {items} with full context below.

EXTRACT ONLY:
1. **Decisions & Rationale**: Why something was chosen over alternatives
2. **Architecture & Patterns**: System structure, component relationships, design patterns
3. **Bug Fixes & Root Causes**: What went wrong, why, how it was fixed
4. **Dependencies & Config**: Libraries added/removed, config changes, environment setup

EXCLUDE:
- Raw code snippets (store WHAT/WHY, not HOW)
- Routine operations ("ran tests", "formatted code")
- WIP/scratch content (fixup commits, debugging traces)

SPECIAL NOTE - Merge commit deduplication:
- If merge commit content overlaps with individual commits in this batch, skip redundant information
- Focus on unique knowledge not already covered by constituent commits

OUTPUT: Single cohesive session summary as a knowledge graph entity.
Focus on knowledge that helps understand the system's evolution and design decisions.

---
{content}
---

Summarize the session:"""

VALID_CAPTURE_MODES = {"decisions-only", "decisions-and-patterns"}
```

### Pattern 2: LLMConfig Extension (frozen dataclass)

**What:** Add `capture_mode: str = "decisions-only"` to `LLMConfig`. Parse `[capture]` section in `load_config()` with validation identical to `retention_days` minimum check pattern.

**When to use:** Exactly as done in Phase 9 for `retention_days`. This is the established pattern.

**Example:**
```python
# src/llm/config.py — additions to existing dataclass + load_config()

@dataclass(frozen=True)
class LLMConfig:
    # ... existing fields ...
    capture_mode: str = "decisions-only"  # "decisions-only" | "decisions-and-patterns"


def load_config(config_path: Path | None = None) -> LLMConfig:
    # ... existing parsing ...
    capture = config_data.get("capture", {})
    raw_mode = capture.get("mode", "decisions-only")
    VALID_MODES = {"decisions-only", "decisions-and-patterns"}
    if raw_mode not in VALID_MODES:
        import structlog as _structlog
        _structlog.get_logger(__name__).warning(
            "invalid capture_mode, falling back to decisions-only",
            configured=raw_mode,
            valid=sorted(VALID_MODES),
        )
        raw_mode = "decisions-only"

    return LLMConfig(
        # ... existing kwargs ...
        capture_mode=raw_mode,
    )
```

### Pattern 3: summarize_batch() parameter threading

**What:** Add `capture_mode: str = "decisions-only"` to `summarize_batch()` and `summarize_and_store()`. Call sites (`git_worker.py`, `conversation.py`) load config and pass the value. The `summarize_batch()` function selects the prompt based on this parameter.

**When to use:** Preferred over reading `load_config()` inside `summarize_batch()` — keeps LLM config dependency explicit, simplifies mocking in tests.

**Example:**
```python
# src/capture/summarizer.py
async def summarize_batch(
    content_items: list[str],
    source: str = "git commits",
    item_label: str = "commits",
    capture_mode: str = "decisions-only",
) -> str:
    # ... existing security gate (unchanged, runs before prompt selection) ...

    # Select prompt based mode
    if capture_mode == "decisions-and-patterns":
        prompt_template = BATCH_SUMMARIZATION_PROMPT_BROAD
    else:
        prompt_template = BATCH_SUMMARIZATION_PROMPT_NARROW

    prompt = prompt_template.format(
        source=source,
        count=len(content_items),
        items=item_label,
        content=safe_content,
    )
    # ... rest of function unchanged ...


async def summarize_and_store(
    content_items: list[str],
    source: str,
    scope: GraphScope,
    project_root: Path | None = None,
    tags: list[str] | None = None,
    capture_mode: str = "decisions-only",
) -> dict | None:
    # ...
    summary = await summarize_batch(
        content_items,
        source=source,
        item_label="items",
        capture_mode=capture_mode,
    )
    # ...
```

### Pattern 4: VALID_CONFIG_KEYS extension with allowed_values

**What:** Add `capture.mode` to `VALID_CONFIG_KEYS` with a custom `allowed_values` list. Validate in `--set` path before writing TOML.

**When to use:** Same approach as existing keys but add enum validation at set-time.

**Example:**
```python
# src/cli/commands/config.py
VALID_CONFIG_KEYS = {
    # ... existing keys ...
    "capture.mode": {
        "type": str,
        "desc": "Capture mode (decisions-only, decisions-and-patterns)",
        "allowed_values": ["decisions-only", "decisions-and-patterns"],
    },
    "retention.retention_days": {
        "type": int,
        "desc": "Days before a node is considered stale (min 30)",
    },
}
```

Note: `retention.retention_days` is also missing from `VALID_CONFIG_KEYS` currently — both keys should be added in the same plan.

The `--set` validation path needs a check for `allowed_values`:
```python
# In config_command(), after _parse_value():
if "allowed_values" in key_info and parsed_value not in key_info["allowed_values"]:
    print_error(
        f"Invalid value for {key}: '{parsed_value}'.",
        suggestion=f"Valid values: {', '.join(key_info['allowed_values'])}"
    )
    sys.exit(EXIT_BAD_ARGS)
```

### Pattern 5: Config show table — new section groups

**What:** Add "Capture Settings" and "Retention Settings" as visually distinct section groups in the Rich table output. The existing table has no section grouping — consider inserting section header rows.

**When to use:** When displaying heterogeneous config categories with the same Rich table style.

**Example:**
```python
# Section header row pattern (reusable):
table.add_row("[bold]Capture Settings[/bold]", "", "", style="dim")
table.add_row("capture.mode", config.capture_mode, "Capture mode (decisions-only, decisions-and-patterns)")

table.add_row("[bold]Retention Settings[/bold]", "", "", style="dim")
table.add_row("retention.retention_days", str(config.retention_days), "Days before a node is considered stale (min 30)")
```

Note: The existing `attr_map` in `config_command()` for the `--get` path must also be extended with `"capture.mode": "capture_mode"` and `"retention.retention_days": "retention_days"`.

### Anti-Patterns to Avoid

- **Filtering LLM output post-hoc:** Never try to strip bug/dep content from an LLM response after the fact. Mode controls the EXTRACT prompt — what the LLM is asked to find, not what we filter from its output.
- **Reading `load_config()` inside `summarize_batch()`:** Creates hidden dependency, makes unit tests require filesystem config setup. Pass `capture_mode` as a parameter instead.
- **Inverting the security gate:** `sanitize_content()` must run before any prompt selection. Never make it conditional on mode.
- **Mutating `BATCH_SUMMARIZATION_PROMPT`:** Do not modify the existing constant — define new named constants and keep the old one (or replace it with the two new ones). Tests may reference the old constant.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Enum validation for config keys | Custom validator class | `allowed_values` list in `VALID_CONFIG_KEYS` + inline check | Already have type-based validation — extend same pattern |
| TOML serialization | Custom TOML writer | Existing `_write_toml()` in `config.py` | Works correctly for all current sections; `[capture]` follows same flat structure |
| Config schema | Pydantic or attrs | Frozen dataclass with manual validation in `load_config()` | Phase 9 established the pattern; do not introduce new schema library |

---

## Common Pitfalls

### Pitfall 1: `BATCH_SUMMARIZATION_PROMPT` still referenced by tests
**What goes wrong:** After renaming/replacing the original constant, existing tests or code that imports `BATCH_SUMMARIZATION_PROMPT` by name will break with `ImportError`.
**Why it happens:** The constant name is part of the public API of `summarizer.py`.
**How to avoid:** Either keep `BATCH_SUMMARIZATION_PROMPT` as an alias for the broad prompt (backward-compatible), or search for all import sites before renaming.
**Warning signs:** `ImportError: cannot import name 'BATCH_SUMMARIZATION_PROMPT'` in test output.

### Pitfall 2: `--get capture.mode` falls through to None
**What goes wrong:** `config --get capture.mode` returns nothing because `capture.mode` is not in the `attr_map` dict inside `config_command()`.
**Why it happens:** `attr_map` is a manual mapping of dotted key → dataclass attribute name; must be extended alongside `VALID_CONFIG_KEYS`.
**How to avoid:** Add `"capture.mode": "capture_mode"` (and `"retention.retention_days": "retention_days"`) to `attr_map` in the same plan that adds the keys.
**Warning signs:** `graphiti config --get capture.mode` prints blank or "(not set)" even when `llm.toml` has `[capture] mode = "..."`.

### Pitfall 3: `_write_toml()` sorts sections alphabetically, putting `[capture]` first
**What goes wrong:** `_write_toml()` iterates `sorted(config_dict.items())` so `[capture]` appears before `[cloud]`. This is cosmetically odd but functionally correct.
**Why it happens:** The existing `_write_toml()` uses alphabetical sort for determinism.
**How to avoid:** Accept the sort order. Do not introduce a custom section ordering unless the user explicitly requests it. It does not affect correctness.

### Pitfall 4: `summarize_and_store` call sites forget to pass `capture_mode`
**What goes wrong:** `git_worker.py` and `conversation.py` call `summarize_and_store()` without `capture_mode`, defaulting to `decisions-only` regardless of config.
**Why it happens:** Adding a defaulted parameter silently works — no type error — but the mode is never actually applied.
**How to avoid:** At each call site that calls `summarize_and_store`, explicitly load config and pass `capture_mode`. Verification tests should assert mode-specific content in the summarized output.
**Warning signs:** `config --set capture.mode=decisions-and-patterns` succeeds, but captured entities always look like narrow-mode output.

### Pitfall 5: `graphiti index` does not use `summarize_and_store`
**What goes wrong:** The `src/indexer/indexer.py` does NOT call `summarize_and_store` — it uses `extract_commit_knowledge` from `src/indexer/extraction.py` instead. If mode is only threaded through `summarize_and_store`, index captures ignore the mode config.
**Why it happens:** The indexer pipeline is a separate two-pass extraction flow that bypasses `summarizer.py` entirely.
**How to avoid:** Check `src/indexer/extraction.py` to see if it has its own prompt that also needs mode-aware parameterization. If so, add a parallel `capture_mode` parameter there. The CONTEXT.md says mode applies to `graphiti index` — this must be verified and implemented.
**Warning signs:** `graphiti index` runs but uses the old 4-category prompt regardless of mode setting.

---

## Code Examples

### Call site pattern — git_worker.py
```python
# src/capture/git_worker.py — load config once per process_pending_commits call
from src.llm.config import load_config

async def process_pending_commits(...) -> list[dict]:
    cfg = load_config()
    # ...
    entity = await summarize_and_store(
        content_items=batch,
        source="git-commits",
        scope=scope,
        project_root=project_root,
        tags=["auto-capture", "git-commits"],
        capture_mode=cfg.capture_mode,
    )
```

### llm.toml example — user-visible config
```toml
[capture]
mode = "decisions-and-patterns"

[retention]
retention_days = 60
```

### Test pattern — mode selection unit test
```python
# tests/test_capture_modes.py
import pytest
from unittest.mock import AsyncMock, patch
from src.capture.summarizer import summarize_batch, BATCH_SUMMARIZATION_PROMPT_NARROW, BATCH_SUMMARIZATION_PROMPT_BROAD

@pytest.mark.asyncio
async def test_decisions_only_uses_narrow_prompt():
    with patch("src.capture.summarizer.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": "summary"}}
        await summarize_batch(["content"], capture_mode="decisions-only")
        prompt_used = mock_chat.call_args[1]["messages"][0]["content"]
        assert "Bug Fixes" not in prompt_used
        assert "Dependencies" not in prompt_used

@pytest.mark.asyncio
async def test_decisions_and_patterns_uses_broad_prompt():
    with patch("src.capture.summarizer.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": "summary"}}
        await summarize_batch(["content"], capture_mode="decisions-and-patterns")
        prompt_used = mock_chat.call_args[1]["messages"][0]["content"]
        assert "Bug Fixes & Root Causes" in prompt_used
        assert "Dependencies & Config" in prompt_used

def test_security_gate_runs_before_prompt_selection():
    """sanitize_content is called regardless of mode."""
    with patch("src.capture.summarizer.sanitize_content") as mock_sanitize, \
         patch("src.capture.summarizer.chat") as mock_chat:
        mock_sanitize.return_value = type("R", (), {"sanitized_content": "safe", "was_modified": False, "findings": []})()
        mock_chat.return_value = {"message": {"content": "summary"}}
        import asyncio
        asyncio.run(summarize_batch(["secret content"], capture_mode="decisions-and-patterns"))
        mock_sanitize.assert_called_once()
```

---

## Critical Investigation: Indexer Extraction Path

The CONTEXT.md states mode applies to `graphiti index`. However, the indexer does NOT use `summarize_and_store`. It uses `extract_commit_knowledge` from `src/indexer/extraction.py`. This file needs to be inspected during planning to determine if it has its own LLM prompt that requires mode-aware parameterization.

Recommended action for planner: include a task to read `src/indexer/extraction.py` and determine whether it has an LLM prompt for summarization that should also be mode-parameterized. If not, the scope is limited to `git_worker.py` + `conversation.py`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single monolithic prompt with all 4 categories | Two named prompt constants, selected by config | Phase 10 | Current implicit behavior (`decisions-and-patterns`) becomes opt-in; new default is narrower, higher signal |
| No `[capture]` config section | `[capture] mode =` in `llm.toml` | Phase 10 | Existing users without `[capture]` section get same behavior (default = decisions-only = current behavior minus bugs/deps categories) |

**Note:** Existing users who have been capturing with the old single prompt will notice Phase 10 produces different (narrower) captures by default after upgrade. If backward compatibility of capture content is important, consider making `decisions-and-patterns` the default. However, CONTEXT.md explicitly locks `decisions-only` as the default.

---

## Open Questions

1. **Does `src/indexer/extraction.py` have a summarization prompt that needs mode parameterization?**
   - What we know: `indexer.py` does not call `summarize_and_store`; it calls `extract_commit_knowledge`
   - What's unclear: Whether `extraction.py` has its own LLM call with a category list
   - Recommendation: Read `src/indexer/extraction.py` as part of Wave 1 planning; add mode support there if it has a prompt

2. **Should `BATCH_SUMMARIZATION_PROMPT` (old constant) be kept as an alias?**
   - What we know: It is imported by name; no existing tests reference it directly (confirmed by search)
   - What's unclear: Whether removing it would break any downstream integrations
   - Recommendation: Replace cleanly with two new constants; keep old name as alias pointing to `BATCH_SUMMARIZATION_PROMPT_BROAD` (the current behavior) for one release cycle

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pytest.ini` or inferred from `pyproject.toml` |
| Quick run command | `pytest tests/test_capture_modes.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAPT-01 | `decisions-only` mode routes to narrow prompt (no Bug/Dep categories) | unit | `pytest tests/test_capture_modes.py::TestCaptureModeSelection::test_decisions_only_prompt -x` | Wave 0 |
| CAPT-01 | `load_config()` parses `[capture] mode = "decisions-only"` and sets `capture_mode` | unit | `pytest tests/test_capture_modes.py::TestCaptureModeConfig::test_decisions_only_from_toml -x` | Wave 0 |
| CAPT-01 | Missing `[capture]` section defaults to `decisions-only` | unit | `pytest tests/test_capture_modes.py::TestCaptureModeConfig::test_default_is_decisions_only -x` | Wave 0 |
| CAPT-01 | Invalid mode value in `llm.toml` falls back to `decisions-only` | unit | `pytest tests/test_capture_modes.py::TestCaptureModeConfig::test_invalid_mode_falls_back -x` | Wave 0 |
| CAPT-02 | `decisions-and-patterns` mode routes to broad prompt (all 4 categories present) | unit | `pytest tests/test_capture_modes.py::TestCaptureModeSelection::test_decisions_and_patterns_prompt -x` | Wave 0 |
| CAPT-01/02 | Security gate (`sanitize_content`) runs unconditionally regardless of mode | unit | `pytest tests/test_capture_modes.py::TestSecurityGate::test_security_gate_is_unconditional -x` | Wave 0 |
| CAPT-03 | `graphiti config show` output contains "Capture Settings" section with `capture.mode` row | unit | `pytest tests/test_capture_modes.py::TestConfigShow::test_config_show_has_capture_section -x` | Wave 0 |
| CAPT-03 | `graphiti config show` output contains "Retention Settings" section with `retention_days` row | unit | `pytest tests/test_capture_modes.py::TestConfigShow::test_config_show_has_retention_section -x` | Wave 0 |
| CAPT-03 | `graphiti config --set capture.mode=decisions-and-patterns` accepts valid value | unit | `pytest tests/test_capture_modes.py::TestConfigSet::test_set_valid_mode -x` | Wave 0 |
| CAPT-03 | `graphiti config --set capture.mode=invalid` rejects with error message | unit | `pytest tests/test_capture_modes.py::TestConfigSet::test_set_invalid_mode_rejected -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_capture_modes.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_capture_modes.py` — covers all CAPT-01, CAPT-02, CAPT-03 test cases listed above

*(Existing test infrastructure: pytest, `tmp_path` fixture, `CliRunner` from typer — all available. No new test framework needed.)*

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `src/capture/summarizer.py` — current prompt structure, `summarize_batch()` and `summarize_and_store()` signatures
- Direct code inspection: `src/llm/config.py` — `LLMConfig` frozen dataclass, `load_config()` patterns, Phase 9 `retention_days` validation as template
- Direct code inspection: `src/cli/commands/config.py` — `VALID_CONFIG_KEYS`, `_parse_value()`, `config_command()` Rich table, `attr_map`
- Direct code inspection: `src/capture/git_worker.py` and `src/capture/conversation.py` — call sites for `summarize_and_store()`
- Direct code inspection: `src/mcp_server/tools.py` — `graphiti_capture` delegates to `graphiti capture` CLI subprocess (no direct summarizer call)
- Direct code inspection: `src/indexer/indexer.py` — does NOT call `summarize_and_store`; uses `extract_commit_knowledge`
- Direct code inspection: `tests/test_retention_config.py` — test template for config field extension pattern

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions — locked user choices verified against code inspection

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all existing libs, no new dependencies
- Architecture: HIGH — all call sites inspected, patterns directly from Phase 9 precedent
- Pitfalls: HIGH — discovered by direct code inspection of indexer path divergence and attr_map gap

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable codebase — no upstream dependency churn risk)
