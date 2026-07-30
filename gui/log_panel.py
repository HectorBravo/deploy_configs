"""
Log panel module for displaying deployment output in real-time.
"""

import customtkinter as ctk
from typing import Dict
import tkinter


class LogPanel(ctk.CTkFrame):
    """Panel for displaying log output with color-coded device entries."""

    def __init__(self, master, **kwargs):
        """
        Initialize LogPanel.

        Args:
            master: Parent widget.
            **kwargs: Additional arguments passed to CTkFrame.
        """
        super().__init__(master, **kwargs)

        # Device color mapping for consistent coloring
        self._device_colors: Dict[str, str] = {}
        self._color_palette = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
            "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
            "#BB8FCE", "#85C1E9", "#82E0AA", "#F8C471",
            "#AED6F1", "#D7BDE2", "#A3E4D7", "#FAD7A0"
        ]
        self._color_index = 0

        # Main container with grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Log text widget with scrollbar
        log_frame = ctk.CTkFrame(self, corner_radius=10)
        log_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        # Label for the log panel
        self._log_label = ctk.CTkLabel(
            log_frame,
            text="Output Log",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self._log_label.grid(row=0, column=0, padx=(10, 10), pady=(10, 5), sticky="w")

        # Text widget for log output
        self._log_text = tkinter.Text(
            log_frame,
            bg="#1e1e1e",
            fg="#d4d4d4",
            font=("Consolas", 11),
            wrap=tkinter.WORD,
            state=tkinter.DISABLED,
            highlightthickness=0
        )

        # Scrollbar
        scrollbar = tkinter.Scrollbar(
            log_frame,
            command=self._log_text.yview,
            bg="#333333",
            activebackground="#555555"
        )
        self._log_text.configure(yscrollcommand=scrollbar.set)

        self._log_text.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 10))
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 10))

        # Clear button
        self._clear_btn = ctk.CTkButton(
            log_frame,
            text="Clear",
            command=self.clear_log,
            width=100,
            height=30,
            corner_radius=5
        )
        self._clear_btn.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="e")

        # Auto-scroll tracking
        self._auto_scroll = True

    def _get_device_color(self, device_id: str) -> str:
        """Get or generate a consistent color for a device."""
        if device_id not in self._device_colors:
            self._device_colors[device_id] = self._color_palette[
                self._color_index % len(self._color_palette)
            ]
            self._color_index += 1
        return self._device_colors[device_id]

    def add_log(self, device_id: str, message: str):
        """
        Add a log entry for a device.

        Args:
            device_id: Device identifier (IP or name).
            message: Log message text.
        """
        self._log_text.configure(state=tkinter.NORMAL)

        # Get color for this device
        color = self._get_device_color(device_id)

        # Format the timestamp
        import time
        timestamp = time.strftime("%H:%M:%S")

        # Insert with tags for coloring
        self._log_text.insert(tkinter.END, f"\n[{timestamp}] ", "timestamp")
        self._log_text.tag_configure("timestamp", foreground="#888888")

        # Device ID with its color
        self._log_text.insert(tkinter.END, f"[{device_id}] ", "device")
        self._log_text.tag_configure(f"device_{device_id}", foreground=color)
        self._log_text.tag_configure("device", foreground=color)

        # Message
        self._log_text.insert(tkinter.END, f"{message}\n", "message")
        self._log_text.tag_configure("message", foreground="#d4d4d4")

        self._log_text.configure(state=tkinter.DISABLED)

        # Auto-scroll to bottom
        if self._auto_scroll:
            self._log_text.see(tkinter.END)

    def add_system_log(self, message: str):
        """
        Add a system log entry.

        Args:
            message: System message text.
        """
        self.add_log("SYSTEM", message)

    def clear_log(self):
        """Clear all log entries."""
        self._log_text.configure(state=tkinter.NORMAL)
        self._log_text.delete(1.0, tkinter.END)
        self._log_text.configure(state=tkinter.DISABLED)

    def set_auto_scroll(self, enabled: bool):
        """Enable or disable auto-scroll."""
        self._auto_scroll = enabled
