"""Hook installation and management for automatic capture.

This package provides:
- Claude Code Stop hook configuration (src/hooks/installer.py)
- Hook lifecycle management (src/hooks/manager.py)

NOTE: Git post-commit hook (install_git_hook / uninstall_git_hook) removed in v2.0.
Git commit capture is superseded by incremental graphiti sync on SessionStart (Phase 15).
"""

from .installer import (
    install_claude_hook,
    is_claude_hook_installed,
    uninstall_claude_hook,
    install_global_hooks,
    is_global_hooks_installed,
)
from .manager import (
    get_hook_status,
    get_hooks_enabled,
    install_hooks,
    set_hooks_enabled,
    uninstall_hooks,
)

__all__ = [
    "install_claude_hook",
    "is_claude_hook_installed",
    "uninstall_claude_hook",
    "install_global_hooks",
    "is_global_hooks_installed",
    "install_hooks",
    "uninstall_hooks",
    "get_hook_status",
    "set_hooks_enabled",
    "get_hooks_enabled",
]
