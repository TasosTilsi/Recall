---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Advanced Features
status: planning
last_updated: "2026-03-01T00:00:00.000Z"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-01 after v1.1 milestone start)

**Core value:** Context continuity without repetition — Claude remembers your preferences, decisions, and project architecture across all sessions without you stating them again, while sensitive data stays out of git through strict security filtering.
**Current focus:** Milestone v1.1 Advanced Features — defining requirements

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-01 — Milestone v1.1 started

## Performance Metrics

**Velocity:**
- Total plans completed: 35
- Average duration: 12.5 min
- Total execution time: 7h 17.6min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-storage-foundation | 3 | 75 min | 25 min |
| 02-security-filtering | 5 | 37 min | 7.4 min |
| 03-llm-integration | 5 | 83 min | 16.6 min |
| 04-cli-interface | 11 | 107 min | 9.7 min |
| 05-background-queue | 3 | 8.7 min | 2.9 min |
| 06-automatic-capture | 4 | 60.7 min | 15.2 min |
| 07-git-integration | 5 | 25 min | 5.0 min |

**Recent Trend:**
- Last 3 plans: 07-03 (7.5 min), 07-04 (5.4 min), 07-05 (9.7 min)
- Trend: Phase 07 complete - Git integration fully implemented with auto-heal, journal compaction, and hook templates. All 5 plans complete.

*Updated after each plan completion*

