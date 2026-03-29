"""Hook installation logic for git and Claude Code.

Provides non-destructive installation of capture hooks with marker-based detection
for idempotent and reversible operations.

# NOTE: The post-commit git hook (install_git_hook / uninstall_git_hook) was removed in v2.0.
# Git commit capture is superseded by incremental recall sync on SessionStart (Phase 15).
# The 5 remaining hook types (pre-commit, post-merge, post-checkout, post-rewrite, Claude Stop)
# are still installed and maintained.
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

HOOK_START_MARKER = "# RECALL_HOOK_START"
HOOK_END_MARKER = "# RECALL_HOOK_END"


def _get_hook_template(hook_type: str = "pre-commit") -> str:
    """Read a hook template from the templates directory.

    Args:
        hook_type: Hook type (post-commit, pre-commit, post-merge)

    Returns:
        Template content as string

    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    template_path = Path(__file__).parent / "templates" / f"{hook_type}.sh"
    return template_path.read_text()


def _get_recall_section(hook_type: str = "post-commit") -> str:
    """Extract the recall section (between markers) from the template.

    Args:
        hook_type: Hook type (post-commit, pre-commit, post-merge)

    Returns:
        Just the section between RECALL_HOOK_START and RECALL_HOOK_END markers (inclusive)
    """
    template = _get_hook_template(hook_type)

    # Find start and end marker positions
    start_idx = template.find(HOOK_START_MARKER)
    end_idx = template.find(HOOK_END_MARKER)

    if start_idx == -1 or end_idx == -1:
        raise ValueError("Template missing RECALL_HOOK_START or RECALL_HOOK_END marker")

    # Include the end marker line (find the newline after END marker)
    end_line_end = template.find('\n', end_idx)
    if end_line_end == -1:
        end_line_end = len(template)
    else:
        end_line_end += 1  # Include the newline

    return template[start_idx:end_line_end]


def is_claude_hook_installed(project_path: Path) -> bool:
    """Check if recall Claude Code Stop hook is installed in .claude/settings.json.

    Args:
        project_path: Path to project root

    Returns:
        True if .claude/settings.json has a Stop hook entry with recall capture command
    """
    settings_path = project_path / ".claude" / "settings.json"

    if not settings_path.exists():
        return False

    try:
        with open(settings_path, 'r') as f:
            settings = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("Failed to read .claude/settings.json",
                      path=str(settings_path), error=str(e))
        return False

    if "hooks" not in settings or "Stop" not in settings["hooks"]:
        return False

    # Structure: hooks.Stop = [{ matcher, hooks: [{type, command, ...}] }]
    for entry in settings["hooks"]["Stop"]:
        if isinstance(entry, dict):
            for h in entry.get("hooks", []):
                if isinstance(h, dict) and ("recall note" in h.get("command", "") or "recall note" in h.get("command", "")):
                    return True

    return False


def install_claude_hook(project_path: Path) -> bool:
    """Create/update .claude/settings.json with Stop hook for auto-capture.

    Adds recall note command to Stop hooks array with async execution.
    Project-local settings only (not global).

    Args:
        project_path: Path to project root

    Returns:
        True if hook was installed, False if already exists
    """
    settings_dir = project_path / ".claude"
    settings_path = settings_dir / "settings.json"

    # NOTE: install_claude_hook() is legacy (v1.x project-local hook). recall init uses
    # install_global_hooks() instead. Kept for backward compatibility.
    # Recall Stop hook configuration (new format with matcher + hooks array)
    recall_hook = {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": 'recall note "$transcript_path"',
                "async": True,
                "timeout": 10,
            }
        ],
    }

    # Load existing settings or create new
    if settings_path.exists():
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse .claude/settings.json",
                        path=str(settings_path), error=str(e))
            return False
    else:
        settings = {}

    # Ensure hooks.Stop array exists
    if "hooks" not in settings:
        settings["hooks"] = {}

    if "Stop" not in settings["hooks"]:
        settings["hooks"]["Stop"] = []

    # Check if recall hook already exists (idempotent) — check inside hooks array
    for entry in settings["hooks"]["Stop"]:
        if isinstance(entry, dict):
            for h in entry.get("hooks", []):
                if "recall note" in h.get("command", "") or "recall note" in h.get("command", ""):
                    logger.info("Recall Claude Code hook already installed",
                               project=str(project_path))
                    return False

    # Add recall hook
    settings["hooks"]["Stop"].append(recall_hook)

    # Ensure directory exists and write settings
    settings_dir.mkdir(parents=True, exist_ok=True)
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)

    logger.info("Recall Claude Code Stop hook installed", project=str(project_path))
    return True


