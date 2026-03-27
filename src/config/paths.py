from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Global scope paths: ~/.recall/global/
GLOBAL_DB_DIR = Path.home() / ".recall" / "global"
GLOBAL_DB_PATH = GLOBAL_DB_DIR / "recall.lbdb"
CONFIG_PATH = Path.home() / ".recall" / "config.toml"

# Project scope: uses .recall/ relative to project root
PROJECT_DB_DIR_NAME = ".recall"
PROJECT_DB_NAME = "recall.lbdb"


def get_project_db_path(project_root: Path) -> Path:
    """Get the database path for a project scope."""
    return project_root / PROJECT_DB_DIR_NAME / PROJECT_DB_NAME


def migrate_dot_graphiti_to_recall() -> None:
    """One-time migration: rename ~/.graphiti -> ~/.recall if .recall does not exist yet.

    Also migrates the project-scope directory (.graphiti/ -> .recall/) in CWD.
    Safe to call on every startup -- no-ops if migration already done or not needed.
    """
    # Global scope migration
    old_global = Path.home() / ".graphiti"
    new_global = Path.home() / ".recall"
    if old_global.exists() and not new_global.exists():
        try:
            old_global.rename(new_global)
            logger.info("Migrated ~/.graphiti to ~/.recall")
        except OSError as e:
            logger.warning("Could not migrate ~/.graphiti to ~/.recall: %s", e)

    # Project scope migration (CWD)
    try:
        cwd = Path.cwd()
        old_project = cwd / ".graphiti"
        new_project = cwd / ".recall"
        if old_project.exists() and not new_project.exists():
            old_project.rename(new_project)
            logger.info("Migrated .graphiti/ to .recall/ in %s", cwd)
    except OSError as e:
        logger.warning("Could not migrate .graphiti/ to .recall/: %s", e)
