"""Git commit data extraction for capture pipeline.

Provides functions to:
- Read and clear pending commits file atomically
- Fetch full diff data from commit SHAs
- Append commit hashes to pending file (for testing/manual queueing)

Key pattern: Atomic rename for pending file to avoid race conditions
where new commits are appended during processing.
"""

import subprocess
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()

# Default pending commits file location
DEFAULT_PENDING_FILE = Path.home() / ".recall" / "pending_commits"


def read_and_clear_pending_commits(pending_file: Path | None = None) -> list[str]:
    """Atomically read and clear pending commits file.
    
    Uses atomic rename pattern to avoid race condition between read and truncate.
    If new commits are appended during processing, they're preserved in the original file.
    
    Args:
        pending_file: Path to pending commits file. Defaults to ~/.recall/pending_commits

    Returns:
        List of commit SHAs (empty list if file doesn't exist or is empty)

    Example:
        >>> commits = read_and_clear_pending_commits()
        >>> # Process commits
        >>> for sha in commits:
        ...     diff = fetch_commit_diff(sha)
    """
    if pending_file is None:
        pending_file = DEFAULT_PENDING_FILE
    
    if not pending_file.exists():
        return []
    
    # Atomic move to temp file
    temp_file = pending_file.with_suffix('.processing')
    try:
        pending_file.rename(temp_file)
    except FileNotFoundError:
        # Race: file deleted between exists check and rename
        logger.debug("pending_file_disappeared", path=str(pending_file))
        return []
    
    # Read temp file
    try:
        content = temp_file.read_text()
        commits = content.strip().split('\n')
    except Exception as e:
        logger.error("failed_to_read_pending_file", path=str(temp_file), error=str(e))
        # Clean up temp file on error
        temp_file.unlink(missing_ok=True)
        return []
    
    # Clean up temp file
    temp_file.unlink(missing_ok=True)
    
    # Filter empty lines
    return [c.strip() for c in commits if c.strip()]


def fetch_commit_diff(
    commit_sha: str,
    repo_path: Path | None = None,
    max_lines_per_file: int = 500,
) -> str:
    """Fetch full diff for a commit with per-file truncation.
    
    Gets commit metadata + stats, then fetches per-file diffs with truncation
    at max_lines_per_file lines per file. For merge commits, shows diff against
    each parent separately.
    
    Args:
        commit_sha: Git commit SHA (full or short)
        repo_path: Repository path. Defaults to current directory.
        max_lines_per_file: Maximum lines per file diff. Default 500.
    
    Returns:
        Combined output string with metadata, stats, and truncated diffs
    
    Raises:
        subprocess.CalledProcessError: If git command fails
        subprocess.TimeoutExpired: If git command times out (30s)
    
    Example:
        >>> diff = fetch_commit_diff('abc123')
        >>> print(diff[:100])  # First 100 chars
        commit abc123...
    """
    cwd = repo_path if repo_path else None
    
    # Step 1: Get commit metadata + summary stats
    # Use --format=fuller for detailed metadata
    try:
        metadata_result = subprocess.run(
            ['git', 'show', '--format=fuller', '--stat', commit_sha],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd,
        )
        metadata_result.check_returncode()
        metadata = metadata_result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(
            "git_show_failed",
            commit_sha=commit_sha,
            returncode=e.returncode,
            stderr=e.stderr,
        )
        raise
    
    # Step 2: Get per-file diffs with truncation
    # Check if this is a merge commit (multiple parents)
    try:
        # Get parent count
        parent_result = subprocess.run(
            ['git', 'rev-parse', f'{commit_sha}^@'],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd,
        )
        
        # If multiple lines in output, it's a merge commit
        parents = [p for p in parent_result.stdout.strip().split('\n') if p]
        is_merge = len(parents) > 1
    except subprocess.CalledProcessError:
        # No parents (initial commit) - not a merge
        is_merge = False
        parents = []
    
    # For merge commits, use -m flag to show diff against each parent
    if is_merge:
        diff_cmd = ['git', 'diff-tree', '-m', '--no-commit-id', '--patch', commit_sha]
    else:
        diff_cmd = ['git', 'diff-tree', '--no-commit-id', '--patch', commit_sha]
    
    try:
        diff_result = subprocess.run(
            diff_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd,
        )
        diff_output = diff_result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(
            "git_diff_tree_failed",
            commit_sha=commit_sha,
            returncode=e.returncode,
            stderr=e.stderr,
        )
        raise
    
    # Step 3: Apply per-file truncation using awk
    # Track line count per file (reset on "diff --git" marker)
    # Print "... (truncated at N lines)" when exceeded
    truncation_script = f'''
    BEGIN {{ file_lines = 0 }}
    /^diff --git/ {{
        if (file_lines > {max_lines_per_file}) {{
            print "... (truncated at " {max_lines_per_file} " lines)"
        }}
        file_lines = 0
        print
        next
    }}
    {{
        file_lines++
        if (file_lines <= {max_lines_per_file}) {{
            print
        }}
    }}
    END {{
        if (file_lines > {max_lines_per_file}) {{
            print "... (truncated at " {max_lines_per_file} " lines)"
        }}
    }}
    '''
    
    try:
        truncated_result = subprocess.run(
            ['awk', truncation_script],
            input=diff_output,
            capture_output=True,
            text=True,
            timeout=30,
        )
        truncated_diff = truncated_result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(
            "awk_truncation_failed",
            commit_sha=commit_sha,
            error=str(e),
        )
        # Fall back to untruncated diff on error
        truncated_diff = diff_output
    
    # Combine metadata + truncated diff
    return metadata + "\n" + truncated_diff


def append_pending_commit(
    commit_sha: str,
    pending_file: Path | None = None,
) -> None:
    """Append commit hash to pending file.
    
    Used for testing and manual queueing. In production, the git post-commit
    hook appends directly via shell.
    
    Args:
        commit_sha: Git commit SHA to append
        pending_file: Path to pending commits file. Defaults to ~/.recall/pending_commits

    Example:
        >>> append_pending_commit('abc123def456')
        >>> # Commit hash now in queue for background processing
    """
    if pending_file is None:
        pending_file = DEFAULT_PENDING_FILE
    
    # Ensure parent directory exists
    pending_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Append commit hash
    with pending_file.open('a') as f:
        f.write(f"{commit_sha}\n")
    
    logger.debug("commit_appended_to_pending", commit_sha=commit_sha, path=str(pending_file))