"""
Deploy worker module for parallel deployment to devices.
"""

import subprocess
import threading
from pathlib import Path
from typing import Dict, Callable, Optional


class DeployWorker:
    """Handles deployment to devices in parallel."""

    def __init__(self, log_callback: Optional[Callable] = None):
        """
        Initialize DeployWorker.

        Args:
            log_callback: Optional callback function for log messages.
        """
        self.log_callback = log_callback
        self._threads: list[threading.Thread] = []

    def _log(self, device_id: str, message: str):
        """Log a message for a device."""
        if self.log_callback:
            self.log_callback(device_id, message)

    def deploy_to_device(self, device: Dict, tag: str, repo_path: str = "deploy_repo",
                         base_dir: str = ".") -> tuple[bool, str]:
        """
        Deploy a specific tag to a single device.

        Args:
            device: Device dictionary with 'ip' and 'name' keys.
            tag: Tag/version to deploy.
            repo_path: Path to the cloned repository.
            base_dir: Base directory for the deploy repo.

        Returns:
            Tuple of (success, message)
        """
        ip = device.get('ip', 'unknown')
        name = device.get('name', ip)
        device_id = name

        try:
            # Calculate last octet
            last_octet = int(ip.split('.')[-1])
            short_id = str(last_octet).zfill(3)  # e.g., 101 -> "101"

            self._log(device_id, f"Starting deployment to {ip} (id: {short_id})")
            self._log(device_id, f"Checking out tag: {tag}")

            # Step 1: Checkout the tag
            checkout_result = subprocess.run(
                ['git', 'checkout', tag],
                capture_output=True,
                text=True,
                cwd=repo_path,
                timeout=60
            )

            if checkout_result.returncode != 0:
                self._log(device_id, f"Checkout failed: {checkout_result.stderr}")
                return False, f"Checkout failed: {checkout_result.stderr}"

            self._log(device_id, "Tag checked out successfully")

            # Step 2: Run install script with short ID
            install_script = Path(repo_path) / 'install.sh'
            if not install_script.exists():
                # Try repo subfolder
                install_script = Path(repo_path) / 'repo' / 'install.sh'

            if not install_script.exists():
                self._log(device_id, "install.sh not found!")
                return False, "install.sh not found"

            cmd = ['bash', str(install_script), short_id]
            self._log(device_id, f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(repo_path).parent if str(install_script).startswith(str(repo_path)) else repo_path,
                timeout=300
            )

            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    self._log(device_id, line)

            if result.stderr:
                for line in result.stderr.strip().split('\n'):
                    self._log(device_id, f"ERR: {line}")

            if result.returncode == 0:
                self._log(device_id, "Deployment completed successfully!")
                return True, "Deployment successful"
            else:
                self._log(device_id, f"Deployment failed with code {result.returncode}")
                return False, f"Deployment failed with code {result.returncode}"

        except subprocess.TimeoutExpired:
            self._log(device_id, "Deployment timed out!")
            return False, "Deployment timed out"
        except Exception as e:
            self._log(device_id, f"Error: {str(e)}")
            return False, str(e)

    def deploy_to_multiple(self, devices: list[Dict], tag: str, repo_path: str = "deploy_repo",
                           base_dir: str = "."):
        """
        Deploy to multiple devices in parallel.

        Args:
            devices: List of device dictionaries.
            tag: Tag/version to deploy.
            repo_path: Path to the cloned repository.
            base_dir: Base directory for the deploy repo.
        """
        self._threads = []

        for device in devices:
            thread = threading.Thread(
                target=self.deploy_to_device,
                args=(device, tag, repo_path, base_dir),
                daemon=True
            )
            self._threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in self._threads:
            thread.join()
