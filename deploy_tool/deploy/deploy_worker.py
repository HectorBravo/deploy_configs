"""
Deploy worker module for handling parallel deployment to multiple devices.
"""

import subprocess
import threading
import queue
from typing import Callable, Optional
from deploy.git_manager import GitManager


class DeployWorker:
    """Manages parallel deployment to multiple devices."""

    def __init__(self, git_manager: GitManager):
        """
        Initialize DeployWorker.

        Args:
            git_manager: GitManager instance for repository operations.
        """
        self.git_manager = git_manager
        self._threads: list[threading.Thread] = []
        self._log_queue: queue.Queue = queue.Queue()
        self._deploy_status: dict[str, str] = {}  # device_ip -> status
        self._lock = threading.Lock()

    def deploy_to_devices(self, devices: list[dict], selected_tag: str,
                          on_log: Callable, on_status: Callable) -> bool:
        """
        Deploy a selected tag to multiple devices in parallel.

        Args:
            devices: List of device dicts with 'ip', 'name', 'enabled' keys.
            selected_tag: The tag/version to deploy.
            on_log: Callback for log messages (device_ip, message).
            on_status: Callback for status updates (device_ip, status).

        Returns:
            True if deployment was initiated successfully.
        """
        # Filter enabled devices
        enabled_devices = [d for d in devices if d.get("enabled", True)]
        selected_devices = [d for d in enabled_devices if d.get("selected", False)]

        if not selected_devices:
            on_log("SYSTEM", "No devices selected for deployment.")
            return False

        if not self.git_manager.is_cloned:
            on_log("SYSTEM", "Repository not cloned. Cannot deploy.")
            on_status("SYSTEM", "error")
            return False

        if self.git_manager.install_sh_path is None:
            on_log("SYSTEM", "install.sh not found in repository. Cannot deploy.")
            on_status("SYSTEM", "error")
            return False

        # Reset status
        with self._lock:
            self._deploy_status = {d["ip"]: "pending" for d in selected_devices}

        # Checkout the selected tag first
        success, message = self.git_manager.checkout_tag(selected_tag)
        on_log("SYSTEM", message)

        if not success:
            on_status("SYSTEM", "error")
            return False

        # Deploy to each device in parallel
        for device in selected_devices:
            ip = device["ip"]
            name = device.get("name", ip)
            # Extract last octet from IP (e.g., 192.168.2.101 -> 101)
            last_octet = ip.split('.')[-1]
            device_id = str(int(last_octet))  # Remove leading zeros

            on_status(ip, "deploying")
            on_log(ip, f"Starting deployment to {name} ({ip}) with version {selected_tag}...")

            thread = threading.Thread(
                target=self._deploy_to_device,
                args=(ip, name, device_id, selected_tag, on_log, on_status),
                daemon=True
            )
            self._threads.append(thread)
            thread.start()

        return True

    def _deploy_to_device(self, ip: str, name: str, device_id: str,
                          tag: str, on_log: Callable, on_status: Callable):
        """
        Deploy to a single device.

        Args:
            ip: Device IP address.
            name: Device name.
            device_id: Last octet of the IP.
            tag: Tag to deploy.
            on_log: Callback for log messages.
            on_status: Callback for status updates.
        """
        try:
            process = self.git_manager.run_install_script(device_id)
            on_log(ip, f"Running install.sh {device_id}...")

            # Read output in real-time
            if process.stdout:
                for line in process.stdout:
                    if line.strip():
                        on_log(ip, f"  {line.rstrip()}")

            # MEDIUM-01 FIX: Add timeout to prevent hanging
            try:
                process.wait(timeout=300)  # 5 minute timeout
            except subprocess.TimeoutExpired:
                process.kill()
                with self._lock:
                    self._deploy_status[ip] = "timeout"
                on_status(ip, "timeout")
                on_log(ip, "✗ Deployment timed out (300s).")
                return

            if process.returncode == 0:
                with self._lock:
                    self._deploy_status[ip] = "success"
                on_status(ip, "success")
                on_log(ip, f"✓ Deployment to {name} ({ip}) completed successfully.")
            else:
                with self._lock:
                    self._deploy_status[ip] = "failed"
                on_status(ip, "failed")
                on_log(ip, f"✗ Deployment to {name} ({ip}) failed with exit code {process.returncode}.")

        except FileNotFoundError as e:
            with self._lock:
                self._deploy_status[ip] = "error"
            on_status(ip, "error")
            on_log(ip, f"✗ Error: {str(e)}")
        except Exception as e:
            with self._lock:
                self._deploy_status[ip] = "error"
            on_status(ip, "error")
            on_log(ip, f"✗ Deployment error: {str(e)}")

    def get_status(self, ip: str) -> str:
        """Get the deployment status for a device."""
        with self._lock:
            return self._deploy_status.get(ip, "pending")

    def get_all_status(self) -> dict[str, str]:
        """Get deployment status for all devices."""
        with self._lock:
            return dict(self._deploy_status)

    def is_running(self) -> bool:
        """Check if any deployment is in progress."""
        return any(t.is_alive() for t in self._threads)

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all deployment threads to complete.

        Args:
            timeout: Maximum time to wait in seconds (None for no timeout).

        Returns:
            True if all deployments completed successfully.
        """
        for thread in self._threads:
            thread.join(timeout=timeout)

        status = self.get_all_status()
        return all(s == "success" for s in status.values()) if status else False
