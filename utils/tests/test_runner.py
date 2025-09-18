"""
Test runner and configuration for the utils folder test suite.
Provides comprehensive test execution with coverage reporting and parallel execution.
"""

from pathlib import Path
import subprocess
import sys
import time
from typing import Any


# Add utils directory to Python path for imports
utils_dir = Path(__file__).parent.parent
sys.path.insert(0, str(utils_dir))


class TestRunner:
    """Comprehensive test runner for utils folder."""

    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.utils_dir = self.test_dir.parent
        self.results: dict[str, Any] = {}

    def discover_test_files(self) -> list[Path]:
        """Discover all test files in the test directory."""
        test_files = list(self.test_dir.glob("test_*.py"))
        # Exclude this runner file
        test_files = [f for f in test_files if f.name != "test_runner.py"]
        return sorted(test_files)

    def run_pytest_command(
        self,
        extra_args: list[str] | None = None,
        use_coverage: bool = True,
        stop_on_failure: bool = False,
    ) -> dict[str, Any]:
        """Run pytest with comprehensive options."""
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(self.test_dir),
            "-v",  # Verbose output
            "--tb=short",  # Shorter traceback format
            "--durations=10",  # Show 10 slowest tests
            "--strict-markers",  # Strict marker checking
        ]
        if stop_on_failure:
            cmd.append("-x")

        # Add coverage if enabled and available
        if use_coverage:
            try:
                import coverage  # noqa: F401

                cmd.extend(
                    [
                        "--cov=" + str(self.utils_dir),
                        "--cov-report=term-missing",
                        "--cov-report=html:htmlcov",
                        "--cov-fail-under=80",
                    ]
                )
            except ImportError:
                pass
        if extra_args:
            cmd.extend(extra_args)

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=self.test_dir,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,  # 5 minute timeout
            )

            end_time = time.time()
            duration = end_time - start_time

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration,
                "command": cmd,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Test execution timed out after 300 seconds",
                "duration": 300,
                "command": cmd,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "pytest not found. Install with: pip install pytest",
                "duration": 0,
                "command": cmd,
            }

    def run_individual_test_file(self, test_file: Path) -> dict[str, Any]:
        """Run a single test file."""
        cmd = [sys.executable, "-m", "pytest", str(test_file), "-v"]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.test_dir,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,  # 1 minute per file
            )

            return {
                "file": test_file.name,
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "output": result.stdout,
                "errors": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {
                "file": test_file.name,
                "success": False,
                "returncode": -1,
                "output": "",
                "errors": f"Test file {test_file.name} timed out",
            }
        except Exception as e:
            return {
                "file": test_file.name,
                "success": False,
                "returncode": -1,
                "output": "",
                "errors": f"Error running {test_file.name}: {str(e)}",
            }

    def validate_test_structure(self) -> dict[str, Any]:
        """Validate test file structure and imports."""
        test_files = self.discover_test_files()
        results = {}

        for test_file in test_files:
            try:
                # Try to import the test module

                # Basic validation - check file can be read
                with open(test_file, encoding="utf-8") as f:
                    content = f.read()

                validation = {
                    "can_read": True,
                    "has_imports": "import" in content,
                    "has_test_classes": "class Test" in content,
                    "has_pytest_imports": "pytest" in content,
                    "file_size": len(content),
                    "line_count": len(content.splitlines()),
                }

                results[test_file.name] = validation

            except Exception as e:
                results[test_file.name] = {"can_read": False, "error": str(e)}

        return results

    def generate_test_report(self, pytest_result: dict[str, Any]) -> str:
        """Generate a comprehensive test report."""
        test_files = self.discover_test_files()
        validation_results = self.validate_test_structure()

        report = []
        report.append("=" * 80)
        report.append("DINOAIR UTILS TEST SUITE REPORT")
        report.append("=" * 80)
        report.append("")

        # Overall summary
        report.append("OVERALL RESULTS:")
        report.append(f"  Status: {'PASSED' if pytest_result['success'] else 'FAILED'}")
        report.append(f"  Duration: {pytest_result['duration']:.2f} seconds")
        report.append(f"  Return Code: {pytest_result['returncode']}")
        report.append("")

        # Test file discovery
        report.append("TEST DISCOVERY:")
        report.append(f"  Test files found: {len(test_files)}")
        for test_file in test_files:
            validation = validation_results.get(test_file.name, {})
            status = "✓" if validation.get("can_read", False) else "✗"
            lines = validation.get("line_count", 0)
            report.append(f"    {status} {test_file.name} ({lines} lines)")
        report.append("")

        # Test structure validation
        report.append("TEST STRUCTURE VALIDATION:")
        structure_issues = []
        for filename, validation in validation_results.items():
            if not validation.get("can_read", False):
                structure_issues.append(f"  ✗ {filename}: Cannot read file")
            elif not validation.get("has_test_classes", False):
                structure_issues.append(f"  ⚠ {filename}: No test classes found")
            elif not validation.get("has_imports", False):
                structure_issues.append(f"  ⚠ {filename}: No imports found")

        if structure_issues:
            report.extend(structure_issues)
        else:
            report.append("  ✓ All test files have valid structure")
        report.append("")

        # Coverage information
        if "cov" in pytest_result.get("stdout", ""):
            report.append("COVERAGE INFORMATION:")
            # Extract coverage info from stdout if available
            lines = pytest_result["stdout"].split("\n")
            coverage_lines = [line for line in lines if "%" in line and "cov" in line.lower()]
            if coverage_lines:
                report.extend(f"  {line}" for line in coverage_lines[-5:])  # Last 5 coverage lines
            report.append("")

        # Execution details
        if pytest_result["stdout"]:
            report.append("PYTEST OUTPUT (last 20 lines):")
            output_lines = pytest_result["stdout"].split("\n")
            for line in output_lines[-20:]:
                if line.strip():
                    report.append(f"  {line}")
            report.append("")

        if pytest_result["stderr"]:
            report.append("ERRORS/WARNINGS:")
            error_lines = pytest_result["stderr"].split("\n")
            for line in error_lines[:10]:  # First 10 error lines
                if line.strip():
                    report.append(f"  {line}")
            report.append("")

        # Recommendations
        report.append("RECOMMENDATIONS:")
        if not pytest_result["success"]:
            report.append("  • Fix failing tests before proceeding")
            report.append("  • Check error output above for specific issues")

        if len(test_files) < 10:
            report.append(f"  • Consider adding more test files (currently {len(test_files)})")

        missing_modules = self.identify_missing_test_modules()
        if missing_modules:
            report.append("  • Missing test files for these modules:")
            for module in missing_modules[:5]:  # Show first 5
                report.append(f"    - {module}")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)

    def identify_missing_test_modules(self) -> list[str]:
        """Identify utility modules without corresponding test files."""
        utils_files = list(self.utils_dir.glob("*.py"))
        utils_modules = {f.stem for f in utils_files if not f.name.startswith("_")}

        test_files = self.discover_test_files()
        tested_modules = {f.stem.replace("test_", "") for f in test_files}

        missing = utils_modules - tested_modules
        # Remove special files
        missing.discard("__init__")
        missing.discard("run_tests")

        return sorted(missing)

    def run_quick_validation(self) -> bool:
        """Run quick validation checks before full test suite."""

        # Check if test files can be imported
        self.discover_test_files()
        validation_results = self.validate_test_structure()

        issues = []
        for filename, validation in validation_results.items():
            if not validation.get("can_read", False):
                issues.append(f"Cannot read {filename}")

        if issues:
            return False

        return True

    def run_all_tests(
        self, coverage: bool = True, parallel: bool = False, stop_on_failure: bool = False
    ) -> dict[str, Any]:
        """Run all tests with specified options."""

        # Quick validation first
        if not self.run_quick_validation():
            return {"success": False, "error": "Quick validation failed", "duration": 0}

        # Prepare pytest arguments
        extra_args = []

        if parallel:
            extra_args.extend(["-n", "auto"])  # Requires pytest-xdist

        if not stop_on_failure:
            extra_args.remove("-x") if "-x" in extra_args else None

        # Run the tests
        result = self.run_pytest_command(extra_args)

        # Generate report
        report = self.generate_test_report(result)

        # Save report to file
        report_file = self.test_dir / "test_report.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        return result


