#!/usr/bin/env python3
"""
Test runner script for the utils package.
Provides convenient commands for running tests with different options.
"""

import subprocess
import sys


def run_command(cmd):
    """Run a command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def run_tests(args=None):
    """Run pytest with given arguments."""
    cmd = "python -m pytest"
    if args:
        cmd += f" {args}"

    success, stdout, stderr = run_command(cmd)

    if stdout:
        pass
    if stderr:
        pass

    return success


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        return

    command = sys.argv[1]

    if command == "all":
        success = run_tests()
    elif command == "unit":
        success = run_tests("-m unit")
    elif command == "coverage":
        success = run_tests("--cov=utils --cov-report=term-missing --cov-report=html")
    elif command == "verbose":
        success = run_tests("-v")
    elif command in [
        "logger",
        "config_loader",
        "error_handling",
        "performance_monitor",
        "dependency_container",
        "artifact_encryption",
    ]:
        success = run_tests(f"tests/test_{command}.py -v")
    else:
        return

    if success:
        pass
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
