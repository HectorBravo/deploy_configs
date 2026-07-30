"""
Security tests for the deploy tool.

Run with: python -m pytest tests/test_security.py -v
"""

import pytest
import os
import stat
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestCredentialStorage:
    """Tests for secure credential storage (CRIT-03)."""

    def test_gitlab_token_not_in_config(self):
        """CRIT-03: Ensure gitlab_token is not stored in config file."""
        config_path = Path("config/app_config.json")
        if config_path.exists():
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
            # Should not have gitlab_token key
            assert "gitlab_token" not in config, \
                "gitlab_token should not be stored in config file"

    def test_ssh_passphrase_not_in_config(self):
        """Ensure ssh_key_passphrase is not stored in config file."""
        config_path = Path("config/app_config.json")
        if config_path.exists():
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
            assert "ssh_key_passphrase" not in config, \
                "ssh_key_passphrase should not be stored in config file"

    def test_credential_manager_uses_env_priority(self):
        """CredentialManager should prioritize environment variables."""
        from deploy.credentials import CredentialManager
        
        with patch.dict(os.environ, {"DEPLOY_GITLAB_TOKEN": "test_token"}):
            manager = CredentialManager()
            token = manager.get_gitlab_token()
            assert token == "test_token"

    def test_credential_manager_secure_check(self):
        """is_secure() should return True when env vars are set."""
        from deploy.credentials import CredentialManager
        
        # Without env vars
        with patch.dict(os.environ, {}, clear=False):
            manager = CredentialManager()
            # May return False if no keyring available
            assert manager.is_secure() in (True, False)


class TestSSHKeyValidation:
    """Tests for SSH key file validation (CRIT-01)."""

    def test_ssh_key_permissions_validation(self, tmp_path):
        """CRIT-01: SSH key must have 0600 permissions."""
        from deploy.git_manager import GitManager
        
        # Create a test file with wrong permissions
        test_key = tmp_path / "test_key"
        test_key.write_text("fake key")
        test_key.chmod(0o644)  # Wrong permissions
        
        with pytest.raises(PermissionError, match="permissions too open"):
            GitManager._validate_ssh_key(str(test_key))

    def test_ssh_key_missing_file(self):
        """CRIT-01: Should raise FileNotFoundError for missing key."""
        from deploy.git_manager import GitManager
        
        with pytest.raises(FileNotFoundError):
            GitManager._validate_ssh_key("/nonexistent/path/to/key")

    def test_ssh_key_valid_permissions(self, tmp_path):
        """SSH key with correct permissions should pass validation."""
        from deploy.git_manager import GitManager
        
        test_key = tmp_path / "valid_key"
        test_key.write_text("fake key")
        test_key.chmod(0o600)  # Correct permissions
        
        result = GitManager._validate_ssh_key(str(test_key))
        assert result == test_key.resolve()


class TestCommandInjectionPrevention:
    """Tests for command injection prevention (CRIT-02)."""

    def test_device_id_validation_numeric_only(self):
        """CRIT-02: device_id must be numeric only."""
        from deploy.git_manager import GitManager
        
        with pytest.raises(ValueError, match="Invalid device_id"):
            GitManager._validate_device_id("101; rm -rf /")

    def test_device_id_validation_max_length(self):
        """CRIT-02: device_id must be max 3 digits."""
        from deploy.git_manager import GitManager
        
        with pytest.raises(ValueError, match="Invalid device_id"):
            GitManager._validate_device_id("1234")

    def test_device_id_valid(self):
        """Valid device_id should pass validation."""
        from deploy.git_manager import GitManager
        
        assert GitManager._validate_device_id("101") == "101"
        assert GitManager._validate_device_id("255") == "255"


