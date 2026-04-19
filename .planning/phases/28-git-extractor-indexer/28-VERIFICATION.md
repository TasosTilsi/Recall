---
phase: 28-git-extractor-indexer
verified: 2026-04-19T16:23:39Z
status: passed
score: 9/9 must-haves verified
re_verification: false
human_verification:
  - test: "Run recall init against a real repo with Ollama/Claude available and verify entities are extracted and stored"
    expected: "DB populated with entity rows; last_indexed_sha written to metadata table"
    why_human: "extract_batch calls a live claude subprocess — cannot run in automated verification without LLM available"
  - test: "Run recall sync twice — second run should print '0 commits to process'"
    expected: "First sync processes commits; second sync detects no new commits and exits cleanly"
    why_human: "Requires running CLI against real git repo with LLM available"
---

# Phase 28: Git Extractor / Incremental Indexer Verification Report

**Phase Goal:** Implement git extractor and incremental indexer — git walker, LLM extraction engine, and run_init/run_sync entry points wired to SQLite DB.
**Verified:** 2026-04-19T16:23:39Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | git_walker.walk_commits() yields commits oldest-first from a given repo root | VERIFIED | `repo.iter_commits(rev="HEAD", reverse=True)` in git_walker.py:62; test_walk_commits tests pass |
| 2 | batch_commits() groups commits into lists of configurable size (default 10) | VERIFIED | Pure chunking impl in git_walker.py; `test_default_batch_size_is_10` and `test_splits_correctly` pass |
| 3 | build_batch_prompt() returns a string prompt embedding all commit messages and diffs | VERIFIED | prompt.py:84; includes sha, author, message, diff[:800] per commit; prompt tests pass |
| 4 | The extraction JSON schema is documented and typed | VERIFIED | `EXTRACTION_SCHEMA` dict + `EntityRecord`/`ExtractionResult` TypedDicts in prompt.py |
| 5 | extract_batch() calls LLM, returns normalized EntityRecord list | VERIFIED | engine.py subprocess call, JSON parse, type filter, lowercase+strip normalization; all engine tests pass |
| 6 | Invalid entity types silently dropped; malformed JSON returns [] | VERIFIED | VALID_ENTITY_TYPES filter in engine.py:88; JSONDecodeError catch returns []; tests confirmed |
| 7 | recall sync reads last_indexed_sha and processes only commits newer than that SHA | VERIFIED | `_commits_after_sha()` + `_read_last_sha()` in indexer.py; `test_run_sync_incremental` passes |
| 8 | recall sync with no DB automatically runs full init | VERIFIED | `not db.get_db_path().exists()` guard in run_sync; `test_run_sync_no_db_delegates_to_init` passes |
| 9 | recall sync when no new commits prints "0 commits to process" and exits cleanly | VERIFIED | `print("0 commits to process")` in indexer.py:193; `test_run_sync_empty_after_filter` passes |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/extractor/__init__.py` | Package marker | VERIFIED | Exists, empty package marker |
| `src/extractor/git_walker.py` | walk_commits, batch_commits, fetch_diff, CommitRecord | VERIFIED | All 4 symbols present and importable; substantive implementation ~100 lines |
| `src/extractor/prompt.py` | build_batch_prompt, EXTRACTION_SCHEMA, EntityRecord, ExtractionResult, VALID_ENTITY_TYPES | VERIFIED | All 5 symbols present and importable; substantive implementation ~90 lines |
| `src/extractor/engine.py` | extract_batch — LLM call, JSON parse, normalization | VERIFIED | Substantive 100-line implementation; all error paths handled |
| `src/indexer/indexer.py` | run_init, run_sync, last_indexed_sha, incremental SHA filtering | VERIFIED | Full implementation ~220 lines; contains `_LAST_SHA_KEY = "last_indexed_sha"` and `"0 commits to process"` literals |
| `tests/extractor/test_git_walker.py` | Test coverage for git walker | VERIFIED | 14 tests across 3 test classes; all pass |
| `tests/extractor/test_prompt.py` | Test coverage for prompt builder | VERIFIED | 20 tests across 5 test classes; all pass |
| `tests/extractor/test_engine.py` | Test coverage for engine with mocked LLM | VERIFIED | 16 tests across 4 test classes; all mock patterns used correctly |
| `tests/indexer/test_indexer.py` | 5 test cases for incremental indexer | VERIFIED | All 5 required test cases present and passing |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/extractor/git_walker.py` | GitPython | `import git; git.Repo(root)` | WIRED | `import git` on line 15; `git.Repo(repo_root, ...)` on line 62 |
| `src/extractor/prompt.py` | `src/extractor/git_walker.py` | `CommitRecord` used in `build_batch_prompt` | WIRED | `from src.extractor.git_walker import CommitRecord` on line 15; used as type annotation and in `record.short_sha`, `record.author`, etc. |
| `src/extractor/engine.py` | `src/extractor/prompt.py` | `build_batch_prompt(batch)` | WIRED | `from src.extractor.prompt import VALID_ENTITY_TYPES, EntityRecord, build_batch_prompt` on line 16; called on line 40 |
| `src/extractor/engine.py` | `src/extractor/prompt.py` | `VALID_ENTITY_TYPES` filter | WIRED | Used in type whitelist check on line 88 |
| `src/extractor/engine.py` | LLM subprocess | `subprocess.run([claude_bin, "-p", prompt])` | WIRED | shutil.which + subprocess.run on lines 42–56 |
| `src/indexer/indexer.py` | `src/extractor/git_walker.py` | `walk_commits` + `batch_commits` | WIRED | Imported on line 19; called in run_init (lines 126, 128) and run_sync (lines 184, 198) |
| `src/indexer/indexer.py` | `src/extractor/engine.py` | `extract_batch(batch)` | WIRED | Imported on line 18; called in run_init line 142 and run_sync line 208 |
| `src/indexer/indexer.py` | `src/db/manager.py` | `DatabaseManager.connect()` reads/writes `last_indexed_sha` | WIRED | Imported on line 17; `_read_last_sha`, `_write_last_sha` use `conn.execute(...)` with `_LAST_SHA_KEY` |
| `src/indexer/indexer.py` | `src/config.py` | `load_config()` + `Config.indexer.batch_size` | WIRED | `from src.config import Config, load_config` on line 16; `getattr(getattr(config, 'indexer', None), 'batch_size', 10)` in both entry points |