def uninstall_claude_hook(project_path: Path) -> bool:
    """Remove recall entry from .claude/settings.json hooks.Stop array.

    Args:
        project_path: Path to project root

    Returns:
        True if hook was removed, False if not installed
    """
    settings_path = project_path / ".claude" / "settings.json"

    if not settings_path.exists():
        logger.info("No .claude/settings.json found, nothing to uninstall",
                   project=str(project_path))
        return False

    try:
        with open(settings_path, 'r') as f:
            settings = json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse .claude/settings.json",
                    path=str(settings_path), error=str(e))
        return False

    # Check if recall hook exists
    if "hooks" not in settings or "Stop" not in settings["hooks"]:
        logger.info("No Stop hooks found, nothing to uninstall",
                   project=str(project_path))
        return False

    # Filter out recall hooks (new format: entries with hooks array)
    original_count = len(settings["hooks"]["Stop"])
    settings["hooks"]["Stop"] = [
        entry for entry in settings["hooks"]["Stop"]
        if not (
            isinstance(entry, dict)
            and any(
                "recall note" in h.get("command", "") or "recall note" in h.get("command", "")
                for h in entry.get("hooks", [])
            )
        )
    ]

    if len(settings["hooks"]["Stop"]) == original_count:
        logger.info("Recall hook not found in Stop hooks", project=str(project_path))
        return False

    # Clean up empty structures
    if not settings["hooks"]["Stop"]:
        del settings["hooks"]["Stop"]

    if not settings["hooks"]:
        del settings["hooks"]

    # Write back settings
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)

    logger.info("Recall Claude Code hook removed", project=str(project_path))
    return True


# Phase 15 global hook installation


def _is_recall_hook(entry: dict) -> bool:
    """Return True if entry contains any recall Phase 15 hook script command."""
    for h in entry.get("hooks", []):
        cmd = h.get("command", "")
        if any(script in cmd for script in [
            "session_start.py", "inject_context.py",
            "capture_entry.py", "session_stop.py"
        ]):
            return True
    return False




def install_global_hooks() -> bool:
    """Write all 5 Phase 15 hook entries to ~/.claude/settings.json (global install).

    Preserves non-recall entries. Overwrites any existing recall hook entries
    (clean overwrite semantics — per user decision in CONTEXT.md).

    Returns:
        True if written successfully, False on error
    """
    settings_path = Path.home() / ".claude" / "settings.json"
    python_exe = sys.executable
    hooks_dir = str(Path(__file__).resolve().parent)

    def hook_script(name: str) -> str:
        return str(Path(hooks_dir) / name)

    hook_entries = {
        "SessionStart": [{
            "matcher": "*",
            "hooks": [{"type": "command",
                        "command": f"{python_exe} {hook_script('session_start.py')}",
                        "timeout": 5000}]
        }],
        "UserPromptSubmit": [{
            "matcher": "",
            "hooks": [{"type": "command",
                        "command": f"{python_exe} {hook_script('inject_context.py')}",
                        "timeout": 6000}]
        }],
        "PostToolUse": [{
            "matcher": "Write|Edit|Bash|WebFetch",
            "hooks": [{"type": "command",
                        "command": f"{python_exe} {hook_script('capture_entry.py')}",
                        "timeout": 1000}]
        }],
        "PreCompact": [{
            "matcher": "",
            "hooks": [{"type": "command",
                        "command": f"{python_exe} {hook_script('session_stop.py')} --mode precompact",
                        "timeout": 30000}]
        }],
        "Stop": [{
            "matcher": "",
            "hooks": [{"type": "command",
                        "command": f"{python_exe} {hook_script('session_stop.py')}",
                        "timeout": 30000}]
        }],
    }

    # Load existing settings (preserve non-recall entries)
    if settings_path.exists():
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("failed_to_read_global_settings",
                           path=str(settings_path), error=str(e))
            settings = {}
    else:
        settings = {}

    if "hooks" not in settings:
        settings["hooks"] = {}

    # For each hook type: remove existing recall entries, add new ones
    for hook_type, new_entries in hook_entries.items():
        existing = settings["hooks"].get(hook_type, [])
        cleaned = [e for e in existing if not _is_recall_hook(e)]
        settings["hooks"][hook_type] = cleaned + new_entries

    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
        logger.info("global_hooks_installed", path=str(settings_path))
        return True
    except (IOError, PermissionError) as e:
        logger.error("failed_to_write_global_settings",
                     path=str(settings_path), error=str(e))
        return False


