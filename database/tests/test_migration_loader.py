#!/usr/bin/env python3
"""
Test script to verify migration loader functionality.
"""

from pathlib import Path
import sqlite3
import sys
import tempfile

from database.migrations.loader import get_notes_migrations
from database.migrations.runner import MigrationRunner


# Add the project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


def test_migration_loader():
    """Test the migration loader."""

    try:
        # Test 1: Load notes migrations
        migrations = get_notes_migrations()

        if migrations:
            for _migration in migrations:
                pass

        # Test 2: Test with runner

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            conn = sqlite3.connect(db_path)

            runner = MigrationRunner("notes")
            runner.register_migrations(migrations)

            # Execute migrations
            runner.run_migrations(conn)

            # Check status
            runner.get_migration_status(conn)

            conn.close()

        finally:
            Path(db_path).unlink(missing_ok=True)

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_migration_loader()
    sys.exit(0 if success else 1)
