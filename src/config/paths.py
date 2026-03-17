from pathlib import Path

# Global scope database path: ~/.graphiti/global/graphiti.lbdb
# Changed from .kuzu to .lbdb in v2.0 to avoid format conflicts with archived KuzuDB files.
# Old .kuzu files are silently orphaned — LadybugDB creates a fresh .lbdb at this path.
GLOBAL_DB_DIR = Path.home() / ".graphiti" / "global"
GLOBAL_DB_PATH = GLOBAL_DB_DIR / "graphiti.lbdb"

# Project scope database is relative to project root
PROJECT_DB_DIR_NAME = ".graphiti"
PROJECT_DB_NAME = "graphiti.lbdb"

def get_project_db_path(project_root: Path) -> Path:
    """Get the database path for a project scope"""
    return project_root / PROJECT_DB_DIR_NAME / PROJECT_DB_NAME
