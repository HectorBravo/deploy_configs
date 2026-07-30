"""
Device panel for the deploy tool GUI.
"""

import customtkinter as ctk
import ipaddress
from typing import List, Callable, Optional


class DevicePanel(ctk.CTkFrame):
    """Device selection panel."""

    def __init__(self, master, devices: List[dict], on_selection_changed: Callable):
        super().__init__(master)
        self.devices = devices
        self.on_selection_changed = on_selection_changed
        self.checkboxes: dict = {}
        self._build_ui()

    @staticmethod
    def _validate_ip(ip_str: str) -> tuple[bool, Optional[str]]:
        """
        Validate an IP address string.
        
        Args:
            ip_str: IP address string to validate.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        if not ip_str or not ip_str.strip():
            return False, "IP address cannot be empty"
        
        try:
            addr = ipaddress.ip_address(ip_str)
            # Only allow IPv4
            if not isinstance(addr, ipaddress.IPv4Address):
                return False, f"Only IPv4 addresses are supported, got: {ip_str}"
            return True, None
        except ValueError:
            return False, f"Invalid IP address: {ip_str}"

    def _build_ui(self):
        """Build the device panel UI."""
        for device in self.devices:
            ip = device.get("ip", "")
            
            # LOW-05 FIX: Validate IP address format
            is_valid, error = self._validate_ip(ip)
            if not is_valid:
                # Skip devices with invalid IPs (log in production)
                continue
            
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
