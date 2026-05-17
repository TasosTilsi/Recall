"""workspace.py — Workspace-level multi-repo connectivity."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional

import structlog

from src.config import Config, load_config
from src.db.manager import DatabaseManager

logger = structlog.get_logger(__name__)

class WorkspaceManager:
    """Manages cross-repo connectivity within a workspace."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or load_config()
        self._db_manager = DatabaseManager(self._config)

    def get_world_view(self) -> Dict:
        """Aggregate data from all repositories in the workspace to build a 'World View'.

        Returns a dict with repos, shared_entities, and cross_repo_links.
        """
        current_db_path = self._db_manager.get_db_path()
        sibling_db_paths = self._db_manager.scan_workspace()

        all_dbs = [current_db_path] + sibling_db_paths
        repos = []
        entity_map = {} # name -> list of (repo_name, entity_id, type)

        for db_path in all_dbs:
            repo_name = db_path.parent.parent.name
            repos.append({"name": repo_name, "path": str(db_path)})

            try:
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT id, name, type FROM entities WHERE type != 'file'").fetchall()
                for row in rows:
                    name = row["name"].lower().strip()
                    if name not in entity_map:
                        entity_map[name] = []
                    entity_map[name].append({
                        "repo": repo_name,
                        "id": row["id"],
                        "type": row["type"]
                    })
                conn.close()
            except Exception as e:
                logger.error("workspace.scan_db_failed", path=str(db_path), error=str(e))

        # Identify "Bridge Nodes" (identical names across different repos)
        bridges = []
        for name, occurrences in entity_map.items():
            unique_repos = {occ["repo"] for occ in occurrences}
            if len(unique_repos) > 1:
                bridges.append({
                    "name": name,
                    "occurrences": occurrences
                })

        return {
            "repositories": repos,
            "bridge_nodes": bridges
        }
