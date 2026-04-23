---
phase: 32-claude-plugin-skills
verified: 2026-04-23T15:47:00Z
status: passed
score: 10/10 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 9/10
  gaps_closed:
    - "SKILL-01: recall_setup.md now includes Step 5 — optional recall init after health check (lines 104-114)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run /recall-setup end-to-end in Claude"
    expected: "Claude walks through provider selection, writes config.toml, runs recall health, then asks if user wants to run recall init on the current repo (Step 5)"
    why_human: "Skill execution is a conversational Claude behavior — cannot be verified programmatically without a running Claude session"
  - test: "Run recall install then restart Claude, type /recall-index"
    expected: "Claude detects DB state, runs the correct command, reports entity breakdown"
    why_human: "Skill dispatch from slash command requires running Claude with plugin installed"
  - test: "Idempotent install — run recall install twice, inspect ~/.claude/settings.json"
    expected: "Single mcpServers.recall entry; second run prints already registered — skipped"
    why_human: "Unit tests cover this with patching; real-filesystem confirmation valuable"
---

# Phase 32: Claude Plugin Skills Verification Report

**Phase Goal:** Deliver Claude plugin manifest, recall install CLI command, /recall-setup skill, and /recall-index skill — enabling one-command plugin installation and guided setup for end users.
**Verified:** 2026-04-23T15:47:00Z
**Status:** passed
**Re-verification:** Yes — after SKILL-01 gap closure (Step 5 recall init added to recall_setup.md)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | claude-plugin.json exists at repo root and is valid JSON with mcpServers and skills keys | VERIFIED | File exists; valid JSON; mcpServers.recall + 2 skills entries (recall-setup, recall-index) |
| 2 | `recall install` command runs without error and writes MCP entry to ~/.claude/settings.json | VERIFIED | `recall install --help` returns correct help; install_mcp_global writes to settings.json per source |
| 3 | `recall install` creates ~/.recall/ if it does not exist | VERIFIED | ensure_recall_dir() creates ~/.recall/ if missing, returns True |
| 4 | `recall install` does NOT overwrite an existing ~/.recall/config.toml | VERIFIED | ensure_recall_dir() only creates the directory, never touches config.toml |
| 5 | Running `recall install` twice is idempotent — no duplicate mcpServers entries | VERIFIED | install_mcp_global checks for existing recall key; skips if present and force=False |
| 6 | A /recall-setup skill file exists that Claude reads when the user types /recall-setup | VERIFIED | src/cli/skills/recall_setup.md exists (120 lines), deployed by installer |
| 7 | The skill guides the user to choose a provider, enter credentials, and writes ~/.recall/config.toml; ends with recall health and optionally runs recall init | VERIFIED | Step 1-4 cover config check, provider, credentials, config.toml write, recall health. Step 5 (lines 104-114) asks user if they want to run `recall init` on the current repo — closes SKILL-01 gap |
| 8 | install_mcp_server() installs recall-setup.md to ~/.claude/skills/recall/ | VERIFIED | RECALL_SETUP_SKILL_CONTENT loaded from .md and confirmed to contain Step 5 recall init content; installed to ~/.claude/skills/recall/recall-setup.md |
| 9 | A /recall-index skill file exists with recall init/sync branching and entity breakdown | VERIFIED | src/cli/skills/recall_index.md (89 lines) contains recall sync, recall init, entity breakdown |
| 10 | install_mcp_server() installs recall-index.md to ~/.claude/skills/recall/ | VERIFIED | RECALL_INDEX_SKILL_CONTENT contains recall sync + entity; 3 grep matches for "recall-index.md" in install.py |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `claude-plugin.json` | Plugin manifest with mcpServers + 2 skills | VERIFIED | Valid JSON; mcpServers.recall = {command: "recall", args: ["mcp","serve"]}; 2 skills: recall-setup, recall-index |
| `src/cli/commands/install_cmd.py` | recall install CLI command | VERIFIED | 103 lines; exports install_mcp_global, ensure_recall_dir, install_command; uses structlog |
| `src/cli/__init__.py` | install command wired into typer app | VERIFIED | Line 31: imports install_command; line 41: app.command("install")(install_command) |
| `src/cli/skills/recall_setup.md` | /recall-setup skill with provider/config/health walkthrough + optional recall init | VERIFIED | 120 lines; Steps 1-4 intact; Step 5 (lines 104-114) adds optional recall init after health check — SKILL-01 satisfied |
| `src/mcp_server/install.py` | Deploys both skills; targets ~/.claude/settings.json | VERIFIED | RECALL_SETUP_SKILL_CONTENT (includes Step 5) + RECALL_INDEX_SKILL_CONTENT constants; writes to settings.json; recall_setup_skill_installed + recall_index_skill_installed keys |
| `src/cli/skills/recall_index.md` | /recall-index skill with DB detection + entity reporting | VERIFIED | 89 lines; recall health → branch to recall init or recall sync; entity type breakdown; fallback via recall list --format json |
| `tests/test_install_cmd.py` | 6 unit tests covering all TDD behaviors | VERIFIED | 6/6 pass in 0.07s |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| src/cli/__init__.py | src/cli/commands/install_cmd.py | app.command("install") | WIRED | Line 31: import; line 41: app.command registration confirmed |
| src/cli/commands/install_cmd.py | ~/.claude/settings.json | json read/write | WIRED | install_mcp_global reads/merges/writes settings.json with mcpServers.recall entry |
| src/mcp_server/install.py | ~/.claude/skills/recall/recall-setup.md | Path.write_text(RECALL_SETUP_SKILL_CONTENT) | WIRED | Section 3 of install_mcp_server() writes recall-setup.md; RECALL_SETUP_SKILL_CONTENT confirmed to include Step 5 recall init content |
| src/mcp_server/install.py | ~/.claude/skills/recall/recall-index.md | Path.write_text(RECALL_INDEX_SKILL_CONTENT) | WIRED | Section 3b of install_mcp_server() writes recall-index.md; 3 grep matches for "recall-index.md" in file |
| src/cli/skills/recall_index.md | recall sync | Bash tool invocation in skill body | WIRED | "recall sync" at line 34; "recall init" at line 29 — both branches present |

