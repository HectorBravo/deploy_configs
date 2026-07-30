"""
Device panel module for displaying and selecting devices.
"""

import customtkinter as ctk
import json
from pathlib import Path
from typing import List, Dict, Optional, Callable


class DevicePanel(ctk.CTkFrame):
    """Panel for displaying and selecting devices from configuration."""

    def __init__(self, master, devices_file: str = "config/devices.json",
                 on_selection_changed: Optional[Callable] = None, **kwargs):
        """
        Initialize DevicePanel.

        Args:
            master: Parent widget.
            devices_file: Path to devices.json file.
            on_selection_changed: Callback when selection changes.
            **kwargs: Additional arguments passed to CTkFrame.
        """
        super().__init__(master, **kwargs)
        self._devices_file = Path(devices_file)
        self._on_selection_changed = on_selection_changed
        self._devices: List[Dict] = []
        self._device_vars: Dict[str, ctk.BooleanVar] = {}  # ip -> selected var
        self._enabled_vars: Dict[str, ctk.BooleanVar] = {}  # ip -> enabled var

        # Status tracking
        self._status_vars: Dict[str, ctk.StringVar] = {}  # ip -> status string var
        self._status_colors: Dict[str, str] = {
            "success": "#2ecc71",
            "failed": "#e74c3c",
            "error": "#e74c3c",
            "deploying": "#f39c12",
            "pending": "#95a5a6",
            "idle": "#3498db"
        }

        # Main container
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header frame
        header_frame = ctk.CTkFrame(self, corner_radius=10)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        header_frame.grid_columnconfigure(2, weight=1)

        self._header_label = ctk.CTkLabel(
            header_frame,
            text="Devices",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self._header_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Load devices count
        self._load_count_label = ctk.CTkLabel(
            header_frame,
            text="Loading...",
            font=ctk.CTkFont(size=12)
        )
        self._load_count_label.grid(row=0, column=1, padx=10, pady=10)

        # Select All button
        self._select_all_btn = ctk.CTkButton(
            header_frame,
            text="Select All",
            command=self._select_all,
            width=130,
            height=30,
            corner_radius=5
        )
        self._select_all_btn.grid(row=0, column=2, padx=10, pady=10, sticky="e")

        # Deselect All button
        self._deselect_all_btn = ctk.CTkButton(
            header_frame,
            text="Deselect All",
            command=self._deselect_all,
            width=140,
            height=30,
            corner_radius=5
        )
        self._deselect_all_btn.grid(row=0, column=3, padx=10, pady=10, sticky="e")

        # Scrollable frame for device list
        scroll_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        scroll_frame.grid_columnconfigure(1, weight=0)

        self._device_frames: Dict[str, ctk.CTkFrame] = {}
        self._load_devices(scroll_frame)

    def _load_devices(self, parent_frame):
        """Load devices from the JSON file."""
        try:
            with open(self._devices_file, 'r') as f:
                data = json.load(f)

            self._devices = data.get("devices", [])
            self._device_frames = {}

            for i, device in enumerate(self._devices):
                ip = device["ip"]
                name = device.get("name", ip)
                enabled = device.get("enabled", True)

                # Create device row frame
                device_frame = ctk.CTkFrame(parent_frame, corner_radius=8)
                device_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=3)
                device_frame.grid_columnconfigure(2, weight=1)

                # Checkbox for selection
                var = ctk.BooleanVar(value=False)
                self._device_vars[ip] = var
                checkbox = ctk.CTkCheckBox(
                    device_frame,
                    variable=var,
                    command=self._on_selection_changed_internal
                )
                checkbox.grid(row=0, column=0, padx=(5, 10), pady=5)

                # Status label
                status_var = ctk.StringVar(value="idle")
                self._status_vars[ip] = status_var
                status_label = ctk.CTkLabel(
                    device_frame,
                    text="\u25cf",
                    text_color=self._status_colors["idle"],
                    font=ctk.CTkFont(size=10)
                )
                status_label.grid(row=0, column=1, padx=(0, 5))
                device_frame.status_label = status_label  # Store reference

                # Name and IP label
                info_label = ctk.CTkLabel(
                    device_frame,
                    text=f"{name}  {ip}",
                    font=ctk.CTkFont(size=12),
                    anchor="w"
                )
                info_label.grid(row=0, column=2, padx=(0, 10), sticky="w")

                # Enabled toggle
                enabled_var = ctk.BooleanVar(value=enabled)
                self._enabled_vars[ip] = enabled_var
                enabled_btn = ctk.CTkSwitch(
                    device_frame,
                    text="Enabled",
                    variable=enabled_var,
                    command=self._on_enabled_changed
                )
                enabled_btn.grid(row=0, column=3, padx=5)

                self._device_frames[ip] = device_frame

            self._update_count()

        except FileNotFoundError:
            self._load_count_label.configure(text=f"File not found: {self._devices_file}")
        except json.JSONDecodeError:
            self._load_count_label.configure(text="Error parsing devices.json")

    def _on_selection_changed_internal(self):
        """Internal callback when selection changes."""
        if self._on_selection_changed:
            self._on_selection_changed()

    def _on_enabled_changed(self):
        """Handle enabled toggle change."""
        for ip, var in self._enabled_vars.items():
            if var.get():
                self._save_device_enabled(ip, True)
                break

    def _save_device_enabled(self, ip: str, enabled: bool):
        """Save device enabled state to file."""
        try:
            with open(self._devices_file, 'r') as f:
                data = json.load(f)

            for device in data.get("devices", []):
                if device["ip"] == ip:
                    device["enabled"] = enabled
                    break

            with open(self._devices_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving device enabled state: {e}")

    def _select_all(self):
        """Select all devices."""
        for var in self._device_vars.values():
            var.set(True)
        if self._on_selection_changed:
            self._on_selection_changed()

    def _deselect_all(self):
        """Deselect all devices."""
        for var in self._device_vars.values():
            var.set(False)
        if self._on_selection_changed:
            self._on_selection_changed()

    def _update_count(self):
        """Update the devices count label."""
        selected = sum(1 for v in self._device_vars.values() if v.get())
        total = len(self._device_vars)
        self._load_count_label.configure(text=f"{selected}/{total} selected")

    def get_selected_devices(self) -> List[Dict]:
        """Get list of selected devices."""
        selected = []
        for device in self._devices:
            ip = device["ip"]
            if self._device_vars.get(ip, ctk.BooleanVar()).get():
                selected.append(device)
        return selected

    def get_devices_for_deploy(self) -> List[Dict]:
        """Get list of selected and enabled devices for deployment."""
        selected = []
        for device in self._devices:
            ip = device["ip"]
            if (self._device_vars.get(ip, ctk.BooleanVar()).get() and
                    device.get("enabled", True)):
                selected.append(device)
        return selected

    def update_status(self, ip: str, status: str):
        """Update the status indicator for a device."""
        if ip in self._device_frames:
            status_label = self._device_frames[ip].status_label
            color = self._status_colors.get(status, "#95a5a6")
            status_label.configure(text_color=color)
            self._status_vars[ip].set(status)

    def refresh_devices(self):
        """Refresh devices from file."""
        for frame in self._device_frames.values():
            frame.destroy()
        self._device_frames.clear()
        self._device_vars.clear()
        self._enabled_vars.clear()
        self._status_vars.clear()

        children = self.winfo_children()
        scroll_frame = None
        for child in children:
            if isinstance(child, ctk.CTkScrollableFrame):
                scroll_frame = child
                break

        if scroll_frame:
            self._load_devices(scroll_frame)