def is_global_hooks_installed() -> bool:
    """Check if all 5 Phase 15 recall hooks are registered in ~/.claude/settings.json.

    Returns:
        True if all 5 hook types have a recall entry, False otherwise
    """
    settings_path = Path.home() / ".claude" / "settings.json"
    if not settings_path.exists():
        return False

    try:
        with open(settings_path, 'r') as f:
            settings = json.load(f)
    except (json.JSONDecodeError, IOError):
        return False

    required_hook_types = {"SessionStart", "UserPromptSubmit", "PostToolUse", "PreCompact", "Stop"}
    hooks = settings.get("hooks", {})

    for hook_type in required_hook_types:
        entries = hooks.get(hook_type, [])
        if not any(_is_recall_hook(e) for e in entries):
            return False

    return True


# Generalized git hook functions for pre-commit and post-merge


def _install_hook(hook_type: str, repo_path: Path, force: bool = False) -> bool:
    """Install a git hook non-destructively (generalized helper).

    Args:
        hook_type: Hook type (pre-commit, post-merge, etc.)
        repo_path: Path to git repository
        force: If True, reinstall even if already installed

    Returns:
        True if hook was installed, False if already installed

    Raises:
        ValueError: If repo_path is not a git repository
    """
    # Verify this is a git repo
    git_dir = repo_path / ".git"
    if not git_dir.exists() or not git_dir.is_dir():
        raise ValueError(f"Not a git repository: {repo_path}")

    hook_path = git_dir / "hooks" / hook_type

    # Check if already installed (idempotent)
    if hook_path.exists():
        content = hook_path.read_text()
        if HOOK_START_MARKER in content:
            logger.info(f"Recall {hook_type} hook already installed", repo=str(repo_path))
            return False

    # Ensure hooks directory exists
    hook_path.parent.mkdir(parents=True, exist_ok=True)

    if hook_path.exists():
        # Existing hook from another tool - append our section
        logger.info(
            f"Existing {hook_type} hook found, appending recall section",
            path=str(hook_path)
        )

        existing_content = hook_path.read_text()

        # Detect pre-commit framework
        if "# pre-commit" in existing_content or "pre-commit hook" in existing_content:
            logger.warning(
                "pre-commit framework detected - appending recall hook",
                suggestion="Consider pre-commit integration for better compatibility"
            )

        # Insert our section before any trailing exit statement so it runs
        recall_section = _get_recall_section(hook_type)
        existing_trimmed = existing_content.rstrip()
        exit_match = re.search(r'(\n+)(exit\s+\d+\s*)$', existing_trimmed)
        if exit_match:
            before_exit = existing_trimmed[:exit_match.start()].rstrip()
            exit_line = exit_match.group(2).rstrip()
            new_content = before_exit + "\n\n" + recall_section + "\n\n" + exit_line
        else:
            new_content = existing_trimmed + "\n\n" + recall_section
        hook_path.write_text(new_content)

    else:
        # No existing hook - create new one with full template
        logger.info(f"Creating new {hook_type} hook", path=str(hook_path))
        template = _get_hook_template(hook_type)
        hook_path.write_text(template)

    # Set executable permission
    hook_path.chmod(0o755)

    logger.info(f"Recall {hook_type} hook installed successfully", repo=str(repo_path))
    return True


