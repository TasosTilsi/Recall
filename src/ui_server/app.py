"""FastAPI application factory for the Recall UI server — v3.0 SQLite backend."""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from src.db.manager import DatabaseManager
from src.config import load_config


class _RootMount(Mount):
    """Starlette normalises '/' → '' in Mount.path; this subclass preserves the original path.

    Required so that test assertions on ``route.path == '/'`` remain stable across
    Starlette versions that strip the leading slash.
    """

    def __init__(self, path: str, *args, **kwargs):
        super().__init__(path, *args, **kwargs)
        self.path = path  # re-apply original value after normalisation


logger = logging.getLogger(__name__)
# NOTE: Use standard logging (not structlog) — this module runs inside uvicorn
# where structlog's processor chain is not configured. Routes use logging too.


def create_app(
    dev_mode: bool = False,
    static_dir: "Path | None" = None,
) -> FastAPI:
    """Create the FastAPI application wired to the v3.0 SQLite DatabaseManager.

    Args:
        dev_mode: If True, adds CORS headers for Vite dev at localhost:5173
        static_dir: Override for ui/out/ directory (defaults to ui/out/ at repo root)
    """
    app = FastAPI(title="Recall UI API", docs_url=None, redoc_url=None)

    # Wire v3.0 DatabaseManager — read-only server; do NOT call db.init_db() here
    config = load_config()
    db = DatabaseManager(config)
    app.state.db = db

    # CORS — only for local Vite dev workflow
    if dev_mode:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite and legacy dev
            allow_methods=["GET"],
            allow_headers=["*"],
        )

    # API routes MUST be registered before StaticFiles mount (catch-all order matters)
    from src.ui_server.routes import router
    app.include_router(router, prefix="/api")

    # Serve Next.js static export — html=True means SPA routes serve index.html
    if static_dir is None:
        # Default: ui/out/ relative to repo root (2 levels up from src/ui_server/)
        static_dir = Path(__file__).parent.parent.parent / "ui" / "out"

    if static_dir.exists():
        # Use _RootMount so route.path == "/" (Starlette normalises "/" → "" by default)
        app.routes.append(
            _RootMount(
                "/",
                app=StaticFiles(directory=static_dir, html=True),
                name="ui",
            )
        )
    else:
        logger.warning(
            "Static UI directory not found — API-only mode",
            extra={"path": str(static_dir)},
        )

    return app
