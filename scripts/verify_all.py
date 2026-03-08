#!/usr/bin/env python3
"""
Run all human verification scripts.

Usage:
    python scripts/verify_all.py [--fail-fast] [--skip-ollama]

Runs:
    Phase 02: Security Filtering  (R3.1, R3.2, R3.3)                    — no Ollama required
    Phase 06: Automatic Capture   (R4.1, R4.2)                           — Ollama optional
    Phase 07: Git Integration     (R8.1)                                 — no Ollama required
    Phase 71: Git Indexing Pivot  (R8.1, R8.2)                           — Ollama optional
    Phase 09: Smart Retention     (RETN-01 … RETN-06)                    — no Ollama required
    Phase 10: Configurable Capture Modes (CAPT-01 · CAPT-02 · CAPT-03)  — no Ollama required
"""

import subprocess
import sys
from pathlib import Path

ROOT    = Path(__file__).parent.parent
SCRIPTS = Path(__file__).parent

GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

SCRIPTS_TO_RUN = [
    ("Phase 02", "verify_phase_02.py", "Security Filtering",  "R3.1 · R3.2 · R3.3"),
    ("Phase 06", "verify_phase_06.py", "Automatic Capture",   "R4.1 · R4.2"),
    ("Phase 07", "verify_phase_07.py", "Git Integration",     "R8.1"),
    ("Phase 71", "verify_phase_71.py", "Git Indexing Pivot",  "R8.1 · R8.2"),
    ("Phase 09", "verify_phase_09.py", "Smart Retention",     "RETN-01 · RETN-02 · RETN-03 · RETN-04 · RETN-05 · RETN-06"),
    ("Phase 10", "verify_phase_10.py", "Configurable Capture Modes", "CAPT-01 · CAPT-02 · CAPT-03"),
]


def main() -> None:
    extra_args = [a for a in sys.argv[1:] if a.startswith("--")]

    print(f"\n{BOLD}{'━' * 55}{RESET}")
    print(f"{BOLD} GSD ► Human Verification — All Phases{RESET}")
    print(f"{BOLD}{'━' * 55}{RESET}\n")

    results: list[tuple[str, str, int]] = []

    for phase, script, name, reqs in SCRIPTS_TO_RUN:
        script_path = SCRIPTS / script
        print(f"{BOLD}▶ {phase}: {name}{RESET}  ({reqs})")
        print(f"  {script_path.relative_to(ROOT)}\n")

        result = subprocess.run(
            [sys.executable, str(script_path), *extra_args],
            cwd=ROOT,
        )
        results.append((phase, name, result.returncode))

    # Final summary
    print(f"\n{BOLD}{'━' * 55}{RESET}")
    print(f"{BOLD} Overall Summary{RESET}")
    print(f"{BOLD}{'━' * 55}{RESET}")

    all_passed = True
    for phase, name, code in results:
        if code == 0:
            print(f"  {GREEN}[PASS]{RESET} {phase}: {name}")
        else:
            print(f"  {RED}[FAIL]{RESET} {phase}: {name}")
            all_passed = False

    print()
    if all_passed:
        print(f"{GREEN}All verification phases passed.{RESET}\n")
        sys.exit(0)
    else:
        print(f"{RED}One or more phases failed.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
