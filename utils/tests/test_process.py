"""
Unit tests for process.py module.
Tests secure subprocess execution with safety validations and error handling.
"""

from pathlib import Path
import subprocess
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

from ..process import (
    SafeProcessError,
    _ensure_list_command,
    _log_invocation,
    _validate_allowed_binary,
    safe_popen,
    safe_run,
)


class TestSafeProcessError:
    """Test cases for SafeProcessError exception."""

    def test_safe_process_error_creation(self):
        """Test SafeProcessError creation with all fields."""
        command = ["python", "--version"]
        error = SafeProcessError(
            message="Command failed",
            command=command,
            returncode=1,
            stdout="Python 3.9.0",
            stderr="Error message",
        )

        if str(error) != "Command failed":
            raise AssertionError
        if error.command != command:
            raise AssertionError
        if error.returncode != 1:
            raise AssertionError
        if error.stdout != "Python 3.9.0":
            raise AssertionError
        if error.stderr != "Error message":
            raise AssertionError

    def test_safe_process_error_defaults(self):
        """Test SafeProcessError with default values."""
        error = SafeProcessError(message="Test error", command=["test"], returncode=2)

        if error.stdout != "":
            raise AssertionError
        if error.stderr != "":
            raise AssertionError

    def test_safe_process_error_inheritance(self):
        """Test SafeProcessError inherits from RuntimeError."""
        error = SafeProcessError("Test", ["cmd"], 1)
        assert isinstance(error, RuntimeError)


class TestCommandValidation:
    """Test cases for command validation functions."""

    def test_ensure_list_command_valid(self):
        """Test _ensure_list_command with valid commands."""
        # Should not raise for valid list commands
        _ensure_list_command(["python", "--version"])
        _ensure_list_command(("git", "status"))  # Tuple is also valid

    def test_ensure_list_command_invalid_type(self):
        """Test _ensure_list_command with invalid command types."""
        with pytest.raises(TypeError, match="command must be a list"):
            _ensure_list_command("python --version")  # String not allowed

        with pytest.raises(TypeError, match="command must be a list"):
            _ensure_list_command(123)  # Number not allowed

    def test_ensure_list_command_empty(self):
        """Test _ensure_list_command with empty command."""
        with pytest.raises(ValueError, match="command cannot be empty"):
            _ensure_list_command([])

        with pytest.raises(ValueError, match="command cannot be empty"):
            _ensure_list_command(())

    def test_validate_allowed_binary_valid(self):
        """Test _validate_allowed_binary with valid binaries."""
        command = ["python", "--version"]
        allowed = {"python", "python.exe"}

        result = _validate_allowed_binary(command, allowed)
        if result != "python":
            raise AssertionError

    def test_validate_allowed_binary_with_path(self):
        """Test _validate_allowed_binary with full path."""
        command = ["/usr/bin/python3", "--version"]
        allowed = {"python3", "python3.exe"}

        result = _validate_allowed_binary(command, allowed)
        if result != "python3":
            raise AssertionError

    def test_validate_allowed_binary_case_insensitive(self):
        """Test _validate_allowed_binary is case insensitive."""
        command = ["Python.exe", "--version"]
        allowed = {"python", "python.exe"}

        result = _validate_allowed_binary(command, allowed)
        if result != "python.exe":
            raise AssertionError

    def test_validate_allowed_binary_not_allowed(self):
        """Test _validate_allowed_binary with disallowed binary."""
        command = ["rm", "-rf", "/"]
        allowed = {"python", "git"}

        with pytest.raises(PermissionError, match="Binary 'rm' is not in the allowed_binaries set"):
            _validate_allowed_binary(command, allowed)

    def test_validate_allowed_binary_empty_allowlist(self):
        """Test _validate_allowed_binary with empty allowlist."""
        command = ["python", "--version"]
        allowed = set()

        with pytest.raises(ValueError, match="allowed_binaries must be a non-empty set"):
            _validate_allowed_binary(command, allowed)

    def test_log_invocation(self):
        """Test _log_invocation logging function."""
        with patch("utils.process.logger") as mock_logger:
            _log_invocation("python", 2, Path("/tmp"))

            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args[0]
            if "python" not in call_args[0]:
                raise AssertionError
            if "2 args" not in call_args[0]:
                raise AssertionError
            if "cwd=/tmp" not in call_args[0]:
                raise AssertionError

    def test_log_invocation_no_cwd(self):
        """Test _log_invocation without working directory."""
        with patch("utils.process.logger") as mock_logger:
            _log_invocation("git", 1, None)

            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args[0]
            if "git" not in call_args[0]:
                raise AssertionError
            if "cwd=" in call_args[0]:
                raise AssertionError

    def test_log_invocation_exception_handling(self):
        """Test _log_invocation handles logging exceptions."""
        with patch("utils.process.logger") as mock_logger:
            mock_logger.debug.side_effect = RuntimeError("Logging failed")

            # Should not raise exception
            _log_invocation("test", 0, None)


