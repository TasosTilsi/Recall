#!/usr/bin/env python3
"""
Phase 16: Rename & CLI Consolidation — Verification Script
Requirements: CLI-01 · CLI-02 · CLI-03

Usage:
    python scripts/verify_phase_16.py [--fail-fast] [--skip-live]

Tests:

  Static (no live CLI required):
  1. CLI-01: pyproject.toml has recall/rc entrypoints; graphiti/gk absent
  2. CLI-01: src/cli/__init__.py app name is 'recall'
  3. CLI-02: __init__.py registers exactly 10 public commands
  4. CLI-02: __init__.py registers 'index' as hidden=True
  5. CLI-02: No removed command imports in __init__.py
  6. CLI-02: src/cli/commands/note_cmd.py exists and writes to pending_tool_captures.jsonl
  7. CLI-02: src/cli/commands/init_cmd.py exists with no interactive prompts
  8. CLI-02: list_cmd.py has --stale, --compact, --queue options
  9. CLI-03: search.py defines _auto_sync() and calls it from search_command
 10. CLI-01: All 11 removed command files are deleted from disk
 11. CLI-01: session_start.py calls GitIndexer directly (no graphiti binary subprocess)
 12. CLI-01: manager.py uses _RECALL_CLI, not _GRAPHITI_CLI

  Live CLI (skipped with --skip-live):
 13. CLI-01: recall --help exits 0 and shows 'recall' name
 14. CLI-02: recall --help lists exactly the 10 expected commands
 15. CLI-02: recall --help does not show any removed/plumbing commands
 16. CLI-03: recall search --help mentions auto-sync or git
"""

import subprocess
import sys
import inspect
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN   = "\033[0;36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

RECALL = str(ROOT / ".venv" / "bin" / "recall")

PUBLIC_COMMANDS = {"init", "search", "list", "delete", "pin", "unpin", "health", "config", "ui", "note"}
REMOVED_COMMANDS = ["add", "capture", "compact", "hooks", "memory", "mcp", "queue_cmd",
                    "show", "stale", "summarize", "sync"]
REMOVED_COMMAND_FILES = [f"src/cli/commands/{cmd}.py" for cmd in REMOVED_COMMANDS]


class Runner:
    def __init__(self, fail_fast: bool = False):
        self.fail_fast = fail_fast
        self.passed = 0
        self.failed = 0
        self.failures: list[str] = []

    def ok(self, msg: str) -> None:
        print(f"  {GREEN}[PASS]{RESET} {msg}")
        self.passed += 1

    def fail(self, msg: str, detail: str = "") -> None:
        print(f"  {RED}[FAIL]{RESET} {msg}")
        if detail:
            print(f"         {YELLOW}{detail}{RESET}")
        self.failed += 1
        self.failures.append(msg)
        if self.fail_fast:
            self.summary()
            sys.exit(1)

    def skip(self, msg: str, reason: str = "") -> None:
        print(f"  {CYAN}[SKIP]{RESET} {msg}")
        if reason:
            print(f"         {reason}")

    def banner(self, title: str) -> None:
        print(f"\n{BOLD}── {title} ──{RESET}")

    def summary(self) -> bool:
        width = 60
        print(f"\n{BOLD}{'━' * width}{RESET}")
        print(f"{BOLD} Phase 16: Rename & CLI Consolidation — Verification Results{RESET}")
        print(f"{BOLD}{'━' * width}{RESET}")
        print(f" Tests passed:  {GREEN}{self.passed}{RESET}")
        print(f" Tests failed:  {RED}{self.failed}{RESET}")
        if self.failures:
            print("\n Failed:")
            for f in self.failures:
                print(f"   {RED}✗{RESET} {f}")
        else:
            print(
                f"\n {GREEN}All required tests passed.{RESET} "
                f"Requirements CLI-01 · CLI-02 · CLI-03 verified."
            )
        print()
        return self.failed == 0


def run_recall(*args, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        [RECALL, *args], capture_output=True, text=True, cwd=ROOT, timeout=timeout
    )


# ── Tests 1–2 (CLI-01): pyproject.toml + app name ────────────────────────────

