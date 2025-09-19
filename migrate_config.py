#!/usr/bin/env python3
"""
Configuration Migration Script for DinoAir
Migrates from old configuration format to new versioned system
"""

import contextlib
import shutil
import sys
from pathlib import Path


def main():
    """Main migration function"""

    base_dir = Path(__file__).parent

    # Check if new system is already in place
    schema_path = base_dir / "config" / "schema.json"
    if schema_path.exists():
        # Test the new system
        try:
            from config.versioned_config import get_config

            config = get_config()

            # Show some sample values
            sample_keys = [
                "app.name",
                "app.version",
                "database.connection_timeout",
                "ai.max_tokens",
            ]
            for key in sample_keys:
                config.get_with_source(key)

        except Exception:
            return False
    else:
        return False

    # Check for .env file
    env_path = base_dir / ".env"
    env_example_path = base_dir / ".env.example"

    if not env_path.exists() and env_example_path.exists():
        with contextlib.suppress(Exception):
            shutil.copy(env_example_path, env_path)

    # Check for jsonschema
    with contextlib.suppress(ImportError):
        pass

    # Provide usage examples

    return True


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
