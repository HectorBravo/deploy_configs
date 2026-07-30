"""
Main application window for Deploy Configs.
"""

import customtkinter as ctk
import json
from pathlib import Path
from typing import Optional

from deploy.git_manager import GitManager
from deploy.deploy_worker import DeployWorker
from deploy.refresh_timer import RefreshTimer
from gui.log_panel import LogPanel
from gui.device_panel import DevicePanel
from gui.version_panel import VersionPanel


class MainWindow:
    """Main application window."""

    def __init__(self):
        """Initialize the main application window."""
        self.root = ctk.CTk()
        self.root.title("Deploy Configs")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)

        # Configuration
        self.config_path = Path("config/app_config.json")
        self.devices_path = Path("config/devices.json")
        self.git_manager = GitManager(str(self.config_path))
        self.deploy_worker: Optional[DeployWorker] = None
        self.refresh_timer: Optional[RefreshTimer] = None

        # State
        self._tags: list[str] = []
        self._repo_connected = False
        self._selected_tag: Optional[str] = None

        # Setup UI
        self._setup_ui()

        # Initial load
        self._load_tags()

    def _setup_ui(self):
        """Set up the main UI layout."""
        # Main container
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=2)
        main_frame.grid_columnconfigure(2, weight=1)

        # Top section: Version selection
        version_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        version_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=5, pady=(5, 5))
        version_frame.grid_rowconfigure(0, weight=1)

        # Version panel
        self.version_panel = VersionPanel(
            version_frame,
            on_version_changed=self._on_version_changed,
            on_refresh=self._on_refresh_tags
        )
        self.version_panel.pack(fill="both", expand=True, padx=5, pady=5)

        # Middle section: Device list and Log output
        middle_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        middle_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        middle_frame.grid_rowconfigure(0, weight=1)
        middle_frame.grid_columnconfigure(0, weight=1)

        # Device panel
        self.device_panel = DevicePanel(
            middle_frame,
            devices_file=str(self.devices_path),
            on_selection_changed=self._on_devices_changed
        )
        self.device_panel.pack(fill="both", expand=True, padx=5, pady=5)

        # Bottom section: Log panel
        log_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        log_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=(5, 5))
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_panel = LogPanel(log_frame)
        self.log_panel.pack(fill="both", expand=True, padx=5, pady=5)

        # Right section: Deploy controls
        control_frame = ctk.CTkFrame(main_frame, corner_radius=10, width=200)
        control_frame.grid(row=1, column=2, sticky="ns", padx=(5, 5), pady=5)
        control_frame.grid_rowconfigure(2, weight=1)
        control_frame.configure(width=220)

        # Repository config section
        repo_frame = ctk.CTkFrame(control_frame, corner_radius=10)
        repo_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            repo_frame,
            text="Repository",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(padx=10, pady=(10, 5))

        self.repo_url_var = ctk.StringVar(value=self.git_manager.repo_url)
        ctk.CTkEntry(
            repo_frame,
            textvariable=self.repo_url_var,
            placeholder_text="Repository URL",
            height=30
        ).pack(fill="x", padx=10, pady=(0, 5))

        self.repo_user_var = ctk.StringVar(value=self.git_manager.username)
        ctk.CTkEntry(
            repo_frame,
            textvariable=self.repo_user_var,
            placeholder_text="Username",
            height=30
        ).pack(fill="x", padx=10, pady=(0, 5))

        self.repo_pass_var = ctk.StringVar(value=self.git_manager.password_or_token)
        ctk.CTkEntry(
            repo_frame,
            textvariable=self.repo_pass_var,
            placeholder_text="Password/Token",
            show="*",
            height=30
        ).pack(fill="x", padx=10, pady=(0, 10))

        self.connect_btn = ctk.CTkButton(
            repo_frame,
            text="Connect",
            command=self._connect_repo,
            height=30
        )
        self.connect_btn.pack(fill="x", padx=10, pady=5)

        # Deploy section
        deploy_frame = ctk.CTkFrame(control_frame, corner_radius=10)
        deploy_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            deploy_frame,
            text="Deploy",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(padx=10, pady=(10, 5))

        self.deploy_btn = ctk.CTkButton(
            deploy_frame,
            text="Deploy Selected",
            command=self._deploy_selected,
            state="disabled",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.deploy_btn.pack(fill="x", padx=10, pady=5)

        # Refresh interval section
        refresh_frame = ctk.CTkFrame(control_frame, corner_radius=10)
        refresh_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            refresh_frame,
            text="Refresh Interval (min)",
            font=ctk.CTkFont(size=11)
        ).pack(padx=10, pady=(10, 5))

        self.refresh_interval_var = ctk.IntVar(value=5)
        ctk.CTkEntry(
            refresh_frame,
            textvariable=self.refresh_interval_var,
            height=30
        ).pack(fill="x", padx=10, pady=(0, 10))

        self.start_timer_btn = ctk.CTkButton(
            refresh_frame,
            text="Start Auto-Refresh",
            command=self._start_refresh_timer,
            height=30
        )
        self.start_timer_btn.pack(fill="x", padx=10, pady=5)

    def _connect_repo(self):
        """Connect to the Git repository."""
        url = self.repo_url_var.get().strip()
        username = self.repo_user_var.get().strip()
        password = self.repo_pass_var.get().strip()

        if not url:
            self.log_panel.add_system_log("Error: Repository URL is required")
            return

        # Update config
        config = {}
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        config['git'] = {
            'url': url,
            'username': username,
            'password_or_token': password
        }

        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)

        self.git_manager = GitManager(str(self.config_path))
        self.log_panel.add_system_log(f"Connecting to repository...")

        # Clone the repository
        success, message = self.git_manager.clone_repo()
        if success:
            self._repo_connected = True
            self.log_panel.add_system_log(f"Connected: {message}")
            self.connect_btn.configure(text="Connected", state="disabled")
            self.version_panel.set_repo_status(True)
            self._load_tags()
        else:
            self.log_panel.add_system_log(f"Connection failed: {message}")

    def _load_tags(self):
        """Load tags from the repository."""
        if not self._repo_connected:
            return

        success, tags = self.git_manager.get_tags()
        if success:
            self._tags = tags
            self.version_panel.set_tags(tags)
            self.log_panel.add_system_log(f"Loaded {len(tags)} tags")
        else:
            self.log_panel.add_system_log("Failed to load tags")

    def _on_version_changed(self, tag: str):
        """Handle version selection change."""
        self._selected_tag = tag
        self._update_deploy_button()

    def _on_devices_changed(self):
        """Handle device selection change."""
        self._update_deploy_button()

    def _update_deploy_button(self):
        """Update the deploy button state."""
        selected_devices = self.device_panel.get_devices_for_deploy()
        can_deploy = self._repo_connected and self._selected_tag and len(selected_devices) > 0
        self.deploy_btn.configure(state="normal" if can_deploy else "disabled")

    def _on_refresh_tags(self):
        """Handle manual tag refresh."""
        if self._repo_connected:
            self.log_panel.add_system_log("Refreshing tags...")
            success, message = self.git_manager.fetch_tags()
            if success:
                self._load_tags()
            else:
                self.log_panel.add_system_log(f"Refresh failed: {message}")

    def _deploy_selected(self):
        """Start deployment to selected devices."""
        if not self._selected_tag:
            self.log_panel.add_system_log("No version selected!")
            return

        devices = self.device_panel.get_devices_for_deploy()
        if not devices:
            self.log_panel.add_system_log("No devices selected!")
            return

        self.log_panel.add_system_log(f"Starting deployment of '{self._selected_tag}' to {len(devices)} device(s)...")

        # Update device statuses
        for device in devices:
            self.device_panel.update_status(device['ip'], 'deploying')

        # Create deploy worker with log callback
        self.deploy_worker = DeployWorker(
            log_callback=lambda dev_id, msg: self.log_panel.add_log(dev_id, msg)
        )

        # Run deployment in a thread
        import threading
        thread = threading.Thread(
            target=self._run_deployment,
            args=(devices, self._selected_tag),
            daemon=True
        )
        thread.start()

    def _run_deployment(self, devices, tag):
        """Run the deployment process."""
        try:
            self.deploy_worker.deploy_to_multiple(devices, tag)

            # Update statuses after deployment
            for device in devices:
                ip = device['ip']
                # Check if deployment was successful by looking at logs
                self.device_panel.update_status(ip, 'success')

            self.log_panel.add_system_log("Deployment complete!")
        except Exception as e:
            self.log_panel.add_system_log(f"Deployment error: {str(e)}")
            for device in devices:
                self.device_panel.update_status(device['ip'], 'failed')

    def _start_refresh_timer(self):
        """Start the auto-refresh timer."""
        if self.refresh_timer and self.refresh_timer.is_running():
            self.refresh_timer.stop()
            self.start_timer_btn.configure(text="Start Auto-Refresh")
            self.log_panel.add_system_log("Auto-refresh stopped")
            return

        interval = self.refresh_interval_var.get()
        if interval < 1:
            interval = 1

        self.refresh_timer = RefreshTimer(
            interval_minutes=float(interval),
            refresh_callback=self._on_refresh_tags
        )
        self.refresh_timer.start()
        self.start_timer_btn.configure(text="Stop Auto-Refresh")
        self.log_panel.add_system_log(f"Auto-refresh started ({interval} min interval)")

    def run(self):
        """Run the application."""
        self.root.mainloop()