def _is_hook_installed(hook_type: str, repo_path: Path) -> bool:
    """Check if recall hook is installed (generalized helper).

    Args:
        hook_type: Hook type (pre-commit, post-merge, etc.)
        repo_path: Path to git repository

    Returns:
        True if hook exists and contains RECALL_HOOK_START marker
    """
    hook_path = repo_path / ".git" / "hooks" / hook_type

    if not hook_path.exists():
        return False

    try:
        content = hook_path.read_text()
        return HOOK_START_MARKER in content
    except Exception as e:
        logger.warning(f"Failed to read {hook_type} hook file", path=str(hook_path), error=str(e))
        return False


def _uninstall_hook(hook_type: str, repo_path: Path) -> bool:
    """Remove recall section from a git hook (generalized helper).

    Args:
        hook_type: Hook type (pre-commit, post-merge, etc.)
        repo_path: Path to git repository

    Returns:
        True if hook was uninstalled, False if not installed
    """
    # Check if installed
    if not _is_hook_installed(hook_type, repo_path):
        logger.info(f"Recall {hook_type} hook not installed, nothing to uninstall", repo=str(repo_path))
        return False

    hook_path = repo_path / ".git" / "hooks" / hook_type
    content = hook_path.read_text()

    # Find recall section boundaries
    start_idx = content.find(HOOK_START_MARKER)
    end_idx = content.find(HOOK_END_MARKER)

    if start_idx == -1 or end_idx == -1:
        logger.error("Hook markers not found despite is_hook_installed check",
                    path=str(hook_path))
        return False

    # Find the end of the end marker line
    end_line_end = content.find('\n', end_idx)
    if end_line_end == -1:
        end_line_end = len(content)
    else:
        end_line_end += 1  # Include the newline

    # Extract content before and after recall section
    before = content[:start_idx]
    after = content[end_line_end:]

    # Remove surrounding blank lines
    before = before.rstrip()
    after = after.lstrip()

    remaining_content = before + ("\n\n" + after if after else "")
    remaining_content = remaining_content.strip()

    if not remaining_content or remaining_content == "#!/bin/sh" or remaining_content == "#!/bin/bash":
        # Hook only contained recall content - remove entire file
        hook_path.unlink()
        logger.info(f"Removed entire {hook_type} hook (only recall content)",
                   path=str(hook_path))
    else:
        # Other content exists - write back without recall section
        hook_path.write_text(remaining_content + "\n")
        logger.info(f"Removed recall section from {hook_type} hook",
                   path=str(hook_path))

    return True


# Public API for pre-commit hook


def install_precommit_hook(repo_path: Path, force: bool = False) -> bool:
    """Install pre-commit hook for journal validation.

    Args:
        repo_path: Path to git repository
        force: If True, reinstall even if already installed

    Returns:
        True if hook was installed, False if already installed
    """
    return _install_hook("pre-commit", repo_path, force)


def is_precommit_hook_installed(repo_path: Path) -> bool:
    """Check if recall pre-commit hook is installed.

    Args:
        repo_path: Path to git repository

    Returns:
        True if hook exists and contains RECALL_HOOK_START marker
    """
    return _is_hook_installed("pre-commit", repo_path)


def uninstall_precommit_hook(repo_path: Path) -> bool:
    """Remove recall section from pre-commit hook.

    Args:
        repo_path: Path to git repository

    Returns:
        True if hook was uninstalled, False if not installed
    """
    return _uninstall_hook("pre-commit", repo_path)


# Public API for post-merge hook


