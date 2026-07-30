"""
Main window for the deploy tool GUI.
"""

import customtkinter as ctk
import threading
from typing import List, Dict

from gui.device_panel import DevicePanel
from gui.log_panel import LogPanel
from deploy.git_manager import GitManager
from deploy.deploy_worker import DeployWorker
from deploy.refresh_timer import RefreshTimer


class MainWindow(ctk.CTk):
    """Main application window."""

    def __init__(self, devices: List[dict], config: dict):
        super().__init__()
        self.devices = devices
        self.config = config
        self.selected_tag = None

        # Initialize components
        self.git_manager = GitManager(
            config.get("repo_clone_dir", "./repo"),
            config.get("gitlab_url", ""),
            config.get("ssh_key_path", "~/.ssh/id_ed25519")
        )
        self.deploy_worker = DeployWorker(self.git_manager)

        # Configure window
        self.title("Deploy Configs")
        self.geometry("900x700")

        self._build_ui()
        self._setup_auto_refresh()

    def _build_ui(self):
        """Build the main UI."""
        # Git URL input frame
        git_frame = ctk.CTkFrame(self)
        git_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(git_frame, text="GitLab URL:").pack(side="left", padx=5)
        self.git_url_entry = ctk.CTkEntry(git_frame, width=400)
        self.git_url_entry.insert(0, self.config.get("gitlab_url", ""))
        self.git_url_entry.pack(side="left", padx=5)

        ctk.CTkButton(git_frame, text="Clone Repo", command=self._clone_repo).pack(side="left", padx=5)

        # Version selection frame
        version_frame = ctk.CTkFrame(self)
        version_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(version_frame, text="Version:").pack(side="left", padx=5)
        self.version_var = ctk.StringVar(value="No tags available")
        self.version_combo = ctk.CTkComboBox(version_frame, values=[], command=self._on_version_selected)
        self.version_combo.pack(side="left", padx=5)

        ctk.CTkButton(version_frame, text="Refresh Tags", command=self._refresh_tags).pack(side="left", padx=5)

        # Device panel
        self.device_panel = DevicePanel(self, self.devices, self._on_device_selection_changed)
        self.device_panel.pack(fill="both", expand=True, padx=10, pady=5)

        # Deploy button
        self.deploy_btn = ctk.CTkButton(
            self,
            text="DEPLOY TO SELECTED",
            command=self._deploy,
            state="disabled"  # Disabled until repo is cloned
        )
        self.deploy_btn.pack(pady=10)

        # Log panel
        self.log_panel = LogPanel(self)
        self.log_panel.pack(fill="both", expand=True, padx=10, pady=5)

    def _setup_auto_refresh(self):
        """Setup auto-refresh timer."""
        interval = self.config.get("refresh_interval_minutes", 5) * 60
        self.refresh_timer = RefreshTimer(interval, self._refresh_tags)
        self.refresh_timer.start()

    def _clone_repo(self):
        """Clone the repository."""
        url = self.git_url_entry.get().strip()
        if url and url != self.config.get("gitlab_url", ""):
            self.config["gitlab_url"] = url
            # Save config
            import json
            config_path = Path(__file__).parent.parent / "config" / "app_config.json"
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)

        success, msg = self.git_manager.clone()
        self.log_panel.add_log("SYSTEM", msg)

        if success:
            self.deploy_btn.configure(state="normal")
            self._refresh_tags()

    def _refresh_tags(self):
        """Refresh the tags list."""
        success, tags = self.git_manager.list_tags()
        if success and tags:
            self.version_combo.configure(values=tags)
            self.log_panel.add_log("SYSTEM", f"Found {len(tags)} tags.")
        else:
            self.version_combo.configure(values=[])
            self.log_panel.add_log("SYSTEM", "No tags found.")

    def _on_version_selected(self, tag):
        """Handle version selection."""
        self.selected_tag = tag

    def _on_device_selection_changed(self, device):
        """Handle device selection change."""
        pass

    def _deploy(self):
        """Start deployment to selected devices."""
        if not self.selected_tag:
            self.log_panel.add_log("SYSTEM", "No version selected.")
            return

        selected_devices = self.device_panel.get_selected_devices()
        if not selected_devices:
            self.log_panel.add_log("SYSTEM", "No devices selected.")
            return

        self.log_panel.add_log("SYSTEM", f"Deploying version {self.selected_tag}...")

        def deploy_thread():
            def on_log(device_ip, message):
                self.log_panel.add_log(device_ip, message)

            def on_status(device_ip, status):
                self.log_panel.add_log(device_ip, f"Status: {status}")

            self.deploy_worker.deploy_to_devices(
                selected_devices,
                self.selected_tag,
                on_log,
                on_status
            )

        threading.Thread(target=deploy_thread, daemon=True).start()
