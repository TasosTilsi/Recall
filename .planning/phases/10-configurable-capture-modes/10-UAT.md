---
status: complete
phase: 10-configurable-capture-modes
source: 10-01-SUMMARY.md, 10-02-SUMMARY.md, 10-03-SUMMARY.md, 10-04-SUMMARY.md
started: 2026-03-09T08:52:00Z
updated: 2026-03-09T08:52:00Z
---

## Current Test

[testing complete]

## Tests

### 1. LLMConfig.capture_mode field — default value
expected: LLMConfig() default capture_mode = "decisions-only". load_config() returns config with capture_mode set.
result: pass

### 2. [capture] TOML section parsing
expected: Setting `[capture] mode = "decisions-and-patterns"` in llm.toml is parsed into LLMConfig.capture_mode correctly.
result: pass

### 3. Dual prompts in summarizer (NARROW / BROAD)
expected: BATCH_SUMMARIZATION_PROMPT_NARROW exists and omits bugs/dependencies. BATCH_SUMMARIZATION_PROMPT_BROAD includes extended categories. summarize_and_store() accepts capture_mode parameter.
result: pass

### 4. Dual prompts in indexer extraction (NARROW / BROAD)
expected: FREE_FORM_EXTRACTION_PROMPT_NARROW omits "bugs fixed" and "dependencies introduced". FREE_FORM_EXTRACTION_PROMPT_BROAD includes both. FREE_FORM_EXTRACTION_PROMPT alias still importable. extract_commit_knowledge() defaults to "decisions-only".
result: pass

### 5. capture_mode wired through git_worker, conversation, indexer
expected: All three call sites pass `capture_mode=cfg.capture_mode` to summarize_and_store() / extract_commit_knowledge(). All import load_config().
result: pass

### 6. graphiti config show — Capture and Retention Settings
expected: `graphiti config --format json` returns JSON with capture.mode and retention.retention_days keys populated.
result: pass
note: JSON shows capture.mode = "decisions-only", retention.retention_days = 90

### 7. graphiti config --set capture.mode — persists to TOML
expected: `graphiti config --set capture.mode=decisions-and-patterns` exits 0, shows success message with the new value, and persists — confirmed by re-running `graphiti config --format json`.
result: pass

### 8. graphiti config --get capture.mode — returns value (not blank)
expected: `graphiti config --get capture.mode` prints the current mode string, not blank.
result: pass
note: Returned "decisions-only"

### 9. graphiti config --set capture.mode=invalid — rejected with valid values
expected: Exits non-zero. Error message contains "Valid values" and lists both "decisions-only" and "decisions-and-patterns".
result: pass

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