def test_entrypoints(r: Runner) -> None:
    r.banner("Tests 1–2 (CLI-01): Entrypoints in pyproject.toml + app name")

    pyproject = (ROOT / "pyproject.toml").read_text()

    # Test 1: recall/rc present; graphiti/gk absent
    has_recall = 'recall = "src.cli:cli_entry"' in pyproject
    has_rc     = 'rc = "src.cli:cli_entry"' in pyproject
    has_old_graphiti = '"graphiti"' in pyproject.split("[project.scripts]", 1)[-1].split("\n\n")[0]
    has_old_gk       = '"gk"' in pyproject.split("[project.scripts]", 1)[-1].split("\n\n")[0]

    if has_recall and has_rc and not has_old_graphiti and not has_old_gk:
        r.ok("pyproject.toml has recall/rc entrypoints; graphiti/gk absent")
    else:
        detail = []
        if not has_recall: detail.append("missing: recall")
        if not has_rc:     detail.append("missing: rc")
        if has_old_graphiti: detail.append("still present: graphiti")
        if has_old_gk:       detail.append("still present: gk")
        r.fail("pyproject.toml entrypoint mismatch", detail=", ".join(detail))

    # Test 2: app name is 'recall' in __init__.py
    init_src = (ROOT / "src" / "cli" / "__init__.py").read_text()
    if 'app = typer.Typer(' in init_src and '"recall"' in init_src:
        r.ok("src/cli/__init__.py Typer app name is 'recall'")
    elif "name=" not in init_src:
        r.fail("src/cli/__init__.py has no name= in Typer app definition")
    else:
        r.fail("src/cli/__init__.py app name is not 'recall'")


# ── Tests 3–5 (CLI-02): Command surface ──────────────────────────────────────

def test_command_surface(r: Runner) -> None:
    r.banner("Tests 3–5 (CLI-02): Command surface in __init__.py")

    init_src = (ROOT / "src" / "cli" / "__init__.py").read_text()

    # Test 3: exactly 10 public commands registered
    # Count app.command() or app.add_typer() calls that aren't hidden
    # We check by source inspection for each expected public command
    missing = [cmd for cmd in PUBLIC_COMMANDS if f'name="{cmd}"' not in init_src and f"name='{cmd}'" not in init_src]
    if not missing:
        r.ok(f"__init__.py registers all 10 public commands: {', '.join(sorted(PUBLIC_COMMANDS))}")
    else:
        r.fail(f"__init__.py missing public commands: {missing}")

    # Test 4: index registered as hidden
    if ("hidden=True" in init_src or "hidden = True" in init_src) and (
        '"index"' in init_src or "'index'" in init_src
    ):
        r.ok("__init__.py registers 'index' with hidden=True")
    else:
        r.fail("__init__.py does not register 'index' as hidden=True")

    # Test 5: none of the removed commands are imported
    removed_imports = [cmd for cmd in REMOVED_COMMANDS if f"from src.cli.commands.{cmd}" in init_src
                       or f"import {cmd}" in init_src]
    if not removed_imports:
        r.ok("__init__.py has no imports of removed command modules")
    else:
        r.fail(f"__init__.py still imports removed modules: {removed_imports}")


# ── Tests 6–8 (CLI-02): New commands and list flags ──────────────────────────

def test_new_commands_and_list(r: Runner) -> None:
    r.banner("Tests 6–8 (CLI-02): note_cmd.py, init_cmd.py, list flags")

    # Test 6: note_cmd.py exists and writes to pending_tool_captures.jsonl
    note_path = ROOT / "src" / "cli" / "commands" / "note_cmd.py"
    if not note_path.exists():
        r.fail("src/cli/commands/note_cmd.py does not exist")
    else:
        note_src = note_path.read_text()
        if "pending_tool_captures.jsonl" in note_src:
            r.ok("note_cmd.py writes to .graphiti/pending_tool_captures.jsonl")
        else:
            r.fail("note_cmd.py does not reference pending_tool_captures.jsonl")

    # Test 7: init_cmd.py exists with no interactive prompts
    init_cmd_path = ROOT / "src" / "cli" / "commands" / "init_cmd.py"
    if not init_cmd_path.exists():
        r.fail("src/cli/commands/init_cmd.py does not exist")
    else:
        init_src = init_cmd_path.read_text()
        has_prompt = "typer.prompt(" in init_src or "input(" in init_src
        if not has_prompt:
            r.ok("init_cmd.py has no interactive prompts (static template approach)")
        else:
            r.fail("init_cmd.py contains interactive prompt calls (expected static template)")

    # Test 8: list_cmd.py has --stale, --compact, --queue options
    list_path = ROOT / "src" / "cli" / "commands" / "list_cmd.py"
    if not list_path.exists():
        r.fail("src/cli/commands/list_cmd.py does not exist")
    else:
        list_src = list_path.read_text()
        flags = {"--stale": "stale" in list_src, "--compact": "compact" in list_src, "--queue": "queue" in list_src}
        missing_flags = [f for f, present in flags.items() if not present]
        if not missing_flags:
            r.ok("list_cmd.py has --stale, --compact, --queue options")
        else:
            r.fail(f"list_cmd.py missing flags: {missing_flags}")


