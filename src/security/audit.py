"""Structured audit logging for security events.

All sanitization events are logged in JSON format with rotation
to support compliance, debugging, and security auditing.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import structlog

from src.config.security import (
    AUDIT_LOG_FILENAME,
    AUDIT_LOG_MAX_BYTES,
    AUDIT_LOG_BACKUP_COUNT,
)
from src.models.security import SecretFinding, DetectionType


class SecurityAuditLogger:
    """Handles structured audit logging for security events."""

    _instance: Optional["SecurityAuditLogger"] = None
    _initialized: bool = False

    def __new__(cls, log_dir: Path | None = None):
        """Singleton pattern - one logger per process."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, log_dir: Path | None = None):
        """Initialize audit logger with file rotation.

        Args:
            log_dir: Directory for audit logs. Defaults to .recall/
        """
        if self._initialized:
            return
        self._initialized = True

        # Default to project-local .recall directory
        self._log_dir = log_dir or Path(".recall")
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._log_dir / AUDIT_LOG_FILENAME

        # Configure stdlib logging handler with rotation
        self._handler = RotatingFileHandler(
            self._log_path,
            maxBytes=AUDIT_LOG_MAX_BYTES,
            backupCount=AUDIT_LOG_BACKUP_COUNT,
        )
        self._handler.setFormatter(logging.Formatter("%(message)s"))

        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Create the audit logger
        stdlib_logger = logging.getLogger("audit.security")
        stdlib_logger.setLevel(logging.INFO)
        stdlib_logger.addHandler(self._handler)
        stdlib_logger.propagate = False  # Don't bubble to root

        self._logger = structlog.wrap_logger(stdlib_logger)

    def log_secret_detected(
        self,
        finding: SecretFinding,
        action: str,
        placeholder: str | None = None,
    ) -> None:
        """Log a secret detection event.

        Args:
            finding: The detected secret finding
            action: What was done (masked, allowlisted, blocked)
            placeholder: The placeholder used for masking
        """
        self._logger.info(
            "secret_detected",
            event_type="sanitization",
            action=action,
            secret_type=finding.detection_type.name,
            line_number=finding.line_number,
            confidence=finding.confidence,
            entropy_score=finding.entropy_score,
            file_path=finding.file_path,
            placeholder=placeholder,
        )

    def log_file_excluded(
        self,
        file_path: Path,
        matched_pattern: str,
    ) -> None:
        """Log a file exclusion event.

        Args:
            file_path: Path that was excluded
            matched_pattern: The pattern that matched
        """
        self._logger.info(
            "file_excluded",
            event_type="exclusion",
            file_path=str(file_path),
            matched_pattern=matched_pattern,
        )

    def log_allowlist_check(
        self,
        finding_hash: str,
        was_allowed: bool,
        comment: str | None = None,
    ) -> None:
        """Log an allowlist lookup.

        Args:
            finding_hash: Hash of the checked content
            was_allowed: Whether it was on the allowlist
            comment: Allowlist entry comment if present
        """
        self._logger.info(
            "allowlist_check",
            event_type="allowlist",
            finding_hash=finding_hash,
            was_allowed=was_allowed,
            comment=comment,
        )

    @property
    def log_path(self) -> Path:
        """Return the current log file path."""
        return self._log_path


# Module-level convenience function
def get_audit_logger(log_dir: Path | None = None) -> SecurityAuditLogger:
    """Get the singleton audit logger instance.

    Args:
        log_dir: Optional custom log directory

    Returns:
        SecurityAuditLogger instance
    """
    return SecurityAuditLogger(log_dir)


def log_sanitization_event(
    finding: SecretFinding,
    action: str,
    placeholder: str | None = None,
) -> None:
    """Convenience function to log a sanitization event.

    Args:
        finding: The secret finding
        action: Action taken (masked, allowlisted)
        placeholder: Placeholder used for masking
    """
    get_audit_logger().log_secret_detected(finding, action, placeholder)
