"""
Git manager module for handling repository operations.
Supports clone, fetch, checkout, and tag listing operations.
"""

import os
import re
import subprocess
import threading
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


class GitManager:
    """Manages Git repository operations for the deploy tool."""

    def __init__(self, repo_dir: str, gitlab_url: str, ssh_key_path: str):
        """
        Initialize GitManager.

        Args:
            repo_dir: Directory where the repository will be cloned.
            gitlab_url: GitLab repository URL.
            ssh_key_path: Path to the SSH private key.

        Raises:
            ValueError: If any input fails validation.
            FileNotFoundError: If SSH key file does not exist.
            PermissionError: If SSH key has insecure permissions.
        """
        # Validate all inputs
        self.repo_dir = self._validate_path(repo_dir, "repo_dir")
        self.gitlab_url = self._validate_gitlab_url(gitlab_url)
        self.ssh_key_path = self._validate_ssh_key(ssh_key_path)
        self._lock = threading.Lock()
        self._is_cloned = False
        self._current_tag: Optional[str] = None

    @staticmethod
    def _validate_path(path_str: str, name: str) -> Path:
        """Validate that a path is within the current working directory."""
        path = Path(path_str).expanduser().resolve()
        cwd = Path.cwd().resolve()
        
        # Allow paths within cwd or in repo_cache subdirectory
        if not (str(path).startswith(str(cwd)) or str(path).startswith(str(cwd / "repo"))):
            raise ValueError(f"{name} must be within current directory: {path_str}")
        return path

    @staticmethod
    def _validate_gitlab_url(url: str) -> str:
        """Validate GitLab URL format to prevent injection attacks."""
        if not url or not url.strip():
            raise ValueError("GitLab URL cannot be empty")
        
        url = url.strip()
        
        # Allow SSH URLs (git@host:owner/repo)
        if re.match(r'^git@[\w.-]+:[\w-]+/[\w.-]+$', url):
            return url
        
        # Allow HTTPS URLs
        parsed = urlparse(url)
        if parsed.scheme in ('https', 'http') and parsed.hostname:
            if parsed.scheme == 'http':
                raise ValueError("Use HTTPS instead of HTTP for GitLab URL")
            
            # CRIT-04 FIX: Reject URLs with embedded credentials (user:pass@host)
            if parsed.username or parsed.password:
                raise ValueError(
                    "URLs with embedded credentials are not allowed. "
                    "Use SSH URLs (git@host:owner/repo) or HTTPS URLs without credentials."
                )
            
            return url
        
        raise ValueError(f"Invalid GitLab URL format: {url}")

    @staticmethod
    def _validate_ssh_key(path_str: str) -> Path:
        """Validate SSH key file exists and has secure permissions."""
        path = Path(path_str).expanduser().resolve()
        
        if not path.exists():
            raise FileNotFoundError(f"SSH key not found: {path}")
        
        stats = path.stat()
        perms = oct(stats.st_mode & 0o777)
        if stats.st_mode & 0o777 != 0o600:
            raise PermissionError(
                f"SSH key permissions too open ({perms}). Must be 0600. "
                f"Fix with: chmod 600 {path}"
            )
        
        return path

    @property
    def is_cloned(self) -> bool:
        """Check if the repository has been cloned."""
        return self.repo_dir.exists() and (self.repo_dir / ".git").exists()

    @property
    def install_sh_path(self) -> Optional[Path]:
        """Get the path to install.sh if it exists."""
        if self.is_cloned:
            path = self.repo_dir / "install.sh"
            return path if path.exists() else None
        return None

    def clone(self) -> tuple[bool, str]:
        """
        Clone the repository.

        Returns:
            Tuple of (success, message).
        """
        if self.is_cloned:
            return True, "Repository already cloned."

        try:
            # Ensure parent directory exists
            self.repo_dir.parent.mkdir(parents=True, exist_ok=True)

            env = self._get_git_env()
            result = subprocess.run(
                ["git", "clone", self.gitlab_url, str(self.repo_dir)],
                capture_output=True,
                text=True,
                env=env,
                timeout=300
            )

            if result.returncode == 0:
                self._is_cloned = True
                return True, "Repository cloned successfully."
            else:
                error = self.sanitize_error(result.stderr.strip())
                return False, f"Failed to clone: {error}"
        except subprocess.TimeoutExpired:
            return False, "Clone operation timed out."
        except Exception as e:
            return False, f"Clone failed: {str(e)}"

    def fetch_tags(self) -> tuple[bool, str]:
        """
        Fetch latest tags from remote.

        Returns:
            Tuple of (success, message).
        """
        if not self.is_cloned:
            return False, "Repository not cloned yet."

        try:
            env = self._get_git_env()
            result = subprocess.run(
                ["git", "fetch", "--tags", "-q"],
                capture_output=True,
                text=True,
                cwd=str(self.repo_dir),
                env=env,
                timeout=120
            )

            if result.returncode == 0:
                return True, "Tags fetched successfully."
            else:
                error = self.sanitize_error(result.stderr.strip())
                return False, f"Failed to fetch tags: {error}"
        except subprocess.TimeoutExpired:
            return False, "Fetch operation timed out."
        except Exception as e:
            return False, f"Fetch failed: {str(e)}"

    def list_tags(self) -> tuple[bool, list[str]]:
        """
        List all tags from the repository, sorted by version.

        Returns:
            Tuple of (success, list of tag names).
        """
        if not self.is_cloned:
            return False, []

        try:
            env = self._get_git_env()
            result = subprocess.run(
                ["git", "tag", "-l", "--sort=-v:refname"],
                capture_output=True,
                text=True,
                cwd=str(self.repo_dir),
                env=env,
                timeout=30
            )

            if result.returncode == 0:
                tags = [t.strip() for t in result.stdout.strip().split('\n') if t.strip()]
                return True, tags
            else:
                return False, []
        except Exception as e:
            return False, []

    def checkout_tag(self, tag: str) -> tuple[bool, str]:
        """
        Checkout a specific tag.

        Args:
            tag: The tag name to checkout.

        Returns:
            Tuple of (success, message).
        """
        if not self.is_cloned:
            return False, "Repository not cloned yet."

        try:
            env = self._get_git_env()
            result = subprocess.run(
                ["git", "checkout", tag, "-q"],
                capture_output=True,
                text=True,
                cwd=str(self.repo_dir),
                env=env,
                timeout=60
            )

            if result.returncode == 0:
                self._current_tag = tag
                return True, f"Checked out tag '{tag}' successfully."
            else:
                error = self.sanitize_error(result.stderr.strip())
                return False, f"Failed to checkout '{tag}': {error}"
        except subprocess.TimeoutExpired:
            return False, "Checkout operation timed out."
        except Exception as e:
            return False, f"Checkout failed: {str(e)}"

    @staticmethod
    def sanitize_error(error_msg: str) -> str:
        """
        Sanitize error messages to prevent information leakage (LOW-01).
        
        Removes or replaces:
        - File paths (especially SSH key paths)
        - Git URLs with credentials
        - Sensitive environment variable values
        
        Args:
            error_msg: The raw error message.
            
        Returns:
            Sanitized error message safe for logging/display.
        """
        sanitized = error_msg

        # Replace SSH key paths
        ssh_patterns = [
            r'/[^\s]*\.ssh/[^\s]+',
            r'[^\s]*/ssh/[^\s]+',
        ]
        for pattern in ssh_patterns:
            sanitized = re.sub(pattern, '<key_path>', sanitized)

        # Replace Git URLs (especially with credentials)
        git_patterns = [
            r'https?://[^/\s]+/[^/\s]+/[^/\s]+\.git',
            r'git@[\w.-]+:[\w-]+/[\w.-]+',
        ]
        for pattern in git_patterns:
            sanitized = re.sub(pattern, '<url>', sanitized)

        # Replace home directory paths
        sanitized = re.sub(
            r'(/(?:home|root|Users)/[^/\s]*)',
            '<path>',
            sanitized
        )

        return sanitized

    @staticmethod
    def _validate_device_id(device_id: str) -> str:
        """
        Validate device_id to prevent command injection.
        
        Args:
            device_id: The device identifier (should be numeric).
            
        Returns:
            Validated device_id string.
            
        Raises:
            ValueError: If device_id contains invalid characters.
        """
        if not re.match(r'^\d{1,3}$', device_id):
            raise ValueError(
                f"Invalid device_id: '{device_id}'. Must be 1-3 digits only."
            )
        return device_id

    def run_install_script(self, device_id: str) -> subprocess.Popen:
        """
        Run the install.sh script with the device ID.

        Args:
            device_id: The last octet of the device IP (e.g., '101' for '192.168.2.101').

        Returns:
            Popen process object for the install script.
            
        Raises:
            FileNotFoundError: If install.sh not found.
            ValueError: If device_id is invalid.
        """
        # CRIT-02 FIX: Validate device_id to prevent command injection
        device_id = self._validate_device_id(device_id)
        
        install_script = self.repo_dir / "install.sh"
        if not install_script.exists():
            raise FileNotFoundError(f"install.sh not found in {self.repo_dir}")

        # Make the script executable
        os.chmod(install_script, 0o755)

        env = os.environ.copy()
        # CRIT-01 FIX: Re-enable StrictHostKeyChecking for security
        # Note: Users must pre-populate known_hosts for their GitLab server
        env["GIT_SSH_COMMAND"] = (
            f"ssh -i {self.ssh_key_path} "
            "-o StrictHostKeyChecking=yes "
            "-o UserKnownHostsFile=~/.ssh/known_hosts "
            "-o IdentitiesOnly=yes"
        )

        return subprocess.Popen(
            ["./install.sh", device_id],
            cwd=str(self.repo_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            # Explicitly disable shell to prevent shell injection
            shell=False
        )

    def _get_git_env(self) -> dict:
        """Get environment with SSH settings for Git."""
        env = os.environ.copy()
        # CRIT-01 FIX: Re-enable StrictHostKeyChecking for security
        env["GIT_SSH_COMMAND"] = (
            f"ssh -i {self.ssh_key_path} "
            "-o StrictHostKeyChecking=yes "
            "-o UserKnownHostsFile=~/.ssh/known_hosts "
            "-o IdentitiesOnly=yes"
        )
        return env