def main():
    """Main entry point for test runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Run DinoAir Utils test suite")
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage reporting")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument(
        "--continue-on-failure", action="store_true", help="Continue on test failures"
    )
    parser.add_argument("--quick", action="store_true", help="Run only quick validation")
    parser.add_argument("--file", type=str, help="Run specific test file")

    args = parser.parse_args()

    runner = TestRunner()

    if args.quick:
        # Quick validation only
        success = runner.run_quick_validation()
        sys.exit(0 if success else 1)

    elif args.file:
        # Run specific test file
        test_file = runner.test_dir / args.file
        if not test_file.exists():
            sys.exit(1)

        result = runner.run_individual_test_file(test_file)

        sys.exit(0 if result["success"] else 1)

    else:
        # Run full test suite
        result = runner.run_all_tests(
            coverage=not args.no_coverage,
            parallel=args.parallel,
            stop_on_failure=not args.continue_on_failure,
        )

        sys.exit(0 if result["success"] else 1)


def run_tests_programmatically(coverage: bool = True, parallel: bool = False) -> dict[str, Any]:
    """Run tests programmatically and return results."""
    runner = TestRunner()
    return runner.run_all_tests(coverage=coverage, parallel=parallel)


def validate_test_setup() -> bool:
    """Validate that test setup is correct."""
    runner = TestRunner()
    return runner.run_quick_validation()


def get_test_coverage_report() -> str:
    """Get test coverage report if available."""
    runner = TestRunner()

    # Check if coverage report exists
    coverage_dir = runner.test_dir / "htmlcov"
    if coverage_dir.exists():
        index_file = coverage_dir / "index.html"
        if index_file.exists():
            return f"Coverage report available at: {index_file}"

    return "No coverage report found. Run tests with coverage enabled."


def list_test_files() -> list[str]:
    """List all available test files."""
    runner = TestRunner()
    test_files = runner.discover_test_files()
    return [f.name for f in test_files]


def get_missing_test_modules() -> list[str]:
    """Get list of modules missing test coverage."""
    runner = TestRunner()
    return runner.identify_missing_test_modules()


if __name__ == "__main__":
    main()
