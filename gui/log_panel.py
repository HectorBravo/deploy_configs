"""
Log panel for the deploy tool GUI.
"""

import customtkinter as ctk


class LogPanel(ctk.CTkFrame):
    """Real-time log output panel with color-coded devices."""

    def __init__(self, master):
        super().__init__(master)
        self.log_text = ctk.CTkTextbox(self, wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Configure text tags for color-coding
        self.log_text.tag_config("SYSTEM", foreground="blue")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("failed", foreground="red")
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("deploying", foreground="orange")

    def add_log(self, device_ip: str, message: str):
        """Add a log entry with color-coding based on device IP."""
        import hashlib
        # Generate consistent color per device
        hash_val = int(hashlib.md5(device_ip.encode()).hexdigest(), 16)
        color = f"#{(hash_val >> 16) & 0xFF:02x}{(hash_val >> 8) & 0xFF:02x}{hash_val & 0xFF:02x}"

        self.log_text.configure(foreground=color)
        self.log_text.insert("end", f"[{device_ip}] {message}\n", device_ip)
        self.log_text.configure(foreground="black")
        self.log_text.see("end")

    def clear(self):
        """Clear the log."""
        self.log_text.delete("1.0", "end")