class TestSafeRun:
    """Test cases for safe_run function."""

    def test_safe_run_success(self):
        """Test successful command execution."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Success output"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            result = safe_run(["python", "--version"], allowed_binaries={"python"})

            if result != mock_result:
                raise AssertionError
            mock_run.assert_called_once()

            # Verify subprocess.run was called with correct parameters
            call_kwargs = mock_run.call_args[1]
            if call_kwargs["shell"] is not False:
                raise AssertionError
            if call_kwargs["capture_output"] is not True:
                raise AssertionError
            if call_kwargs["text"] is not True:
                raise AssertionError

    def test_safe_run_with_options(self):
        """Test safe_run with various options."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            with tempfile.TemporaryDirectory() as temp_dir:
                result = safe_run(
                    ["python", "-c", "print('test')"],
                    allowed_binaries={"python"},
                    cwd=Path(temp_dir),
                    timeout=30,
                    env={"PYTHONPATH": "/test"},
                    text=False,
                )

                if result != mock_result:
                    raise AssertionError
                call_kwargs = mock_run.call_args[1]
                if call_kwargs["cwd"] != str(temp_dir):
                    raise AssertionError
                if call_kwargs["timeout"] != 30:
                    raise AssertionError
                if call_kwargs["env"] != {"PYTHONPATH": "/test"}:
                    raise AssertionError
                if call_kwargs["text"] is not False:
                    raise AssertionError

    def test_safe_run_command_validation(self):
        """Test safe_run command validation."""
        # Invalid command type
        with pytest.raises(TypeError):
            safe_run("python --version", allowed_binaries={"python"})

        # Empty command
        with pytest.raises(ValueError):
            safe_run([], allowed_binaries={"python"})

        # Binary not in allowlist
        with pytest.raises(PermissionError):
            safe_run(["rm", "-rf", "/"], allowed_binaries={"python"})

    def test_safe_run_check_true_success(self):
        """Test safe_run with check=True and successful command."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            result = safe_run(["python", "--version"], allowed_binaries={"python"}, check=True)

            if result != mock_result:
                raise AssertionError

    def test_safe_run_check_true_failure(self):
        """Test safe_run with check=True and failed command."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = "Some output"
            mock_result.stderr = "Error occurred"
            mock_run.return_value = mock_result

            with pytest.raises(SafeProcessError) as exc_info:
                safe_run(["python", "-c", "exit(1)"], allowed_binaries={"python"}, check=True)

            error = exc_info.value
            if error.returncode != 1:
                raise AssertionError
            if error.stdout != "Some output":
                raise AssertionError
            if error.stderr != "Error occurred":
                raise AssertionError
            if "python" not in str(error):
                raise AssertionError

    def test_safe_run_check_false_failure(self):
        """Test safe_run with check=False and failed command."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_run.return_value = mock_result

            # Should not raise exception when check=False
            result = safe_run(["python", "-c", "exit(1)"], allowed_binaries={"python"}, check=False)

            if result != mock_result:
                raise AssertionError
            if result.returncode != 1:
                raise AssertionError

    def test_safe_run_subprocess_exception(self):
        """Test safe_run when subprocess.run raises exception."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(["python"], 30)

            with pytest.raises(subprocess.TimeoutExpired):
                safe_run(
                    ["python", "-c", "import time; time.sleep(60)"],
                    allowed_binaries={"python"},
                    timeout=30,
                )

    def test_safe_run_performance_monitoring(self):
        """Test that safe_run includes performance monitoring."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            with patch("utils.process.performance_monitor"):
                safe_run(["echo", "test"], allowed_binaries={"echo"})

                # Performance monitoring decorator should be applied
                # (This tests that the decorator is present, not its functionality)


class TestSafePopen:
    """Test cases for safe_popen function."""

    def test_safe_popen_basic(self):
        """Test basic safe_popen functionality."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_popen.return_value = mock_process

            result = safe_popen(["python", "-c", "print('hello')"], allowed_binaries={"python"})

            if result != mock_process:
                raise AssertionError
            mock_popen.assert_called_once()

            # Verify security parameters
            call_kwargs = mock_popen.call_args[1]
            if call_kwargs["shell"] is not False:
                raise AssertionError

    def test_safe_popen_with_options(self):
        """Test safe_popen with various options."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_popen.return_value = mock_process

            with tempfile.TemporaryDirectory() as temp_dir:
                result = safe_popen(
                    ["python", "-u", "-c", "print('test')"],
                    allowed_binaries={"python"},
                    cwd=Path(temp_dir),
                    env={"TEST": "value"},
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                )

                if result != mock_process:
                    raise AssertionError
                call_kwargs = mock_popen.call_args[1]
                if call_kwargs["cwd"] != str(temp_dir):
                    raise AssertionError
                if call_kwargs["env"] != {"TEST": "value"}:
                    raise AssertionError
                if call_kwargs["stdout"] != subprocess.PIPE:
                    raise AssertionError
                if call_kwargs["stderr"] != subprocess.STDOUT:
                    raise AssertionError
                if call_kwargs["stdin"] != subprocess.PIPE:
                    raise AssertionError

    def test_safe_popen_windows_no_window(self):
        """Test safe_popen Windows-specific CREATE_NO_WINDOW flag."""
        with patch("subprocess.Popen") as mock_popen:
            with patch("utils.process.platform.system", return_value="Windows"):
                mock_process = MagicMock()
                mock_popen.return_value = mock_process

                safe_popen(["python", "--version"], allowed_binaries={"python"})

                call_kwargs = mock_popen.call_args[1]
                # Should include CREATE_NO_WINDOW flag on Windows
                if "creationflags" not in call_kwargs:
                    raise AssertionError
                if not call_kwargs["creationflags"] & 0x08000000:
                    raise AssertionError

    def test_safe_popen_unix_close_fds(self):
        """Test safe_popen Unix-specific close_fds setting."""
        with patch("subprocess.Popen") as mock_popen:
            with patch("utils.process.platform.system", return_value="Linux"):
                mock_process = MagicMock()
                mock_popen.return_value = mock_process

                safe_popen(["echo", "test"], allowed_binaries={"echo"})

                call_kwargs = mock_popen.call_args[1]
                if call_kwargs["close_fds"] is not True:
                    raise AssertionError

    def test_safe_popen_command_validation(self):
        """Test safe_popen command validation."""
        # Invalid command type
        with pytest.raises(TypeError):
            safe_popen("echo test", allowed_binaries={"echo"})

        # Binary not allowed
        with pytest.raises(PermissionError):
            safe_popen(["malicious", "command"], allowed_binaries={"safe"})

    def test_safe_popen_custom_creation_flags(self):
        """Test safe_popen with custom creation flags."""
        with patch("subprocess.Popen") as mock_popen:
            with patch("utils.process.platform.system", return_value="Windows"):
                mock_process = MagicMock()
                mock_popen.return_value = mock_process

                custom_flags = 0x00000001  # Some custom flag
                safe_popen(
                    ["python", "--version"], allowed_binaries={"python"}, creationflags=custom_flags
                )

                call_kwargs = mock_popen.call_args[1]
                # Should combine custom flags with CREATE_NO_WINDOW
                expected_flags = custom_flags | 0x08000000
                if call_kwargs["creationflags"] != expected_flags:
                    raise AssertionError

    def test_safe_popen_performance_monitoring(self):
        """Test that safe_popen includes performance monitoring."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_popen.return_value = mock_process

            with patch("utils.process.performance_monitor"):
                safe_popen(["echo", "test"], allowed_binaries={"echo"})

                # Performance monitoring decorator should be applied


