"""Hook installation and management for automatic capture.

This package provides:
- Git post-commit hook installation (src/hooks/installer.py)
- Claude Code Stop hook configuration (src/hooks/installer.py)
- Hook lifecycle management (src/hooks/manager.py)
"""

from .installer import (
    install_claude_hook,
    install_git_hook,
    is_claude_hook_installed,
    is_git_hook_installed,
    uninstall_claude_hook,
    uninstall_git_hook,
)
from .manager import (
    get_hook_status,
    get_hooks_enabled,
    install_hooks,
    set_hooks_enabled,
    uninstall_hooks,
)

__all__ = [
    "install_git_hook",
    "uninstall_git_hook",
    "is_git_hook_installed",
    "install_claude_hook",
    "is_claude_hook_installed",
    "uninstall_claude_hook",
    "install_hooks",
    "uninstall_hooks",
    "get_hook_status",
    "set_hooks_enabled",
    "get_hooks_enabled",
]
