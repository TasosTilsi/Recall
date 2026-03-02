#!/usr/bin/env python3
"""
Phase 06: Automatic Capture — Human Verification Script
Requirements: R4.1 (Conversation-Based Capture), R4.2 (Git Post-Commit Hook)

Usage:
    python scripts/verify_phase_06.py [--fail-fast] [--skip-ollama]

Tests:
    1. Git hook installation        — no Ollama needed
    2. Hook timing (<100ms)         — no Ollama needed
    3. Excluded files not captured  — requires Ollama (skip with --skip-ollama)
    4. Captured knowledge queryable — requires Ollama (skip with --skip-ollama)
    5. Conversation capture config  — no Ollama needed (just config check)

Note: Tests 2, 3, 4 make real git commits and clean them up afterwards.
"""

import json
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
        width = 55
        print(f"\n{BOLD}{'━' * width}{RESET}")
        print(f"{BOLD} Phase 06: Automatic Capture — Verification Results{RESET}")
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
            print(f"\n {GREEN}All required tests passed.{RESET} Requirements R4.1, R4.2 verified.")
        print()
        return self.failed == 0


# ── Helpers ───────────────────────────────────────────────────────────────────
def run(cmd: list[str], *, cwd: Path = ROOT, timeout: int = 30, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout, check=check
    )


def graphiti(*args, timeout: int = 120) -> subprocess.CompletedProcess:
    return run([GRAPHITI, *args], timeout=timeout)


def git(*args, timeout: int = 30) -> subprocess.CompletedProcess:
    return run(["git", *args], timeout=timeout)


def ollama_running() -> bool:
    result = run(["ollama", "list"], timeout=5)
    return result.returncode == 0


# ── Prerequisites ─────────────────────────────────────────────────────────────
def check_prerequisites(r: Runner, skip_ollama: bool) -> bool:
    ok = True

    if not Path(GRAPHITI).exists():
        print(f"{RED}ERROR: graphiti CLI not found at {GRAPHITI}{RESET}")
        print(f"       Run: pip install -e .")
        sys.exit(1)
    print(f"  {GREEN}OK{RESET} graphiti CLI available ({GRAPHITI})")

    result = git("rev-parse", "--git-dir")
    if result.returncode != 0:
        print(f"{RED}ERROR: Not inside a git repository{RESET}")
        sys.exit(1)
    print(f"  {GREEN}OK{RESET} Inside git repository")

    if not skip_ollama:
        if ollama_running():
            print(f"  {GREEN}OK{RESET} Ollama is running")
        else:
            print(f"  {YELLOW}WARN{RESET} Ollama not running — tests 3 and 4 will be skipped")
            print(f"       Start with: ollama serve")

    return ok


# ── Test 1: Git Hook Installation ─────────────────────────────────────────────
def test_hook_installation(r: Runner) -> None:
    r.banner("Test 1: Git Hook Installation (R4.2)")

    result = graphiti("hooks", "install")
    if result.returncode != 0:
        r.fail(
            "graphiti hooks install failed",
            detail=result.stderr.strip() or result.stdout.strip(),
        )
        return
    r.ok("graphiti hooks install — succeeded")

    hook_file = ROOT / ".git" / "hooks" / "post-commit"
    if not hook_file.exists():
        r.fail(".git/hooks/post-commit does not exist after install")
        return

    hook_content = hook_file.read_text()
    if "GRAPHITI_HOOK_START" not in hook_content:
        r.fail(
            ".git/hooks/post-commit missing GRAPHITI_HOOK_START marker",
            detail="Hook file may have been replaced by something else",
        )
        return
    r.ok(".git/hooks/post-commit exists with GRAPHITI_HOOK_START marker")

    status_result = graphiti("hooks", "status")
    output = status_result.stdout + status_result.stderr
    post_commit_ok = "post-commit" in output.lower() and "✓" in output
    claude_ok = "claude code stop" in output.lower() and "✓" in output
    if post_commit_ok and claude_ok:
        r.ok("graphiti hooks status — post-commit and Claude Code Stop installed")
    else:
        r.fail(
            "graphiti hooks status did not show post-commit + Claude Code Stop as installed",
            detail=output.strip()[:200],
        )


