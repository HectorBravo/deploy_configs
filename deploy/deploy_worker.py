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

        The deployment process:
        1. Clone/fetch the repository to repo_path (subfolder where GUI is located)
        2. Checkout the selected tag
        3. Run ./repo/install.sh XX where XX = last octet + 1 of device IP

        Args:
            device: Device dictionary with 'ip' and 'name' keys.
            tag: Tag/version to deploy.
            repo_path: Path to the cloned repository (subfolder where GUI runs).
            base_dir: Base directory where repo_path is located.

        Returns:
            Tuple of (success, message)
        """
        ip = device.get('ip', 'unknown')
        name = device.get('name', ip)
        device_id = name

        try:
            # Calculate last octet + 1 (e.g., 192.168.2.101 -> 102)
            last_octet = int(ip.split('.')[-1])
            short_id = str(last_octet + 1)  # e.g., 101 -> "102"

            self._log(device_id, f"Starting deployment to {ip} (id: {short_id})")
            self._log(device_id, f"Checking out tag: {tag}")

            # Step 1: Checkout the tag in the cloned repo
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

            # Step 2: Run ./repo/install.sh XX from the base_dir (where GUI is located)
            # The repo is cloned as a subfolder, so install.sh is at base_dir/repo/install.sh
            install_script = Path(base_dir) / 'repo' / 'install.sh'

            if not install_script.exists():
                self._log(device_id, f"install.sh not found at {install_script}")
                return False, f"install.sh not found at {install_script}"

            cmd = ['bash', str(install_script), short_id]
            self._log(device_id, f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=base_dir,
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
            base_dir: Base directory where the GUI is located.
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
