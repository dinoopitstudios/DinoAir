#!/usr/bin/env python3
"""
Pre-commit Hook Management Script for DinoAir

This script helps manage pre-commit hooks and resolve any configuration issues.
It provides utilities to enable/disable hooks selectively and troubleshoot problems.
"""

from pathlib import Path
import subprocess
import sys


def run_command(cmd: list[str], capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    try:
        return subprocess.run(
            cmd, capture_output=capture_output, text=True, check=False, cwd=Path(__file__).parent
        )
    except (subprocess.SubprocessError, OSError):
        sys.exit(1)


def install_hooks():
    """Install pre-commit hooks."""
    result = run_command(["pre-commit", "install", "--install-hooks"])
    if result.returncode == 0:
        pass
    else:
        return False
    return True


def run_basic_checks():
    """Run basic file checks only (no Python linting)."""
    basic_hooks = [
        "trailing-whitespace",
        "end-of-file-fixer",
        "check-yaml",
        "check-toml",
        "check-json",
        "check-merge-conflict",
        "check-added-large-files",
        "check-case-conflict",
        "mixed-line-ending",
    ]

    for hook in basic_hooks:
        result = run_command(["pre-commit", "run", hook, "--all-files"])
        if result.returncode != 0:
            pass
        else:
            pass


def run_formatting_only():
    """Run only formatting tools (Black, Ruff format)."""
    formatting_hooks = ["black", "ruff-format"]

    for hook in formatting_hooks:
        result = run_command(["pre-commit", "run", hook, "--all-files"])
        if result.returncode != 0:
            pass
        else:
            pass


def run_linting_only():
    """Run only linting tools (Ruff)."""
    result = run_command(["pre-commit", "run", "ruff", "--all-files"])
    if result.returncode != 0:
        pass
    else:
        pass


def run_type_checking():
    """Run MyPy type checking."""
    result = run_command(["pre-commit", "run", "mypy", "--all-files"])
    if result.returncode != 0:
        pass
    else:
        pass


def run_security_checks():
    """Run security scanning."""
    security_hooks = ["bandit", "python-safety-dependencies-check"]

    for hook in security_hooks:
        result = run_command(["pre-commit", "run", hook, "--all-files"])
        if result.returncode != 0:
            pass
        else:
            pass


def run_all_hooks():
    """Run all pre-commit hooks."""
    result = run_command(["pre-commit", "run", "--all-files"])
    if result.returncode != 0:
        pass
    else:
        pass


def update_hooks():
    """Update pre-commit hooks to latest versions."""
    result = run_command(["pre-commit", "autoupdate"])
    if result.returncode == 0:
        pass
    else:
        pass


def main():
    """Main function with command-line interface."""
    if len(sys.argv) < 2:
        return

    command = sys.argv[1].lower()

    if command == "install":
        install_hooks()
    elif command == "basic":
        run_basic_checks()
    elif command == "format":
        run_formatting_only()
    elif command == "lint":
        run_linting_only()
    elif command == "types":
        run_type_checking()
    elif command == "security":
        run_security_checks()
    elif command == "all":
        run_all_hooks()
    elif command == "update":
        update_hooks()
    else:
        pass


if __name__ == "__main__":
    main()
