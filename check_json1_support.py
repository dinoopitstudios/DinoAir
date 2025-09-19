#!/usr/bin/env python3
"""
Check if SQLite installation supports JSON1 extension functions.
"""

import contextlib
import os
import sqlite3
import sys
import tempfile


def check_json1_support():
    """Check if SQLite has JSON1 extension support"""
    # Create a temporary database to test
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        temp_db_path = temp_db.name

    try:
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Test JSON1 functions
        test_queries = [
            ("json_extract", "SELECT json_extract('[\"tag1\", \"tag2\"]', '$[0]')"),
            ("json_each", 'SELECT value FROM json_each(\'["tag1", "tag2"]\')'),
            ("json_valid", 'SELECT json_valid(\'["tag1", "tag2"]\')'),
            ("json_array_length", 'SELECT json_array_length(\'["tag1", "tag2"]\')'),
        ]

        supported_functions = []
        unsupported_functions = []

        for func_name, query in test_queries:
            try:
                cursor.execute(query)
                cursor.fetchone()
                supported_functions.append(func_name)
            except sqlite3.OperationalError:
                unsupported_functions.append(func_name)

        conn.close()

        # Check SQLite version
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        cursor.execute("SELECT sqlite_version()")
        cursor.fetchone()[0]

        conn.close()

        # Summary
        json1_supported = len(supported_functions) > 0

        return json1_supported, supported_functions

    except Exception:
        return False, []

    finally:
        with contextlib.suppress(OSError):
            os.unlink(temp_db_path)


if __name__ == "__main__":
    has_json1, functions = check_json1_support()
    sys.exit(0 if has_json1 else 1)
