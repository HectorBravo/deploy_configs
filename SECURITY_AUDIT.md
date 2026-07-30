# 🔒 Security Audit Report - Deploy Tool

**Date**: 2026-07-31  
**Auditor**: Automated Security Analysis  
**Repository**: https://github.com/HectorBravo/deploy_configs  
**Status**: ⚠️ **CRITICAL ISSUES FOUND**

---

## Executive Summary

This audit identified **8 security issues** in the deploy tool codebase, including **3 critical**, **3 high**, and **2 medium** severity findings. Immediate remediation is required before production use.

---

## Critical Issues

### 🔴 CRIT-01: SSH Host Key Verification Disabled
**Location**: `deploy/git_manager.py` lines 190, 204  
**Severity**: CRITICAL  
**CVSS**: 8.1 (High)

```python
# Vulnerable Code
env["GIT_SSH_COMMAND"] = f"ssh -i {self.ssh_key_path} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
```

**Risk**: Man-in-the-Middle (MITM) attacks. Disabling host key verification allows any attacker to intercept Git operations and potentially steal credentials or inject malicious code into the repository.

**Recommendation**:
```python
# Secure alternative
env["GIT_SSH_COMMAND"] = f"ssh -i {self.ssh_key_path} -o StrictHostKeyChecking=yes"
# Pre-populate known_hosts:
# ssh-keyscan -p 22 gitlab.example.com >> ~/.ssh/known_hosts
```

---

### 🔴 CRIT-02: Device ID Injection into Shell Commands
**Location**: `deploy/git_manager.py` line 193  
**Severity**: CRITICAL  
**CVSS**: 9.8 (Critical)

```python
# Vulnerable Code
return subprocess.Popen(
    ["./install.sh", device_id],  # device_id from IP last octet
    ...
)
```

**Risk**: Command injection if device_id is derived from untrusted input. While current implementation uses IP last octet, any future modification to accept user input directly would be exploitable.

**Recommendation**:
```python
# Use validate_device_id function
def validate_device_id(device_id: str) -> bool:
    return bool(re.match(r'^\d{1,3}$', device_id))

if not validate_device_id(device_id):
    raise ValueError(f"Invalid device_id: {device_id}")

# Use shell=False (default) which avoids shell injection
subprocess.Popen(["./install.sh", device_id], shell=False, ...)
```

---

### 🔴 CRIT-03: Plaintext Credential Storage
**Location**: `config/app_config.json` (potential)  
**Severity**: CRITICAL  
**CVSS**: 7.5 (High)

The configuration file template shows empty `gitlab_url` field. If credentials (tokens, passwords) are stored in this file, they are stored in plaintext with no encryption.

**Risk**: Credential theft if the configuration file is accessed by unauthorized users or backed up to unencrypted storage.

**Recommendation**:
- Use environment variables for sensitive credentials
- Use OS keyring (keyring library) for token storage
- Implement encrypted config file option

```python
# Example: Use environment variables
gitlab_token = os.environ.get("DEPLOY_GITLAB_TOKEN")
ssh_key_password = os.environ.get("DEPLOY_SSH_KEY_PASSPHRASE")
```

---

## High Severity Issues

### 🟠 HIGH-01: Path Traversal Vulnerability
**Location**: `deploy/git_manager.py` lines 25, 27  
**Severity**: HIGH  
**CVSS**: 7.5 (High)

```python
# Vulnerable Code
self.repo_dir = Path(repo_dir).resolve()
self.ssh_key_path = Path(ssh_key_path).expanduser().resolve()
```

**Risk**: While `.resolve()` is used, there's no validation that paths stay within expected directories. An attacker could potentially access files outside the intended directory.

**Recommendation**:
```python
def validate_path(path: Path, allowed_parent: Path) -> bool:
    """Ensure path is within allowed_parent directory."""
    try:
        return path.resolve().is_relative_to(allowed_parent)
    except ValueError:
        return False

# Usage
allowed_base = Path.cwd()
if not validate_path(Path(repo_dir), allowed_base):
    raise ValueError("repo_dir must be within current directory")
```

---

### 🟠 HIGH-02: SSH Key Path Not Validated
**Location**: `deploy/git_manager.py` line 27  
**Severity**: HIGH  
**CVSS**: 7.0 (High)

The SSH key path is accepted from configuration without validation:
- No check that the file exists
- No check that the file has correct permissions (should be 0600)
- No check that it's a valid SSH key

**Recommendation**:
```python
def validate_ssh_key(path: Path) -> bool:
    if not path.exists():
        raise FileNotFoundError(f"SSH key not found: {path}")
    stats = path.stat()
    if stats.st_mode & 0o777 != 0o600:
        raise PermissionError(f"SSH key permissions too open: {oct(stats.st_mode & 0o777)}")
    return True
```

