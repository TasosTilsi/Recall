"""connector.py — External context connectors (GitHub, GitLab)."""
from __future__ import annotations

import httpx
import structlog
from typing import Optional, Dict

from src.config import Config

logger = structlog.get_logger(__name__)

async def fetch_github_pr(repo_url: str, pr_number: int, config: Config) -> Optional[str]:
    """Fetch PR description from GitHub API."""
    token = config.integrations.github_token
    if not token:
        return None

    # Simple parser for repo path
    if "github.com/" not in repo_url:
        return None

    repo_path = repo_url.split("github.com/")[-1].replace(".git", "")
    api_url = f"https://api.github.com/repos/{repo_path}/pulls/{pr_number}"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(api_url, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("body", "")
        except Exception as e:
            logger.warning("connector.github_pr_failed", error=str(e), pr=pr_number)

    return None

def extract_pr_number(message: str) -> Optional[int]:
    """Identify PR number from merge commit message (e.g., 'Merge pull request #123')."""
    import re
    match = re.search(r"\(#(\d+)\)", message) # Squashed merge style: "feat: something (#123)"
    if match:
        return int(match.group(1))

    match = re.search(r"pull request #(\d+)", message, re.IGNORECASE) # Classic merge style
    if match:
        return int(match.group(1))

    return None
