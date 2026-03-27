"""Git hygiene utilities for Recall.

This module provides general-purpose git utilities:
- Gitignore generation for .recall/ directory
- Git config setup helpers
- Staged file secret scanning
- Repository size checking

Journal-based storage and LFS helpers were removed in Phase 7.1 as part
of the architectural pivot to local-first on-demand git indexing.
"""

from src.gitops.config import (
    ensure_git_config,
    generate_gitignore,
)
from src.gitops.hooks import (
    check_recall_size,
    scan_staged_secrets,
)

__all__ = [
    "check_recall_size",
    "ensure_git_config",
    "generate_gitignore",
    "scan_staged_secrets",
]
