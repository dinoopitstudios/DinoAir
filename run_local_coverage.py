#!/usr/bin/env python3
"""
Local Coverage Runner

Run tests with coverage locally and generate reports.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Run coverage locally."""
    print("🧪 Running tests with coverage...")

    try:
        # Run tests with coverage
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "--cov=.",
            "--cov-report=xml:coverage.xml",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-branch",
            "tests/",
        ]

        result = subprocess.run(cmd, check=False)

        if result.returncode == 0:
            print("✅ Tests completed successfully")
        else:
            print("⚠️  Some tests failed or no tests found")

        # Check if coverage file was created
        if Path("coverage.xml").exists():
            print("✅ Coverage report generated: coverage.xml")
            print("📊 HTML report available: htmlcov/index.html")
        else:
            print("❌ No coverage report generated")

    except FileNotFoundError:
        print("❌ pytest not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "pytest-cov"])
        main()


if __name__ == "__main__":
    main()
