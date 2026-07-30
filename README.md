# Deploy Configs

Python desktop application for deploying versions from a GitLab repository to multiple devices in parallel.

## Features

- Device management via JSON configuration
- Git integration for tag management
- Parallel deployment to multiple devices
- Auto-refresh of tags at configurable intervals
- Real-time color-coded log output

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Configure devices in `config/devices.json`
3. Set GitLab URL and SSH key in `config/app_config.json`
4. Run: `python main.py`