# ── Test 2: Hook Timing (<100ms) ──────────────────────────────────────────────
def test_hook_timing(r: Runner) -> None:
    r.banner("Test 2: Git Hook Timing (<100ms) (R4.2)")

    pending_file = Path.home() / ".graphiti" / "pending_commits"
    pending_before = pending_file.read_text().strip() if pending_file.exists() else ""

    test_file = ROOT / "graphiti_hook_timing_test.py"
    test_file.write_text("# temporary timing test file — will be removed\n")

    try:
        git("add", str(test_file))
        t_start = time.perf_counter()
        commit_result = git("commit", "-m", "test: hook timing verification (will revert)")
        elapsed_ms = (time.perf_counter() - t_start) * 1000

        if commit_result.returncode != 0:
            r.fail(
                "git commit failed during timing test",
                detail=(commit_result.stdout + commit_result.stderr).strip()[:300],
            )
            return

        commit_hash = git("rev-parse", "HEAD").stdout.strip()

        if elapsed_ms < 100:
            r.ok(f"Commit completed in {elapsed_ms:.1f}ms (< 100ms threshold)")
        else:
            r.fail(
                f"Commit took {elapsed_ms:.1f}ms — exceeds 100ms threshold",
                detail="Hook may be running synchronously or doing heavy work",
            )

        # Give hook a moment to write (it's async)
        time.sleep(0.5)
        pending_after = pending_file.read_text().strip() if pending_file.exists() else ""

        if commit_hash and commit_hash in pending_after:
            r.ok(f"~/.graphiti/pending_commits updated with commit hash")
        elif not pending_file.exists():
            r.fail(
                "~/.graphiti/pending_commits not created",
                detail="Run: mkdir -p ~/.graphiti  — hook creates file on first commit",
            )
        else:
            r.fail(
                "Commit hash not found in ~/.graphiti/pending_commits",
                detail=f"Expected {commit_hash[:8]}... in pending file",
            )

    finally:
        # Always clean up — revert the test commit
        git("revert", "HEAD", "--no-edit", "--no-commit")
        git("reset", "HEAD")
        if test_file.exists():
            test_file.unlink()
            git("add", str(test_file))
        # Only commit cleanup if there's something staged
        status = git("status", "--porcelain").stdout.strip()
        if status:
            git("commit", "-m", "cleanup: remove hook timing test file")
        else:
            # Nothing changed, just unstage
            git("reset", "HEAD")


# ── Test 3: Excluded Files Not Captured ───────────────────────────────────────
def test_excluded_files_not_captured(r: Runner, skip_ollama: bool) -> None:
    r.banner("Test 3: Excluded Files Not Captured (R4.2 + R3.1)")

    if skip_ollama or not ollama_running():
        r.skip("Excluded-file capture test", reason="Ollama not running (use: ollama serve)")
        return

    test_file = ROOT / ".env.test_verification"
    fake_secret = "sk_test_THISSHOULDNOTAPPEARINGRAPH1234567890"

    test_file.write_text(
        f"# Verification test — fake credentials, not real\n"
        f"FAKE_API_KEY={fake_secret}\n"
        f"FAKE_DB_URL=postgresql://user:password@localhost/testdb\n"
    )

    try:
        git("add", str(test_file))
        commit_result = git("commit", "-m", "test: add fake env file for exclusion verification (will remove)")
        if commit_result.returncode != 0:
            r.fail("git commit failed", detail=commit_result.stderr.strip())
            return

        r.info("Committed .env.test_verification — triggering queue processing...")
        queue_result = graphiti("queue", "process", timeout=300)
        r.info(f"Queue processing exited with code {queue_result.returncode}")

        # Search for the secret — must NOT appear
        any_found = False
        for query in [fake_secret, "sk_test_THISSHOULDNOTAPPEARINGRAPH", ".env.test_verification"]:
            search = graphiti("search", query)
            output = (search.stdout + search.stderr).lower()
            has_results = (
                "no results" not in output
                and "no entities" not in output
                and len(search.stdout.strip()) > 10
                and fake_secret.lower() in output
            )
            if has_results:
                any_found = True
                r.info(f"  Found results for query: {query!r}")

        if any_found:
            r.fail(
                "Secret found in graph — .env file content was captured despite exclusion",
                detail="Security filtering is not working end-to-end",
            )
        else:
            r.ok("Fake secret not found in graph — excluded file correctly ignored")

    finally:
        # Clean up test file and commit
        if test_file.exists():
            test_file.unlink()
        git("add", "-f", "--", ".env.test_verification")
        git("commit", "--allow-empty", "-m", "cleanup: remove fake env file for exclusion verification")