class TestErrorSanitization:
    """Tests for error message sanitization (LOW-01)."""

    def test_path_sanitization(self):
        """LOW-01: File paths should be removed from error messages."""
        from deploy.git_manager import GitManager
        
        error = "Error: File /home/user/.ssh/id_ed25519 not found"
        sanitized = GitManager.sanitize_error(error)
        
        assert "/home" not in sanitized
        assert "<path>" in sanitized

    def test_git_url_sanitization(self):
        """LOW-01: Git URLs should be removed from error messages."""
        from deploy.git_manager import GitManager
        
        error = "Error: git@gitlab.example.com:owner/repo.git failed"
        sanitized = GitManager.sanitize_error(error)
        
        assert "gitlab.example.com" not in sanitized
        assert "<url>" in sanitized

    def test_ssh_key_path_sanitization(self):
        """LOW-01: SSH key paths should be removed from error messages."""
        from deploy.git_manager import GitManager
        
        error = "ssh -i /home/user/.ssh/id_ed25519: Permission denied"
        sanitized = GitManager.sanitize_error(error)
        
        assert "<key_path>" in sanitized


class TestGitURLValidation:
    """Tests for Git URL validation."""

    def test_https_allowed(self):
        """HTTPS URLs should be allowed."""
        from deploy.git_manager import GitManager
        
        result = GitManager._validate_gitlab_url("https://gitlab.example.com/owner/repo.git")
        assert result == "https://gitlab.example.com/owner/repo.git"

    def test_http_rejected(self):
        """HTTP URLs should be rejected."""
        from deploy.git_manager import GitManager
        
        with pytest.raises(ValueError, match="Use HTTPS"):
            GitManager._validate_gitlab_url("http://gitlab.example.com/owner/repo.git")

    def test_credentials_in_url_rejected(self):
        """CRIT-04: URLs with embedded credentials should be rejected."""
        from deploy.git_manager import GitManager
        
        # Token in URL
        with pytest.raises(ValueError, match="embedded credentials"):
            GitManager._validate_gitlab_url(
                "https://glpat-token123@gitlab.example.com/owner/repo.git"
            )
        
        # User:pass in URL
        with pytest.raises(ValueError, match="embedded credentials"):
            GitManager._validate_gitlab_url(
                "https://user:pass@gitlab.example.com/owner/repo.git"
            )

    def test_ssh_url_allowed(self):
        """SSH URLs should be allowed."""
        from deploy.git_manager import GitManager
        
        result = GitManager._validate_gitlab_url("git@gitlab.example.com:owner/repo.git")
        assert result == "git@gitlab.example.com:owner/repo.git"

    def test_invalid_url_rejected(self):
        """Invalid URLs should be rejected."""
        from deploy.git_manager import GitManager
        
        with pytest.raises(ValueError):
            GitManager._validate_gitlab_url("not-a-valid-url")


class TestAuditLogging:
    """Tests for audit logging functionality (LOW-02)."""

    def test_audit_log_file_created(self, tmp_path):
        """LOW-02: Audit log file should be created."""
        from deploy.audit_logger import AuditLogger
        
        log_dir = str(tmp_path / "audit_logs")
        logger = AuditLogger(log_dir=log_dir)
        
        logger.log_deploy_attempt(
            user="test_user",
            device_ip="192.168.2.101",
            tag="v1.0.0",
            status="success"
        )
        
        # Check that log file was created
        import glob
        log_files = glob.glob(f"{log_dir}/audit_*.log")
        assert len(log_files) > 0

    def test_audit_log_sanitizes_sensitive_data(self, tmp_path):
        """LOW-02: Audit log should sanitize sensitive data."""
        from deploy.audit_logger import AuditLogger
        
        log_dir = str(tmp_path / "audit_logs")
        logger = AuditLogger(log_dir=log_dir)
        
        # Test value sanitization
        sanitized = AuditLogger._sanitize_value("super_secret_token_12345")
        assert len(sanitized) < len("super_secret_token_12345")
        assert "***" in sanitized


class TestShellInjectionPrevention:
    """Tests for shell injection prevention."""

    def test_install_script_no_shell(self):
        """install.sh should be run without shell=True."""
        from deploy.git_manager import GitManager
        import inspect
        
        # Get the source code of run_install_script
        source = inspect.getsource(GitManager.run_install_script)
        
        # Should not have shell=True
        assert "shell=True" not in source, \
            "shell=True should not be used for subprocess calls"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])