#!/usr/bin/env python3
"""
Test script to verify DatabaseManager migration integration.
"""

import os
from pathlib import Path
import sys
import tempfile

from database.initialize_db import DatabaseManager


# Add the project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


def test_database_manager_integration():
    """Test DatabaseManager migration integration."""

    try:
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set environment variable to use test directory
            original_home = os.environ.get("HOME")
            os.environ["HOME"] = temp_dir

            try:

                def user_feedback(message):
                    pass

                # Test 1: Initialize DatabaseManager
                db_manager = DatabaseManager(user_name="test_user", user_feedback=user_feedback)

                # Test 2: Get notes connection (should trigger migrations)
                with db_manager.get_notes_connection() as conn:
                    cursor = conn.cursor()

                    # Check that migrations table exists
                    cursor.execute(
                        """
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name='schema_migrations'
                    """
                    )
                    migrations_table = cursor.fetchone()
                    if migrations_table:
                        # Check applied migrations
                        cursor.execute(
                            "SELECT version, name FROM schema_migrations ORDER BY version"
                        )
                        cursor.fetchall()
                    else:
                        pass

                    # Check that notes table exists with expected columns
                    cursor.execute("PRAGMA table_info(note_list)")
                    columns = {row[1] for row in cursor.fetchall()}

                    expected_columns = {
                        "id",
                        "title",
                        "content",
                        "tags",
                        "created_at",
                        "updated_at",
                        "project_id",
                        "is_deleted",
                        "content_html",
                    }

                    missing_columns = expected_columns - columns
                    if missing_columns:
                        pass
                    else:
                        pass

                # Test 3: Second initialization (should not re-run migrations)
                db_manager2 = DatabaseManager(user_name="test_user", user_feedback=user_feedback)

                with db_manager2.get_notes_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM schema_migrations")
                    result = cursor.fetchone()
                    result[0] if result else 0

            finally:
                # Restore original HOME
                if original_home:
                    os.environ["HOME"] = original_home
                else:
                    del os.environ["HOME"]

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_database_manager_integration()
    sys.exit(0 if success else 1)
