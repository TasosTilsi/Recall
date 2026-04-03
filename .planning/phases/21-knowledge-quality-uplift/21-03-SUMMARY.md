---
phase: 21-knowledge-quality-uplift
plan: "03"
subsystem: indexer-tests, ui-lib
tags: [testing, tdd, extraction, typescript, SC-2, SC-3, SC-4, SC-5]
dependency_graph:
  requires: [21-01, 21-02]
  provides: [test-extraction-phase21, parseCodeBlockMeta-standalone]
  affects: [tests/, ui/src/lib/, ui/src/components/panels/EntityPanel.tsx]
tech_stack:
  added: []
  patterns: [asyncio.run-in-sync-test, npx-tsx-test-runner, TDD-green-first]
key_files:
  created:
    - tests/test_extraction_phase21.py
    - ui/src/lib/parseCodeBlockMeta.ts
    - ui/src/lib/parseCodeBlockMeta.test.ts
  modified:
    - ui/src/components/panels/EntityPanel.tsx
decisions:
  - "Test runner for TypeScript tests: npx tsx (not Vitest — not installed); throw Error on failure instead of process.exit(1) to avoid TS2591 node type error"
  - "Unused _name parameter prefixed with underscore to satisfy tsc noUnusedParameters in test helper function"
metrics:
  duration_seconds: 198
  completed: "2026-04-03T06:50:11Z"
  tasks_completed: 2
  files_changed: 4
---

# Phase 21 Plan 03: Test Suite for Knowledge Quality Uplift Summary

One-liner: Python + TypeScript unit tests verifying SC-2 code block extraction, SC-3 episode body propagation, SC-4 semantic verb steering, and SC-5 UI parser logic, with parseCodeBlockMeta extracted to a testable standalone module.

## What Was Built

### Task 1: tests/test_extraction_phase21.py (10 tests)

Five test classes covering Phase 21 success criteria:

- **TestBatchPromptCodeBlocks** (4 tests): Verifies `BATCH_EXTRACTION_PROMPT` contains `Code Block:` instruction, `File:` / `Language:` / `Type:` fields, pipe-delimited `" | "` example, and that `.format(commits_block=..., count=...)` works without KeyError.
- **TestBatchPromptSemanticVerbs** (1 test): Asserts all 7 semantic verbs are present — MODIFIES, INTRODUCES, FIXES, DEPENDS_ON, REMOVES, REFACTORS, TESTS.
- **TestEpisodeBodyCodeBlocks** (2 tests): Mocks `_claude_p` via `patch("src.llm.claude_cli_client._claude_p")`, runs `extract_commits_batch()`, and inspects the `episode_body` kwarg. Verifies single and multiple code block entity strings appear in the Entities line.
- **TestRelationshipVocab** (1 test): Verifies a relationship string with `MODIFIES` verb appears in the episode body Relationships line.
- **TestColorMap** (2 tests): File-read check that `ui/src/lib/colors.ts` contains `Function` and `Class` keys in `ENTITY_TYPE_COLORS`.

### Task 2: parseCodeBlockMeta module extraction + TypeScript tests

- **ui/src/lib/parseCodeBlockMeta.ts**: `CodeBlockMeta` interface and `parseCodeBlockMeta()` function extracted from `EntityPanel.tsx` into a standalone module. Both exported.
- **ui/src/components/panels/EntityPanel.tsx**: Updated to `import { parseCodeBlockMeta } from '@/lib/parseCodeBlockMeta'` — removes inline definition.
- **ui/src/lib/parseCodeBlockMeta.test.ts**: 8 test groups with 19 assertions, run via `npx tsx`. Covers valid format, null for plain text, empty string, remainder extraction, incomplete format (< 4 segments), class type, TypeScript language, multi-line remainder.

## Verification Results

```
pytest tests/test_extraction_phase21.py -x -v
10 passed in 0.67s

cd ui && npx tsx src/lib/parseCodeBlockMeta.test.ts
8 tests: 8 passed, 0 failed
All parseCodeBlockMeta tests passed!

cd ui && npm run build
✓ built in 518ms
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TypeScript compilation errors in parseCodeBlockMeta.test.ts**
- **Found during:** Task 2 Step 3 verification (`npm run build`)
- **Issue 1:** `name` parameter in `test()` helper declared but never read — TS6133 error under strict mode
- **Issue 2:** `process.exit(1)` requires node type definitions (TS2591 — `Cannot find name 'process'`)
- **Fix:** Prefixed `name` to `_name` to mark intentionally unused. Replaced `process.exit(1)` with `throw new Error(...)` which works in any TypeScript context without node types
- **Files modified:** `ui/src/lib/parseCodeBlockMeta.test.ts`
- **Commit:** 5f6aae7

## Self-Check: PASSED

Files exist:
- tests/test_extraction_phase21.py: FOUND
- ui/src/lib/parseCodeBlockMeta.ts: FOUND
- ui/src/lib/parseCodeBlockMeta.test.ts: FOUND

Commits exist:
- f790255: test(21-03): add Phase 21 Python test suite for SC-2, SC-3, SC-4, SC-5
- 5f6aae7: feat(21-03): extract parseCodeBlockMeta to standalone module + TypeScript tests
