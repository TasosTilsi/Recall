"""Content sanitization with typed placeholder masking.

Combines secret detection, allowlist checking, and masking
to produce content safe for knowledge graph storage.

User decisions:
- Storage never blocked: Always return sanitized content
- Typed placeholders: [REDACTED:type] format
- Very aggressive: Prefer false positives over leaking secrets
"""
from pathlib import Path
from typing import Optional

from src.config.security import REDACTION_PLACEHOLDER
from src.models.security import (
    SecretFinding,
    SanitizationResult,
    DetectionType,
)
from src.security.detector import SecretDetector
from src.security.allowlist import Allowlist
from src.security.audit import get_audit_logger, log_sanitization_event
from src.security.exclusions import is_excluded_file


# Map DetectionType to placeholder suffix
PLACEHOLDER_TYPE_MAP: dict[DetectionType, str] = {
    DetectionType.AWS_KEY: "aws_key",
    DetectionType.GITHUB_TOKEN: "github_token",
    DetectionType.JWT: "jwt",
    DetectionType.GENERIC_API_KEY: "api_key",
    DetectionType.PRIVATE_KEY: "private_key",
    DetectionType.CONNECTION_STRING: "connection_string",
    DetectionType.HIGH_ENTROPY_BASE64: "high_entropy",
    DetectionType.HIGH_ENTROPY_HEX: "high_entropy",
}


def get_placeholder(detection_type: DetectionType) -> str:
    """Get placeholder string for a detection type.

    Args:
        detection_type: Type of secret detected

    Returns:
        Placeholder string like [REDACTED:aws_key]
    """
    type_suffix = PLACEHOLDER_TYPE_MAP.get(detection_type, detection_type.name.lower())
    return REDACTION_PLACEHOLDER.format(type=type_suffix)


class ContentSanitizer:
    """Sanitizes content by detecting and masking secrets.

    Integrates:
    - SecretDetector for finding secrets
    - Allowlist for false positive overrides
    - Audit logging for traceability
    """

    def __init__(
        self,
        project_root: Path | None = None,
        enable_allowlist: bool = True,
    ):
        """Initialize sanitizer.

        Args:
            project_root: Project root for allowlist and audit log location
            enable_allowlist: Whether to check allowlist (default True)
        """
        self._project_root = project_root
        self._detector = SecretDetector()
        self._allowlist = Allowlist(project_root) if enable_allowlist else None
        # Pass project_root to audit logger for proper log location
        log_dir = project_root / ".recall" if project_root else None
        self._audit = get_audit_logger(log_dir)

    def sanitize(
        self,
        content: str,
        file_path: str | None = None,
    ) -> SanitizationResult:
        """Sanitize content by masking detected secrets.

        IMPORTANT: Storage never blocked. This method always returns
        sanitized content, even if secrets are found.

        Args:
            content: Raw content to sanitize
            file_path: Optional source file path for audit logging

        Returns:
            SanitizationResult with sanitized content and metadata
        """
        # Step 1: Detect secrets
        all_findings = self._detector.detect(content, file_path)

        # Step 2: Filter out allowlisted findings
        findings_to_mask: list[SecretFinding] = []
        allowlisted_count = 0

        for finding in all_findings:
            if self._allowlist and self._allowlist.is_allowed(finding.matched_text):
                # Allowlisted - log but don't mask
                allowlisted_count += 1
                entry = self._allowlist.get_entry(finding.matched_text)
                self._audit.log_allowlist_check(
                    finding_hash=Allowlist.compute_hash(finding.matched_text),
                    was_allowed=True,
                    comment=entry.comment if entry else None,
                )
            else:
                findings_to_mask.append(finding)

        # Step 3: Mask secrets in content
        sanitized = content
        for finding in findings_to_mask:
            placeholder = get_placeholder(finding.detection_type)

            # Replace the matched text with placeholder
            sanitized = sanitized.replace(finding.matched_text, placeholder)

            # Log the sanitization event
            log_sanitization_event(
                finding=finding,
                action="masked",
                placeholder=placeholder,
            )

        # Step 4: Build result
        # Note: findings_to_mask contains what was actually masked
        # allowlisted ones are counted but not in the list
        return SanitizationResult(
            original_content=content,
            sanitized_content=sanitized,
            findings=findings_to_mask,
            allowlisted_count=allowlisted_count,
        )

    def should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed through sanitizer.

        Excluded files should not even reach content sanitization -
        they are blocked at the file level.

        Args:
            file_path: Path to check

        Returns:
            True if file should be processed, False if excluded
        """
        if is_excluded_file(file_path):
            self._audit.log_file_excluded(file_path, "<default_exclusions>")
            return False
        return True

    def sanitize_file(self, file_path: Path) -> Optional[SanitizationResult]:
        """Sanitize content from a file.

        Checks file exclusions first, then sanitizes content.

        Args:
            file_path: Path to file to sanitize

        Returns:
            SanitizationResult if processed, None if file excluded
        """
        if not self.should_process_file(file_path):
            return None

        content = file_path.read_text()
        return self.sanitize(content, str(file_path))


def sanitize_content(
    content: str,
    file_path: str | None = None,
    project_root: Path | None = None,
) -> SanitizationResult:
    """Convenience function to sanitize content.

    Args:
        content: Raw content to sanitize
        file_path: Optional source file path
        project_root: Project root for allowlist

    Returns:
        SanitizationResult with sanitized content
    """
    sanitizer = ContentSanitizer(project_root)
    return sanitizer.sanitize(content, file_path)
