"""
Deploy Configs - Main application entry point.
"""

import customtkinter as ctk
import json
import os
from pathlib import Path

from gui.main_window import MainWindow


def load_config():
    """Load application configuration."""
    config_path = Path(__file__).parent / "config" / "app_config.json"
    with open(config_path, 'r') as f:
        return json.load(f)


def load_devices():
    """Load device configuration."""
    devices_path = Path(__file__).parent / "config" / "devices.json"
    with open(devices_path, 'r') as f:
        config = json.load(f)
    return config.get("devices", [])


def main():
    """Main entry point."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    config = load_config()
    devices = load_devices()

    app = MainWindow(devices, config)
    app.mainloop()


if __name__ == "__main__":
    main()