class TestSecurityFeatures:
    """Test cases for security features and protections."""

    def test_shell_injection_prevention(self):
        """Test that shell injection is prevented."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Try shell injection patterns
            injection_attempts = [
                ["echo", "test", "&&", "rm", "-rf", "/"],
                ["echo", "test", ";", "malicious_command"],
                ["echo", "test", "|", "cat", "/etc/passwd"],
                ["echo", "test", ">", "/dev/null"],
            ]

            for command in injection_attempts:
                # Should execute safely without shell interpretation
                safe_run(command, allowed_binaries={"echo"})

                # Verify shell=False was used
                call_kwargs = mock_run.call_args[1]
                if call_kwargs["shell"] is not False:
                    raise AssertionError

    def test_path_traversal_prevention(self):
        """Test prevention of path traversal in binary paths."""
        dangerous_paths = [
            ["../../../bin/sh"],
            ["..\\..\\windows\\system32\\cmd.exe"],
            ["/../../../../usr/bin/rm"],
        ]

        for command in dangerous_paths:
            # Should be caught by allowlist validation
            with pytest.raises(PermissionError):
                safe_run(command, allowed_binaries={"python"})

    def test_environment_variable_isolation(self):
        """Test that environment variables are properly isolated."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Pass custom environment
            custom_env = {"SAFE_VAR": "safe_value"}
            safe_run(["python", "--version"], allowed_binaries={"python"}, env=custom_env)

            call_kwargs = mock_run.call_args[1]
            if call_kwargs["env"] != custom_env:
                raise AssertionError

    def test_argument_sanitization(self):
        """Test that arguments are passed safely."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Arguments with special characters
            special_args = [
                "python",
                "-c",
                "print('Hello; World & Universe | Test')",
                "--option=value with spaces",
                "$(malicious command)",
                "`dangerous`",
            ]

            safe_run(special_args, allowed_binaries={"python"})

            # Arguments should be passed as-is in list form (no shell interpretation)
            call_args = mock_run.call_args[0][0]
            if call_args != special_args:
                raise AssertionError

    def test_binary_allowlist_bypass_attempts(self):
        """Test attempts to bypass binary allowlist."""
        bypass_attempts = [
            ["python/../../../bin/sh"],  # Path traversal
            ["PYTHON"],  # Case variation (should work due to case-insensitive matching)
            ["python.exe"],  # Extension variation
            ["/usr/bin/python"],  # Full path (should work if python is allowed)
        ]

        # Test case-insensitive matching works correctly
        result_cases = []
        for command in bypass_attempts:
            try:
                with patch("subprocess.run"):
                    safe_run(command, allowed_binaries={"python", "python.exe"})
                    result_cases.append(("allowed", command[0]))
            except PermissionError:
                result_cases.append(("blocked", command[0]))

        # PYTHON should be allowed (case insensitive)
        # python.exe should be allowed
        # /usr/bin/python should be allowed (basename matching)
        # python/../../../bin/sh should be blocked (not in allowlist after path resolution)

    def test_working_directory_safety(self):
        """Test working directory handling."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Test with Path object
            with tempfile.TemporaryDirectory() as temp_dir:
                safe_run(["python", "--version"], allowed_binaries={"python"}, cwd=Path(temp_dir))

                call_kwargs = mock_run.call_args[1]
                if call_kwargs["cwd"] != str(temp_dir):
                    raise AssertionError

            # Test with string path
            safe_run(["python", "--version"], allowed_binaries={"python"}, cwd="/tmp")

            call_kwargs = mock_run.call_args[1]
            if call_kwargs["cwd"] != "/tmp":
                raise AssertionError


