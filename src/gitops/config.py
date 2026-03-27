"""Git configuration file generators for Recall.

This module provides utilities to generate and maintain .gitignore files
for proper version control of Recall knowledge graphs.

LFS-related helpers (generate_gitattributes, RECALL_GITATTRIBUTES) were
removed in Phase 7.1 as part of the architectural pivot to local-first indexing.
"""

from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Gitignore content for .recall directory
RECALL_GITIGNORE = """# Recall Knowledge Graph - Git Ignores
# Transient per-developer state (not shared)

# SQLite queue database (per-developer processing state)
queue.db
queue.db-wal
queue.db-shm

# Temporary files
*.tmp
*.lock

# Rebuild-in-progress markers
.rebuilding

# Debug and log artifacts
*.log
audit.log
"""


def generate_gitignore(project_root: Path) -> Path:
    """Generate .gitignore file for .recall directory.

    Args:
        project_root: Root directory of the project

    Returns:
        Path to the created .gitignore file
    """
    recall_dir = project_root / ".recall"
    recall_dir.mkdir(parents=True, exist_ok=True)

    gitignore_path = recall_dir / ".gitignore"
    gitignore_path.write_text(RECALL_GITIGNORE.lstrip())

    logger.info("generated_gitignore", path=str(gitignore_path))
    return gitignore_path


def ensure_git_config(project_root: Path) -> dict[str, bool]:
    """Ensure git configuration files are generated.

    Best-effort pattern: catches and logs errors, never raises exceptions.

    Args:
        project_root: Root directory of the project

    Returns:
        Dictionary with status of each configuration file:
        {"gitignore": bool}
    """
    result = {"gitignore": False}

    # Generate gitignore
    try:
        generate_gitignore(project_root)
        result["gitignore"] = True
    except Exception as e:
        logger.warning("gitignore_generation_failed", error=str(e))

    return result
