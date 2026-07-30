# Deploy Configs

Python desktop application for deploying versions from a GitLab repository to multiple devices in parallel. Designed for Linux systems with a CustomTkinter GUI.

## Features

- **Device Management**: JSON-based device configuration with enable/disable toggle
- **Git Integration**: Clone, fetch tags, and checkout versions from GitLab CE repositories
- **Parallel Deployment**: Deploy to multiple devices simultaneously using threading
- **Auto-Refresh**: Configurable interval (default: 5 minutes) for automatic tag refresh
- **Real-time Logs**: Color-coded output per device during deployment
- **Security Hardened**: SSH host key verification, credential sanitization, input validation, audit logging

## GUI Layout

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│  Deploy Configs                                                                  │
├──────────────────────────────────────────────────────────────────────────────────┤
│  GitLab URL: [git@gitlab.example.com:owner/repo.git        ] [Clone Repo]       │
├──────────────────────────────────────────────────────────────────────────────────┤
│  Version:     [v1.0.0                                      ]  [Refresh Tags]    │
│  (1 version)                                                                     │
├──────────────────────────────────────────────────────────────────────────────────┤
│  Devices                         │  Logs                                         │
│  ┌─────────────────────────────┬──┼──┬──────────────────────────────────────────┐ │
│  │ ☑ Device Alpha (192.168.2.1│  │  │ [14:23:01] SYSTEM Repository cloned     │ │
│  │  01) [enabled]              │  │  │ [14:23:02] SYSTEM Tags fetched: 5       │ │
│  │ ☐ Device Beta  (192.168.2.1│  │  │                                            │ │
│  │  02) [enabled]              │  │  │ ────────────────────────────────────────── │ │
│  │ ☐ Device Gamma (192.168.2.1│  │  │ [14:23:10] 101 Starting deployment...     │ │
│  │  03) [enabled]              │  │  │ [14:23:10] 101   git checkout v1.0.0     │ │
│  │ ☐ Device Delta (192.168.2.1│  │  │ [14:23:11] 101   ./install.sh 101        │ │
│  │  04) [disabled]             │  │  │ [14:23:15] 101 ✓ Deployment success.      │ │
│  └─────────────────────────────┴──┴──┴──────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────────┤
│  [ Deploy ]     [ Cancel ]                                                       │
├──────────────────────────────────────────────────────────────────────────────────┤
│  Last refresh: 14:23:01                                                          │
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Panel descriptions:**
- **Git URL**: Input field for GitLab repository URL + Clone button
- **Version**: Dropdown to select a tag/version from the repository
- **Devices**: List of all configured devices with checkboxes. Enabled devices can be selected; disabled devices appear grayed out
- **Logs**: Real-time color-coded output. Each device has a unique color. System messages appear in white
- **Deploy button**: Enabled only after a version is selected. Deploys to all selected devices in parallel
- **Refresh Tags**: Manual refresh button for the tag list
- **Last refresh**: Timestamp of the last tag refresh (automatic or manual)

## Architecture

```
deploy_configs/
├── config/
│   ├── devices.json              # Device configuration (IP, name, enabled status)
│   └── app_config.json           # Application settings (Git URL, SSH key, refresh interval)
├── deploy/
│   ├── __init__.py
│   ├── git_manager.py            # Git operations (clone, fetch, checkout, tags)
│   ├── deploy_worker.py          # Parallel deployment workers with threading
│   ├── refresh_timer.py          # Auto-refresh timer for tags
│   ├── credentials.py            # Secure credential management (keyring/env var)
│   └── audit_logger.py           # Audit logging with sensitive data redaction
├── gui/
│   ├── __init__.py
│   ├── main_window.py            # Main application window
│   ├── device_panel.py           # Device selection panel with checkboxes
│   ├── version_panel.py          # Version/tag selection panel
│   └── log_panel.py              # Real-time log output panel
├── tests/
│   └── test_security.py          # Security test suite (20+ test cases)
├── requirements.txt              # Python dependencies
├── SECURITY_AUDIT.md             # Security audit report
├── status.md                     # Project status tracking
├── main.py                       # Application entry point
└── README.md                     # This file
```

## Installation

### Prerequisites

