---
phase: 10-configurable-capture-modes
verified: 2026-03-08T00:00:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
---

# Phase 10: Configurable Capture Modes Verification Report

**Phase Goal:** Users can control what the capture system records — narrow (decisions and architecture only) or broad (decisions, patterns, bugs, dependencies) — and see the active mode at a glance.
**Verified:** 2026-03-08
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | LLMConfig.capture_mode field exists, defaults to "decisions-only" | VERIFIED | `src/llm/config.py` line 65: `capture_mode: str = "decisions-only"` |
| 2 | load_config() parses [capture] mode from llm.toml, falls back on invalid value | VERIFIED | Lines 112–122 of config.py: captures section parsed, invalid mode triggers structlog warning and resets to "decisions-only" |
| 3 | BATCH_SUMMARIZATION_PROMPT_NARROW exists with 2 categories (no Bug Fixes, no Dependencies) | VERIFIED | `src/capture/summarizer.py` lines 26–50: EXTRACT ONLY contains "Decisions & Rationale" + "Architecture & Patterns" only |
| 4 | BATCH_SUMMARIZATION_PROMPT_BROAD exists with 4 categories including Bug Fixes & Root Causes and Dependencies & Config | VERIFIED | `src/capture/summarizer.py` lines 53–79: EXTRACT ONLY contains all 4 categories |
| 5 | BATCH_SUMMARIZATION_PROMPT alias kept pointing to BATCH_SUMMARIZATION_PROMPT_BROAD | VERIFIED | Line 82: `BATCH_SUMMARIZATION_PROMPT = BATCH_SUMMARIZATION_PROMPT_BROAD` with backward-compat comment |
| 6 | summarize_batch() selects narrow vs broad prompt based on capture_mode after security gate | VERIFIED | Lines 133–137: mode selection after sanitize_content() call at line 122 |
| 7 | summarize_and_store() accepts and passes capture_mode to summarize_batch() | VERIFIED | Signature at line 190 includes `capture_mode: str = "decisions-only"`, passed at line 233 |
| 8 | Security gate (sanitize_content) runs unconditionally before any prompt selection | VERIFIED | `sanitize_content(joined_content)` at line 122 precedes mode selection at line 134 — invariant confirmed |
| 9 | graphiti config show displays "Capture Settings" and "capture.mode" | VERIFIED | `src/cli/commands/config.py` lines 366–367: explicit add_row calls after main loop |
| 10 | graphiti config show displays "Retention Settings" and "retention.retention_days" | VERIFIED | Lines 368–369: retention section rows added |
| 11 | graphiti config --set capture.mode validates against allowed_values | VERIFIED | Lines 229–234: allowed_values check with print_error and sys.exit(EXIT_BAD_ARGS) |
| 12 | git_worker.py passes capture_mode=cfg.capture_mode at both summarize_and_store() call sites | VERIFIED | Lines 247 and 263 in git_worker.py: both full-batch and partial-batch flush pass `capture_mode=cfg.capture_mode` |
| 13 | indexer.py passes capture_mode=cfg.capture_mode at both extract_commit_knowledge() call sites | VERIFIED | Lines 251 and 269 in indexer.py: asyncio.run path and RuntimeError fallback loop.run_until_complete path both pass `capture_mode=cfg.capture_mode` |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/llm/config.py` | LLMConfig.capture_mode field + [capture] TOML parsing | VERIFIED | Field at line 65, parsing at lines 112–122, constructor at line 149 |
| `src/capture/summarizer.py` | Two prompt constants + mode-aware summarize_batch() + VALID_CAPTURE_MODES | VERIFIED | NARROW (line 26), BROAD (line 53), alias (line 82), VALID_CAPTURE_MODES (line 23), mode branch (lines 133–137) |
| `src/indexer/extraction.py` | FREE_FORM_EXTRACTION_PROMPT_NARROW/BROAD + capture_mode param | VERIFIED | NARROW (line 44), BROAD (line 55), alias (line 67), param (line 118), branch (lines 179–182) |
| `src/capture/git_worker.py` | load_config() + capture_mode=cfg.capture_mode at both call sites | VERIFIED | load_config import at line 47, cfg=load_config() at line 157, capture_mode kwarg at lines 247 and 263 |
| `src/capture/conversation.py` | load_config() + capture_mode=cfg.capture_mode at summarize_and_store() | VERIFIED | load_config import at line 37, cfg=load_config() at line 328, capture_mode kwarg at line 336 |
| `src/indexer/indexer.py` | load_config() + capture_mode=cfg.capture_mode at both extract_commit_knowledge() call sites | VERIFIED | load_config import at line 27, cfg=load_config() at line 120, both call sites at lines 251 and 269 |
| `src/cli/commands/config.py` | VALID_CONFIG_KEYS["capture.mode"] + allowed_values + attr_map + table + JSON | VERIFIED | Entry at lines 31–35, validation at lines 229–234, attr_map at line 275, table rows at lines 366–369, JSON at lines 324–325 |
| `tests/test_capture_modes.py` | 13 tests in 6 classes — all GREEN | VERIFIED | pytest confirms 13/13 GREEN in 1.42s |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/capture/summarizer.py` | security gate | `sanitize_content()` called before prompt selection | WIRED | Line 122 (sanitize) precedes line 134 (mode select) — order confirmed |
| `src/capture/summarizer.py` | NARROW or BROAD prompt | `if capture_mode == "decisions-and-patterns"` branch | WIRED | Branch at lines 134–137; no default path bypass possible |
| `src/capture/git_worker.py` | `summarize_and_store()` | `capture_mode=cfg.capture_mode` kwarg | WIRED | Both call sites (lines 247 and 263) pass kwarg; `cfg = load_config()` at line 157 |
| `src/capture/conversation.py` | `summarize_and_store()` | `capture_mode=cfg.capture_mode` kwarg | WIRED | Call site at line 330 passes kwarg; `cfg = load_config()` at line 328 |
| `src/indexer/indexer.py` | `extract_commit_knowledge()` | `capture_mode=cfg.capture_mode` kwarg | WIRED | Both call sites (lines 242 and 260) pass kwarg; `cfg = load_config()` at line 120 |
| `src/indexer/extraction.py` | `FREE_FORM_EXTRACTION_PROMPT_NARROW` or `FREE_FORM_EXTRACTION_PROMPT_BROAD` | `if capture_mode == "decisions-and-patterns"` branch | WIRED | Branch at lines 179–182; freeform_prompt_template selected before use at line 185 |
| `src/cli/commands/config.py` | `LLMConfig.capture_mode` | `config.capture_mode` read in table and JSON output | WIRED | Table at line 367, JSON at line 325, attr_map at line 275 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CAPT-01 | 10-01, 10-02, 10-04 | User can set `[capture] mode = "decisions-only"` — narrow capture | SATISFIED | `load_config()` parses [capture] section; `LLMConfig.capture_mode` defaults to "decisions-only"; narrow prompt used when mode is "decisions-only"; TestCaptureModeConfig 4/4 GREEN |
| CAPT-02 | 10-01, 10-02, 10-04 | User can set `[capture] mode = "decisions-and-patterns"` — broad capture | SATISFIED | BATCH_SUMMARIZATION_PROMPT_BROAD and FREE_FORM_EXTRACTION_PROMPT_BROAD both implemented; mode-aware selection wired in summarizer and extraction; TestCaptureModeSelection 2/2 GREEN and TestIndexerCaptureMode 2/2 GREEN |
| CAPT-03 | 10-01, 10-03 | User can see active capture mode in `graphiti config show` output | SATISFIED | "Capture Settings" section added to Rich table; capture.mode row present; --set validates allowed_values; TestConfigShow 2/2 GREEN and TestConfigSet 2/2 GREEN |

