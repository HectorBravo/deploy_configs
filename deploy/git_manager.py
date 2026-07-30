"""
Git manager module for handling repository operations.
"""

import subprocess
import os
from pathlib import Path
from typing import List, Optional


class GitManager:
    """Manages Git repository operations for deployment."""

    def __init__(self, config_path: str = "config/app_config.json"):
        """
        Initialize GitManager.

        Args:
            config_path: Path to the app configuration file.
        """
        self.config_path = Path(config_path)
        self.repo_url = ""
        self.username = ""
        self.password_or_token = ""
        self.ssh_key_path = "~/.ssh/id_ed25519"
        self.deploy_repo_folder = "deploy_repo"
        self._load_config()

    def _load_config(self):
        """Load configuration from app_config.json."""
        import json
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            git_config = config.get('git', {})
            self.repo_url = git_config.get('url', '')
            self.username = git_config.get('username', '')
            self.password_or_token = git_config.get('password_or_token', '')

            ssh_config = config.get('ssh', {})
            self.ssh_key_path = ssh_config.get('key_path', '~/.ssh/id_ed25519')

            deploy_config = config.get('deploy', {})
            self.deploy_repo_folder = deploy_config.get('repo_folder', 'deploy_repo')
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading config: {e}")

    def _get_authenticated_url(self) -> str:
        """Get the Git URL with embedded credentials."""
        if self.username and self.password_or_token:
            return f"https://{self.username}:{self.password_or_token}@{self.repo_url.replace('https://', '')}"
        return self.repo_url

    def clone_repo(self, target_dir: Optional[str] = None) -> tuple[bool, str]:
        """
        Clone the deployment repository.

        Args:
            target_dir: Directory to clone into. Defaults to deploy_repo folder.

        Returns:
            Tuple of (success, message)
        """
        try:
            if target_dir is None:
                target_dir = self.deploy_repo_folder

            if os.path.exists(target_dir):
                return True, "Repository already exists"

            url = self._get_authenticated_url()
            result = subprocess.run(
                ['git', 'clone', url, target_dir],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                return True, "Repository cloned successfully"
            else:
                return False, f"Failed to clone: {result.stderr}"
        except Exception as e:
            return False, f"Clone error: {str(e)}"

    def fetch_tags(self, repo_path: Optional[str] = None) -> tuple[bool, str]:
        """
        Fetch latest tags from the remote.

        Args:
            repo_path: Path to the repository. Defaults to deploy_repo folder.

        Returns:
            Tuple of (success, message)
        """
        try:
            if repo_path is None:
                repo_path = self.deploy_repo_folder

            result = subprocess.run(
                ['git', 'fetch', '--tags'],
                capture_output=True,
                text=True,
                cwd=repo_path,
                timeout=120
            )

            if result.returncode == 0:
                return True, "Tags fetched successfully"
            else:
                return False, f"Failed to fetch tags: {result.stderr}"
        except Exception as e:
            return False, f"Fetch error: {str(e)}"

    def get_tags(self, repo_path: Optional[str] = None) -> tuple[bool, List[str]]:
        """
        Get list of tags from the repository.

        Args:
            repo_path: Path to the repository. Defaults to deploy_repo folder.

        Returns:
            Tuple of (success, list of tags)
        """
        try:
            if repo_path is None:
                repo_path = self.deploy_repo_folder

            result = subprocess.run(
                ['git', 'tag', '--sort=-creatordate'],
                capture_output=True,
                text=True,
                cwd=repo_path,
                timeout=30
            )

            if result.returncode == 0:
                tags = [t.strip() for t in result.stdout.strip().split('\n') if t.strip()]
                return True, tags
            else:
                return False, []
        except Exception as e:
            return False, []

    def checkout_tag(self, tag: str, repo_path: Optional[str] = None) -> tuple[bool, str]:
        """
        Checkout a specific tag in the repository.

        Args:
            tag: Tag name to checkout.
            repo_path: Path to the repository. Defaults to deploy_repo folder.

        Returns:
            Tuple of (success, message)
        """
        try:
            if repo_path is None:
                repo_path = self.deploy_repo_folder

            result = subprocess.run(
                ['git', 'checkout', tag],
                capture_output=True,
                text=True,
                cwd=repo_path,
                timeout=60
            )

            if result.returncode == 0:
                return True, f"Checked out tag: {tag}"
            else:
                return False, f"Failed to checkout: {result.stderr}"
        except Exception as e:
            return False, f"Checkout error: {str(e)}"
