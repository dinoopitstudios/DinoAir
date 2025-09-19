#!/usr/bin/env python3
"""
Manual docstring generation script for DinoAir project.

This script analyzes Python files and adds basic docstrings following Google style
for functions, classes, and modules that are missing documentation.
"""

import ast
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

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
                            classes_without_docs.append(
                                {"name": node.name, "lineno": node.lineno, "type": "class"}
                            )

                    elif isinstance(node, ast.FunctionDef):
                        has_docstring = ast.get_docstring(node) is not None
                        if not has_docstring and not node.name.startswith("_"):
                            # Extract function signature info
                            args = []
                            for arg in node.args.args:
                                args.append(arg.arg)

                            functions_without_docs.append(
                                {
                                    "name": node.name,
                                    "lineno": node.lineno,
                                    "type": "function",
                                    "args": args,
                                    "returns": node.returns is not None,
                                }
                            )

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


def generate_function_docstring(func_info: Dict[str, Any]) -> str:
    """
    Generate a basic docstring for a function based on its signature.

    Args:
        func_info: Dictionary containing function information

    Returns:
        Generated docstring text
    """
    name = func_info["name"]
    args = func_info.get("args", [])
    has_return = func_info.get("returns", False)

    # Generate a basic description based on function name
    description = generate_description_from_name(name)

    docstring_parts = [f'    """{description}']

    # Add Args section if function has parameters
    if args and len(args) > 0:
        # Filter out 'self' and 'cls'
        filtered_args = [arg for arg in args if arg not in ["self", "cls"]]
        if filtered_args:
            docstring_parts.append("    ")
            docstring_parts.append("    Args:")
            for arg in filtered_args:
                docstring_parts.append(f"        {arg}: TODO: Add description")

    # Add Returns section if function has return annotation
    if has_return:
        if args and len([arg for arg in args if arg not in ["self", "cls"]]) > 0:
            docstring_parts.append("        ")
        else:
            docstring_parts.append("    ")
        docstring_parts.append("    Returns:")
        docstring_parts.append("        TODO: Add return description")

    docstring_parts.append('    """')

    return "\n".join(docstring_parts)


def generate_class_docstring(class_info: Dict[str, Any]) -> str:
    """
    Generate a basic docstring for a class.

    Args:
        class_info: Dictionary containing class information

    Returns:
        Generated docstring text
    """
    name = class_info["name"]
    description = generate_description_from_name(name)

    return f'    """{description}"""'


def generate_description_from_name(name: str) -> str:
    """
    Generate a description based on a function or class name.

    Args:
        name: The function or class name

    Returns:
        Generated description
    """
    # Convert camelCase and snake_case to readable text
    # Split on capital letters and underscores
    words = re.sub(r"([A-Z])", r" \1", name).replace("_", " ").strip().split()

    # Common patterns
    if name.startswith("get_"):
        return f"Get {' '.join(words[1:]).lower()}."
    elif name.startswith("set_"):
        return f"Set {' '.join(words[1:]).lower()}."
    elif name.startswith("create_"):
        return f"Create {' '.join(words[1:]).lower()}."
    elif name.startswith("delete_"):
        return f"Delete {' '.join(words[1:]).lower()}."
    elif name.startswith("update_"):
        return f"Update {' '.join(words[1:]).lower()}."
    elif name.startswith("is_"):
        return f"Check if {' '.join(words[1:]).lower()}."
    elif name.startswith("has_"):
        return f"Check if has {' '.join(words[1:]).lower()}."
    elif name.startswith("can_"):
        return f"Check if can {' '.join(words[1:]).lower()}."
    elif name.startswith("should_"):
        return f"Check if should {' '.join(words[1:]).lower()}."
    elif name.startswith("load_"):
        return f"Load {' '.join(words[1:]).lower()}."
    elif name.startswith("save_"):
        return f"Save {' '.join(words[1:]).lower()}."
    elif name.startswith("parse_"):
        return f"Parse {' '.join(words[1:]).lower()}."
    elif name.startswith("validate_"):
        return f"Validate {' '.join(words[1:]).lower()}."
    elif name.startswith("process_"):
        return f"Process {' '.join(words[1:]).lower()}."
    elif name.startswith("handle_"):
        return f"Handle {' '.join(words[1:]).lower()}."
    else:
        # Capitalize first word and add period
        words = [w.lower() for w in words]
        if words:
            words[0] = words[0].capitalize()
            return f"{' '.join(words)}."
        else:
            return "TODO: Add description."


def add_docstrings_to_file(file_path: str, file_info: Dict[str, Any]) -> bool:
    """
    Add docstrings to functions and classes in a specific file.

    Args:
        file_path: Path to the Python file
        file_info: Dictionary containing missing docstring information

    Returns:
        True if file was modified, False otherwise
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        modified = False

        # Sort items by line number in descending order to avoid line number changes
        all_items = []

        for func_info in file_info["functions_without_docs"]:
            all_items.append(("function", func_info))

        for class_info in file_info["classes_without_docs"]:
            all_items.append(("class", class_info))

        # Sort by line number (descending) to process from bottom to top
        all_items.sort(key=lambda x: x[1]["lineno"], reverse=True)

        for item_type, item_info in all_items:
            line_num = item_info["lineno"]

            # Find the line with the function/class definition
            if line_num <= len(lines):
                definition_line = lines[line_num - 1]  # Convert to 0-based index

                # Get indentation level
                indent = len(definition_line) - len(definition_line.lstrip())

                # Generate appropriate docstring
                if item_type == "function":
                    docstring = generate_function_docstring(item_info)
                else:  # class
                    docstring = generate_class_docstring(item_info)

                # Insert docstring after the definition line
                docstring_lines = [line + "\n" for line in docstring.split("\n")]
                lines[line_num:line_num] = docstring_lines
                modified = True

                logger.info(
                    f"Added docstring to {item_type} '{item_info['name']}' at line {line_num}"
                )

        # Write back if modified
        if modified:
            # Create backup
            backup_path = f"{file_path}.backup"
            with open(backup_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            # Read original content for backup
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(original_content)

            # Write updated file
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            logger.info(f"Updated {file_path} with generated docstrings (backup: {backup_path})")

        return modified

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to orchestrate docstring generation."""

    # Directories to scan for missing docstrings
    target_directories = ["utils", "models", "database", "tools"]

    logger.info("Starting manual docstring generation for DinoAir project...")

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
    print(f"\nWould you like to add basic docstrings to {len(missing_files)} files?")
    print("This will create .backup files and add Google-style docstrings.")
    response = input("Continue? (y/N): ")
    if response.lower() != "y":
        logger.info("Operation cancelled by user")
        return

    # Process files
    success_count = 0
    total_functions = 0
    total_classes = 0

    for file_info in missing_files:
        total_functions += len(file_info["functions_without_docs"])
        total_classes += len(file_info["classes_without_docs"])

        if add_docstrings_to_file(file_info["absolute_path"], file_info):
            success_count += 1

    logger.info(f"Successfully processed {success_count}/{len(missing_files)} files")
    logger.info(f"Added docstrings to {total_functions} functions and {total_classes} classes")


if __name__ == "__main__":
    main()
