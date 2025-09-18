# Security Configuration Guide

## Overview

DinoAir implements comprehensive security controls for process execution, binary allowlists, and platform-specific protections. This document outlines the security configuration system, approved binaries, and best practices.

## Configuration Structure

### security.process.allowlist

Controls which binaries can be executed by the application.

#### binaries

- **Type**: `array[string]`
- **Default**: See [Default Allowed Binaries](#default-allowed-binaries)
- **Environment Variable**: `SECURITY_PROCESS_ALLOWLIST_BINARIES`
- **Description**: List of binary names (basenames) allowed for execution

#### arg_patterns

- **Type**: `object`
- **Default**: `{}`
- **Environment Variable**: `SECURITY_PROCESS_ALLOWLIST_ARG_PATTERNS`
- **Description**: Optional regex patterns for validating arguments per binary
- **Format**: `{"binary_name": ["pattern1", "pattern2"]}`

#### enable_merge

- **Type**: `boolean`
- **Default**: `false`
- **Environment Variable**: `SECURITY_PROCESS_ALLOWLIST_ENABLE_MERGE`
- **Description**: Controls how config allowlists merge with per-call allowlists
  - `false`: Intersection (more restrictive)
  - `true`: Union (less restrictive)

### security.process.flags

Platform-specific security controls.

#### no_window_windows

- **Type**: `boolean`
- **Default**: `true`
- **Environment Variable**: `SECURITY_PROCESS_FLAGS_NO_WINDOW_WINDOWS`
- **Description**: On Windows, suppress console windows for subprocess execution
- **Implementation**: Adds `CREATE_NO_WINDOW` flag to `creationflags`

#### close_fds_unix

- **Type**: `boolean`
- **Default**: `true`
- **Environment Variable**: `SECURITY_PROCESS_FLAGS_CLOSE_FDS_UNIX`
- **Description**: On Unix systems, close file descriptors in child processes
- **Implementation**: Sets `close_fds=True` in subprocess calls

#### disallow_tty

- **Type**: `boolean`
- **Default**: `true`
- **Environment Variable**: `SECURITY_PROCESS_FLAGS_DISALLOW_TTY`
- **Description**: Prevent subprocess from accessing TTY/terminal

#### stdin_default_devnull

- **Type**: `boolean`
- **Default**: `true`
- **Environment Variable**: `SECURITY_PROCESS_FLAGS_STDIN_DEFAULT_DEVNULL`
- **Description**: Default stdin to /dev/null for subprocess security

### security.process.logging

Security-focused logging controls.

#### redact_env_keys

- **Type**: `array[string]`
- **Default**: `["secret", "key", "token", "password", "credential", "auth"]`
- **Environment Variable**: `SECURITY_PROCESS_LOGGING_REDACT_ENV_KEYS`
- **Description**: Environment variable keys to redact from logs (case-insensitive substring matching)

#### redact_arg_patterns

- **Type**: `array[string]`
- **Default**: See [Default Redaction Patterns](#default-redaction-patterns)
- **Environment Variable**: `SECURITY_PROCESS_LOGGING_REDACT_ARG_PATTERNS`
- **Description**: Regex patterns for redacting sensitive arguments from logs

#### log_command_execution

- **Type**: `boolean`
- **Default**: `true`
- **Environment Variable**: `SECURITY_PROCESS_LOGGING_LOG_COMMAND_EXECUTION`
- **Description**: Enable logging of process execution events

## Default Allowed Binaries

The following binaries are allowed by default:

### Python Ecosystem

- `python`, `python.exe`, `python3`, `python3.exe`
- `pip`, `pip.exe`, `pip3`, `pip3.exe`

### Version Control

- `git`, `git.exe`

### Node.js Ecosystem

- `node`, `node.exe`
- `npm`, `npm.exe`

### Database Tools

- `sqlite3`, `sqlite3.exe`

### System Utilities

- `echo`, `cat`, `head`, `tail`, `find`, `grep`, `wc`, `sort`, `uniq`
- `ls`, `dir`, `pwd`, `whoami`, `date`, `hostname`

### Network Tools

- `ping`, `curl`, `wget`

### Binary Naming Rules

1. **Case Insensitive**: `Python.exe` matches `python.exe`
2. **Basename Matching**: `/usr/bin/python3` matches `python3`
3. **Extension Handling**: Both `python` and `python.exe` should be included for cross-platform compatibility

## Default Redaction Patterns

The following regex patterns redact sensitive information from logs:

```
--password=.*
--token=.*
--secret=.*
--key=.*
-p\s+\S+
--auth\s+\S+
```

## Security Policies

### Binary Execution Policy

1. **Allowlist-Only**: Only binaries in the allowlist can be executed
2. **No Shell Access**: `shell=False` is enforced for all subprocess calls
3. **Argument Validation**: Optional regex patterns can validate arguments per binary
4. **Path Normalization**: Full paths are resolved to basenames for allowlist checking

### Platform-Specific Protections

#### Windows

- **No Console Windows**: Prevents subprocess from creating visible console windows
- **Creation Flags**: Uses `CREATE_NO_WINDOW` flag
- **File Descriptors**: Maintains default Windows behavior for `close_fds`

#### Unix/Linux/macOS

- **File Descriptor Isolation**: Closes file descriptors in child processes
- **TTY Prevention**: Blocks access to terminal devices
- **Process Isolation**: Ensures clean process separation

### Logging Security

1. **Redaction**: Sensitive information is redacted from logs
2. **Structured Logging**: Process execution is logged with context
3. **No Secrets**: Command arguments with credentials are masked
4. **Environment Safety**: Environment variables with sensitive names are redacted

## Configuration Examples

### Basic Configuration

```json
{
  "security": {
    "process": {
      "allowlist": {
        "binaries": ["python", "git", "node"],
        "enable_merge": false
      },
      "flags": {
        "no_window_windows": true,
        "close_fds_unix": true
      }
    }
  }
}
```

### Advanced Configuration with Argument Patterns

```json
{
  "security": {
    "process": {
      "allowlist": {
        "binaries": ["python", "git", "curl"],
        "arg_patterns": {
          "git": ["^(clone|pull|push|status|log|diff)$"],
          "curl": ["^https?://[a-zA-Z0-9.-]+.*$"]
        },
        "enable_merge": false
      },
      "logging": {
        "redact_env_keys": ["api_key", "token", "secret"],
        "redact_arg_patterns": ["--token=.*", "--auth=.*"]
      }
    }
  }
}
```

### Environment Variable Override

```bash
# Override allowlist via environment
export SECURITY_PROCESS_ALLOWLIST_BINARIES='["python", "git"]'

# Enable merge mode
export SECURITY_PROCESS_ALLOWLIST_ENABLE_MERGE=true

# Disable Windows no-window protection
export SECURITY_PROCESS_FLAGS_NO_WINDOW_WINDOWS=false
```

## Best Practices

### Binary Management

1. **Minimal Allowlist**: Only include binaries actually needed
2. **Regular Review**: Periodically audit the allowlist
3. **Environment Specific**: Use different allowlists for development vs. production
4. **Argument Validation**: Use `arg_patterns` for additional security on critical binaries

### Configuration Management

1. **Environment Overrides**: Use environment variables for deployment-specific changes
2. **Version Control**: Track allowlist changes in version control
3. **Testing**: Test security configurations in staging environments
4. **Documentation**: Document why each binary is needed

### Monitoring

1. **Execution Logging**: Monitor process execution logs
2. **Denied Attempts**: Watch for denied binary execution attempts
3. **Anomaly Detection**: Alert on unusual binary usage patterns
4. **Security Audits**: Regular security reviews of process execution

## Troubleshooting

### Common Issues

#### Binary Not Allowed

```
PermissionError: Binary 'somebinary' is not in the allowed_binaries set
```

**Solution**: Add the binary to `security.process.allowlist.binaries`

#### Windows Console Windows Appearing

**Solution**: Ensure `security.process.flags.no_window_windows` is `true`

#### File Descriptor Issues on Unix

**Solution**: Check `security.process.flags.close_fds_unix` setting

### Debugging

1. **Enable Debug Logging**: Set appropriate log levels
2. **Check Configuration**: Verify schema validation passes
3. **Test Environment Variables**: Confirm environment overrides work
4. **Process Monitoring**: Use system tools to monitor subprocess behavior

## Security Considerations

### Threat Model

1. **Code Injection**: Prevented by allowlist and no-shell policy
2. **Privilege Escalation**: Limited by binary restrictions
3. **Information Disclosure**: Mitigated by logging redaction
4. **Resource Exhaustion**: Limited by process controls

### Risk Assessment

- **High Risk**: Allowing shell access or unrestricted binaries
- **Medium Risk**: Overly permissive allowlists
- **Low Risk**: Well-configured allowlists with argument validation

### Compliance

This security configuration supports:

- **Defense in Depth**: Multiple layers of security controls
- **Principle of Least Privilege**: Minimal binary access rights
- **Audit Requirements**: Comprehensive execution logging
- **Incident Response**: Clear security event tracking
