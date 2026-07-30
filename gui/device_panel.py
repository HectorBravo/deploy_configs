"""
Device panel for the deploy tool GUI.
"""

import customtkinter as ctk
from typing import List, Callable


class DevicePanel(ctk.CTkFrame):
    """Device selection panel."""

    def __init__(self, master, devices: List[dict], on_selection_changed: Callable):
        super().__init__(master)
        self.devices = devices
        self.on_selection_changed = on_selection_changed
        self.checkboxes: dict = {}
        self._build_ui()

    def _build_ui(self):
        """Build the device panel UI."""
        for device in self.devices:
            ip = device["ip"]
            name = device.get("name", ip)
            enabled = device.get("enabled", True)

            var = ctk.BooleanVar(value=device.get("selected", False))
            cb = ctk.CTkCheckBox(
                self,
                text=f"{name} ({ip}) {'[disabled]' if not enabled else ''}",
                variable=var,
                state="disabled" if not enabled else "normal",
                command=lambda d=device: self._on_checkbox_changed(d)
            )
            cb.pack(fill="x", padx=5, pady=2)
            self.checkboxes[ip] = (cb, var)

    def _on_checkbox_changed(self, device):
        """Handle checkbox state change."""
        ip = device["ip"]
        selected = self.checkboxes[ip][1].get()
        device["selected"] = selected
        self.on_selection_changed(device)

    def get_selected_devices(self) -> List[dict]:
        """Get list of selected devices."""
        return [d for d in self.devices if d.get("selected", False) and d.get("enabled", True)]
