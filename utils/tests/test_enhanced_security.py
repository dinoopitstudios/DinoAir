"""
Enhanced security tests for process execution with centralized configuration.

Tests cover:
- Centralized allowlist configuration
- Windows/Unix platform-specific guards
- Argument pattern validation
- Security logging and redaction
- Configuration override functionality
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from utils.process import (
    SecurityConfig,
    _get_platform_kwargs,
    _get_secure_stdin,
    _merge_allowlists,
    _redact_arguments,
    _redact_environment,
    _validate_arguments,
    safe_popen,
    safe_run,
)


class TestSecurityConfig:
    """Test cases for SecurityConfig class."""

    def test_security_config_defaults(self):
        """Test default security configuration values."""
        config = SecurityConfig()

        # Test default allowlist
        allowlist = config.get_allowed_binaries()
        if "python" not in allowlist:
            raise AssertionError
        if "git" not in allowlist:
            raise AssertionError
        if "node" not in allowlist:
            raise AssertionError

        # Test default flags
        if config.get_no_window_windows() is not True:
            raise AssertionError
        if config.get_close_fds_unix() is not True:
            raise AssertionError
        if config.get_disallow_tty() is not True:
            raise AssertionError
        if config.get_stdin_default_devnull() is not True:
            raise AssertionError

        # Test default logging
        if config.get_log_command_execution() is not True:
            raise AssertionError
        redact_keys = config.get_redact_env_keys()
        if "secret" not in redact_keys:
            raise AssertionError
        if "password" not in redact_keys:
            raise AssertionError

    @patch("utils.process.config")
    def test_security_config_with_mock_config(self, mock_config):
        """Test SecurityConfig with mocked configuration."""
        # Mock configuration responses
        mock_config.get.side_effect = {
            "security.process.allowlist.binaries": ["python", "git"],
            "security.process.allowlist.enable_merge": True,
            "security.process.flags.no_window_windows": False,
            "security.process.logging.log_command_execution": False,
        }.get

        config = SecurityConfig()

        if config.get_allowed_binaries() != {"python", "git"}:
            raise AssertionError
        if config.get_merge_enabled() is not True:
            raise AssertionError
        if config.get_no_window_windows() is not False:
            raise AssertionError
        if config.get_log_command_execution() is not False:
            raise AssertionError

    @patch("utils.process.config")
    def test_security_config_exception_handling(self, mock_config):
        """Test SecurityConfig handles configuration exceptions gracefully."""
        # Mock configuration to raise exceptions
        mock_config.get.side_effect = Exception("Config error")

        config = SecurityConfig()

        # Should fall back to defaults without raising
        allowlist = config.get_allowed_binaries()
        assert isinstance(allowlist, set)
        if len(allowlist) <= 0:
            raise AssertionError


class TestAllowlistMerging:
    """Test cases for allowlist merging functionality."""

    def test_merge_allowlists_union_mode(self):
        """Test allowlist merging in union mode (enable_merge=True)."""
        per_call = {"python", "node"}
        config_list = {"git", "curl"}

        result = _merge_allowlists(per_call, config_list, enable_merge=True)

        if result != {"python", "node", "git", "curl"}:
            raise AssertionError

    def test_merge_allowlists_intersection_mode(self):
        """Test allowlist merging in intersection mode (enable_merge=False)."""
        per_call = {"python", "git"}
        config_list = {"git", "curl"}

        result = _merge_allowlists(per_call, config_list, enable_merge=False)

        if result != {"git"}:
            raise AssertionError

    def test_merge_allowlists_empty_per_call(self):
        """Test allowlist merging with empty per-call allowlist."""
        per_call = set()
        config_list = {"git", "curl"}

        # Should use config as fallback regardless of merge mode
        result_union = _merge_allowlists(per_call, config_list, enable_merge=True)
        result_intersection = _merge_allowlists(per_call, config_list, enable_merge=False)

        if result_union != {"git", "curl"}:
            raise AssertionError
        if result_intersection != {"git", "curl"}:
            raise AssertionError


class TestArgumentValidation:
    """Test cases for argument pattern validation."""

    @patch("utils.process._security_config")
    def test_validate_arguments_no_patterns(self, mock_config):
        """Test argument validation when no patterns are configured."""
        mock_config.get_arg_patterns.return_value = []

        # Should not raise any exceptions
        _validate_arguments("python", ["python", "--version", "--help"])

    @patch("utils.process._security_config")
    def test_validate_arguments_with_patterns(self, mock_config):
        """Test argument validation with configured patterns."""
        mock_config.get_arg_patterns.return_value = [r"^--version$", r"^--help$"]

        # Valid arguments should pass
        _validate_arguments("python", ["python", "--version"])
        _validate_arguments("python", ["python", "--help"])

        # Invalid arguments should fail
        with pytest.raises(PermissionError, match="does not match any allowed patterns"):
            _validate_arguments("python", ["python", "--invalid"])

    @patch("utils.process._security_config")
    def test_validate_arguments_invalid_regex(self, mock_config):
        """Test argument validation with invalid regex patterns."""
        mock_config.get_arg_patterns.return_value = [r"[invalid(regex"]

        # Should handle invalid regex gracefully
        with pytest.raises(PermissionError):
            _validate_arguments("python", ["python", "--version"])


class TestSecurityLogging:
    """Test cases for security logging and redaction."""

    @patch("utils.process._security_config")
    def test_redact_environment(self, mock_config):
        """Test environment variable redaction."""
        mock_config.get_redact_env_keys.return_value = ["password", "secret", "token"]

        env = {
            "PATH": "/usr/bin",
            "API_SECRET": "sensitive",
            "PASSWORD": "also_sensitive",
            "NORMAL_VAR": "safe",
        }

        redacted = _redact_environment(env)

        if redacted["PATH"] != "/usr/bin":
            raise AssertionError
        if redacted["API_SECRET"] != "[REDACTED]":
            raise AssertionError
        if redacted["PASSWORD"] != "[REDACTED]":
            raise AssertionError
        if redacted["NORMAL_VAR"] != "safe":
            raise AssertionError

    @patch("utils.process._security_config")
    def test_redact_arguments(self, mock_config):
        """Test command argument redaction."""
        mock_config.get_redact_arg_patterns.return_value = [r"--password=.*", r"--token=.*"]

        command = ["curl", "--url", "https://api.com", "--password=secret123", "--token=abc"]

        redacted = _redact_arguments(command)

        if redacted[0] != "curl":
            raise AssertionError
        if redacted[1] != "--url":
            raise AssertionError
        if redacted[2] != "https://api.com":
            raise AssertionError
        if redacted[3] != "[REDACTED]":
            raise AssertionError
        if redacted[4] != "[REDACTED]":
            raise AssertionError

    def test_redact_environment_empty(self):
        """Test environment redaction with empty environment."""
        result = _redact_environment(None)
        if result != {}:
            raise AssertionError

        result = _redact_environment({})
        if result != {}:
            raise AssertionError


class TestPlatformSpecificSecurity:
    """Test cases for platform-specific security features."""

    @patch("utils.process.platform.system")
    @patch("utils.process._security_config")
    def test_get_platform_kwargs_windows(self, mock_config, mock_system):
        """Test Windows platform-specific kwargs."""
        mock_system.return_value = "Windows"
        mock_config.get_no_window_windows.return_value = True

        kwargs = _get_platform_kwargs()

        if kwargs["shell"] is not False:
            raise AssertionError
        if "creationflags" not in kwargs:
            raise AssertionError
        # Should include CREATE_NO_WINDOW flag
        if kwargs["creationflags"] & 0x08000000 == 0:
            raise AssertionError

    @patch("utils.process.platform.system")
    @patch("utils.process._security_config")
    def test_get_platform_kwargs_windows_no_window_disabled(self, mock_config, mock_system):
        """Test Windows kwargs when no-window is disabled."""
        mock_system.return_value = "Windows"
        mock_config.get_no_window_windows.return_value = False

        kwargs = _get_platform_kwargs()

        if kwargs["shell"] is not False:
            raise AssertionError
        if "creationflags" in kwargs:
            raise AssertionError

    @patch("utils.process.platform.system")
    @patch("utils.process._security_config")
    def test_get_platform_kwargs_unix(self, mock_config, mock_system):
        """Test Unix platform-specific kwargs."""
        mock_system.return_value = "Linux"
        mock_config.get_close_fds_unix.return_value = True

        kwargs = _get_platform_kwargs()

        if kwargs["shell"] is not False:
            raise AssertionError
        if kwargs["close_fds"] is not True:
            raise AssertionError

    @patch("utils.process.platform.system")
    @patch("utils.process._security_config")
    def test_get_platform_kwargs_unix_close_fds_disabled(self, mock_config, mock_system):
        """Test Unix kwargs when close_fds is disabled."""
        mock_system.return_value = "Linux"
        mock_config.get_close_fds_unix.return_value = False

        kwargs = _get_platform_kwargs()

        if kwargs["shell"] is not False:
            raise AssertionError
        if "close_fds" in kwargs:
            if kwargs["close_fds"] is not False:
                raise AssertionError

    @patch("utils.process._security_config")
    def test_get_secure_stdin_default_devnull(self, mock_config):
        """Test secure stdin with devnull default."""
        mock_config.get_stdin_default_devnull.return_value = True

        result = _get_secure_stdin(None)
        if result != subprocess.DEVNULL:
            raise AssertionError

    @patch("utils.process._security_config")
    def test_get_secure_stdin_disabled(self, mock_config):
        """Test secure stdin when devnull default is disabled."""
        mock_config.get_stdin_default_devnull.return_value = False

        result = _get_secure_stdin(None)
        assert result is None

    def test_get_secure_stdin_explicit_value(self):
        """Test secure stdin with explicitly provided value."""
        custom_stdin = subprocess.PIPE
        result = _get_secure_stdin(custom_stdin)
        if result != custom_stdin:
            raise AssertionError


class TestEnhancedSafeRun:
    """Test cases for enhanced safe_run function."""

    @patch("utils.process.subprocess.run")
    @patch("utils.process._security_config")
    def test_safe_run_with_config_allowlist(self, mock_config, mock_run):
        """Test safe_run using configuration allowlist."""
        mock_config.get_allowed_binaries.return_value = {"python", "git"}
        mock_config.get_merge_enabled.return_value = False
        mock_config.get_arg_patterns.return_value = []
        mock_config.get_log_command_execution.return_value = False

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Should work with empty per-call allowlist due to config fallback
        result = safe_run(["python", "--version"])

        if result != mock_result:
            raise AssertionError
        mock_run.assert_called_once()

    @patch("utils.process.subprocess.run")
    @patch("utils.process._security_config")
    def test_safe_run_merge_enabled(self, mock_config, mock_run):
        """Test safe_run with allowlist merging enabled."""
        mock_config.get_allowed_binaries.return_value = {"git"}
        mock_config.get_merge_enabled.return_value = True
        mock_config.get_arg_patterns.return_value = []
        mock_config.get_log_command_execution.return_value = False

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Should work with union of per-call and config allowlists
        result = safe_run(["python", "--version"], allowed_binaries={"python"})

        if result != mock_result:
            raise AssertionError

    @patch("utils.process._security_config")
    def test_safe_run_effective_allowlist_validation(self, mock_config):
        """Test safe_run allowlist validation with merged lists."""
        mock_config.get_allowed_binaries.return_value = {"git"}
        mock_config.get_merge_enabled.return_value = False  # Intersection mode

        # Should fail when intersection is empty
        with pytest.raises(PermissionError):
            safe_run(["python", "--version"], allowed_binaries={"python"})


class TestEnhancedSafePopen:
    """Test cases for enhanced safe_popen function."""

    @patch("utils.process.subprocess.Popen")
    @patch("utils.process._security_config")
    def test_safe_popen_with_security_config(self, mock_config, mock_popen):
        """Test safe_popen with security configuration."""
        mock_config.get_allowed_binaries.return_value = {"python"}
        mock_config.get_merge_enabled.return_value = False
        mock_config.get_arg_patterns.return_value = []
        mock_config.get_log_command_execution.return_value = False
        mock_config.get_stdin_default_devnull.return_value = True

        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        result = safe_popen(["python", "-c", "print('test')"])

        if result != mock_process:
            raise AssertionError
        mock_popen.assert_called_once()

        # Check that stdin was set to DEVNULL
        call_kwargs = mock_popen.call_args[1]
        if call_kwargs["stdin"] != subprocess.DEVNULL:
            raise AssertionError


class TestSecurityIntegration:
    """Integration tests for security features."""

    @patch("utils.process.subprocess.run")
    def test_full_security_pipeline(self, mock_run):
        """Test complete security pipeline from config to execution."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Should work with default configuration
        result = safe_run(["python", "--version"])

        if result != mock_result:
            raise AssertionError

        # Verify security flags were applied
        call_kwargs = mock_run.call_args[1]
        if call_kwargs["shell"] is not False:
            raise AssertionError
        if call_kwargs["check"] is not False:
            raise AssertionError

    def test_backward_compatibility(self):
        """Test that enhanced security maintains backward compatibility."""
        # Test with explicit allowlist (original behavior)
        with patch("utils.process.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Original style call should still work
            result = safe_run(["python", "--version"], allowed_binaries={"python"})

            if result != mock_result:
                raise AssertionError


class TestConfigurationOverrides:
    """Test cases for configuration overrides via environment variables."""

    @patch.dict(
        "os.environ",
        {
            "SECURITY_PROCESS_ALLOWLIST_BINARIES": '["python", "custom_binary"]',
            "SECURITY_PROCESS_FLAGS_NO_WINDOW_WINDOWS": "false",
            "SECURITY_PROCESS_LOGGING_LOG_COMMAND_EXECUTION": "false",
        },
    )
    @patch("utils.process.config")
    def test_environment_variable_overrides(self, mock_config):
        """Test that environment variables can override configuration."""
        # Mock config to return environment values
        mock_config.get.side_effect = {
            "security.process.allowlist.binaries": ["python", "custom_binary"],
            "security.process.flags.no_window_windows": False,
            "security.process.logging.log_command_execution": False,
        }.get

        config = SecurityConfig()

        if config.get_allowed_binaries() != {"python", "custom_binary"}:
            raise AssertionError
        if config.get_no_window_windows() is not False:
            raise AssertionError
        if config.get_log_command_execution() is not False:
            raise AssertionError


class TestErrorHandling:
    """Test cases for security error handling."""

    def test_invalid_command_type_security(self):
        """Test security validation with invalid command types."""
        with pytest.raises(TypeError):
            safe_run("string command instead of list")

    def test_empty_command_security(self):
        """Test security validation with empty commands."""
        with pytest.raises(ValueError):
            safe_run([])

    @patch("utils.process._security_config")
    def test_empty_effective_allowlist(self, mock_config):
        """Test handling of empty effective allowlist after merging."""
        mock_config.get_allowed_binaries.return_value = set()
        mock_config.get_merge_enabled.return_value = False

        with pytest.raises(ValueError, match="effective allowlist must be non-empty"):
            safe_run(["python", "--version"], allowed_binaries=set())


if __name__ == "__main__":
    pytest.main([__file__])
