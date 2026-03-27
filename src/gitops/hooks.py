"""Git hook helper functions for general repo hygiene.

Provides staged file secret scanning and repository size checking.
Journal-specific functions removed in Phase 7.1.
"""

import os
from pathlib import Path

import structlog

from src.security import sanitize_content

logger = structlog.get_logger()

# Constants
SIZE_WARNING_MB = 50
SIZE_STRONG_WARNING_MB = 100
SKIP_ENV_VAR = "RECALL_SKIP"


def _is_skip_enabled() -> bool:
    """Check if RECALL_SKIP environment variable is set to bypass all checks.

    Returns:
        True if RECALL_SKIP=1, False otherwise.
    """
    return os.environ.get(SKIP_ENV_VAR) == "1"


def scan_staged_secrets(project_root: Path) -> list[str]:
    """Scan all staged files for secrets using Phase 2's sanitize_content.

    Runs on delta-only (staged files) for performance. Can be bypassed
    with RECALL_SKIP=1 for WIP commits.

    Args:
        project_root: Path to project root containing .git directory.

    Returns:
        List of secret detection warnings (empty if clean or RECALL_SKIP=1).
    """
    if _is_skip_enabled():
        return []

    warnings = []

    try:
        import git

        repo = git.Repo(project_root)

        # Find all staged files (comparing index to HEAD)
        # repo.index.diff("HEAD") marks files relative to HEAD:
        #   new staged file (in index, not in HEAD):  deleted_file=True, a_blob has content
        #   staged deletion (in HEAD, removed from index): new_file=True, a_blob=None
        try:
            staged_diffs = repo.index.diff("HEAD")
            staged_paths: list[str] = []
            for diff_item in staged_diffs:
                # Skip files staged for deletion (a_blob=None — removed from index)
                if diff_item.new_file:
                    continue
                staged_paths.append(diff_item.a_path)
        except git.exc.BadName:
            # No HEAD yet (initial commit) — all index entries are new staged files.
            # git.NULL_TREE is not supported by repo.index.diff() in GitPython 3.x;
            # iterate repo.index.entries directly instead.
            staged_paths = [entry_key[0] for entry_key in repo.index.entries.keys()]

        for rel_path in staged_paths:
            file_path = project_root / rel_path

            try:
                # Read file content
                content = file_path.read_text(encoding="utf-8")

                # Scan for secrets using Phase 2's sanitize_content
                result = sanitize_content(content)

                if result.was_modified:
                    warnings.append(
                        f"{rel_path}: secrets detected - {len(result.findings)} finding(s)"
                    )
            except (FileNotFoundError, UnicodeDecodeError):
                # Skip binary files or files deleted between detection and scan
                continue
            except Exception as e:
                # Log but don't fail on scanning errors
                logger.warning("secret_scan_error", file=str(file_path), error=str(e))

        if warnings:
            logger.warning("staged_secrets_detected", warning_count=len(warnings))

    except ImportError:
        # Security module not available - log warning but continue
        logger.warning("security_module_unavailable", msg="Secret scanning disabled")
    except Exception as e:
        # Unexpected error - log and continue
        logger.warning("staged_secret_scan_error", error=str(e))

    return warnings


def check_recall_size(project_root: Path) -> tuple[float, str | None]:
    """Check .recall/ directory size and return warnings if thresholds exceeded.

    Monitors .recall/ size to inform developers when they should run
    'recall compact' to clean up deduplicated entities.

    Args:
        project_root: Path to project root containing .recall directory.

    Returns:
        Tuple of (size_mb, warning_message). warning_message is None if below thresholds
        or if RECALL_SKIP=1.
    """
    if _is_skip_enabled():
        return (0.0, None)

    try:
        recall_dir = project_root / ".recall"

        if not recall_dir.exists():
            return (0.0, None)

        # Calculate total size excluding database directory
        total_bytes = 0
        for file_path in recall_dir.rglob("*"):
            if file_path.is_file() and "database" not in file_path.parts:
                total_bytes += file_path.stat().st_size

        # Convert to MB
        size_mb = total_bytes / (1024 * 1024)

        # Check thresholds
        if size_mb > SIZE_STRONG_WARNING_MB:
            return (
                size_mb,
                f"STRONG_WARNING: .recall/ is {size_mb:.1f}MB. Run 'recall compact' to clean up.",
            )
        elif size_mb > SIZE_WARNING_MB:
            return (
                size_mb,
                f"WARNING: .recall/ is {size_mb:.1f}MB. Consider running 'recall compact'.",
            )
        else:
            return (size_mb, None)

    except Exception as e:
        # On error, return zero size with no warning
        logger.warning("recall_size_check_error", error=str(e))
        return (0.0, None)
