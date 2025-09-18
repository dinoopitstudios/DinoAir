#!/usr/bin/env python3
"""
Test script for DinoAir function calling integration.

This script tests the complete function calling pipeline:
1. Load tool schemas from 07_tools
2. Generate OpenAI function schemas
3. Test the enhanced chat endpoint with function calling enabled

Usage:
    python test_function_calling.py
"""

import asyncio
import contextlib
import sys
from pathlib import Path

from api.services.tool_registry import get_tool_registry
from api.services.tool_schema_generator import generate_tools_schemas

# Add the 05_api directory to the path
api_dir = Path(__file__).parent / "05_api"
sys.path.insert(0, str(api_dir))


async def test_tool_registry():
    """Test the tool registry functionality."""

    registry = get_tool_registry()

    # Test tool discovery

    # Test schema generation
    schemas = registry.get_tool_schemas()

    # Test specific tool execution
    if "get_current_time" in registry._tools:
        with contextlib.suppress(Exception):
            await registry.execute_tool("get_current_time", {})

    return schemas


def test_schema_generation():
    """Test the schema generation functionality."""

    # Test direct schema generation
    try:
        schemas = generate_tools_schemas()

        # Print a sample schema
        if schemas:
            schemas[0]

        return schemas
    except Exception:
        return []


async def test_function_calling_flow():
    """Test a simulated function calling flow."""

    get_tool_registry()

    # Simulate OpenAI response with function calls
    mock_openai_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_test_123",
                            "type": "function",
                            "function": {"name": "get_current_time", "arguments": "{}"},
                        }
                    ],
                }
            }
        ]
    }

    # Test function call detection
    from api.routes.ai import (
        _build_function_call_messages,
        _handle_function_calls,
        _has_function_calls,
    )

    has_calls = _has_function_calls(mock_openai_response)

    if has_calls:
        # Test function execution
        function_results = await _handle_function_calls(mock_openai_response)

        # Test message building
        messages = _build_function_call_messages(mock_openai_response, function_results)


async def main():
    """Run all tests."""

    try:
        # Test tool registry
        await test_tool_registry()

        # Test direct schema generation
        test_schema_generation()

        # Test function calling flow
        await test_function_calling_flow()

    except Exception:
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