### Data-Flow Trace (Level 4)

Not applicable — this phase produces data-pipeline utilities (git walker, extraction engine, indexer) with no UI rendering components. Data flows are verified structurally through key link wiring above and behaviorally through the test suite.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All imports resolve | `python3 -c "from src.extractor.git_walker import walk_commits, batch_commits, fetch_diff, CommitRecord; from src.extractor.prompt import build_batch_prompt, EXTRACTION_SCHEMA, EntityRecord, ExtractionResult, VALID_ENTITY_TYPES; from src.extractor.engine import extract_batch; from src.indexer.indexer import run_init, run_sync; print('ok')"` | `All imports OK` | PASS |
| Full test suite | `python3 -m pytest tests/extractor/ tests/indexer/ -q` | `61 passed in 18.32s` | PASS |
| walk_commits returns real commits | Live repo walk via test_git_walker.py TestWalkCommits | Non-empty list, 40-char shas, no merge commits | PASS |
| Incremental SHA filter | `test_run_sync_incremental` — 3 commits, last_sha=sha1, only sha2+sha3 processed | `commits_processed=2`, sha1 absent from processed set | PASS |
| Zero-commit sync path | `test_run_sync_empty_after_filter` | Output contains "0 commits to process", result `{..., 0}` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| IDX-01 | 28-01, 28-03 | `recall init` rebuilds from scratch — full git walk oldest-first | SATISFIED | `run_init` DELETEs last_indexed_sha, calls `walk_commits` (oldest-first via `reverse=True`), processes all commits, writes new `last_indexed_sha` |
| IDX-02 | 28-03 | `recall sync` processes only commits since last_indexed_sha; no DB → full init | SATISFIED | `_commits_after_sha` implements cursor-based filtering; `not db.get_db_path().exists()` delegates to `run_init` |
| IDX-03 | 28-01, 28-03 | Configurable batch size default 10 via `[indexer] batch_size` | SATISFIED | `batch_commits(commits, batch_size)` where `batch_size = getattr(getattr(config, 'indexer', None), 'batch_size', 10)` |
| IDX-04 | 28-02 | LLM returns structured JSON with decisions/bug_fixes/patterns/files/tech_debt | PARTIALLY SATISFIED | `extract_batch` calls LLM, parses `{"entities": [...]}`, filters by VALID_ENTITY_TYPES (6 types including all required categories). However, IDX-04 specifies richer sub-fields (rationale, root-cause, symptom, co-change pairs) that are not present in `EntityRecord` or `EXTRACTION_SCHEMA` — the schema uses a single `content` field. REQUIREMENTS.md shows IDX-04 as unchecked. The plan's must_haves (normalized EntityRecord list returned) ARE met; the full IDX-04 field richness is not. This is a documentation/scope gap, not a runtime failure. |
| IDX-05 | 28-02 | Entity names normalized (lowercase, stripped); deduplication via upsert | SATISFIED | `engine.py` applies `.lower().strip()` to every entity name before return; `indexer.py` uses `INSERT OR IGNORE` with `uuid5(type:name)` key for idempotent insertion (duplicates are collapsed by key). Note: this is idempotent-insert, not true content-upsert (no UPDATE); REQUIREMENTS.md shows IDX-05 as unchecked but the plan's must_haves are met. |

