"""
Deploy Configs - Main Application Entry Point

A Python desktop application for deploying versions from a GitLab repository
to multiple devices in parallel.
"""

import sys
from pathlib import Path

# Add the deploy_tool directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from gui.main_window import MainWindow


def main():
    """Main entry point."""
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