| Plan | Duration (s) | Tasks | Files |
|------|--------------|-------|-------|
| Phase 04 P01 | 161 | 2 tasks | 6 files |
| Phase 04 P02 | 355 | 2 tasks | 2 files |
| Phase 04 P03 | 180 | 2 tasks | 4 files |
| Phase 04 P04 | 141 | 2 tasks | 3 files |
| Phase 04 P05 | 227 | 2 tasks | 3 files |
| Phase 04 P06 | 420 | 2 tasks | 2 files |
| Phase 04 P07 | 219 | 2 tasks | 3 files |
| Phase 04 P08 | 4390 | 2 tasks | 3 files |
| Phase 04 P09 | 4353 | 2 tasks | 4 files |
| Phase 04 P10 | 106 | 2 tasks | 1 files |
| Phase 04 P11 | 112 | 2 tasks | 1 files |
| Phase 05 P01 | 214 | 2 tasks | 4 files |
| Phase 05 P02 | 167 | 2 tasks | 2 files |
| Phase 05 P03 | 141 | 2 tasks | 2 files |
| Phase 06 P01 | 202 | 2 tasks | 5 files |
| Phase 06 P02 | 1966 | 2 tasks | 4 files |
| Phase 06 P03 | 172 | 2 tasks | 3 files |
| Phase 06 P04 | 1300 | 2 tasks | 4 files |
| Phase 07 P02 | 160 | 2 tasks | 4 files |
| Phase 07 P01 | 300 | 2 tasks | 3 files |
| Phase 07 P03 | 447 | 2 tasks | 4 files |
| Phase 07 P04 | 325 | 2 tasks | 2 files |
| Phase 07 P05 | 583 | 2 tasks | 7 files |
| Phase 7.1 P04 | 300 | 2 tasks | 3 files |
| Phase 7.1 P03 | 180 | 2 tasks | 5 files |
| Phase 7.1 P02 | 230 | 2 tasks | 5 files |
| Phase 7.1 P01 | 240 | 2 tasks | 10 files |
| Phase 08-mcp-server P01 | 107 | 2 tasks | 3 files |
| Phase 08 P02 | 270 | 2 tasks | 1 files |
| Phase 08 P03 | 1577 | 2 tasks | 5 files |
| Phase 08-mcp-server P04 | 2173 | 2 tasks | 13 files |
| Phase 8.1-gap-closure-verification-files-inserted P02 | 117 | 1 tasks | 1 files |
| Phase 8.1-gap-closure-verification-files-inserted P01 | 300 | 1 tasks | 1 files |
| Phase 8.4-gap-closure-documentation-traceability-inserted P01 | 900 | 2 tasks | 32 files |
| Phase 8.6-gap-closure-runtime-bugs-inserted P01 | 70 | 2 tasks | 1 files |
| Phase 8.6-gap-closure-runtime-bugs-inserted P02 | 255 | 2 tasks | 1 files |
| Phase 8.7 P01 | 130 | 4 tasks | 1 files |
| Phase 8.7 P02 | 126 | 7 tasks | 1 files |
| Phase 8.7 P03 | 120 | 5 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- CLI-first architecture: CLI provides single source of truth, hooks and MCP wrap it
- Kuzu instead of in-memory: Better persistence, performance, and graph query capabilities
- Cloud Ollama with local fallback: Free tier for most operations, local models when quota exhausted
- Separate global + per-project graphs: Global preferences apply everywhere, project knowledge isolated
- Background async capture: Never blocks dev work, queues locally and processes in background
- Path configuration using Path.home(): Cross-platform compatibility for global database location
- GraphScope enum pattern: Type-safe routing between global and project scopes
- .git directory detection for project roots: Standard git convention, reliable across platforms
- Singleton pattern per scope: Prevents multiple Database objects to same Kuzu path
- asyncio.run() for async cleanup: Wraps KuzuDriver.close() for synchronous API
- Kuzu Connection API: Use kuzu.Connection(db) constructor, not db.connect() method
- Test isolation with monkeypatch: Prevents test pollution of user's real databases
- Aggressive entropy thresholds: BASE64=3.5, HEX=2.5 for maximum secret detection sensitivity
- Frozen dataclasses for security: Immutable security findings prevent accidental modification
- Computed properties pattern: was_modified computed from findings list rather than stored state
- Symlink resolution for security: Always Path.resolve() before pattern matching to prevent bypass attacks
- Fail-closed security posture: Unresolvable paths are excluded rather than allowed through
- Singleton audit logger: One SecurityAuditLogger per process to prevent multiple file handles
- Project-local audit logs: .graphiti/audit.log for per-project security tracking
- detect-secrets plugin config format: List of dicts with 'name' key and plugin-specific params
- Allowlist SHA256 hashes only: Never store plain text secrets, only hashes for secure lookup
- Required comments on allowlist: All allowlist entries require comment for audit trail
- transient_settings for thread-safety: Use detect-secrets transient_settings context manager
- Typed placeholders format: [REDACTED:type] format preserves detection type for debugging
- Storage never blocked: Sanitization always returns content, never raises exceptions for detected secrets
- Path.match() for glob patterns: Use Path.match() instead of string manipulation for proper ** glob semantics
- Project-scoped audit logger: Pass project_root to audit logger for correct log directory location
- Singleton reset in tests: Reset singleton instances in test setup for proper isolation
- Frozen dataclass for LLM config: Immutable configuration via dataclass(frozen=True)
- TOML configuration format: Python 3.11+ stdlib support, human-readable, type-safe parsing
- Environment variables override TOML: Security best practice for API keys, 12-factor app pattern
- Extensive configuration docs: WHY/WHEN/GOTCHA documentation for every configurable option
- Cloud-first failover pattern: Try cloud Ollama first, fall back to local on errors
- 429-only cooldown: Only rate-limit errors trigger cooldown; other errors retry cloud on next request
- Fixed delay retry: 10s fixed delay between retries (not exponential) for predictability
- Cooldown state persistence: Persist to JSON to survive restarts and prevent re-hitting rate limits
- Largest model selection: Select largest available model from fallback chain based on parameter count
- Header-based quota tracking: Parse x-ratelimit-* headers with local counting fallback
- SQLite-backed request queue: Persistent queue via persistqueue.SQLiteAckQueue with ack/nack pattern
- Bounded queue with pruning: Remove oldest items when max_size reached to prevent disk fill
- TTL-based expiry: Skip stale items older than configured TTL during processing
- Integrated quota tracking: OllamaClient tracks quota from headers or local count after cloud calls
- Queue-and-raise pattern: Failed requests queued with ID, exception includes tracking info
- Singleton LLM client: get_client() provides shared instance for quota/cooldown/queue state
- Convenience API: chat(), generate(), embed() functions at module level for clean imports
- [Phase 04]: DEFAULT_LIMIT = 15 for result pagination (user decision: 10-20 range)
- Mock data stubs for graph operations: Enables CLI testing before graph implementation with clear TODO markers for integration
- Rich Panel with Markdown for summaries: Professional formatted output respecting terminal capabilities
- confirm_action() for destructive ops: Single confirmation with --force bypass balances safety and UX
- list_cmd.py filename: Avoid shadowing Python's built-in list keyword
- Ambiguous name resolution pattern: Interactive numbered list prompts for user selection in show/delete commands
- Delete --force no short flag: Avoid conflict with --format (-f), makes destructive ops more explicit
- [Phase 04-02]: Auto-init .graphiti/ directory on first project-scope add operation for frictionless onboarding
- [Phase 04-02]: Stub functions return mock data for CLI flow testing before full graph integration
- [Phase 04-02]: Remove explicit Exit(SUCCESS) calls - Typer handles normal exit automatically
- [Phase 04-02]: Default search mode is semantic (--exact enables literal matching)
- [Phase 04-05]: Config uses dotted key paths (cloud.endpoint, retry.max_attempts) matching TOML structure for intuitive navigation
- [Phase 04-05]: Health checks use ok/warning/error status with 80%/95% quota thresholds for advance warning
- [Phase 04-05]: Sensitive values (api_key) masked as *** in display while remaining writable via --set for security
- [Phase 04-05]: Manual TOML writing for simple config structure avoids tomli_w dependency while remaining maintainable
- [Phase 04-06]: Separate test files for foundation vs commands improves maintainability and enables parallel test execution
- [Phase 04-06]: Mock all stub functions for fast, isolated CLI tests (<1s) that validate UX without requiring graph integration
- [Phase 04-06]: Human verification checkpoint ensures terminal UX meets professional standards beyond what automated tests can verify
- [Phase 04-06]: JSON extraction via bracket matching handles Rich pretty-printing while testing actual user-facing output
- [Phase 04-08]: LLMUnavailableError handling in CLI provides user-friendly messages directing to 'graphiti health' for diagnostics
- [Phase 04-08]: project_root parameter threading ensures correct scope resolution from CLI commands through to GraphService
- [Phase 04-08]: Date/type/tag filters in search documented as future enhancements while maintaining CLI UX
- [Phase 04-09]: Direct delegation pattern for CLI stub replacement preserves existing CLI interface while connecting to real graph operations
- [Phase 04-10]: Use EntityNode.get_by_group_ids() instead of raw Cypher for list_entities() - leverages graphiti_core's built-in API
- [Phase 04-10]: Case-insensitive CONTAINS matching for get_entity() enables flexible entity lookup ("python" matches "Python SDK")
- [Phase 04-10]: Node.delete_by_uuids() handles Kuzu-specific deletion including RelatesToNode_ cleanup automatically
- [Phase 04-10]: Best-effort stats pattern: get_stats() returns zeros on failure rather than raising exceptions for robustness
- [Phase 04-11]: summarize() limits to 200 entities with 100-entity prompt cap to avoid overwhelming LLM context
- [Phase 04-11]: LLM fallback pattern: summarize() returns entity listing on LLMUnavailableError rather than failing
- [Phase 04-11]: compact() uses exact case-insensitive name matching for deduplication (fuzzy/semantic dedup deferred to Phase 9)
- [Phase 04-11]: Deduplication keeps entity with longest summary (assumes most informative), deletes rest via Node.delete_by_uuids()
- [Phase 04-11]: Extracted _get_db_size() helper to avoid code duplication between compact() and get_stats()
- [Phase 05-01]: JobStatus enum for type-safe status tracking (PENDING, PROCESSING, FAILED, DEAD)
- [Phase 05-01]: QueuedJob dataclass non-frozen to allow status/attempts mutation during processing
- [Phase 05-01]: Dead letter table uses separate SQLite connection with WAL mode for thread safety
- [Phase 05-01]: Soft capacity limit always accepts jobs but logs warnings at 80% and 100%+ capacity
- [Phase 05-01]: is_hook_context() checks CLAUDE_* env vars, TTY status, and CI/CD markers for silent mode
- [Phase 05-01]: FIFO batching: get_batch() collects consecutive parallel jobs, stops at sequential barrier
- [Phase 05-01]: Connection-per-call pattern for dead letter operations ensures thread safety
- [Phase 05-02]: ThreadPoolExecutor with 4 max_workers optimal for I/O-bound CLI replay
- [Phase 05-02]: Non-daemon threads prevent job loss on process exit during graceful shutdown
- [Phase 05-02]: Event.wait(timeout) for responsive shutdown without busy-waiting during backoff delays
- [Phase 05-02]: Conditional worker startup with threshold=1 (start on any pending job)
- [Phase 05-02]: Health levels at 80%/100% thresholds match established health check pattern
- [Phase 05-02]: CLI-first architecture: worker replays CLI commands via subprocess for consistency
- [Phase 05-03]: Queue CLI uses Typer command group pattern (app.add_typer) for subcommand organization
- [Phase 05-03]: JSON format support enables programmatic queue monitoring and automation
- [Phase 05-03]: Blocking process command provides synchronous CLI fallback when MCP not running
- [Phase 05-03]: Retry 'all' enables bulk dead letter recovery for operational convenience
- [Phase 06-01]: Atomic rename pattern for pending_commits file prevents race conditions during concurrent append
- [Phase 06-01]: Per-file diff truncation at 500 lines via awk for context preservation with payload limits
- [Phase 06-01]: Security filter runs BEFORE LLM (sanitize_content gate prevents secrets reaching LLM)
- [Phase 06-01]: Graceful LLM fallback to concatenation on unavailable (better to store raw than lose capture)
- [Phase 06-01]: All 4 relevance categories enabled by default (decisions/architecture/bugs/dependencies)
- [Phase 06-01]: Batch size defaults to 10 items per user decision from Phase 6 research
- [Phase 06-02]: Append strategy for existing hooks (non-destructive, preserves other tools' hooks)
- [Phase 06-02]: GRAPHITI_HOOK_START/END markers for idempotent detection and removal
- [Phase 06-02]: Config check on every hook run (exit immediately if hooks.enabled=false)
- [Phase 06-02]: Default enabled=True when config key missing (hooks installed intentionally)
- [Phase 06-02]: Graceful failure handling (try both git and Claude hooks even if one fails)
- [Phase 06-04]: Auto-install hooks on first 'graphiti add' in any git project (frictionless onboarding)
- [Phase 06-04]: Best-effort auto-install pattern (never fails add operation, logs warning on failure)
- [Phase 06-04]: CLI capture command supports both manual and auto modes for user/hook-triggered capture
- [Phase 06-04]: Hooks command group provides install/uninstall/status lifecycle management
- [Phase 07-01]: YYYYMMDD_HHMMSS_<uuid6hex>.json filename format ensures chronological sorting and collision prevention
- [Phase 07-01]: UTC timezone-aware timestamps for cross-timezone deterministic sorting
- [Phase 07-01]: Frozen Pydantic models for immutable journal entries (consistent with frozen dataclass pattern)
- [Phase 07-01]: Git author auto-detection with graceful fallback to unknown/unknown@local
- [Phase 07-01]: Migration-style individual timestamped files eliminate merge conflicts vs append-only log
- [Phase 07-02]: Best-effort pattern for git config generation (logs warnings, never raises exceptions)
- [Phase 07-02]: Idempotent gitattributes generation to prevent duplicate LFS tracking lines
- [Phase 07-02]: LFS pointer detection via file size (<200 bytes) and version string check
- [Phase 07-02]: Journal rebuild fallback when LFS unavailable ensures system works without LFS installed
- [Phase 07-04]: Auto-stage journal entries on best-effort basis (never block commits on staging errors)
- [Phase 07-04]: Schema validation uses JournalEntry.model_validate for strict Pydantic enforcement
- [Phase 07-04]: Secret scanning leverages existing Phase 2 sanitize_content (belt-and-suspenders with LFS)
- [Phase 07-04]: Size thresholds at 50MB/100MB excluding LFS-tracked database with warnings not blocking commits
- [Phase 07-04]: GRAPHITI_SKIP=1 environment variable bypasses all pre-commit checks for WIP commits
- [Phase 07-04]: Errors block commits (schema/secrets), warnings inform but allow (size)
- [Phase 07-03]: Atomic checkpoint updates using temp file + Path.replace() prevents corruption during crash recovery
- [Phase 07-03]: Per-entry checkpoint updates (not batch) prevent duplicate processing on crash recovery
- [Phase 07-03]: Microsecond precision in journal filenames (YYYYMMDD_HHMMSS_ffffff_<uuid>) ensures chronological ordering for entries in same second
- [Phase 07-03]: Callback pattern (apply_fn) allows replay engine testing independently from database application
- [Phase 07-03]: Last-write-wins conflict resolution achieved by processing entries in chronological order
- [Phase 07-05]: Post-merge auto-heal never blocks merge (always exit 0 even on errors)
- [Phase 07-05]: Auto-setup is best-effort (logs warnings, never raises exceptions)
- [Phase 07-05]: Journal compaction requires checkpoint to ensure safe deletion boundaries
- [Phase 07-05]: Safety buffer of 7 days prevents accidental deletion of very recent entries
- [Phase 07-05]: Hook installer generalized with _install_hook helper for DRY across hook types
- [Architectural pivot 2026-02-20]: Local-first decision — .graphiti/ fully gitignored, no journal committed to git. Journal writer, replay engine, checkpoint tracking, LFS helpers removed in Phase 7.1. Pre-commit hooks (secrets, size) preserved. On-demand git history indexer replaces journal replay as source of knowledge.
- [Architectural pivot 2026-02-20]: Phase 7.1 inserted to execute the pivot before Phase 8. Phase 10 (Frontend UI) added as final phase — localhost graph visualization + monitoring dashboard. Total phases now 10.
- [Phase 7.1-03]: post-checkout.sh checks $3 argument after graphiti availability but before config — exits on $3=0 (file checkout), only indexes on $3=1 (branch switch)
- [Phase 7.1-03]: New hook installer functions take git_dir: Path (the .git directory) while existing helpers take repo_path — new functions derive repo_path via git_dir.parent
- [Phase 7.1-03]: upgrade_postmerge_hook detects old Phase 7 hooks by 'autoheal', 'auto_heal', 'journal' string presence in hook content; only upgrades hooks with GRAPHITI_HOOK_START marker (graphiti-owned hooks)
- [Phase 7.1]: Store only 8-char SHA prefixes in processed_shas list, capped at 10,000 entries to prevent unbounded growth
- [Phase 7.1]: Two-pass extraction per commit: structured Q&A + free-form entity facts, both tagged git-history-index: for traceability
- [Phase 7.1]: Quality gate fails open: exception during commit stats check = process the commit rather than skip
- [Phase 7.1]: save_state() after every processed commit for crash recovery at cost of I/O (crash-safe indexing)
- [Phase 7.1]: scan_staged_secrets() scans ALL staged files (not just journal/) — broader scope than old scan_journal_secrets()
- [Phase 7.1]: ensure_git_config() return dict simplified to {gitignore: bool} only — gitattributes key removed with LFS feature
- [Phase 7.1-04]: Pre-validate git repo with git.Repo() before GitIndexer instantiation for earlier error messaging
- [Phase 7.1-04]: full=False passed to indexer.run() even after --full; reset_full() handles the wipe step separately
- [Phase 7.1-04]: upgrade_postmerge_hook() called first in hooks install sequence to migrate Phase 7 hooks before installing new ones
- [Phase 7.1-04]: git_dir derived as root / '.git' from resolve_scope() result for git_dir-based installer functions
- [Phase 08-mcp-server]: mcp[cli]>=1.26.0,<2.0.0 upper bound pins to stable 1.x branch before MCP v2 Q1 2026
- [Phase 08-mcp-server]: TOON 3-item threshold: encode_response applies TOON for 3+ item lists, JSON for scalars/small responses (header overhead exceeds savings below threshold)
- [Phase 08-mcp-server]: 4 chars/token approximation for token budget trimming — avoids tiktoken dependency (OpenAI-specific, 12% error for Claude)
- [Phase 08]: Always pass --force to graphiti_delete: MCP callers have no interactive TTY for confirmation
- [Phase 08]: graphiti_health never raises on non-zero exit: health check failures are informational status not errors
- [Phase 08]: graphiti_capture uses subprocess.Popen with start_new_session=True and DEVNULL to prevent stdio corruption and zombie processes
- [Phase 08-03]: graphiti://context resource returns empty string silently for empty graph — no user-visible error or prompt (silent = correct UX for new projects)
- [Phase 08-03]: Stale index triggers non-blocking background re-index via Popen; context injection returns immediately with current (possibly stale) data
- [Phase 08-03]: SKILL_MD_CONTENT embedded as constant in install.py — mcp install works from any installation path without external file dependencies
- [Phase 08-03]: install_mcp_server() merges into existing ~/.claude.json rather than overwriting — preserves other MCP servers' configs
- [Phase 08-03]: FastMCP registration: mcp.tool()(fn) pattern (not decorator at definition site) keeps tool handlers as plain testable callables
- [Phase 08-mcp-server]: Resolve graphiti CLI via sys.executable parent dir: bare 'graphiti' fails when Claude Code's PATH excludes venv bin/
- [Phase 08-mcp-server]: MCP 1.x uses newline-delimited JSON protocol (not HTTP Content-Length headers from MCP 0.x)
- [Phase 8.1-gap-closure-verification-files-inserted]: Phase 08 VERIFICATION.md status is 'passed' — post-verification bug discovery does not retroactively block procedural verification
- [Phase 8.1-gap-closure-verification-files-inserted]: R6.2 and R6.3 declared SATISFIED (issues noted) with forward reference to Phase 8.2 gap closure — known-issue notes distinguish procedural completion from post-verification bug tracking
- [Phase 8.1-gap-closure-verification-files-inserted]: Synthesize Phase 03 VERIFICATION.md from UAT.md + SUMMARY files — evidence complete for retrospective verification
- [Phase 8.4-gap-closure-documentation-traceability-inserted]: Apply gap-closure phase reality over plan spec: when dependency phases already ran, mark requirements Complete rather than Pending
- [Phase 8.4-gap-closure-documentation-traceability-inserted]: requirements-completed YAML frontmatter in SUMMARY.md makes requirement tracking machine-readable and consistent with REQUIREMENTS.md traceability table
- [Phase 8.4-gap-closure-documentation-traceability-inserted]: R4.1 stays Pending until human runs Phase 8.5 verification guide — guide written != human execution confirmed
- [Phase 8.6-01]: Single normalization call site in _generate_response() after json.loads() and before isinstance check covers both bare-list fallback and normal dict path with one call
- [Phase 8.6-01]: Use lstrip('.') not strip('.') — only strip leading dots, never trailing, to preserve dot-prefixed values like '.env.test_verification'
- [Phase 8.6-02]: process_queue() race condition: use worker.stop(timeout=120) join pattern instead of qsize()-only polling — qsize() drops to 0 on dequeue into unacked state, not on job completion
- [Phase 8.6-02]: 120s stop timeout: accommodates slow LLM calls (gemma2:9b commit summarization can take 60-120s)
- [Phase 8.7]: Skip when new_file=True (not deleted_file=True) — GitPython marks index-only files as deleted_file when diffing index->HEAD
- [Phase 8.7]: Initial-commit fallback uses repo.index.entries directly — git.NULL_TREE unsupported in GitPython 3.1.x
- [Phase 8.7-02]: Pass root (repo_path) not git_dir to pre-commit installer functions — install_precommit_hook takes repo_path unlike post-checkout/post-rewrite which take git_dir
- [Phase 8.7-02]: Pre-commit row placed first in status table — secret-scanning is primary security gate, ordering emphasizes importance
- [Phase 8.7-02]: Uninstall non-destructive for pre-commit — graphiti section removed but template header stub remains (consistent with all other hooks)
- [Phase 8.7-03]: Commit clean version before new-file sub-test so index is in known state — prevents false positives from leftover staged changes
- [Phase 8.7-03]: Verification scripts must be updated after fixing bugs to directly assert correct behaviour (not document workarounds)

### Pending Todos

1. **Distribution/polish phase** — PATH detection in `graphiti mcp install`, codebase refactor sweep, Claude plugin configuration (`hooks/hooks.json` + manifest for marketplace distribution)
   → `.planning/todos/pending/2026-02-23-create-distribution-polish-phase-for-plugin-path-and-refactor.md`

### Blockers/Concerns

**BLOCKING Phase 06 human verification (Tests 3 & 4) — discovered 2026-02-26:**

1. ~~**Bug: LLM `.name` field parsing** (`src/graph/adapters.py`)~~ **FIXED 2026-02-27** (commit 7f55287)
   - `_normalize_field_names()` added to `OllamaLLMClient` in `src/graph/adapters.py`
   - Called before `model_validate()` in `_generate_response()`; dot-prefixed keys stripped recursively

2. ~~**Bug: `process_queue()` race condition** (`src/queue/__init__.py`)~~ **FIXED 2026-02-27** (commit df7d984)
   - `process_queue()` now calls `worker.stop(timeout=120.0)` after `qsize()==0`, joining the thread to ensure in-flight jobs complete
   - Docstring explains: qsize() drops to 0 on dequeue to "unacked" state, not on ack; join() is the correct completion gate

**Phase 06 verification status**: Tests 1 (hook install) and 2 (timing) PASSED. Tests 3 and 4 blocked by above bugs. Must re-run after Phase 8.6 is executed.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Fix invalid permission entry in settings.local.json causing Claude startup error | 2026-02-19 | n/a (gitignored) | [1-fix-invalid-permission-entry-in-settings](./quick/1-fix-invalid-permission-entry-in-settings/) |

## Session Continuity

Last session: 2026-02-27
Stopped at: Phase 8.7 executed and verified (3/3 plans, passed 3/3). ROADMAP updated. Ready for Phase 9.
Resume file: .planning/ — Phase 8.7 COMPLETE; next is Phase 9 (Advanced Features)

**Phase 7.1 Context Captured:** Git Indexing Pivot. Key decisions: remove journal/replay/LFS/checkpoint from Phase 7, keep secrets+size pre-commit hooks. Indexer = historical bootstrap (brownfield), Phase 6 = ongoing real-time capture. SHA deduplication prevents overlap. --full flag for clean rebuild. Quality gate skips version-bump/bot/merge/tiny commits. Two-pass extraction (structured Q&A + free-form entity). Stale triggers: post-merge, post-checkout, post-rewrite (NOT post-commit). Cooldown 5 min between auto-triggers.
**Phase 8 Context Captured:** SKILL.md + MCP Server. Key decisions: all CLI commands as MCP tools (graphiti_ prefix), subprocess wrapper, plain text responses, context from local Kuzu DB (built by Phase 7.1 indexer), mcp.context_tokens config key (default 8192), stdio default + HTTP, graphiti mcp install command for zero-config setup.