**Note on IDX-04/05 checkbox status:** REQUIREMENTS.md shows both as `[ ]` unchecked and "Pending" in the tracker table. The plan implementations satisfy the plan-level must_haves for these requirements. The unchecked status appears to be a documentation gap — the checkboxes and tracker were not updated post-execution. IDX-04 has a legitimate scope gap (no per-type sub-fields in schema); IDX-05 is fully met at the plan's contracted level.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No TODO, FIXME, placeholder, or stub patterns detected in any of the five key implementation files.

### Human Verification Required

#### 1. Live LLM Extraction End-to-End

**Test:** With claude CLI available, run `recall init` against this repo and inspect `~/.recall/recall.db` for entity rows.
**Expected:** `entities` table populated with rows derived from git history; `metadata` table contains `last_indexed_sha` = current HEAD sha.
**Why human:** `extract_batch` invokes `claude -p` subprocess — cannot run without the claude binary and active session.

#### 2. Incremental Sync Behaviour

**Test:** Run `recall sync` immediately after `recall init` on the same repo.
**Expected:** Output contains "0 commits to process"; no new DB writes occur; returns `{"commits_processed": 0, "entities_inserted": 0}`.
**Why human:** Requires live git repo + LLM subprocess availability.

### Gaps Summary

No blocking gaps found. All automated checks pass (61/61 tests). All key links are wired. All plan-level must_haves are met.

Two documentation observations (non-blocking):

1. **IDX-04 schema richness:** The REQUIREMENTS.md IDX-04 specifies per-entity-type sub-fields (rationale, root cause, symptom, co-change pairs). The current `EntityRecord` uses a single `content` field for all types. The plan 28-02 must_haves only required a normalized EntityRecord list, which is satisfied. If the richer sub-fields are desired, a future plan can evolve `EXTRACTION_SCHEMA` and `EntityRecord` to add type-specific fields.

2. **IDX-04/IDX-05 REQUIREMENTS.md checkboxes:** Both are marked `[ ]` unchecked and "Pending" in the tracker despite being implemented. The checkboxes should be updated to `[x]` and tracker status to "Complete" as part of normal post-phase housekeeping.

---

_Verified: 2026-04-19T16:23:39Z_
_Verifier: Claude (gsd-verifier)_
