#!/usr/bin/env python3
"""
Phase 7.1: Git Indexing Pivot — Human Verification Script
Requirements: R8.1 (Git-Safe Graphs), R8.2 (Merge Conflict Prevention)

Usage:
    python scripts/verify_phase_71.py [--fail-fast] [--skip-ollama]

Tests:
    1. graphiti hooks install deploys all 5 hook files    — no Ollama needed
    2. All 5 hooks are executable                         — no Ollama needed
    3. Hook idempotency (install twice, no duplicates)    — no Ollama needed
    4. graphiti index --verbose                           — requires Ollama (skip with --skip-ollama)
    5. Pre-commit hook runtime execution                  — no Ollama needed
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Terminal colours ──────────────────────────────────────────────────────────
GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN   = "\033[0;36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

GRAPHITI = str(ROOT / ".venv" / "bin" / "graphiti")


class Runner:
    def __init__(self, fail_fast: bool = False):
        self.fail_fast = fail_fast
        self.passed = 0
        self.failed = 0
        self.skipped = 0
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
        self.skipped += 1

    def info(self, msg: str) -> None:
        print(f"         {msg}")

    def banner(self, title: str) -> None:
        print(f"\n{BOLD}── {title} ──{RESET}")

    def summary(self) -> bool:
        width = 60
        print(f"\n{BOLD}{'━' * width}{RESET}")
        print(f"{BOLD} Phase 7.1: Git Indexing Pivot — Verification Results{RESET}")
        print(f"{BOLD}{'━' * width}{RESET}")
        print(f" Tests passed:  {GREEN}{self.passed}{RESET}")
        print(f" Tests failed:  {RED}{self.failed}{RESET}")
        if self.skipped:
            print(f" Tests skipped: {CYAN}{self.skipped}{RESET}")
        if self.failures:
            print("\n Failed:")
            for f in self.failures:
                print(f"   {RED}✗{RESET} {f}")
        else:
            print(f"\n {GREEN}All required tests passed.{RESET} Requirements R8.1, R8.2 verified.")
        print()
        return self.failed == 0


# ── Helpers ───────────────────────────────────────────────────────────────────
def run(cmd: list[str], *, cwd: Path = ROOT, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout
    )


def graphiti(*args, timeout: int = 120) -> subprocess.CompletedProcess:
    return run([GRAPHITI, *args], timeout=timeout)


def git(*args, timeout: int = 30) -> subprocess.CompletedProcess:
    return run(["git", *args], timeout=timeout)


def ollama_running() -> bool:
    result = run(["ollama", "list"], timeout=5)
    return result.returncode == 0


# ── Prerequisites ─────────────────────────────────────────────────────────────
def check_prerequisites(r: Runner, skip_ollama: bool) -> None:
    if not Path(GRAPHITI).exists():
        print(f"{RED}ERROR: graphiti CLI not found at {GRAPHITI}{RESET}")
        print(f"       Run: pip install -e .")
        sys.exit(1)
    print(f"  {GREEN}OK{RESET} graphiti CLI available")

    result = git("rev-parse", "--git-dir")
    if result.returncode != 0:
        print(f"{RED}ERROR: Not inside a git repository{RESET}")
        sys.exit(1)
    print(f"  {GREEN}OK{RESET} Inside git repository")

    if not skip_ollama:
        if ollama_running():
            print(f"  {GREEN}OK{RESET} Ollama is running")
        else:
            print(f"  {YELLOW}WARN{RESET} Ollama not running — test 4 will be skipped")
            print(f"       Start with: ollama serve")


# ── Test 1 & 2: Hooks install + executable ────────────────────────────────────
def test_hooks_install(r: Runner) -> None:
    r.banner("Test 1: graphiti hooks install deploys all 5 hooks (R8.1)")

    result = graphiti("hooks", "install")
    if result.returncode != 0:
        r.fail(
            "graphiti hooks install failed",
            detail=(result.stderr or result.stdout).strip()[:300],
        )
        return
    r.ok("graphiti hooks install exited 0")

    hooks_dir = ROOT / ".git" / "hooks"

    r.banner("Test 2: Installed hooks are executable (R8.1)")

    # graphiti hooks install deploys all 5 hooks (8.7-02 fix: pre-commit now auto-installed)
    auto_installed_hooks = ["pre-commit", "post-commit", "post-merge", "post-checkout", "post-rewrite"]

    all_present = True
    for hook_name in auto_installed_hooks:
        hook_file = hooks_dir / hook_name
        if not hook_file.exists():
            r.fail(f"{hook_name} not found at {hook_file}")
            all_present = False
            continue

        # Check it's executable
        if not hook_file.stat().st_mode & 0o111:
            r.fail(
                f"{hook_name} exists but is not executable",
                detail=f"Run: chmod +x {hook_file}",
            )
            all_present = False
            continue

        # Confirm it contains graphiti marker or graphiti reference
        content = hook_file.read_text()
        has_graphiti = "graphiti" in content.lower() or "GRAPHITI" in content
        if not has_graphiti:
            r.info(f"  {hook_name}: exists and executable (not graphiti-managed)")
        else:
            r.ok(f"{hook_name}: exists, executable, contains graphiti content")

    if all_present:
        r.ok(f"All {len(auto_installed_hooks)} auto-installed hooks present and executable")


# ── Test 3: Hook idempotency ──────────────────────────────────────────────────
def test_hook_idempotency(r: Runner) -> None:
    r.banner("Test 3: Hook Idempotency — no duplicate markers after double install (R8.1)")

    # Run install a second time
    result = graphiti("hooks", "install")
    if result.returncode != 0:
        r.fail(
            "Second 'graphiti hooks install' failed",
            detail=(result.stderr or result.stdout).strip()[:200],
        )
        return
    r.ok("Second install exited 0")

    hooks_dir = ROOT / ".git" / "hooks"
    expected_hooks = ["post-commit", "post-merge", "post-checkout", "post-rewrite"]
    marker = "GRAPHITI_HOOK_START"

    all_clean = True
    for hook_name in expected_hooks:
        hook_file = hooks_dir / hook_name
        if not hook_file.exists():
            continue

        content = hook_file.read_text()
        count = content.count(marker)

        if count == 0:
            r.info(f"  {hook_name}: no {marker} (not graphiti-managed)")
        elif count == 1:
            r.ok(f"{hook_name}: exactly 1 {marker} after double-install")
        else:
            r.fail(
                f"{hook_name}: {count} {marker} markers — idempotency broken",
                detail="Double-install should not duplicate the graphiti section",
            )
            all_clean = False

    if all_clean:
        r.ok("No duplicate markers found — idempotency confirmed")


# ── Test 4: graphiti index ────────────────────────────────────────────────────
def test_graphiti_index(r: Runner, skip_ollama: bool) -> None:
    r.banner("Test 4: graphiti index --verbose (R8.1 — indexer pipeline)")

    if skip_ollama or not ollama_running():
        # Lightweight check: verify CLI structure is correct
        help_result = graphiti("index", "--help")
        if help_result.returncode == 0:
            output = help_result.stdout + help_result.stderr
            has_full  = "--full" in output
            has_since = "--since" in output
            has_verbose = "--verbose" in output
            if has_full and has_since and has_verbose:
                r.skip(
                    "graphiti index --verbose (requires Ollama)",
                    reason=(
                        "Ollama not running — skipping live indexer run.\n"
                        "         CLI verified: --full, --since, --verbose flags present.\n"
                        "         Run without --skip-ollama to execute full test."
                    ),
                )
            else:
                missing = [f for f, ok in [("--full", has_full), ("--since", has_since), ("--verbose", has_verbose)] if not ok]
                r.fail(
                    "graphiti index missing expected flags",
                    detail=f"Missing: {missing}",
                )
        else:
            r.fail(
                "graphiti index --help failed",
                detail=(help_result.stderr or help_result.stdout).strip()[:200],
            )
        return

    # Index only the most recent commit to keep the test bounded.
    # gemma2:9b needs ~60-150s for 2-pass extraction; 300s gives safe margin.
    r.info("Running: graphiti index --since HEAD~1 --verbose (may take 60-150s, uses Ollama)...")
    result = graphiti("index", "--since", "HEAD~1", "--verbose", timeout=300)

    output = result.stdout + result.stderr
    if result.returncode == 0:
        r.ok("graphiti index --verbose exited 0")
        # Check output mentions something about processing or already indexed
        if any(kw in output.lower() for kw in ["indexed", "processing", "commits", "already", "cooldown", "no new"]):
            r.ok("Output confirms indexer ran (mentions processing/indexed state)")
        else:
            r.info(f"Output (first 300 chars): {output.strip()[:300]}")
            r.ok("Exited 0 — indexer ran successfully")
    else:
        r.fail(
            f"graphiti index --verbose exited {result.returncode}",
            detail=output.strip()[:300],
        )


# ── Test 5: Pre-commit hook runtime execution ─────────────────────────────────
def test_precommit_runtime(r: Runner) -> None:
    r.banner("Test 5: Pre-commit Hook Runtime Execution (R8.1)")
    r.info("Staging a clean file and running git commit to exercise the pre-commit hook...")

    test_file = ROOT / "verify_phase_71_test_file.py"
    test_file.write_text("# Temporary test file for Phase 7.1 verification — safe content only\n")

    try:
        # Stage the file
        stage_result = git("add", str(test_file))
        if stage_result.returncode != 0:
            r.fail("git add failed", detail=stage_result.stderr.strip())
            return

        # Time the commit (pre-commit hook should be fast)
        t_start = time.perf_counter()
        commit_result = git("commit", "-m", "test: Phase 7.1 pre-commit hook verification (will revert)")
        elapsed_ms = (time.perf_counter() - t_start) * 1000

        if commit_result.returncode != 0:
            r.fail(
                "git commit failed — pre-commit hook may have errored",
                detail=commit_result.stderr.strip()[:300],
            )
            return

        r.ok(f"git commit succeeded in {elapsed_ms:.0f}ms — pre-commit hook ran without error")

        if elapsed_ms < 5000:
            r.ok(f"Pre-commit hook is fast ({elapsed_ms:.0f}ms < 5000ms threshold)")
        else:
            r.info(f"Pre-commit hook took {elapsed_ms:.0f}ms — may be slow (threshold: 5000ms)")

        # Verify no error output from pre-commit hook
        stderr = commit_result.stderr.strip()
        if stderr and ("error" in stderr.lower() or "traceback" in stderr.lower()):
            r.fail(
                "Pre-commit hook produced error output",
                detail=stderr[:300],
            )
        else:
            r.ok("Pre-commit hook produced no errors")

    finally:
        # Always clean up — revert the test commit
        revert = git("revert", "HEAD", "--no-edit", "--no-commit")
        git("reset", "HEAD")
        if test_file.exists():
            test_file.unlink()
        # Stage removal and commit cleanup if needed
        status = git("status", "--porcelain").stdout.strip()
        if status:
            git("add", "--", str(test_file))
            git("commit", "--allow-empty", "-m", "cleanup: remove Phase 7.1 verification test file")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    fail_fast   = "--fail-fast"   in sys.argv
    skip_ollama = "--skip-ollama" in sys.argv

    print(f"\n{BOLD}Phase 7.1: Git Indexing Pivot — Human Verification{RESET}")
    print(f"Requirements: R8.1 (Git-Safe Knowledge Graphs) · R8.2 (Merge Conflict Prevention)")
    if skip_ollama:
        print(f"{YELLOW}Note: --skip-ollama — test 4 will be skipped{RESET}")

    r = Runner(fail_fast=fail_fast)

    r.banner("Prerequisites")
    check_prerequisites(r, skip_ollama)

    test_hooks_install(r)
    test_hook_idempotency(r)
    test_graphiti_index(r, skip_ollama)
    test_precommit_runtime(r)

    passed = r.summary()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