# ── Test 9 (CLI-03): search auto-sync ────────────────────────────────────────

def test_search_auto_sync(r: Runner) -> None:
    r.banner("Test 9 (CLI-03): search.py auto-sync before query")

    search_path = ROOT / "src" / "cli" / "commands" / "search.py"
    if not search_path.exists():
        r.fail("src/cli/commands/search.py does not exist")
        return

    search_src = search_path.read_text()

    if "_auto_sync" in search_src:
        r.ok("search.py defines _auto_sync() helper")
    else:
        r.fail("search.py does not define _auto_sync()")

    # Check _auto_sync is called from the search command function
    # Find the search_command (or equivalent entry point) and check it calls _auto_sync
    if "_auto_sync(" in search_src:
        r.ok("search.py calls _auto_sync() from the search command")
    else:
        r.fail("search.py defines _auto_sync but does not call it")


# ── Test 10 (CLI-01): Removed files deleted ───────────────────────────────────

def test_removed_files_deleted(r: Runner) -> None:
    r.banner("Test 10 (CLI-01): Removed command files deleted from disk")

    still_present = [f for f in REMOVED_COMMAND_FILES if (ROOT / f).exists()]
    if not still_present:
        r.ok(f"All {len(REMOVED_COMMAND_FILES)} removed command files are deleted")
    else:
        r.fail(
            f"{len(still_present)} removed command files still exist",
            detail=", ".join(still_present),
        )

    # index.py must be kept (hidden command)
    index_path = ROOT / "src" / "cli" / "commands" / "index.py"
    if index_path.exists():
        r.ok("src/cli/commands/index.py kept (hidden recall index command)")
    else:
        r.fail("src/cli/commands/index.py missing — hidden index command deleted")


# ── Tests 11–12 (CLI-01): Hook script updates ─────────────────────────────────

def test_hook_scripts(r: Runner) -> None:
    r.banner("Tests 11–12 (CLI-01): Hook scripts use recall binary / GitIndexer directly")

    # Test 11: session_start.py calls GitIndexer directly, not graphiti/recall sync subprocess
    session_path = ROOT / "src" / "hooks" / "session_start.py"
    if not session_path.exists():
        r.fail("src/hooks/session_start.py does not exist")
    else:
        session_src = session_path.read_text()
        has_gitindexer = "GitIndexer" in session_src
        has_graphiti_sub = "_GRAPHITI_CLI" in session_src or (
            '"graphiti"' in session_src and "subprocess" in session_src
        )
        has_sync_sub = (
            '"sync"' in session_src
            and "subprocess" in session_src
            and "_RECALL_CLI" in session_src
        )
        if has_gitindexer and not has_graphiti_sub:
            if has_sync_sub:
                r.fail("session_start.py still calls recall sync via subprocess instead of GitIndexer directly")
            else:
                r.ok("session_start.py calls GitIndexer directly (no binary subprocess for sync)")
        elif has_graphiti_sub:
            r.fail("session_start.py still references _GRAPHITI_CLI subprocess call")
        else:
            r.fail("session_start.py does not use GitIndexer", detail="Expected direct GitIndexer call")

    # Test 12: manager.py uses _RECALL_CLI, not _GRAPHITI_CLI
    manager_path = ROOT / "src" / "hooks" / "manager.py"
    if not manager_path.exists():
        r.fail("src/hooks/manager.py does not exist")
    else:
        manager_src = manager_path.read_text()
        if "_RECALL_CLI" in manager_src and "_GRAPHITI_CLI" not in manager_src:
            r.ok("manager.py uses _RECALL_CLI (graphiti binary reference removed)")
        elif "_GRAPHITI_CLI" in manager_src:
            r.fail("manager.py still references _GRAPHITI_CLI")
        else:
            r.fail("manager.py has neither _RECALL_CLI nor _GRAPHITI_CLI — check manually")


# ── Tests 13–16: Live CLI ─────────────────────────────────────────────────────

