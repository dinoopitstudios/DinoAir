#!/usr/bin/env python3
"""
Test Suite for DinoAir Import Organization Automation
==================================================

This script tests all components of the import organization automation system
implemented in Phase 7.

Usage:
    python scripts/test_automation.py [options]

Options:
    --verbose    Enable detailed output
    --fix        Attempt to fix detected issues
    --report     Generate comprehensive test report
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class AutomationTester:
    """Tests the complete import organization automation system."""

    def __init__(self, root_path: Path, verbose: bool = False):
        self.root_path = root_path
        self.verbose = verbose
        self.test_results: list[dict] = []

    def log(self, message: str, level: str = "info") -> None:
        """Log a message if verbose mode is enabled."""
        if self.verbose or level == "error":
            timestamp = datetime.now().strftime("%H:%M:%S")
            prefix = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
            print(f"[{timestamp}] {prefix.get(level, 'ℹ️')} {message}")

    def run_test(
        self,
        name: str,
        description: str,
        command: list[str],
        expected_exit_code: int = 0,
        timeout: int = 60,
    ) -> dict:
        """Run a single test and record results."""
        self.log(f"Running test: {name}")

        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.root_path,
                check=False,
            )

            duration = time.time() - start_time
            success = result.returncode == expected_exit_code

            test_result = {
                "name": name,
                "description": description,
                "command": " ".join(command),
                "success": success,
                "exit_code": result.returncode,
                "expected_exit_code": expected_exit_code,
                "duration": round(duration, 2),
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "timestamp": datetime.now().isoformat(),
            }

            if success:
                self.log(f"✅ {name} passed ({duration:.2f}s)", "success")
            else:
                self.log(f"❌ {name} failed (exit code: {result.returncode})", "error")
                if self.verbose and result.stderr:
                    self.log(f"Error output: {result.stderr[:200]}...", "error")

            self.test_results.append(test_result)
            return test_result

        except subprocess.TimeoutExpired:
            self.log(f"❌ {name} timed out after {timeout}s", "error")
            test_result = {
                "name": name,
                "description": description,
                "command": " ".join(command),
                "success": False,
                "exit_code": -1,
                "expected_exit_code": expected_exit_code,
                "duration": timeout,
                "stdout": "",
                "stderr": "Test timed out",
                "timestamp": datetime.now().isoformat(),
            }
            self.test_results.append(test_result)
            return test_result

        except Exception as e:
            self.log(f"❌ {name} failed with exception: {e}", "error")
            test_result = {
                "name": name,
                "description": description,
                "command": " ".join(command),
                "success": False,
                "exit_code": -1,
                "expected_exit_code": expected_exit_code,
                "duration": 0,
                "stdout": "",
                "stderr": str(e),
                "timestamp": datetime.now().isoformat(),
            }
            self.test_results.append(test_result)
            return test_result

    def test_circular_dependency_detection(self) -> bool:
        """Test circular dependency detection system."""
        self.log("Testing circular dependency detection...")

        result = self.run_test(
            "circular_dependency_check",
            "Run circular dependency detection script",
            [sys.executable, "scripts/check_circular_dependencies.py", "--verbose"],
            expected_exit_code=0,
        )

        return result["success"]

    def test_python_import_organization(self) -> bool:
        """Test Python import organization tools."""
        self.log("Testing Python import organization...")

        tests = [
            (
                "isort_check",
                "Check import sorting",
                [sys.executable, "-m", "isort", "--check-only", "--profile", "black", "."],
            ),
            ("ruff_check", "Run ruff linter", [sys.executable, "-m", "ruff", "check", "."]),
            (
                "ruff_format_check",
                "Check ruff formatting",
                [sys.executable, "-m", "ruff", "format", "--check", "."],
            ),
        ]

        results = []
        for name, desc, cmd in tests:
            result = self.run_test(name, desc, cmd)
            results.append(result["success"])

        return all(results)

    def test_typescript_tools(self) -> bool:
        """Test TypeScript import organization tools."""
        self.log("Testing TypeScript tools...")

        # Check if package.json exists
        if not (self.root_path / "package.json").exists():
            self.log("⚠️ No package.json found, skipping TypeScript tests", "warning")
            return True

        tests = [
            ("npm_install", "Install TypeScript dependencies", ["npm", "install"]),
            ("eslint_check", "Run ESLint", ["npm", "run", "lint"]),
            ("typescript_check", "Check TypeScript compilation", ["npm", "run", "type-check"]),
            ("prettier_check", "Check Prettier formatting", ["npm", "run", "format:check"]),
        ]

        results = []
        for name, desc, cmd in tests:
            result = self.run_test(name, desc, cmd)
            results.append(result["success"])

        return all(results)

    def test_pre_commit_hooks(self) -> bool:
        """Test pre-commit hook configuration."""
        self.log("Testing pre-commit hooks...")

        tests = [
            (
                "pre_commit_validate",
                "Validate pre-commit configuration",
                ["pre-commit", "validate-config"],
            ),
            (
                "pre_commit_install",
                "Install pre-commit hooks",
                ["pre-commit", "install", "--install-hooks"],
            ),
        ]

        results = []
        for name, desc, cmd in tests:
            result = self.run_test(name, desc, cmd, timeout=120)
            results.append(result["success"])

        return all(results)

    def test_configuration_files(self) -> bool:
        """Test configuration file validity."""
        self.log("Testing configuration files...")

        config_files = [
            "pyproject.toml",
            ".pre-commit-config.yaml",
            ".eslintrc.json",
            ".prettierrc.json",
            "tsconfig.json",
            "package.json",
        ]

        all_valid = True
        for config_file in config_files:
            file_path = self.root_path / config_file
            if file_path.exists():
                try:
                    if config_file.endswith(".json"):
                        with open(file_path, encoding="utf-8") as f:
                            json.load(f)
                    elif config_file.endswith(".yaml"):
                        import yaml

                        with open(file_path, encoding="utf-8") as f:
                            yaml.safe_load(f)
                    elif config_file.endswith(".toml"):
                        try:
                            import tomli

                            with open(file_path, "rb") as f:
                                tomli.load(f)
                        except ImportError:
                            import toml

                            with open(file_path, encoding="utf-8") as f:
                                toml.load(f)

                    self.log(f"✅ {config_file} is valid", "success")
                except Exception as e:
                    self.log(f"❌ {config_file} is invalid: {e}", "error")
                    all_valid = False
            else:
                self.log(f"⚠️ {config_file} not found", "warning")

        return all_valid

    def test_monitoring_scripts(self) -> bool:
        """Test monitoring and alerting scripts."""
        self.log("Testing monitoring scripts...")

        monitoring_scripts = [
            ("dependency_monitor.py", "Dependency monitoring system"),
            ("import_alerts.py", "Import alert system"),
        ]

        results = []
        for script, desc in monitoring_scripts:
            script_path = self.root_path / "scripts" / script
            if script_path.exists():
                result = self.run_test(
                    f"test_{script}",
                    f"Test {desc}",
                    [sys.executable, str(script_path), "--help"],
                    expected_exit_code=0,
                )
                results.append(result["success"])
            else:
                self.log(f"⚠️ {script} not found", "warning")
                results.append(False)

        return all(results)

    def run_all_tests(self) -> dict:
        """Run complete test suite."""
        self.log("🚀 Starting DinoAir Import Organization Automation Test Suite")
        start_time = time.time()

        test_categories = [
            ("Configuration Files", self.test_configuration_files),
            ("Circular Dependency Detection", self.test_circular_dependency_detection),
            ("Python Import Organization", self.test_python_import_organization),
            ("TypeScript Tools", self.test_typescript_tools),
            ("Pre-commit Hooks", self.test_pre_commit_hooks),
            ("Monitoring Scripts", self.test_monitoring_scripts),
        ]

        category_results = {}

        for category_name, test_func in test_categories:
            self.log(f"\n🔍 Testing {category_name}...")
            try:
                category_results[category_name] = test_func()
            except Exception as e:
                self.log(f"❌ {category_name} test failed with exception: {e}", "error")
                category_results[category_name] = False

        total_duration = time.time() - start_time

        # Calculate summary statistics
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - successful_tests

        successful_categories = sum(1 for success in category_results.values() if success)
        total_categories = len(category_results)

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_duration": round(total_duration, 2),
            "categories": {
                "total": total_categories,
                "successful": successful_categories,
                "failed": total_categories - successful_categories,
                "results": category_results,
            },
            "tests": {
                "total": total_tests,
                "successful": successful_tests,
                "failed": failed_tests,
                "success_rate": (
                    round(successful_tests / total_tests * 100, 1) if total_tests > 0 else 0
                ),
                "details": self.test_results,
            },
            "overall_success": all(category_results.values()) and failed_tests == 0,
        }

        # Print summary
        self.log("\n📊 Test Suite Summary:")
        self.log(f"   Categories: {successful_categories}/{total_categories} passed")
        self.log(
            f"   Tests: {successful_tests}/{total_tests} passed ({summary['tests']['success_rate']}%)"
        )
        self.log(f"   Duration: {total_duration:.2f} seconds")

        if summary["overall_success"]:
            self.log(
                "🎉 All tests passed! Import organization automation is working correctly.",
                "success",
            )
        else:
            self.log("❌ Some tests failed. Please review the results and fix issues.", "error")

        return summary


def main():
    """Main entry point for automation testing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test DinoAir import organization automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--report", type=Path, help="Generate JSON test report")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path(),
        help="Path to DinoAir repository (default: current directory)",
    )

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: Path {args.path} does not exist", file=sys.stderr)
        sys.exit(1)

    tester = AutomationTester(args.path, verbose=args.verbose)
    summary = tester.run_all_tests()

    # Generate report if requested
    if args.report:
        try:
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, default=str)
            print(f"📄 Test report saved to {args.report}")
        except Exception as e:
            print(f"❌ Failed to save report: {e}", file=sys.stderr)

    # Exit with appropriate code
    sys.exit(0 if summary["overall_success"] else 1)


if __name__ == "__main__":
    main()
