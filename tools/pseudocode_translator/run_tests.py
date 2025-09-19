#!/usr/bin/env python3
"""
Test runner script for pseudocode_translator

This script provides a convenient way to run all tests with various options.
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys


def run_command(cmd, cwd=None):
    """Run a command and return the result"""
    result = subprocess.run(cmd, cwd=cwd, check=False)
    return result.returncode


def add_test_selection_args(parser):
    parser.add_argument(
        "tests",
        nargs="*",
        default=["tests"],
        help="Specific test files or directories to run (default: all tests)",
    )


def add_test_options_args(parser):
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-vv", "--very-verbose", action="store_true", help="Very verbose output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet output")
    parser.add_argument("-x", "--exitfirst", action="store_true", help="Exit on first failure")
    parser.add_argument(
        "-k",
        "--keyword",
        metavar="EXPRESSION",
        help="Only run tests matching the expression",
    )
    parser.add_argument(
        "-m",
        "--mark",
        metavar="MARKEXPR",
        help="Only run tests matching given mark expression",
    )


def add_coverage_args(parser):
    parser.add_argument(
        "--cov", "--coverage", action="store_true", help="Run with coverage analysis"
    )
    parser.add_argument(
        "--cov-report",
        choices=["term", "html", "xml", "json"],
        default="term",
        help="Coverage report format (default: term)",
    )
    parser.add_argument("--cov-html", action="store_true", help="Generate HTML coverage report")


def add_performance_args(parser):
    parser.add_argument(
        "-n",
        "--numprocesses",
        type=int,
        metavar="NUM",
        help="Number of processes to use for parallel testing",
    )
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark tests")


def main():
    parser = argparse.ArgumentParser(description="Run tests for pseudocode_translator")
    add_test_selection_args(parser)
    add_test_options_args(parser)
    add_coverage_args(parser)
    add_performance_args(parser)

    # Other options
    parser.add_argument("--pdb", action="store_true", help="Drop into debugger on failures")
    parser.add_argument(
        "--lf",
        "--last-failed",
        action="store_true",
        dest="last_failed",
        help="Rerun only the tests that failed last time",
    )
    parser.add_argument(
        "--ff",
        "--failed-first",
        action="store_true",
        dest="failed_first",
        help="Run all tests but run failed tests first",
    )
    parser.add_argument("--markers", action="store_true", help="Show available markers")
    parser.add_argument("--fixtures", action="store_true", help="Show available fixtures")
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="Only collect tests, don't execute them",
    )

    # Code quality options
    parser.add_argument("--lint", action="store_true", help="Run linting (flake8) before tests")
    parser.add_argument("--mypy", action="store_true", help="Run type checking (mypy) before tests")
    parser.add_argument(
        "--format",
        action="store_true",
        help="Check code formatting (ruff) before tests",
    )
    parser.add_argument(
        "--all-checks",
        action="store_true",
        help="Run all checks (lint, mypy, format) before tests",
    )

    args = parser.parse_args()

    # Auto environment setup for local runs
    repo_root = Path(__file__).resolve().parent.parent
    if "PSEUDOCODE_ENABLE_PLUGINS" not in os.environ:
        os.environ["PSEUDOCODE_ENABLE_PLUGINS"] = "0"
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
        # Ensure child processes inherit for pytest collection
        os.environ["PYTHONPATH"] = str(repo_root) + (
            os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""
        )

    # Change to project directory (keep behavior for relative ops)
    project_dir = Path(__file__).parent
    os.chdir(project_dir)

    # Track exit codes
    exit_codes = []

    # Run code quality checks if requested
    if args.all_checks or args.lint:
        exit_codes.append(
            run_command(
                [
                    sys.executable,
                    "-m",
                    "flake8",
                    ".",
                    "--exclude=tests/fixtures,build,dist,.venv",
                ]
            )
        )

    if args.all_checks or args.mypy:
        exit_codes.append(
            run_command([sys.executable, "-m", "mypy", ".", "--exclude=tests/fixtures"])
        )

    if args.all_checks or args.format:
        exit_codes.append(
            run_command(
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "format",
                    "--check",
                    ".",
                ]
            )
        )

    # Build pytest command
    pytest_cmd = [sys.executable, "-m", "pytest"]

    # Add verbosity
    if args.very_verbose:
        pytest_cmd.append("-vv")
    elif args.verbose:
        pytest_cmd.append("-v")
    elif args.quiet:
        pytest_cmd.append("-q")

    # Add other pytest options
    if args.exitfirst:
        pytest_cmd.append("-x")

    if args.keyword:
        pytest_cmd.extend(["-k", args.keyword])

    if args.mark:
        pytest_cmd.extend(["-m", args.mark])

    if args.pdb:
        pytest_cmd.append("--pdb")

    if args.last_failed:
        pytest_cmd.append("--lf")

    if args.failed_first:
        pytest_cmd.append("--ff")

    if args.markers:
        pytest_cmd.append("--markers")
        exit_codes.append(run_command(pytest_cmd))
        return max(exit_codes) if exit_codes else 0

    if args.fixtures:
        pytest_cmd.append("--fixtures")
        exit_codes.append(run_command(pytest_cmd))
        return max(exit_codes) if exit_codes else 0

    if args.collect_only:
        pytest_cmd.append("--collect-only")

    # Add coverage options
    if args.cov:
        pytest_cmd.extend(
            ["--cov=.", "--cov-config=.coveragerc", f"--cov-report={args.cov_report}"]
        )

        if args.cov_html or args.cov_report == "html":
            pytest_cmd.append("--cov-report=html:htmlcov")

    # Add parallel processing
    if args.numprocesses:
        pytest_cmd.extend(["-n", str(args.numprocesses)])

    # Add benchmark option
    if args.benchmark:
        pytest_cmd.append("--benchmark-only")

    # Determine test targets
    default_selection = args.tests == ["tests"]
    internal_tests = repo_root / "pseudocode_translator" / "tests"
    outer_tests = repo_root / "tests"

    runs: list[list[str]] = []
    if default_selection:
        # Run both suites like the Windows batch script
        runs.append(pytest_cmd + [str(internal_tests)])
        runs.append(pytest_cmd + [str(outer_tests)])
    else:
        # Respect explicit selection
        runs.append(pytest_cmd + args.tests)

    # Run pytest invocations and combine results
    for cmd in runs:
        exit_codes.append(run_command(cmd))

    # Generate coverage badge if coverage was run
    if args.cov and args.cov_html:
        run_command([sys.executable, "-m", "coverage_badge", "-o", "coverage.svg"])

    # Return the highest exit code
    return max(exit_codes) if exit_codes else 0


if __name__ == "__main__":
    sys.exit(main())