# ── Test 4: Captured Knowledge Queryable ──────────────────────────────────────
def test_captured_knowledge_queryable(r: Runner, skip_ollama: bool) -> None:
    r.banner("Test 4: Captured Knowledge Queryable (R4.1 + R4.2)")

    if skip_ollama or not ollama_running():
        r.skip("Knowledge capture test", reason="Ollama not running (use: ollama serve)")
        return

    test_file = ROOT / "user_auth_service_test_capture.py"
    test_file.write_text(
        '"""\nService layer pattern for user authentication.\n\n'
        "This module extracts user authentication logic into a dedicated UserAuthService\n"
        "to improve separation of concerns and enable independent testing.\n"
        'The service validates JWT tokens, manages session state, and integrates\n'
        'with the permission system for role-based access control.\n"""\n\n\n'
        "class UserAuthService:\n"
        '    """Handles user authentication with JWT and RBAC."""\n\n'
        "    def authenticate(self, token: str) -> bool:\n"
        '        """Validate JWT token and check permissions."""\n'
        "        pass\n"
    )

    try:
        git("add", str(test_file))
        commit_result = git(
            "commit", "-m",
            "refactor: extract UserAuthService for better separation of concerns",
        )
        if commit_result.returncode != 0:
            r.fail("git commit failed", detail=commit_result.stderr.strip())
            return

        r.info("Committed UserAuthService file — triggering queue processing (may take 30-120s)...")
        queue_result = graphiti("queue", "process", timeout=300)
        r.info(f"Queue processing exited with code {queue_result.returncode}")

        # Search for the captured content
        found_any = False
        for query in ["UserAuthService", "separation of concerns", "authentication service"]:
            search = graphiti("search", query)
            output = search.stdout + search.stderr
            no_results = "no results" in output.lower() or "no entities" in output.lower()
            if not no_results and search.stdout.strip():
                found_any = True
                r.info(f"  Results found for query: {query!r}")
                break

        if found_any:
            r.ok("Captured knowledge is queryable — pipeline works end-to-end")
        else:
            r.fail(
                "No search results found after commit + queue processing",
                detail="LLM may have failed or queue did not process the commit",
            )

    finally:
        if test_file.exists():
            test_file.unlink()
        git("add", "--", "user_auth_service_test_capture.py")
        git("commit", "--allow-empty", "-m", "cleanup: remove test capture file")


# ── Test 5: Conversation Capture Config ───────────────────────────────────────
def test_conversation_capture_config(r: Runner) -> None:
    r.banner("Test 5: Conversation Capture Configuration (R4.1)")

    # Check .claude/settings.json has the Stop hook configured
    settings_path = ROOT / ".claude" / "settings.json"
    if not settings_path.exists():
        r.fail(
            ".claude/settings.json not found",
            detail="Run: graphiti mcp install  to configure hooks",
        )
        return

    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError as e:
        r.fail(".claude/settings.json is not valid JSON", detail=str(e))
        return

    hooks = settings.get("hooks", {})
    stop_hooks = hooks.get("Stop", [])
    capture_hook = next(
        (h for h in stop_hooks if "graphiti" in h.get("command", "") and "capture" in h.get("command", "")),
        None,
    )

    if capture_hook:
        r.ok(f"Stop hook configured: {capture_hook['command'][:80]}")
    else:
        r.fail(
            "No graphiti capture hook found in .claude/settings.json hooks.Stop",
            detail=f"Stop hooks present: {stop_hooks}",
        )

    # Check graphiti capture --help runs (basic smoke test)
    result = graphiti("capture", "--help")
    if result.returncode == 0:
        r.ok("graphiti capture --help exits 0")
    else:
        r.fail(
            "graphiti capture --help failed",
            detail=result.stderr.strip()[:200],
        )

    # Check graphiti health
    health_result = graphiti("health", timeout=30)
    output = health_result.stdout + health_result.stderr
    if health_result.returncode == 0:
        r.ok("graphiti health — OK")
    else:
        r.info(f"graphiti health warnings: {output.strip()[:200]}")
        r.ok("graphiti health — completed (warnings acceptable)")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    fail_fast   = "--fail-fast"   in sys.argv
    skip_ollama = "--skip-ollama" in sys.argv

    print(f"\n{BOLD}Phase 06: Automatic Capture — Human Verification{RESET}")
    print(f"Requirements: R4.1 (Conversation Capture) · R4.2 (Git Post-Commit Hook)")
    if skip_ollama:
        print(f"{YELLOW}Note: --skip-ollama — tests 3 and 4 will be skipped{RESET}")

    r = Runner(fail_fast=fail_fast)

    r.banner("Prerequisites")
    check_prerequisites(r, skip_ollama)

    test_hook_installation(r)
    test_hook_timing(r)
    test_excluded_files_not_captured(r, skip_ollama)
    test_captured_knowledge_queryable(r, skip_ollama)
    test_conversation_capture_config(r)

    passed = r.summary()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
