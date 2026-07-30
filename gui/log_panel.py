"""
Log panel for the deploy tool GUI.
"""

import customtkinter as ctk


class LogPanel(ctk.CTkFrame):
    """Real-time log output panel with color-coding based on device IP.
    
    Security: MEDIUM-02 - Thread-safe GUI updates via after() callback.
    All log updates from worker threads MUST use add_log_threadsafe() 
    to avoid tkinter thread-safety issues.
    """

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
        
        # Store device IP colors for consistency
        self._device_colors: dict[str, str] = {}

    def _get_device_color(self, device_ip: str) -> str:
        """Generate or retrieve a consistent color for a device IP."""
        if device_ip not in self._device_colors:
            import hashlib
            hash_val = int(hashlib.md5(device_ip.encode()).hexdigest(), 16)
            color = f"#{(hash_val >> 16) & 0xFF:02x}{(hash_val >> 8) & 0xFF:02x}{hash_val & 0xFF:02x}"
            self._device_colors[device_ip] = color
        return self._device_colors[device_ip]

    def add_log(self, device_ip: str, message: str):
        """
        Add a log entry with color-coding based on device IP.
        
        WARNING: This method is NOT thread-safe.
        From worker threads, use add_log_threadsafe() instead.
        Must be called from the main (GUI) thread only.
        """
        color = self._get_device_color(device_ip)
        self.log_text.configure(foreground=color)
        self.log_text.insert("end", f"[{device_ip}] {message}\n", device_ip)
        self.log_text.configure(foreground="black")
        self.log_text.see("end")

    def add_log_threadsafe(self, device_ip: str, message: str):
        """
        Thread-safe method to add a log entry from worker threads.
        
        This method uses tkinter's after() to schedule the GUI update
        on the main thread, preventing thread-safety issues.
        
        Args:
            device_ip: The device IP address for color-coding.
            message: The log message to add.
        """
        # Use after() to schedule GUI update on main thread
        self.after(0, self.add_log, device_ip, message)

    def add_system_log(self, message: str):
        """Add a system-level log entry (blue color). Thread-safe via after()."""
        self.after(0, self._add_system_log_inner, message)
    
    def _add_system_log_inner(self, message: str):
        """Inner method to add system log (must be called from main thread)."""
        self.log_text.configure(foreground="blue")
        self.log_text.insert("end", f"[SYSTEM] {message}\n", "SYSTEM")
        self.log_text.configure(foreground="black")
        self.log_text.see("end")

    def add_success_log(self, device_ip: str, message: str):
        """Add a success log entry (green color). Thread-safe via after()."""
        self.after(0, self._add_success_log_inner, device_ip, message)
    
    def _add_success_log_inner(self, device_ip: str, message: str):
        """Inner method to add success log (must be called from main thread)."""
        self.log_text.configure(foreground="green")
        self.log_text.insert("end", f"[{device_ip}] {message}\n", "success")
        self.log_text.configure(foreground="black")
        self.log_text.see("end")

    def add_error_log(self, device_ip: str, message: str):
        """Add an error log entry (red color). Thread-safe via after()."""
        self.after(0, self._add_error_log_inner, device_ip, message)
    
    def _add_error_log_inner(self, device_ip: str, message: str):
        """Inner method to add error log (must be called from main thread)."""
        self.log_text.configure(foreground="red")
        self.log_text.insert("end", f"[{device_ip}] {message}\n", "error")
        self.log_text.configure(foreground="black")
        self.log_text.see("end")

    def clear(self):
        """Clear the log."""
        self.log_text.delete("1.0", "end")
