"""Per-project allowlist for false positive management.

Stores SHA256 hashes of allowlisted content (never plain text)
with required comments explaining why each entry is safe.
User decision: Optional, disabled by default, maximum security.
"""
import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class AllowlistEntry:
    """Entry in the allowlist with audit metadata."""
    hash: str  # SHA256 hash of the allowlisted text
    comment: str  # Required explanation of why this is safe
    added_date: str  # ISO format timestamp
    added_by: str  # Who added this (e.g., git user)


class Allowlist:
    """Per-project allowlist management.

    Stores allowlist in .recall/allowlist.json with:
    - SHA256 hashes (never plain text secrets)
    - Required comments for each entry
    - Audit metadata (date, who added)
    """

    def __init__(self, project_root: Path | None = None):
        """Initialize allowlist for a project.

        Args:
            project_root: Project root directory. Uses cwd if None.
        """
        self._root = project_root or Path.cwd()
        self._path = self._root / ".recall" / "allowlist.json"
        self._entries: dict[str, AllowlistEntry] = {}
        self._load()

    def _load(self) -> None:
        """Load allowlist from disk if exists."""
        if not self._path.exists():
            return

        try:
            with open(self._path) as f:
                data = json.load(f)

            # Parse entries
            for hash_key in data.get("allowed_patterns", []):
                self._entries[hash_key] = AllowlistEntry(
                    hash=hash_key,
                    comment=data.get("comments", {}).get(hash_key, ""),
                    added_date=data.get("metadata", {}).get(hash_key, {}).get("added_date", ""),
                    added_by=data.get("metadata", {}).get(hash_key, {}).get("added_by", ""),
                )
        except (json.JSONDecodeError, KeyError):
            # Corrupted file, start fresh
            self._entries = {}

    def _save(self) -> None:
        """Save allowlist to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "allowed_patterns": list(self._entries.keys()),
            "comments": {h: e.comment for h, e in self._entries.items()},
            "metadata": {
                h: {"added_date": e.added_date, "added_by": e.added_by}
                for h, e in self._entries.items()
            },
        }

        with open(self._path, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def compute_hash(text: str) -> str:
        """Compute SHA256 hash for allowlist lookup.

        Args:
            text: Text to hash (the detected "secret")

        Returns:
            Hash string in format "sha256:hexdigest"
        """
        digest = hashlib.sha256(text.encode()).hexdigest()
        return f"sha256:{digest}"

    def is_allowed(self, text: str) -> bool:
        """Check if text is on the allowlist.

        Args:
            text: Text to check

        Returns:
            True if allowlisted (and should not be redacted)
        """
        text_hash = self.compute_hash(text)
        return text_hash in self._entries

    def get_entry(self, text: str) -> Optional[AllowlistEntry]:
        """Get allowlist entry for text if exists.

        Args:
            text: Text to look up

        Returns:
            AllowlistEntry if found, None otherwise
        """
        text_hash = self.compute_hash(text)
        return self._entries.get(text_hash)

    def add(
        self,
        text: str,
        comment: str,
        added_by: str = "unknown",
    ) -> AllowlistEntry:
        """Add text to allowlist.

        Args:
            text: Text to allowlist (will be stored as hash only)
            comment: REQUIRED explanation of why this is safe
            added_by: Who is adding this entry

        Returns:
            The created AllowlistEntry

        Raises:
            ValueError: If comment is empty (required for audit)
        """
        if not comment or not comment.strip():
            raise ValueError("Comment is required when adding to allowlist")

        text_hash = self.compute_hash(text)
        entry = AllowlistEntry(
            hash=text_hash,
            comment=comment.strip(),
            added_date=datetime.now().isoformat(),
            added_by=added_by,
        )
        self._entries[text_hash] = entry
        self._save()
        return entry

    def remove(self, text: str) -> bool:
        """Remove text from allowlist.

        Args:
            text: Text to remove

        Returns:
            True if removed, False if wasn't in allowlist
        """
        text_hash = self.compute_hash(text)
        if text_hash in self._entries:
            del self._entries[text_hash]
            self._save()
            return True
        return False

    def list_entries(self) -> list[AllowlistEntry]:
        """List all allowlist entries.

        Returns:
            List of all entries (hashes, not original text)
        """
        return list(self._entries.values())

    @property
    def path(self) -> Path:
        """Return path to allowlist file."""
        return self._path


def is_allowlisted(
    text: str,
    project_root: Path | None = None,
) -> bool:
    """Convenience function to check if text is allowlisted.

    Args:
        text: Text to check
        project_root: Project root directory

    Returns:
        True if on allowlist
    """
    allowlist = Allowlist(project_root)
    return allowlist.is_allowed(text)
