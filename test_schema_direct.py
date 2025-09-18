"""Quick test of schema generation without importing from api/services"""

from collections.abc import Callable
import inspect
import re
from typing import Any


def convert_python_type_to_json_schema(python_type: str) -> str:
    """Convert Python type strings to JSON Schema types."""
    type_mapping = {
        "str": "string",
        "string": "string",
        "int": "integer",
        "integer": "integer",
        "float": "number",
        "number": "number",
        "bool": "boolean",
        "boolean": "boolean",
        "list": "array",
        "array": "array",
        "dict": "object",
        "object": "object",
        "any": "string",
        "optional": "string",
    }

    python_type = python_type.lower().strip()
    if "optional" in python_type:
        return "string"
    if python_type.startswith("list[") or "list" in python_type:
        return "array"
    if python_type.startswith("dict[") or "dict" in python_type:
        return "object"

    return type_mapping.get(python_type, "string")


def extract_docstring_info(func: Callable[..., Any]) -> dict[str, Any]:
    """Extract function information from docstring."""
    doc = inspect.getdoc(func)
    if not doc:
        return {"description": f"Function {func.__name__}", "parameters": {}}

    lines = doc.strip().split("\n")
    description_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith(("Args:", "Returns:", "Example:", "Raises:")):
            description_lines.append(stripped)
        else:
            break

    description = " ".join(description_lines)
    parameters = {}
    in_args_section = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("Args:"):
            in_args_section = True
            continue
        if stripped.startswith(("Returns:", "Example:", "Raises:")):
            in_args_section = False
            continue

        if in_args_section and stripped:
            if param_match := re.match(r"^(\w+)\s*\(([^)]+)\):\s*(.+)$", stripped):
                param_name, param_type, param_desc = param_match.groups()
                parameters[param_name] = {
                    "type": convert_python_type_to_json_schema(param_type.strip()),
                    "description": param_desc.strip(),
                }

    return {"description": description, "parameters": parameters}


def generate_openai_function_schema(func: Callable[..., Any]) -> dict[str, Any]:
    """Generate OpenAI function calling schema from a Python function."""
    doc_info = extract_docstring_info(func)

    # Get basic signature info
    try:
        sig = inspect.signature(func)
        required_params = []
        all_params = {}

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_info = {"type": "string", "description": f"Parameter {param_name}"}

            if param.default == inspect.Parameter.empty:
                required_params.append(param_name)

            all_params[param_name] = param_info
    except Exception:
        required_params = []
        all_params = {}

    # Merge with docstring parameters
    for param_name, param_info in doc_info["parameters"].items():
        if param_name in all_params:
            all_params[param_name].update(param_info)
        else:
            all_params[param_name] = param_info
            required_params.append(param_name)

    return {
        "name": func.__name__,
        "description": doc_info["description"],
        "parameters": {"type": "object", "properties": all_params, "required": required_params},
    }


# Now test with the actual tools
import contextlib
from pathlib import Path
import sys


project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    # Import the tools module directly
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "basic_tools", project_root / "07_tools" / "basic_tools.py"
    )
    basic_tools = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(basic_tools)
    AVAILABLE_TOOLS = basic_tools.AVAILABLE_TOOLS

    # Test with one tool
    test_func = AVAILABLE_TOOLS["add_two_numbers"]
    schema = generate_openai_function_schema(test_func)

    # Test with a few more
    schemas = []
    for _name, func in list(AVAILABLE_TOOLS.items())[:5]:
        with contextlib.suppress(Exception):
            schemas.append(generate_openai_function_schema(func))


except Exception:
    import traceback

    traceback.print_exc()
