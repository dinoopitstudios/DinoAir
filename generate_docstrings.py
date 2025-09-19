#!/usr/bin/env python3
"""
Docstring generation script for DinoAir project.

This script uses the autodocstring package to automatically generate
missing docstrings for functions, classes, and modules across the codebase.
"""

import ast
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

try:
    from autodocstring.autodocstring import generate_all_docstrings, generate_docstring
except ImportError:
    print("autodocstring package not found. Please install it first:")
    print("pip install autodocstring")
    exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def find_files_missing_docstrings(directories: List[str]) -> List[Dict[str, Any]]:
    """
    Find Python files with missing docstrings in specified directories.

    Args:
        directories: List of directory paths to scan

    Returns:
        List of dictionaries containing file info and missing docstring details
    """
    missing_docstrings = []

    for directory in directories:
        if not os.path.exists(directory):
            logger.warning(f"Directory {directory} does not exist, skipping...")
            continue

        for py_file in Path(directory).rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)

                # Check module-level docstring
                has_module_docstring = (
                    (
                        isinstance(tree.body[0], ast.Expr)
                        and isinstance(tree.body[0].value, ast.Constant)
                        and isinstance(tree.body[0].value.value, str)
                    )
                    if tree.body
                    else False
                )

                # Check classes and functions
                classes_without_docs = []
                functions_without_docs = []

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        has_docstring = ast.get_docstring(node) is not None
                        if not has_docstring:
                            classes_without_docs.append(node.name)

                    elif isinstance(node, ast.FunctionDef):
                        has_docstring = ast.get_docstring(node) is not None
                        if not has_docstring and not node.name.startswith("_"):
                            functions_without_docs.append(node.name)

                if not has_module_docstring or classes_without_docs or functions_without_docs:
                    missing_docstrings.append(
                        {
                            "file": str(py_file.relative_to(Path("."))),
                            "absolute_path": str(py_file),
                            "module_docstring": has_module_docstring,
                            "classes_without_docs": classes_without_docs,
                            "functions_without_docs": functions_without_docs,
                        }
                    )

            except Exception as e:
                logger.error(f"Error processing {py_file}: {e}")
                continue

    return missing_docstrings


def test_autodocstring_on_sample() -> bool:
    """
    Test autodocstring generation on a sample function.

    Returns:
        True if test successful, False otherwise
    """
    try:
        # Test sample code
        sample_code = """
def calculate_sum(a: int, b: int) -> int:
    return a + b

class Calculator:
    def multiply(self, x: float, y: float) -> float:
        return x * y
"""

        logger.info("Testing autodocstring generation...")

        # Try to generate docstring for the sample
        result = generate_docstring(sample_code)
        logger.info(f"Generated docstring test result: {result}")
        return True

    except Exception as e:
        logger.error(f"Error testing autodocstring: {e}")
        return False


def generate_docstrings_for_file(file_path: str) -> bool:
    """
    Generate docstrings for a specific Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Processing file: {file_path}")

        # Read original file
        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        # Generate docstrings for the entire file
        updated_content = generate_all_docstrings(original_content)

        # Write updated content if it's different
        if updated_content and updated_content != original_content:
            # Create backup
            backup_path = f"{file_path}.backup"
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(original_content)

            # Write updated file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated_content)

            logger.info(f"Updated {file_path} with generated docstrings (backup: {backup_path})")
            return True

        logger.info(f"No changes needed for {file_path}")
        return False

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to orchestrate docstring generation."""

    # Directories to scan for missing docstrings
    target_directories = ["utils", "models", "database", "tools", "API_files"]

    logger.info("Starting docstring generation for DinoAir project...")

    # Test autodocstring functionality first
    if not test_autodocstring_on_sample():
        logger.error("Autodocstring test failed. Cannot proceed.")
        return

    # Find files with missing docstrings
    logger.info(f"Scanning directories: {target_directories}")
    missing_files = find_files_missing_docstrings(target_directories)

    logger.info(f"Found {len(missing_files)} files with missing docstrings")

    # Display summary
    for file_info in missing_files[:10]:  # Show first 10
        print(
            f"- {file_info['file']}: "
            f"Module: {'✓' if file_info['module_docstring'] else '✗'}, "
            f"Classes: {len(file_info['classes_without_docs'])}, "
            f"Functions: {len(file_info['functions_without_docs'])}"
        )

    if len(missing_files) > 10:
        print(f"... and {len(missing_files) - 10} more files")

    # Ask for confirmation
    response = input(f"\nProcess {len(missing_files)} files with autodocstring generation? (y/N): ")
    if response.lower() != "y":
        logger.info("Operation cancelled by user")
        return

    # Process files
    success_count = 0
    for file_info in missing_files:
        if generate_docstrings_for_file(file_info["absolute_path"]):
            success_count += 1

    logger.info(f"Successfully processed {success_count}/{len(missing_files)} files")


if __name__ == "__main__":
    main()