---

### Data-Flow Trace (Level 4)

Not applicable — artifacts are skill definition files (markdown prompts) and a CLI command. No dynamic data rendering components involved. The installer reads .md source files at import time and writes them to the filesystem — this is a static copy operation, not a data flow from a query.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| claude-plugin.json is valid JSON with required keys | python3 -c "import json; d=json.load(open('claude-plugin.json')); assert 'mcpServers' in d and 'skills' in d and len(d['skills'])==2" | Pass | PASS |
| RECALL_SETUP_SKILL_CONTENT contains recall health + recall init + Step 5 | python -c "from src.mcp_server.install import RECALL_SETUP_SKILL_CONTENT; assert 'recall health' in RECALL_SETUP_SKILL_CONTENT; assert 'recall init' in RECALL_SETUP_SKILL_CONTENT; assert 'Step 5' in RECALL_SETUP_SKILL_CONTENT" | Pass | PASS |
| RECALL_INDEX_SKILL_CONTENT importable and contains recall sync + entity | python -c "from src.mcp_server.install import RECALL_INDEX_SKILL_CONTENT; assert 'recall sync' in RECALL_INDEX_SKILL_CONTENT and 'entity' in RECALL_INDEX_SKILL_CONTENT.lower()" | Pass | PASS |
| install_cmd.py 6 unit tests | .venv/bin/python -m pytest tests/test_install_cmd.py -x -q | 6 passed in 0.07s | PASS |
| recall install --help works | .venv/bin/recall install --help | Shows help with --force option | PASS |
| install-related tests | .venv/bin/python -m pytest tests/ -x -q -k "install" | 6 passed, 93 deselected | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INST-02 | 32-01 | claude-plugin.json manifest registers two skills and MCP server | SATISFIED | claude-plugin.json at repo root; valid JSON; mcpServers.recall + 2 skills entries confirmed |
| INST-03 | 32-01 | Plugin install creates ~/.recall/ if missing; does not overwrite config.toml | SATISFIED | ensure_recall_dir() creates dir only; never writes config.toml; Test 5 covers config.toml preservation |
| SKILL-01 | 32-02 | /recall-setup skill: provider choice, credentials, config.toml write, recall health, optionally recall init | SATISFIED | Skill file (120 lines) covers Steps 1-4 (config check, provider, credentials, health) + Step 5 (lines 104-114): asks user whether to run recall init on current repo; RECALL_SETUP_SKILL_CONTENT in installer confirmed to include Step 5 |
| SKILL-02 | 32-03 | /recall-index skill: recall sync or init, commits processed, entity type breakdown | SATISFIED | recall_index.md covers DB detection, both branches, entity breakdown with fallback; installer deploys it |

**Orphaned requirements check:** No additional Phase 32 requirements found in REQUIREMENTS.md beyond SKILL-01, SKILL-02, INST-02, INST-03.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No TODOs, FIXMEs, placeholder text, empty handlers, or hardcoded stub returns found in any phase 32 artifact.

---

### Human Verification Required

#### 1. /recall-setup End-to-End Flow (including Step 5)

**Test:** Install plugin with `recall install`, open Claude, type `/recall-setup`
**Expected:** Claude follows the walkthrough: checks existing config, asks for provider, writes config.toml, runs recall health, then at Step 5 asks "Would you like to index the current repository's git history now?" and runs `recall init` if confirmed
**Why human:** Skill dispatch and conversational execution require a live Claude session with the plugin installed

#### 2. /recall-index End-to-End Flow

**Test:** In a repo with no DB, type `/recall-index` in Claude; verify it runs `recall init`; then in a repo with existing DB, type `/recall-index` and verify it runs `recall sync`
**Expected:** Correct branch taken; entity type breakdown shown; commit count reported
**Why human:** DB detection logic branches on exit code of `recall health` — requires a real execution environment

#### 3. Idempotent Install

**Test:** Run `recall install` twice in a real shell; inspect `~/.claude/settings.json` for duplicate mcpServers entries
**Expected:** Single mcpServers.recall entry; no duplicates; second run prints "already registered — skipped"
**Why human:** Test environment patching covers this in unit tests, but real-filesystem confirmation is valuable

---

### Gaps Summary

No gaps remain. The single gap from the initial verification (SKILL-01: missing optional `recall init` step in `/recall-setup` skill) is now closed. `src/cli/skills/recall_setup.md` was updated to 120 lines and now includes Step 5 (lines 104-114): after health passes, Claude asks the user if they want to index the current repository's git history and runs `recall init` if confirmed. The installer's `RECALL_SETUP_SKILL_CONTENT` constant reflects this change and was verified programmatically.

All four requirements (INST-02, INST-03, SKILL-01, SKILL-02) are satisfied. All 10 observable truths verified. All 7 required artifacts exist, are substantive, and are wired. All 6 unit tests pass.

**Commits verified present:** 6d7ab8e, 0c41ac7, 575b9f2, e52f14e, 408805e, 69fb4a7, c914a9a (original phase commits) + gap-fix commit adding Step 5 to recall_setup.md

---

_Verified: 2026-04-23T15:47:00Z_
_Verifier: Claude (gsd-verifier)_
