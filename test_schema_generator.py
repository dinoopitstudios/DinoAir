"""
Simple test for the tool schema generator
"""

import sys
from pathlib import Path

# Add the project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from api.services.tool_schema_generator import generate_tools_schemas
    from tools.basic_tools import AVAILABLE_TOOLS

    # Test with just one tool first
    test_tools = {"add_two_numbers": AVAILABLE_TOOLS["add_two_numbers"]}
    schemas = generate_tools_schemas(test_tools)

except Exception:
    import traceback

    traceback.print_exc()
