"""Hook lifecycle management for enable/disable/uninstall operations.

Provides high-level hook management functions that coordinate installation,
status checking, and configuration toggling across both git and Claude Code hooks.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict

import structlog

# Use the recall binary from the same venv as the running interpreter
# NOTE: get/set_hooks_enabled() calls are vestigial v1.x code — hooks are always enabled in v2.0
_RECALL_CLI = str(Path(sys.executable).parent / "recall")

from .installer import (
    install_claude_hook,
    is_claude_hook_installed,
    uninstall_claude_hook,
)

logger = structlog.get_logger(__name__)


def get_hooks_enabled() -> bool:
    """Read hooks.enabled from graphiti config.

    Returns:
        True if hooks are enabled, False otherwise.
        Defaults to True if config key is missing or graphiti not available
        (hooks are installed intentionally, so enabled by default).
    """
    try:
        result = subprocess.run(
            [_RECALL_CLI, "config", "get", "hooks.enabled"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            # Config key found — parse the value
            output = result.stdout.strip().lower()
            if output == "false":
                return False
            # "true", "1", "yes", or any non-false output = enabled
            return True
        else:
            # Config key doesn't exist or graphiti unavailable — default to enabled
            # (hooks are installed intentionally, so enabled by default)
            return True

    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
        # graphiti not in PATH or config error - default to enabled
        logger.debug("Failed to read hooks.enabled config, defaulting to True",
                    error=str(e))
        return True


def set_hooks_enabled(enabled: bool) -> None:
    """Set hooks.enabled in graphiti config.

    Args:
        enabled: True to enable hooks, False to disable
    """
    try:
        result = subprocess.run(
            [_RECALL_CLI, "config", "set", "hooks.enabled", str(enabled).lower()],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            logger.info("Hooks config updated", enabled=enabled)
        else:
            logger.error("Failed to set hooks.enabled config",
                        enabled=enabled,
                        error=result.stderr)

    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
        logger.error("Failed to execute graphiti config command",
                    enabled=enabled, error=str(e))


def _is_claude_hook_installed(project_path: Path) -> bool:
    """Check if graphiti Claude Code hook is installed.

    Delegates to installer.is_claude_hook_installed — single source of truth.

    Args:
        project_path: Path to project root

    Returns:
        True if .claude/settings.json has graphiti Stop hook
    """
    return is_claude_hook_installed(project_path)


def install_hooks(
    repo_path: Path,
    install_git: bool = True,
    install_claude: bool = True
) -> Dict[str, bool]:
    """Install hook types (Claude Code hook; git post-commit hook removed in v2.0).

    Args:
        repo_path: Path to git repository / project root
        install_git: Ignored — git post-commit hook removed in v2.0 (Phase 15 prep)
        install_claude: Whether to install Claude Code hook

    Returns:
        Dict with keys "git_hook" and "claude_hook" indicating what was installed.
        True means newly installed, False means already installed or not requested.
        "git_hook" is always False (post-commit hook removed in v2.0).
    """
    results = {"git_hook": False, "claude_hook": False}

    # Install Claude Code hook
    if install_claude:
        try:
            results["claude_hook"] = install_claude_hook(repo_path)
        except Exception as e:
            logger.error("Failed to install Claude hook",
                        project=str(repo_path), error=str(e))

    # Ensure hooks.enabled is set to True
    if results["claude_hook"]:
        set_hooks_enabled(True)

    logger.info("Hook installation complete", repo=str(repo_path), results=results)
    return results


def uninstall_hooks(
    repo_path: Path,
    remove_git: bool = True,
    remove_claude: bool = True
) -> Dict[str, bool]:
    """Uninstall specified hook types (git post-commit hook removed in v2.0).

    Args:
        repo_path: Path to git repository / project root
        remove_git: Ignored — git post-commit hook removed in v2.0 (Phase 15 prep)
        remove_claude: Whether to remove Claude Code hook

    Returns:
        Dict with keys "git_hook" and "claude_hook" indicating what was removed.
        True means successfully removed, False means not installed or not requested.
        "git_hook" is always False (post-commit hook removed in v2.0).
    """
    results = {"git_hook": False, "claude_hook": False}

    # Uninstall Claude Code hook
    if remove_claude:
        try:
            results["claude_hook"] = uninstall_claude_hook(repo_path)
        except Exception as e:
            logger.error("Failed to uninstall Claude hook",
                        project=str(repo_path), error=str(e))

    logger.info("Hook uninstallation complete", repo=str(repo_path), results=results)
    return results


def get_hook_status(repo_path: Path) -> Dict[str, object]:
    """Return status dict with hook installation and configuration state.

    Args:
        repo_path: Path to git repository / project root

    Returns:
        Dict with:
        - "hooks_enabled": bool from config
        - "git_hook_installed": always False (post-commit hook removed in v2.0)
        - "claude_hook_installed": bool (check .claude/settings.json)
        - "repo_path": str(repo_path)
    """
    return {
        "hooks_enabled": get_hooks_enabled(),
        "git_hook_installed": False,  # post-commit hook removed in v2.0 (Phase 15 prep)
        "claude_hook_installed": _is_claude_hook_installed(repo_path),
        "repo_path": str(repo_path),
    }