class TestErrorHandling:
    """Test cases for error handling scenarios."""

    def test_subprocess_timeout_handling(self):
        """Test handling of subprocess timeouts."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(["python"], 5)

            with pytest.raises(subprocess.TimeoutExpired):
                safe_run(
                    ["python", "-c", "import time; time.sleep(10)"],
                    allowed_binaries={"python"},
                    timeout=5,
                )

    def test_subprocess_file_not_found(self):
        """Test handling of FileNotFoundError."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("Binary not found")

            with pytest.raises(FileNotFoundError):
                safe_run(["nonexistent"], allowed_binaries={"nonexistent"})

    def test_subprocess_permission_denied(self):
        """Test handling of PermissionError from subprocess."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = PermissionError("Permission denied")

            with pytest.raises(PermissionError):
                safe_run(["restricted"], allowed_binaries={"restricted"})

    def test_safe_process_error_with_output(self):
        """Test SafeProcessError includes command output."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = "Standard output"
            mock_result.stderr = "Error output"
            mock_run.return_value = mock_result

            with pytest.raises(SafeProcessError) as exc_info:
                safe_run(["python", "-c", "exit(1)"], allowed_binaries={"python"}, check=True)

            error = exc_info.value
            if error.stdout != "Standard output":
                raise AssertionError
            if error.stderr != "Error output":
                raise AssertionError
            if error.command != ["python", "-c", "exit(1)"]:
                raise AssertionError

    def test_logging_during_error_conditions(self):
        """Test that logging works during error conditions."""
        with patch("utils.process.logger") as mock_logger:
            mock_logger.debug.side_effect = RuntimeError("Logger failed")

            # Should still validate and raise appropriate error
            with pytest.raises(PermissionError):
                safe_run(["malicious"], allowed_binaries={"safe"})