def install_postmerge_hook(repo_path: Path, force: bool = False) -> bool:
    """Install post-merge hook for auto-heal.

    Args:
        repo_path: Path to git repository
        force: If True, reinstall even if already installed

    Returns:
        True if hook was installed, False if already installed
    """
    return _install_hook("post-merge", repo_path, force)


def is_postmerge_hook_installed(repo_path: Path) -> bool:
    """Check if recall post-merge hook is installed.

    Args:
        repo_path: Path to git repository

    Returns:
        True if hook exists and contains RECALL_HOOK_START marker
    """
    return _is_hook_installed("post-merge", repo_path)


def uninstall_postmerge_hook(repo_path: Path) -> bool:
    """Remove recall section from post-merge hook.

    Args:
        repo_path: Path to git repository

    Returns:
        True if hook was uninstalled, False if not installed
    """
    return _uninstall_hook("post-merge", repo_path)


# Public API for post-checkout hook


def install_postcheckout_hook(git_dir: Path) -> bool:
    """Install post-checkout hook for background indexing on branch switches.

    The hook exits early on file checkouts ($3=0) and only triggers indexing
    on branch switches ($3=1) to avoid excessive indexing.

    Args:
        git_dir: Path to the .git directory of the repository

    Returns:
        True if hook was installed, False if already installed or on error
    """
    repo_path = git_dir.parent if git_dir.name == ".git" else git_dir
    try:
        return _install_hook("post-checkout", repo_path)
    except Exception as e:
        logger.error("Failed to install post-checkout hook", git_dir=str(git_dir), error=str(e))
        return False


def is_postcheckout_hook_installed(git_dir: Path) -> bool:
    """Check if recall post-checkout hook is installed.

    Args:
        git_dir: Path to the .git directory of the repository

    Returns:
        True if hook exists and contains RECALL_HOOK_START marker
    """
    repo_path = git_dir.parent if git_dir.name == ".git" else git_dir
    return _is_hook_installed("post-checkout", repo_path)


def uninstall_postcheckout_hook(git_dir: Path) -> bool:
    """Remove recall section from post-checkout hook.

    Args:
        git_dir: Path to the .git directory of the repository

    Returns:
        True if hook was uninstalled, False if not installed
    """
    repo_path = git_dir.parent if git_dir.name == ".git" else git_dir
    return _uninstall_hook("post-checkout", repo_path)


# Public API for post-rewrite hook


def install_postrewrite_hook(git_dir: Path) -> bool:
    """Install post-rewrite hook for background indexing after rebase or amend.

    Triggered by 'git rebase' and 'git commit --amend' to re-index rewritten commits.

    Args:
        git_dir: Path to the .git directory of the repository

    Returns:
        True if hook was installed, False if already installed or on error
    """
    repo_path = git_dir.parent if git_dir.name == ".git" else git_dir
    try:
        return _install_hook("post-rewrite", repo_path)
    except Exception as e:
        logger.error("Failed to install post-rewrite hook", git_dir=str(git_dir), error=str(e))
        return False


def is_postrewrite_hook_installed(git_dir: Path) -> bool:
    """Check if recall post-rewrite hook is installed.

    Args:
        git_dir: Path to the .git directory of the repository

    Returns:
        True if hook exists and contains RECALL_HOOK_START marker
    """
    repo_path = git_dir.parent if git_dir.name == ".git" else git_dir
    return _is_hook_installed("post-rewrite", repo_path)


def uninstall_postrewrite_hook(git_dir: Path) -> bool:
    """Remove recall section from post-rewrite hook.

    Args:
        git_dir: Path to the .git directory of the repository

    Returns:
        True if hook was uninstalled, False if not installed
    """
    repo_path = git_dir.parent if git_dir.name == ".git" else git_dir
    return _uninstall_hook("post-rewrite", repo_path)


# Upgrade path for Phase 7 to Phase 7.1 migration