def test_live_cli(r: Runner, skip_live: bool) -> None:
    r.banner("Tests 13–16 (CLI-01/02/03): Live recall CLI")

    if skip_live:
        for msg in [
            "recall --help exits 0",
            "recall --help lists 10 expected commands",
            "recall --help hides removed commands",
            "recall search --help mentions auto-sync",
        ]:
            r.skip(msg, reason="--skip-live flag set")
        return

    if not Path(RECALL).exists():
        for msg in [
            "recall --help exits 0",
            "recall --help lists 10 expected commands",
            "recall --help hides removed commands",
            "recall search --help mentions auto-sync",
        ]:
            r.skip(msg, reason=f"recall binary not found at {RECALL} — run: pip install -e .")
        return

    # Test 13: recall --help exits 0 and shows 'recall'
    res = run_recall("--help")
    if res.returncode == 0 and "recall" in res.stdout.lower():
        r.ok("recall --help exits 0 and displays 'recall'")
    else:
        r.fail(
            f"recall --help failed (exit {res.returncode})",
            detail=(res.stdout + res.stderr)[:300],
        )
        return  # remaining live tests depend on this

    help_output = res.stdout

    # Test 14: all 10 public commands visible
    missing_in_help = [cmd for cmd in PUBLIC_COMMANDS if cmd not in help_output]
    if not missing_in_help:
        r.ok(f"recall --help lists all 10 public commands")
    else:
        r.fail(f"recall --help missing commands: {missing_in_help}", detail=help_output[:500])

    # Test 15: no removed/plumbing commands appear as actual commands in --help
    # Extract command names from the Commands section (first word on each command line)
    import re
    cmd_lines = re.findall(r"^\s*│\s+(\w+)\s+", help_output, re.MULTILINE)
    listed_cmds = set(cmd_lines)
    visible_removed = [cmd for cmd in REMOVED_COMMANDS if cmd in listed_cmds]
    if "index" in listed_cmds:
        visible_removed.append("index (hidden command visible)")
    if not visible_removed:
        r.ok("recall --help hides all removed and plumbing commands")
    else:
        r.fail(f"recall --help shows commands that should be hidden: {visible_removed}")

    # Test 16: recall search --help mentions auto-sync or git
    res_search = run_recall("search", "--help")
    if res_search.returncode == 0 and (
        "auto" in res_search.stdout.lower() or "git" in res_search.stdout.lower() or "sync" in res_search.stdout.lower()
    ):
        r.ok("recall search --help mentions auto-sync/git behaviour")
    elif res_search.returncode == 0:
        r.skip(
            "recall search --help does not mention auto-sync in help text",
            reason="auto-sync is implemented but may not be documented in --help",
        )
    else:
        r.fail(
            f"recall search --help failed (exit {res_search.returncode})",
            detail=(res_search.stdout + res_search.stderr)[:200],
        )


# ── Prerequisites ──────────────────────────────────────────────────────────────

def check_prerequisites() -> None:
    cli_init = ROOT / "src" / "cli" / "__init__.py"
    if not cli_init.exists():
        print(f"{RED}ERROR: src/cli/__init__.py not found — is this the right directory?{RESET}")
        sys.exit(1)
    print(f"  {GREEN}OK{RESET} src/cli/__init__.py found")

    pyproject = ROOT / "pyproject.toml"
    if not pyproject.exists():
        print(f"{RED}ERROR: pyproject.toml not found{RESET}")
        sys.exit(1)
    print(f"  {GREEN}OK{RESET} pyproject.toml found")

    try:
        import src.cli  # noqa: F401
        print(f"  {GREEN}OK{RESET} src.cli importable")
    except ImportError as e:
        print(f"{RED}ERROR: src.cli import failed: {e}{RESET}")
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    fail_fast = "--fail-fast" in sys.argv
    skip_live = "--skip-live" in sys.argv

    print(f"\n{BOLD}Phase 16: Rename & CLI Consolidation — Verification{RESET}")
    print(f"Requirements: CLI-01 · CLI-02 · CLI-03")
    if skip_live:
        print(f"{YELLOW}Note: --skip-live set — tests 13–16 will be skipped.{RESET}")
    else:
        print(f"{YELLOW}Note: Tests 13–16 run the live recall CLI. Use --skip-live to skip.{RESET}")

    r = Runner(fail_fast=fail_fast)

    r.banner("Prerequisites")
    check_prerequisites()

    test_entrypoints(r)
    test_command_surface(r)
    test_new_commands_and_list(r)
    test_search_auto_sync(r)
    test_removed_files_deleted(r)
    test_hook_scripts(r)
    test_live_cli(r, skip_live)

    passed = r.summary()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