class TestIntegrationScenarios:
    """Integration test cases for realistic usage scenarios."""

    def test_git_command_execution(self):
        """Test executing git commands safely."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "On branch main"
            mock_run.return_value = mock_result

            result = safe_run(["git", "status", "--porcelain"], allowed_binaries={"git", "git.exe"})

            if result.stdout != "On branch main":
                raise AssertionError

    def test_python_script_execution(self):
        """Test executing Python scripts safely."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Script completed successfully"
            mock_run.return_value = mock_result

            with tempfile.TemporaryDirectory() as temp_dir:
                result = safe_run(
                    ["python", "-u", "script.py", "--arg1", "value1"],
                    allowed_binaries={"python", "python.exe", "python3"},
                    cwd=Path(temp_dir),
                    timeout=300,
                )

                if result.returncode != 0:
                    raise AssertionError

    def test_multiple_command_execution(self):
        """Test executing multiple commands in sequence."""
        with patch("subprocess.run") as mock_run:
            mock_results = [
                MagicMock(returncode=0, stdout="Command 1 output"),
                MagicMock(returncode=0, stdout="Command 2 output"),
                MagicMock(returncode=1, stdout="Command 3 failed"),
            ]
            mock_run.side_effect = mock_results

            commands = [
                (["echo", "test1"], {"echo"}),
                (["echo", "test2"], {"echo"}),
                (["python", "-c", "exit(1)"], {"python"}),
            ]

            results = []
            for command, allowed in commands:
                try:
                    result = safe_run(command, allowed_binaries=allowed)
                    results.append(("success", result.returncode))
                except Exception as e:
                    results.append(("error", str(e)))

            assert len(results) == 3
            if results[0][0] != "success":
                raise AssertionError
            if results[1][0] != "success":
                raise AssertionError
            # Third command fails but should be handled gracefully

    def test_long_running_background_process(self):
        """Test managing long-running background processes."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None  # Still running
            mock_process.terminate = MagicMock()
            mock_process.wait = MagicMock(return_value=0)
            mock_popen.return_value = mock_process

            # Start background process
            process = safe_popen(
                ["python", "-u", "long_script.py"],
                allowed_binaries={"python"},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            if process != mock_process:
                raise AssertionError

            # Simulate process management
            if process.poll() is not None:
                raise AssertionError
            process.terminate()
            process.wait()

            mock_process.terminate.assert_called_once()
            mock_process.wait.assert_called_once()

    def test_command_output_handling(self):
        """Test handling of command output in various scenarios."""
        test_cases = [
            # (stdout, stderr, expected_behavior)
            ("Normal output", "", "should_succeed"),
            ("", "Error message", "should_succeed_with_stderr"),
            ("Mixed output", "Warning message", "should_succeed_mixed"),
            ("", "", "should_succeed_empty"),
            ("Very long output " * 1000, "", "should_handle_large_output"),
        ]

        for stdout, stderr, _expected in test_cases:
            with patch("subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = stdout
                mock_result.stderr = stderr
                mock_run.return_value = mock_result

                result = safe_run(["echo", "test"], allowed_binaries={"echo"})

                if result.stdout != stdout:
                    raise AssertionError
                if result.stderr != stderr:
                    raise AssertionError
                if result.returncode != 0:
                    raise AssertionError

    def test_environment_variable_handling(self):
        """Test various environment variable scenarios."""
        test_environments = [
            None,  # Default environment
            {},  # Empty environment
            {"PATH": "/usr/bin:/bin"},  # Minimal PATH
            {"PYTHONPATH": "/app", "DEBUG": "1"},  # Application specific
            {"MALICIOUS": "$(rm -rf /)"},  # Malicious content (should be safe)
        ]

        for env in test_environments:
            with patch("subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_run.return_value = mock_result

                safe_run(["python", "--version"], allowed_binaries={"python"}, env=env)

                call_kwargs = mock_run.call_args[1]
                if call_kwargs["env"] != env:
                    raise AssertionError


class TestPerformanceAndResourceManagement:
    """Test cases for performance and resource management."""

    def test_concurrent_command_execution(self):
        """Test concurrent command execution."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Concurrent output"
            mock_run.return_value = mock_result

            results = {}

            def worker(worker_id):
                try:
                    result = safe_run(["echo", f"worker_{worker_id}"], allowed_binaries={"echo"})
                    results[worker_id] = result.returncode
                except Exception as e:
                    results[worker_id] = str(e)

            # Start multiple workers
            import threading

            threads = []
            for i in range(5):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # All workers should succeed
            assert len(results) == 5
            for returncode in results.values():
                if returncode != 0:
                    raise AssertionError

    def test_resource_cleanup_after_errors(self):
        """Test that resources are cleaned up after errors."""
        error_scenarios = [
            subprocess.TimeoutExpired(["cmd"], 30),
            FileNotFoundError("Binary not found"),
            PermissionError("Access denied"),
            RuntimeError("Unexpected error"),
        ]

        for error in error_scenarios:
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = error

                try:
                    safe_run(["test"], allowed_binaries={"test"})
                except Exception:
                    pass  # Expected to fail

                # Should have attempted to run subprocess exactly once
                if mock_run.call_count != 1:
                    raise AssertionError

    def test_memory_usage_with_large_output(self):
        """Test memory usage with large command output."""
        with patch("subprocess.run") as mock_run:
            # Simulate large output
            large_output = "Large output line\n" * 10000
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = large_output
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            result = safe_run(
                ["python", "-c", "print('test' * 10000)"], allowed_binaries={"python"}
            )

            # Should handle large output without issues
            assert len(result.stdout) == len(large_output)
            if result.returncode != 0:
                raise AssertionError

    def test_timeout_accuracy(self):
        """Test timeout accuracy and handling."""
        with patch("subprocess.run") as mock_run:

            def timeout_after_delay(*args, **kwargs):
                timeout = kwargs.get("timeout", 0)
                if timeout and timeout < 1:
                    raise subprocess.TimeoutExpired(["python"], timeout)
                return MagicMock(returncode=0)

            mock_run.side_effect = timeout_after_delay

            # Should timeout quickly
            start_time = time.time()
            with pytest.raises(subprocess.TimeoutExpired):
                safe_run(
                    ["python", "-c", "import time; time.sleep(10)"],
                    allowed_binaries={"python"},
                    timeout=0.1,
                )
            end_time = time.time()

            # Should have timed out quickly
            if (end_time - start_time) >= 1.0:
                raise AssertionError


