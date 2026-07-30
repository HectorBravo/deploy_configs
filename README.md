# Deploy Configs

A Python desktop application for deploying versions from a GitLab CE repository to multiple devices in parallel.

## Features

- **Device Management**: JSON-based device configuration with enable/disable toggle
- **Git Integration**: Clone, fetch tags, checkout versions from GitLab CE repository
- **Parallel Deployment**: Deploy to multiple devices simultaneously using threading
- **Auto-Refresh**: Configurable interval (default: 5 minutes) for automatic tag refresh
- **Real-time Logs**: Color-coded output per device during deployment
- **Repository Validation**: Deploy button disabled until repository is cloned

## Requirements

- Python 3.10+
- Linux operating system
- SSH key for GitLab and device access
- Network access to target devices (192.168.2.0/24 range)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/HectorBravo/deploy_configs.git
cd deploy_configs
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure devices in `config/devices.json`:
```json
{
  "devices": [
    {
      "ip": "192.168.2.10",
      "name": "Device 1",
      "enabled": true
    }
  ]
}
```

4. Configure repository settings in `config/app_config.json`:
```json
{
  "git": {
    "url": "https://gitlab.example.com/your/repo.git",
    "username": "your_username",
    "password_or_token": "your_gitlab_token"
  },
  "ssh": {
    "key_path": "~/.ssh/id_ed25519"
  },
  "refresh": {
    "interval_minutes": 5
  },
  "deploy": {
    "repo_folder": "deploy_repo"
  }
}
```

## Usage

Run the application:
```bash
python main.py
```

1. Enter your GitLab repository URL, username, and token in the Repository section
2. Click "Connect" to clone the repository and load tags
3. Select the version/tag to deploy
4. Select the devices to deploy to (use "Select All" / "Deselect All" buttons)
5. Click "Deploy Selected" to start the deployment
6. Optionally enable auto-refresh to automatically update tags periodically

## Deployment Process

For each selected device, the application:
1. Clones/fetches the Git repository
2. Checks out the selected tag
3. Runs `./repo/install.sh XX` where `XX` is the last octet of the device IP (zero-padded to 3 digits)

For example, for device `192.168.2.101`, it runs `./repo/install.sh 101`.

## Project Structure

```
deploy_configs/
├── config/
│   ├── devices.json          # Device configuration
│   └── app_config.json       # Application settings
├── deploy/
│   ├── __init__.py
│   ├── git_manager.py        # Git operations
│   ├── deploy_worker.py      # Parallel deployment workers
│   └── refresh_timer.py      # Auto-refresh timer
├── gui/
│   ├── __init__.py
│   ├── main_window.py        # Main application window
│   ├── device_panel.py       # Device selection panel
│   ├── version_panel.py      # Version/tag selection panel
│   └── log_panel.py          # Real-time log output panel
├── main.py                   # Application entry point
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Configuration

### devices.json

Each device entry:
- `ip`: Device IP address (must be in 192.168.2.0/24 range)
- `name`: Display name for the device
- `enabled`: Whether the device is enabled for deployment

### app_config.json

- `git.url`: GitLab repository URL
- `git.username`: GitLab username
- `git.password_or_token`: GitLab personal access token
- `ssh.key_path`: Path to SSH private key
- `refresh.interval_minutes`: Auto-refresh interval in minutes
- `deploy.repo_folder`: Local folder name for the cloned repository

## License

MIT License