def _remove_hook_section(hook_path: Path) -> bool:
    """Remove all recall marker sections from a hook file.

    Handles the case where a hook contains an old recall section that needs
    to be replaced with an updated version. Removes content between all
    RECALL_HOOK_START / RECALL_HOOK_END marker pairs.

    Args:
        hook_path: Full path to the git hook file

    Returns:
        True if section was removed, False if no markers found or on error
    """
    if not hook_path.exists():
        return False

    try:
        content = hook_path.read_text()
    except Exception as e:
        logger.error("Failed to read hook file for removal", path=str(hook_path), error=str(e))
        return False

    if HOOK_START_MARKER not in content:
        return False

    # Remove all recall sections (handles edge case of multiple sections)
    result = content
    while HOOK_START_MARKER in result:
        start_idx = result.find(HOOK_START_MARKER)
        end_idx = result.find(HOOK_END_MARKER, start_idx)

        if end_idx == -1:
            # Malformed: start without end — remove from start to end of string
            result = result[:start_idx].rstrip()
            break

        # Find end of end-marker line
        end_line_end = result.find('\n', end_idx)
        if end_line_end == -1:
            end_line_end = len(result)
        else:
            end_line_end += 1

        before = result[:start_idx].rstrip()
        after = result[end_line_end:].lstrip()
        result = before + ("\n\n" + after if after else "")

    result = result.strip()

    if not result or result in ("#!/bin/sh", "#!/bin/bash"):
        # Hook only contained recall content — remove the file
        hook_path.unlink()
        logger.info("Removed entire hook file (only recall content)", path=str(hook_path))
    else:
        hook_path.write_text(result + "\n")
        logger.info("Removed recall section(s) from hook", path=str(hook_path))

    return True


def upgrade_postmerge_hook(git_dir: Path) -> bool:
    """Upgrade a Phase 7 post-merge hook to the Phase 7.1 indexer-based hook.

    Phase 7 installed a post-merge hook that called auto_heal() or replayed
    journal entries. Phase 7.1 replaces this with a lightweight background
    recall index trigger. This function detects old Phase 7 hooks and
    upgrades them in place.

    Args:
        git_dir: Path to the .git directory of the repository

    Returns:
        True if upgraded or already up-to-date, False on error
    """
    repo_path = git_dir.parent if git_dir.name == ".git" else git_dir
    hook_path = repo_path / ".git" / "hooks" / "post-merge"

    if not hook_path.exists():
        logger.info("No post-merge hook found, installing fresh", git_dir=str(git_dir))
        try:
            _install_hook("post-merge", repo_path)
            return True
        except Exception as e:
            logger.error("Failed to install post-merge hook", git_dir=str(git_dir), error=str(e))
            return False

    try:
        content = hook_path.read_text()
    except Exception as e:
        logger.error("Failed to read post-merge hook", path=str(hook_path), error=str(e))
        return False

    # Only attempt upgrade if recall installed this hook (has our marker)
    if HOOK_START_MARKER not in content:
        logger.info(
            "post-merge hook not installed by recall, skipping upgrade",
            path=str(hook_path)
        )
        return True

    # Detect Phase 7 autoheal / journal-based hook content
    old_indicators = ("autoheal", "auto_heal", "journal")
    is_old_phase7_hook = any(indicator in content for indicator in old_indicators)

    if not is_old_phase7_hook:
        logger.info(
            "post-merge hook already up-to-date (no Phase 7 journal references)",
            path=str(hook_path)
        )
        return True

    # Remove old hook section and reinstall with new template
    logger.info(
        "Upgrading post-merge hook from Phase 7 journal replay to Phase 7.1 git indexer",
        path=str(hook_path)
    )

    removed = _remove_hook_section(hook_path)
    if not removed and hook_path.exists():
        logger.warning(
            "Could not remove old hook section, aborting upgrade",
            path=str(hook_path)
        )
        return False

    try:
        _install_hook("post-merge", repo_path)
        logger.info(
            "Successfully upgraded post-merge hook to Phase 7.1 indexer",
            path=str(hook_path)
        )
        return True
    except Exception as e:
        logger.error(
            "Failed to install new post-merge hook after removal",
            git_dir=str(git_dir),
            error=str(e)
        )
        return False
