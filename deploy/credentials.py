"""
Secure credential management for the deploy tool.

This module handles sensitive credentials (GitLab tokens, SSH key passphrases)
using environment variables and the system keyring where available.

Security: CRIT-03 - Secure Credential Storage
- Credentials are NEVER stored in config files
- Environment variables take priority over keyring
- Falls back to interactive prompt if no secure storage available
"""

import os
import sys
from pathlib import Path
from typing import Optional


class CredentialManager:
    """Manages secure credential storage and retrieval."""

    def __init__(self):
        """Initialize the credential manager."""
        self._gitlab_token: Optional[str] = None
        self._ssh_key_path: Optional[str] = None
        self._ssh_key_passphrase: Optional[str] = None
        self._keyring_available = self._check_keyring()

    def _check_keyring(self) -> bool:
        """Check if keyring is available."""
        try:
            import keyring
            # Test basic functionality
            keyring.get_system()
            return True
        except (ImportError, OSError):
            return False

    def get_gitlab_token(self) -> Optional[str]:
        """
        Get the GitLab API token.
        
        Priority:
        1. Environment variable DEPLOY_GITLAB_TOKEN
        2. System keyring
        3. Interactive prompt
        
        Returns:
            The GitLab token, or None if not available.
        """
        # Check environment variable first
        token = os.environ.get("DEPLOY_GITLAB_TOKEN")
        if token:
            return token

        # Try keyring
        if self._keyring_available:
            try:
                import keyring
                token = keyring.get_password("deploy_tool", "gitlab_token")
                if token:
                    return token
            except Exception:
                pass

        # Fall back to interactive prompt
        return self._prompt_credential("GitLab Token", "DEPLOY_GITLAB_TOKEN")

    def get_ssh_key_path(self) -> Optional[str]:
        """
        Get the SSH key path.
        
        Priority:
        1. Environment variable DEPLOY_SSH_KEY
        2. Config file (non-sensitive)
        3. Interactive prompt
        
        Returns:
            The SSH key path, or None if not available.
        """
        # Check environment variable first
        key_path = os.environ.get("DEPLOY_SSH_KEY")
        if key_path:
            return key_path

        # Try config file
        config_path = Path(__file__).parent.parent / "config" / "app_config.json"
        if config_path.exists():
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
            key_path = config.get("ssh_key_path")
            if key_path:
                return key_path

        # Fall back to interactive prompt
        return self._prompt_credential(
            "SSH Key Path",
            "DEPLOY_SSH_KEY",
            default="~/.ssh/id_ed25519"
        )

    def get_ssh_key_passphrase(self) -> Optional[str]:
        """
        Get the SSH key passphrase.
        
        Priority:
        1. Environment variable DEPLOY_SSH_PASSPHRASE
        2. System keyring
        3. Interactive prompt
        
        Returns:
            The SSH key passphrase, or None if not available.
        """
        # Check environment variable first
        passphrase = os.environ.get("DEPLOY_SSH_PASSPHRASE")
        if passphrase:
            return passphrase

        # Try keyring
        if self._keyring_available:
            try:
                import keyring
                passphrase = keyring.get_password("deploy_tool", "ssh_passphrase")
                if passphrase:
                    return passphrase
            except Exception:
                pass

        # Fall back to interactive prompt
        return self._prompt_credential(
            "SSH Key Passphrase",
            "DEPLOY_SSH_PASSPHRASE",
            password=True  # Hide input
        )

    def set_gitlab_token(self, token: str) -> bool:
        """
        Store the GitLab token securely.
        
        Args:
            token: The GitLab API token to store.
            
        Returns:
            True if the token was stored successfully, False otherwise.
        """
        # Store in environment variable (current session)
        os.environ["DEPLOY_GITLAB_TOKEN"] = token
        self._gitlab_token = token

        # Try to store in keyring
        if self._keyring_available:
            try:
                import keyring
                keyring.set_password("deploy_tool", "gitlab_token", token)
                return True
            except Exception:
                pass

        # If keyring is not available, the environment variable is the best we can do
        return True  # Still return True since env var is set

    def set_ssh_key_passphrase(self, passphrase: str) -> bool:
        """
        Store the SSH key passphrase securely.
        
        Args:
            passphrase: The SSH key passphrase to store.
            
        Returns:
            True if the passphrase was stored successfully, False otherwise.
        """
        # Store in environment variable (current session)
        os.environ["DEPLOY_SSH_PASSPHRASE"] = passphrase
        self._ssh_key_passphrase = passphrase

        # Try to store in keyring
        if self._keyring_available:
            try:
                import keyring
                keyring.set_password("deploy_tool", "ssh_passphrase", passphrase)
                return True
            except Exception:
                pass

        # If keyring is not available, the environment variable is the best we can do
        return True  # Still return True since env var is set

    def is_secure(self) -> bool:
        """
        Check if credentials are stored securely.
        
        Returns:
            True if at least one secure storage method is available.
        """
        # Check environment variables
        if os.environ.get("DEPLOY_GITLAB_TOKEN") and os.environ.get("DEPLOY_SSH_PASSPHRASE"):
            return True

        # Check keyring
        if self._keyring_available:
            try:
                import keyring
                token = keyring.get_password("deploy_tool", "gitlab_token")
                passphrase = keyring.get_password("deploy_tool", "ssh_passphrase")
                if token and passphrase:
                    return True
            except Exception:
                pass

        return False

    def _prompt_credential(
        self,
        name: str,
        env_var: str,
        default: Optional[str] = None,
        password: bool = False
    ) -> Optional[str]:
        """
        Prompt the user for a credential interactively.
        
        Args:
            name: Human-readable name of the credential.
            env_var: Environment variable name to set.
            default: Default value to suggest.
            password: Whether to hide input.
            
        Returns:
            The entered credential, or None if cancelled.
        """
        import getpass

        prompt = f"Enter {name}:"
        if default:
            prompt += f" (default: {default})"
        prompt += " "

        if password:
            value = getpass.getpass(prompt)
        else:
            value = input(prompt)

        if not value and default:
            value = default

        if not value:
            return None

        # Set environment variable for child processes
        os.environ[env_var] = value
        return value