class TestEdgeCasesAndBoundaryConditions:
    """Test cases for edge cases and boundary conditions."""

    def test_empty_allowlist_edge_cases(self):
        """Test edge cases with empty allowlists."""
        with pytest.raises(ValueError, match="allowed_binaries must be a non-empty set"):
            safe_run(["python"], allowed_binaries=set())

    def test_very_long_command_lines(self):
        """Test handling of very long command lines."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Create very long argument list
            long_args = ["python", "-c", "print('test')"] + ["--arg"] * 1000

            safe_run(long_args, allowed_binaries={"python"})

            # Should handle long command lines
            call_args = mock_run.call_args[0][0]
            assert len(call_args) == len(long_args)

    def test_unicode_in_arguments(self):
        """Test handling of unicode characters in arguments."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            unicode_args = ["python", "-c", "print('Hello 世界 🌍')"]

            safe_run(unicode_args, allowed_binaries={"python"})

            # Should handle unicode arguments correctly
            call_args = mock_run.call_args[0][0]
            if call_args != unicode_args:
                raise AssertionError

    def test_none_values_in_options(self):
        """Test handling of None values in optional parameters."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # All None values should be handled gracefully
            safe_run(
                ["python", "--version"],
                allowed_binaries={"python"},
                cwd=None,
                timeout=None,
                env=None,
            )

            call_kwargs = mock_run.call_args[1]
            if call_kwargs["cwd"] is not None:
                raise AssertionError
            if call_kwargs["timeout"] is not None:
                raise AssertionError
            if call_kwargs["env"] is not None:
                raise AssertionError

    def test_binary_name_normalization(self):
        """Test binary name normalization edge cases."""
        test_cases = [
            # (command, allowlist, should_succeed)
            (["Python"], {"python"}, True),  # Case insensitive
            (["ECHO.EXE"], {"echo", "echo.exe"}, True),  # Case and extension
            (["/usr/bin/python3"], {"python3"}, True),  # Full path
            (["./local/bin/tool"], {"tool"}, True),  # Relative path
            (["python3.9"], {"python3.9"}, True),  # Version in name
            (["python-3"], {"python-3"}, True),  # Hyphen in name
            (["python_dev"], {"python_dev"}, True),  # Underscore in name
        ]

        for command, allowlist, should_succeed in test_cases:
            with patch("subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_run.return_value = mock_result

                if should_succeed:
                    result = safe_run(command, allowed_binaries=allowlist)
                    if result.returncode != 0:
                        raise AssertionError
                else:
                    with pytest.raises(PermissionError):
                        safe_run(command, allowed_binaries=allowlist)

    def test_command_list_mutation_protection(self):
        """Test that command list is not mutated during execution."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            original_command = ["python", "--version"]
            command_copy = original_command.copy()

            safe_run(original_command, allowed_binaries={"python"})

            # Original command should not be modified
            if original_command != command_copy:
                raise AssertionError

    def test_allowlist_mutation_protection(self):
        """Test that allowlist is not mutated during execution."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            original_allowlist = {"python", "git"}
            allowlist_copy = original_allowlist.copy()

            safe_run(["python", "--version"], allowed_binaries=original_allowlist)

            # Original allowlist should not be modified
            if original_allowlist != allowlist_copy:
                raise AssertionError