- Linux operating system
- Python 3.10 or higher
- SSH key configured for GitLab access
- Git installed on the system

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/HectorBravo/deploy_configs.git
   cd deploy_configs
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure devices** in `config/devices.json`:
   ```json
   {
       "devices": [
           {
               "ip": "192.168.2.101",
               "name": "Device Alpha",
               "enabled": true,
               "selected": false
           },
           {
               "ip": "192.168.2.102",
               "name": "Device Beta",
               "enabled": true,
               "selected": false
           }
       ]
   }
   ```

4. **Configure application** in `config/app_config.json`:
   ```json
   {
       "gitlab_url": "git@gitlab.example.com:owner/repo.git",
       "ssh_key_path": "~/.ssh/id_ed25519",
       "repo_clone_dir": "./repo",
       "refresh_interval": 300
   }
   ```

5. **Run the application**:
   ```bash
   python main.py
   ```

## Configuration

### devices.json

Each device entry requires:

| Field | Type | Description |
|-------|------|-------------|
| `ip` | string | IPv4 address (must be in 192.168.2.0/24 range) |
| `name` | string | Human-readable device name |
| `enabled` | boolean | Whether the device is available for deployment |
| `selected` | boolean | Initial selection state (can be changed in GUI) |

### app_config.json

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `gitlab_url` | string | `""` | GitLab repository URL (SSH or HTTPS) |
| `ssh_key_path` | string | `"~/.ssh/id_ed25519"` | Path to SSH private key |
| `repo_clone_dir` | string | `"./repo"` | Directory where the repository will be cloned |
| `refresh_interval` | integer | `300` | Auto-refresh interval in seconds |

## Usage

### 1. Connect to Repository

- Enter the GitLab URL in the "GitLab URL" field
- Click **"Clone Repo"** to clone the repository
- The application will fetch and display all available tags

### 2. Select Version

- Choose a version/tag from the dropdown list
- The deploy button will become enabled once a version is selected

### 3. Select Devices

- Check the boxes next to devices you want to deploy to
- All enabled devices are shown in the device panel
- You can select multiple devices for parallel deployment

### 4. Deploy

- Click **"Deploy"** to start the deployment process
- The application will:
  1. Checkout the selected tag in the local `./repo` directory
  2. Execute `./repo/install.sh XX` for each selected device, where `XX` is the last octet of the device IP (e.g., `192.168.2.101` → `./repo/install.sh 101`)
- Real-time logs are displayed in the log panel with color-coded device output

### 5. Auto-Refresh

- Tags are automatically refreshed at the configured interval (default: 5 minutes)
- Manual refresh is available via the **"Refresh Tags"** button

## Security

This application has undergone two rounds of security auditing with **15 vulnerabilities identified and fixed**:

### Round 1 (Initial Audit)
- **CRIT-01**: SSH host key verification enabled (`StrictHostKeyChecking=yes`)
- **CRIT-02**: Device ID validation to prevent command injection
- **CRIT-03**: Secure credential storage with keyring/environment variable priority
- **HIGH-01/02/03**: Path traversal prevention, SSH key validation, GitLab URL validation
- **MEDIUM-01/02**: Subprocess timeout, thread-safe GUI callbacks

### Round 2 (Follow-up Audit)
- **CRIT-04**: URLs with embedded credentials are rejected
- **LOW-03/04/05/06**: Frame tracking fix, tag validation, IP validation, clipboard implementation
- **MEDIUM-03**: Input validation for refresh timer interval

See `SECURITY_AUDIT.md` for the full audit report.

### Running Security Tests

```bash
pip install pytest
python -m pytest tests/test_security.py -v
```

## Limitations

- Only IPv4 addresses are supported
- Devices must be in the `192.168.2.0/24` range
- SSH key must have `0600` permissions
- GitLab server must be pre-populated in `~/.ssh/known_hosts` for first-time connections
- Requires CustomTkinter GUI framework (not headless-compatible)

## Troubleshooting

### SSH Connection Issues

Ensure your SSH key has correct permissions:
```bash
chmod 600 ~/.ssh/id_ed25519
```

For first-time GitLab connection, populate known_hosts:
```bash
ssh-keyscan -p 22 gitlab.example.com >> ~/.ssh/known_hosts
```

### GitLab Token Authentication

For HTTPS URLs with token authentication, set the environment variable:
```bash
export DEPLOY_GITLAB_TOKEN="glpat-your-token-here"
```

### Device Deployment Fails

- Verify SSH connectivity to the target device
- Ensure `install.sh` exists and is executable in the repository root
- Check that the device is enabled in `devices.json`

## License

MIT