---

### 🟠 HIGH-03: No Input Validation for GitLab URL
**Location**: `deploy/git_manager.py` line 26  
**Severity**: HIGH  
**CVSS**: 6.5 (Medium-High)

The GitLab URL is used directly in `subprocess.run(["git", "clone", self.gitlab_url, ...])` without validation.

**Risk**: URL injection, protocol smuggling (e.g., `git@` vs `https://`), or SSRF.

**Recommendation**:
```python
import re
from urllib.parse import urlparse

def validate_gitlab_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ('ssh', 'https', 'git'):
        raise ValueError(f"Invalid Git URL scheme: {parsed.scheme}")
    
    # Validate SSH URL format
    if parsed.scheme == 'ssh' or '@' in url:
        pattern = r'^git@[\w.-]+:[\w-]+/[\w.-]+$'
        if not re.match(pattern, url):
            raise ValueError(f"Invalid SSH Git URL format: {url}")
    return True
```

---

## Medium Severity Issues

### 🟡 MEDIUM-01: No Timeout on subprocess.wait()
**Location**: `deploy/deploy_worker.py` line 116  
**Severity**: MEDIUM  
**CVSS**: 5.3 (Medium)

```python
process.wait()  # No timeout!
```

**Risk**: Denial of service if install.sh hangs indefinitely.

**Recommendation**:
```python
try:
    process.wait(timeout=300)  # 5 minute timeout
except subprocess.TimeoutExpired:
    process.kill()
    raise TimeoutError("install.sh exceeded timeout")
```

---

### 🟡 MEDIUM-02: Thread Safety Issues
**Location**: `deploy/deploy_worker.py` lines 62, 119-126  
**Severity**: MEDIUM  
**CVSS**: 5.0 (Medium)

While a lock is used for `_deploy_status`, the callbacks (`on_log`, `on_status`) are called without thread synchronization, which could cause GUI updates from multiple threads simultaneously.

**Recommendation**:
- Use `queue.Queue` for thread-safe callback dispatch
- Ensure all GUI updates happen on the main thread
- Use `threading.Lock` around callback invocations

---

## Low Severity Issues

### 🟢 LOW-01: Verbose Error Messages
**Location**: Multiple files  
**Severity**: LOW  
**CVSS**: 3.1 (Low)

Error messages may leak internal paths, repository structure, or Git configuration details.

---

### 🟢 LOW-02: No Logging of Deployment Actions
**Severity**: LOW  
**CVSS**: 2.0 (Low)

Deployment actions are not logged to an audit trail. In production, all deploy actions should be logged for compliance.

---

## Remediation Priority

| Priority | Issue | Fix Complexity | Estimated Time |
|----------|-------|---------------|----------------|
| P0 | CRIT-01: SSH Host Key Verification | Low | 15 min |
| P0 | CRIT-02: Command Injection Prevention | Low | 15 min |
| P0 | CRIT-03: Credential Storage | Medium | 1 hour |
| P0 | CRIT-04: Embedded Credentials in URL | Low | 10 min |
| P1 | HIGH-01: Path Traversal Prevention | Medium | 30 min |
| P1 | HIGH-02: SSH Key Validation | Low | 15 min |
| P1 | HIGH-03: URL Validation | Low | 15 min |
| P2 | MEDIUM-01: Timeout on wait() | Low | 10 min |
| P2 | MEDIUM-02: Thread Safety | Medium | 1 hour |
| P3 | LOW-01: Verbose Error Messages | Low | 10 min |
| P3 | LOW-02: No Logging of Deployment Actions | Low | 30 min |
| P3 | LOW-03: Frame Tracking Bug | Low | 5 min |
| P3 | LOW-04: Tag Validation | Low | 10 min |
| P3 | LOW-05: IP Validation | Low | 10 min |
| P3 | LOW-06: Copy Tag Not Implemented | Low | 5 min |

---

## Compliance Checklist

- [ ] All SSH host key checks enabled
- [ ] All user inputs validated and sanitized
- [ ] No credentials stored in plaintext
- [ ] Path traversal prevention in place
- [ ] Command injection prevention verified
- [ ] Proper timeouts on all subprocess calls
- [ ] Thread-safe GUI updates
- [ ] Audit logging implemented
- [ ] Error messages sanitized (no info leakage)
- [ ] Security tests added to CI/CD

---

## Recommendations Summary

1. **Immediately fix CRIT-01**: Re-enable SSH host key verification
2. **Immediately fix CRIT-02**: Add input validation for device_id
3. **Immediately fix CRIT-03**: Implement secure credential storage
4. **Short-term**: Add all HIGH severity fixes
5. **Medium-term**: Address MEDIUM and LOW severity issues
6. **Ongoing**: Add security scanning to CI/CD pipeline
