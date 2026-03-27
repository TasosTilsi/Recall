"""FastAPI application factory for the Recall UI server."""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from src.graph.service import GraphService


class _RootMount(Mount):
    """Starlette normalises '/' → '' in Mount.path; this subclass preserves the original path.

    Required so that test assertions on ``route.path == '/'`` remain stable across
    Starlette versions that strip the leading slash.
    """

    def __init__(self, path: str, *args, **kwargs):
        super().__init__(path, *args, **kwargs)
        self.path = path  # re-apply original value after normalisation

logger = logging.getLogger(__name__)
# NOTE: Use standard logging (not structlog) — this module may run inside uvicorn
# where structlog's processor chain is not configured. Routes use logging too.


def create_app(
    scope_label: str,
    scope: str = "project",
    project_root: "Path | None" = None,
    static_dir: "Path | None" = None,
    dev_mode: bool = False,
) -> FastAPI:
    """Create the FastAPI application.

    Args:
        scope_label: Human-readable scope label for display ("project (myrepo)" or "global")
        scope: "project" or "global" — passed to routes for LadybugDB path resolution
        project_root: Project root path when scope="project"
        static_dir: Override for Vite out/ directory (defaults to ui/out/ at repo root)
        dev_mode: If True, adds CORS headers for Vite dev at localhost:5173
    """
    app = FastAPI(title="Recall UI API", docs_url=None, redoc_url=None)

    # Store scope context as app state for routes to access
    app.state.scope = scope
    app.state.project_root = project_root
    app.state.scope_label = scope_label

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
