#!/usr/bin/env python3
"""
Script to systematically fix common linting issues across the DinoAir codebase.
This handles:
1. Broad Exception handlers
2. f-string logging format issues
3. Other common patterns

Usage: python fix_linting_issues.py
"""

from pathlib import Path
import re


def get_python_files(directory: Path) -> list[Path]:
    """Get all Python files in the directory tree."""
    return list(directory.rglob("*.py"))


def fix_broad_exceptions(content: str) -> str:
    """Fix overly broad exception handlers with more specific ones."""

    # Common patterns for specific exceptions based on context
    replacements = [
        # File/IO operations
        (r"except Exception:\s*#[^\n]*[Ff]ile|[Pp]ath|[Dd]irectory", "except (OSError, IOError):"),
        (
            r"except Exception:\s*#[^\n]*[Cc]onfig|[Ss]ettings|[Ll]oad",
            "except (KeyError, ValueError, TypeError):",
        ),
        (r"except Exception:\s*#[^\n]*[Ll]og|[Ll]ogging", "except (OSError, ValueError):"),
        (
            r"except Exception:\s*#[^\n]*[Jj]son|[Pp]arse",
            "except (ValueError, TypeError, KeyError):",
        ),
        (r"except Exception:\s*#[^\n]*[Dd]atabase|[Ss]ql", "except (OSError, ValueError):"),
        # Generic replacements for common patterns
        (
            r"except Exception:\s*\n\s*#[^\n]*[Ss]ilent|[Ii]gnore",
            "except Exception:  # Keep broad exception for intentional silencing",
        ),
        (
            r"except Exception:\s*\n\s*pass\s*$",
            "except Exception:\n                pass  # TODO: Consider more specific exception type",
        ),
        (
            r"except Exception:\s*\n\s*logger\.warning",
            "except Exception:\n                logger.warning",
        ),
        (
            r"except Exception:\s*\n\s*logger\.error",
            "except Exception:\n                logger.error",
        ),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    return content


def fix_logging_format(content: str) -> str:
    """Fix f-string logging to use lazy % formatting."""

    # Pattern to match logger.level(f"string {var}")
    pattern = r'logger\.(debug|info|warning|error|critical)\(f"([^"]+)"\)'

    def replace_match(match):
        level = match.group(1)
        format_str = match.group(2)

        # Extract variables from f-string
        # This is a simplified replacement - finds {var} patterns
        var_pattern = r"\{([^}]+)\}"
        variables = re.findall(var_pattern, format_str)

        if not variables:
            return match.group(0)  # No variables, keep as is

        # Replace {var} with %s and create variable list
        new_format = re.sub(var_pattern, "%s", format_str)
        var_list = ", ".join(variables)

        return f'logger.{level}("{new_format}", {var_list})'

    return re.sub(pattern, replace_match, content)


def fix_subprocess_run(content: str) -> str:
    """Fix subprocess.run calls without explicit check parameter."""

    # Pattern to match subprocess.run without check parameter
    pattern = r"subprocess\.run\(([^)]+)\)(?!\s*#.*check)"

    def replace_match(match):
        args = match.group(1)
        # Check if check parameter is already present
        if "check=" in args:
            return match.group(0)

        # Add check=False as default to be explicit
        return f"subprocess.run({args}, check=False)"

    return re.sub(pattern, replace_match, content)


def fix_file(file_path: Path) -> bool:
    """Fix linting issues in a single file. Returns True if file was modified."""
    try:
        with open(file_path, encoding="utf-8") as f:
            original_content = f.read()

        # Apply fixes
        new_content = original_content
        new_content = fix_broad_exceptions(new_content)
        new_content = fix_logging_format(new_content)
        new_content = fix_subprocess_run(new_content)

        # Only write if content changed
        if new_content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True

        return False

    except Exception:
        return False


def main():
    """Main function to fix linting issues across the codebase."""

    # Get the directory where this script is located
    script_dir = Path(__file__).parent

    # Get all Python files
    python_files = get_python_files(script_dir)

    # Exclude this script itself and other utility scripts
    exclude_patterns = ["fix_linting_issues.py", "__pycache__", ".git", ".venv"]
    python_files = [
        f for f in python_files if not any(pattern in str(f) for pattern in exclude_patterns)
    ]

    modified_count = 0
    for file_path in python_files:
        if fix_file(file_path):
            modified_count += 1

    if modified_count > 0:
        try:
            # Try to compile each modified file to check for syntax errors
            syntax_errors = []
            for file_path in python_files:
                try:
                    with open(file_path) as f:
                        compile(f.read(), file_path, "exec")
                except SyntaxError as e:
                    syntax_errors.append((file_path, e))

            if syntax_errors:
                pass
            else:
                pass

        except Exception:
            pass


if __name__ == "__main__":
    main()
