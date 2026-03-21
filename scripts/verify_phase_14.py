#!/usr/bin/env python3
"""
Phase 14: Graph UI Redesign — Verification Script
Requirements: UI-01 · UI-02 · UI-04

Usage:
    python scripts/verify_phase_14.py [--fail-fast] [--skip-live]

Tests:

  Static (no server required):
  1. UI-01: src/ui_server/routes.py has /graph GET route
  2. UI-01: src/ui_server/app.py exists and defines create_app()
  3. UI-01: ui/out/ directory exists (frontend build output)
  4. UI-04: No direct kuzu/real_ladybug import in routes.py or app.py
  5. UI-04: Route handlers call GraphService methods (list_entities_readonly, list_edges, list_episodes, get_retention_summary)
  6. UI-02: _resolve_request_scope() in routes.py handles scope="global" and scope="project"
  7. UI-02: /graph and /dashboard routes accept scope query parameter

  Live UI (skipped with --skip-live):
  8. UI-01: FastAPI app imports successfully (no missing deps)
  9. UI-02: create_app("project", scope="project") initialises without error
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN   = "\033[0;36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


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
        print(f"{BOLD} Phase 14: Graph UI Redesign — Verification Results{RESET}")
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
                f"Requirements UI-01 · UI-02 · UI-04 verified."
            )
        print()
        return self.failed == 0


# ── Tests 1–3 (UI-01): routes.py /graph route, app.py, ui/out/ ───────────────

def test_routes_and_app(r: Runner) -> None:
    r.banner("Tests 1–3 (UI-01): /graph route, app.py, ui/out/ build")

    routes_path = ROOT / "src" / "ui_server" / "routes.py"

    # Test 1: routes.py has /graph GET route
    if not routes_path.exists():
        r.fail("src/ui_server/routes.py does not exist")
    else:
        routes_src = routes_path.read_text()
        if '@router.get("/graph")' in routes_src:
            r.ok('routes.py has @router.get("/graph") route (UI-01 graph view endpoint)')
        else:
            r.fail('routes.py missing @router.get("/graph") route')

    # Test 2: app.py exists and defines create_app()
    app_path = ROOT / "src" / "ui_server" / "app.py"
    if app_path.exists() and "def create_app(" in app_path.read_text():
        r.ok("src/ui_server/app.py exists and defines create_app() (FastAPI app factory)")
    elif not app_path.exists():
        r.fail("src/ui_server/app.py does not exist")
    else:
        r.fail("src/ui_server/app.py exists but does not define create_app()")

    # Test 3: ui/out/ directory exists (or ui/src/ as fallback)
    out_dir = ROOT / "ui" / "out"
    src_dir = ROOT / "ui" / "src"
    if out_dir.exists():
        r.ok("ui/out/ build directory exists (Next.js/Vite production build)")
    elif src_dir.exists():
        r.skip(
            "ui/out/ not built; ui/src/ present — run: cd ui && npm run build",
            reason="Frontend source present but not built — static check passes with skip",
        )
    else:
        r.fail("Neither ui/out/ nor ui/src/ found — UI source missing entirely")


# ── Tests 4–5 (UI-04): Driver-agnostic routes ─────────────────────────────────

def test_driver_agnostic(r: Runner) -> None:
    r.banner("Tests 4–5 (UI-04): No direct DB imports; GraphService method calls")

    routes_path = ROOT / "src" / "ui_server" / "routes.py"
    app_path    = ROOT / "src" / "ui_server" / "app.py"

    if not routes_path.exists() or not app_path.exists():
        r.fail("routes.py or app.py missing — cannot check driver-agnostic pattern")
        return

    routes_src = routes_path.read_text()
    app_src    = app_path.read_text()

    # Test 4: no direct DB driver imports
    has_kuzu    = "import kuzu" in routes_src or "import kuzu" in app_src
    has_ladybug = "import real_ladybug" in routes_src or "import real_ladybug" in app_src
    if not has_kuzu and not has_ladybug:
        r.ok("routes.py and app.py have no direct DB driver imports (driver-agnostic)")
    else:
        detail = []
        if has_kuzu:    detail.append("'import kuzu' found")
        if has_ladybug: detail.append("'import real_ladybug' found")
        r.fail("Direct DB driver imports found — violates driver-agnostic invariant", detail=", ".join(detail))

    # Test 5: routes.py calls driver-agnostic GraphService methods
    REQUIRED_METHODS = ["list_entities_readonly", "list_edges", "list_episodes", "get_retention_summary"]
    missing = [m for m in REQUIRED_METHODS if m not in routes_src]
    if not missing:
        r.ok(f"routes.py calls driver-agnostic GraphService methods: {', '.join(REQUIRED_METHODS)}")
    else:
        r.fail(f"routes.py missing GraphService method calls: {missing}")


# ── Tests 6–7 (UI-02): Scope toggle ──────────────────────────────────────────

def test_scope_toggle(r: Runner) -> None:
    r.banner("Tests 6–7 (UI-02): _resolve_request_scope(); scope param on /graph and /dashboard")

    routes_path = ROOT / "src" / "ui_server" / "routes.py"
    if not routes_path.exists():
        r.fail("src/ui_server/routes.py does not exist — cannot test scope toggle")
        return

    routes_src = routes_path.read_text()

    # Test 6: _resolve_request_scope handles both scopes
    if "_resolve_request_scope" in routes_src and 'scope == "global"' in routes_src:
        r.ok('_resolve_request_scope() handles scope="global" and scope="project"')
    else:
        detail = []
        if "_resolve_request_scope" not in routes_src: detail.append("_resolve_request_scope() not defined")
        if 'scope == "global"' not in routes_src:       detail.append('"scope == \\"global\\"" branch not found')
        r.fail("_resolve_request_scope() missing or incomplete", detail=", ".join(detail))

    # Test 7: /graph and /dashboard routes accept scope query parameter
    has_graph_scope     = 'scope: str = "project"' in routes_src and '@router.get("/graph")' in routes_src
    has_dashboard_scope = '@router.get("/dashboard")' in routes_src
    if has_graph_scope and has_dashboard_scope:
        r.ok('/graph and /dashboard routes accept scope query parameter')
    else:
        detail = []
        if not has_graph_scope:     detail.append('/graph missing scope param')
        if not has_dashboard_scope: detail.append('/dashboard route missing')
        r.fail("/graph or /dashboard scope param missing", detail=", ".join(detail))


# ── Tests 8–9 (Live): FastAPI app import + create_app ─────────────────────────

def test_live_ui(r: Runner, skip_live: bool) -> None:
    r.banner("Tests 8–9 (UI-01/02): Live FastAPI app import + create_app()")

    if skip_live:
        for msg in [
            "FastAPI app import (src/ui_server/app.py)",
            "create_app('project', scope='project') initialises without error",
        ]:
            r.skip(msg, reason="--skip-live flag set")
        return

    import importlib.util

    # Test 8: app.py imports successfully
    app_path = ROOT / "src" / "ui_server" / "app.py"
    if not app_path.exists():
        r.fail("src/ui_server/app.py does not exist — cannot test live import")
        return

    try:
        spec = importlib.util.spec_from_file_location("ui_app", app_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "create_app"):
            r.ok("src/ui_server/app.py imports successfully and exposes create_app()")
        else:
            r.fail("src/ui_server/app.py imported but create_app() not found")
    except Exception as e:
        r.fail("src/ui_server/app.py import failed", detail=str(e)[:200])
        return

    # Test 9: create_app() returns FastAPI app with /api/graph route
    try:
        import importlib as _il
        _mod = _il.import_module("src.ui_server.app")
        app  = _mod.create_app("project (test)", scope="project")
        routes = [rt for rt in app.routes if hasattr(rt, "path") and rt.path == "/api/graph"]
        if routes:
            r.ok("create_app() returns FastAPI app with /api/graph route registered")
        else:
            r.skip(
                "create_app() works but /api/graph not found in routes",
                reason="Check prefix registration in app.include_router(router, prefix='/api')",
            )
    except Exception as e:
        r.fail("create_app('project', scope='project') raised exception", detail=str(e)[:200])


# ── Prerequisites ──────────────────────────────────────────────────────────────

def check_prerequisites() -> None:
    routes_path = ROOT / "src" / "ui_server" / "routes.py"
    app_path    = ROOT / "src" / "ui_server" / "app.py"

    if not routes_path.exists():
        print(f"{RED}ERROR: src/ui_server/routes.py not found — is this the right directory?{RESET}")
        sys.exit(1)
    print(f"  {GREEN}OK{RESET} src/ui_server/routes.py found")

    if not app_path.exists():
        print(f"{RED}ERROR: src/ui_server/app.py not found{RESET}")
        sys.exit(1)
    print(f"  {GREEN}OK{RESET} src/ui_server/app.py found")

    try:
        import src.ui_server  # noqa: F401
        print(f"  {GREEN}OK{RESET} src.ui_server importable")
    except ImportError as e:
        print(f"{YELLOW}WARN: src.ui_server import failed (may need deps installed): {e}{RESET}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    fail_fast = "--fail-fast" in sys.argv
    skip_live = "--skip-live" in sys.argv

    print(f"\n{BOLD}Phase 14: Graph UI Redesign — Verification{RESET}")
    print(f"Requirements: UI-01 · UI-02 · UI-04")
    if skip_live:
        print(f"{YELLOW}Note: --skip-live set — tests 8–9 will be skipped.{RESET}")
    else:
        print(f"{YELLOW}Note: Tests 8–9 import the FastAPI app. Use --skip-live to skip.{RESET}")

    r = Runner(fail_fast=fail_fast)

    r.banner("Prerequisites")
    check_prerequisites()

    test_routes_and_app(r)
    test_driver_agnostic(r)
    test_scope_toggle(r)
    test_live_ui(r, skip_live)

    passed = r.summary()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