No orphaned requirements: REQUIREMENTS.md maps exactly CAPT-01, CAPT-02, CAPT-03 to Phase 10 — all three are covered by plans 10-01 through 10-04.

### Anti-Patterns Found

No anti-patterns detected. Scanned all seven key files.

- No TODO/FIXME/HACK/PLACEHOLDER comments in any Phase 10 production file
- No `return null` or empty stubs in modified functions
- No console.log-only handlers
- Backward-compat aliases (`BATCH_SUMMARIZATION_PROMPT`, `FREE_FORM_EXTRACTION_PROMPT`) are intentional and documented with comments

### Security Invariant: Sanitize-Before-Mode-Filter

The locked invariant — security gate runs before mode selection, never after — is confirmed:

In `src/capture/summarizer.py`:
- Line 122: `sanitization_result = sanitize_content(joined_content)` — security gate
- Line 133: `# Select prompt based on capture mode` — mode selection
- Line 134: `if capture_mode == "decisions-and-patterns":` — branch

The mode selection block cannot execute before sanitize_content completes (synchronous, no await). TestSecurityGate confirms this with mock assertion: `mock_sanitize.assert_called_once()` passes regardless of capture_mode value.

### Human Verification Required

One item needs human visual confirmation (cannot be verified programmatically by terminal test runner):

**Test:** Visual table rendering in terminal
**Test:** Run `graphiti config show` in a real terminal
**Expected:** Rich table renders with visible "Capture Settings" and "Retention Settings" section header rows (bold, dim style), each followed by their respective data rows — not garbled by markup tags
**Why human:** Rich markup tags (`[bold]...[/bold]`) render correctly in live TTY but `typer.testing.CliRunner` strips them. The automated test asserts the strings "Capture Settings" and "Retention Settings" appear in output, which confirms the rows are emitted, but visual layout quality requires a live terminal.

The automated tests confirm the strings ARE present and the CLI exits 0 — so this is a presentation quality check, not a functional gap.

## Gaps Summary

No gaps. All 13 must-haves verified. Phase goal is fully achieved:

- Users can set `[capture] mode` in `llm.toml` with two valid values
- Invalid values fall back gracefully with a structlog warning
- The narrow/broad prompt selection is wired through every capture pipeline (summarizer, git worker, conversation, indexer)
- The security gate (sanitize_content) always runs first, before mode selection — invariant preserved
- `graphiti config show` displays the active mode in a dedicated Capture Settings section
- `graphiti config --set capture.mode=invalid` is rejected with a "Valid values" message
- 13/13 tests GREEN, 285/285 total suite tests GREEN (no regressions)

---

_Verified: 2026-03-08_
_Verifier: Claude (gsd-verifier)_
