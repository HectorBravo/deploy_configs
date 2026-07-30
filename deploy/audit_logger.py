"""
Audit logging for the deploy tool.

This module provides secure audit logging for all deploy operations.
Logs are stored in a dedicated directory with proper file permissions.

Security: LOW-02 - Audit Logging
- Sensitive values are redacted before logging
- Log files have restricted permissions on Linux/macOS
- Logs include timestamps, user, action, and result
"""

import os
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional


class AuditLogger:
    """Provides audit logging for deploy operations."""

    # Patterns for sensitive data redaction
    _SENSITIVE_PATTERNS = [
        (r'https?://[^/\s]+/[^/\s]+/[^/\s]+\.git', '<url>'),  # Git URLs
        (r'gitlab\.[^/\s]+', 'gitlab.<domain>'),  # GitLab domain
        (r'[A-Za-z0-9_]{20,}', '<token>'),  # Long alphanumeric strings (tokens)
    ]

    # SSH key path pattern
    _SSH_KEY_PATTERN = r'(/[^/\s]*(?:\.ssh/|ssh/)[^/\s]+)'

    # Path pattern
    _PATH_PATTERN = r'(/[a-zA-Z0-9_.\-]+)+'

    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize the audit logger.
        
        Args:
            log_dir: Directory for audit logs. Defaults to ./audit_logs.
        """
        if log_dir is None:
            log_dir = str(Path(__file__).parent.parent / "audit_logs")

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Set restrictive permissions on log directory (owner only)
        try:
            os.chmod(self.log_dir, 0o700)
        except (OSError, AttributeError):
            pass  # Ignore on Windows where chmod is limited

        # Create logger
        self.logger = logging.getLogger("deploy_audit")
        self.logger.setLevel(logging.INFO)

        # Avoid adding duplicate handlers
        if not self.logger.handlers:
            # Create file handler
            log_file = self._get_log_file()
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)

            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)

            # Create console handler (minimal output)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def _get_log_file(self) -> Path:
        """
        Get the log file path for today.
        
        Returns:
            Path to the log file.
        """
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.log_dir / f"audit_{today}.log"
        return log_file

    @staticmethod
    def _sanitize_value(value: str) -> str:
        """
        Sanitize a value for safe logging.
        
        Args:
            value: The value to sanitize.
            
        Returns:
            The sanitized value with sensitive data redacted.
        """
        if not value:
            return ""

        # Apply sensitive patterns
        sanitized = value
        for pattern, replacement in AuditLogger._SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized)

        # Apply SSH key pattern
        sanitized = re.sub(AuditLogger._SSH_KEY_PATTERN, '<key_path>', sanitized)

        # Apply general path pattern (but keep common paths)
        sanitized = re.sub(
            r'(/(?:home|root|Users)[^/\s]*)',
            '<path>',
            sanitized
        )

        return sanitized

    def log_deploy_attempt(
        self,
        user: str,
        device_ip: str,
        tag: str,
        status: str,
        details: Optional[str] = None
    ) -> None:
        """
        Log a deploy attempt.
        
        Args:
            user: Username performing the deploy.
            device_ip: Target device IP address.
            tag: Git tag being deployed.
            status: Deploy status (success/failed/cancelled).
            details: Optional additional details.
        """
        message = (
            f"DEPLOY - user={self._sanitize_value(user)} | "
            f"device={device_ip} | tag={self._sanitize_value(tag)} | "
            f"status={status}"
        )
        if details:
            message += f" | details={self._sanitize_value(details)}"

        self.logger.info(message)

    def log_git_operation(
        self,
        user: str,
        operation: str,
        repo_url: str,
        tag: str,
        status: str,
        details: Optional[str] = None
    ) -> None:
        """
        Log a Git operation.
        
        Args:
            user: Username performing the operation.
            operation: Git operation (fetch, checkout, etc.).
            repo_url: Repository URL (will be sanitized).
            tag: Git reference used.
            status: Operation status (success/failed).
            details: Optional additional details.
        """
        message = (
            f"GIT - user={self._sanitize_value(user)} | "
            f"op={operation} | repo={self._sanitize_value(repo_url)} | "
            f"tag={self._sanitize_value(tag)} | status={status}"
        )
        if details:
            message += f" | details={self._sanitize_value(details)}"

        self.logger.info(message)

    def log_config_change(
        self,
        user: str,
        config_type: str,
        action: str,
        details: Optional[str] = None
    ) -> None:
        """
        Log a configuration change.
        
        Args:
            user: Username making the change.
            config_type: Type of configuration (devices, app, etc.).
            action: Action performed (add, remove, update).
            details: Optional additional details.
        """
        message = (
            f"CONFIG - user={self._sanitize_value(user)} | "
            f"type={config_type} | action={action}"
        )
        if details:
            message += f" | details={self._sanitize_value(details)}"

        self.logger.info(message)

    def log_authentication(self, user: str, method: str, status: str) -> None:
        """
        Log an authentication attempt.
        
        Args:
            user: Username attempting authentication.
            method: Authentication method (keyring, env, prompt).
            status: Authentication status (success/failed).
        """
        message = (
            f"AUTH - user={self._sanitize_value(user)} | "
            f"method={method} | status={status}"
        )
        self.logger.info(message)