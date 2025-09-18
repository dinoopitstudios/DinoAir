#!/usr/bin/env python3
"""
Simple test script to verify migration system functionality.
"""

from pathlib import Path
import sqlite3
import sys
import tempfile

from database.migrations.base import (
    BaseMigration,
    ensure_migrations_table,
    is_migration_applied,
    record_migration,
)
from database.migrations.runner import MigrationRunner


# Add the project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class TestMigration(BaseMigration):
    """Simple test migration."""

    def __init__(self):
        super().__init__("001", "test_migration", "Test migration")

    def up(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
        conn.commit()


def test_migration_system():
    """Test the migration system."""

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        conn = sqlite3.connect(db_path)

        # Test 1: Ensure migrations table
        ensure_migrations_table(conn)

        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        )
        assert cursor.fetchone() is not None

        # Test 2: Test migration recording
        migration = TestMigration()
        record_migration(conn, migration)

        assert is_migration_applied(conn, migration)

        # Test 3: Test migration runner
        runner = MigrationRunner("test_db")
        runner.register_migration(migration)

        # Should be no pending migrations since we already recorded it
        pending = runner.get_pending_migrations(conn)
        assert len(pending) == 0

        # Test 4: Test new migration execution

        class NewTestMigration(BaseMigration):
            def __init__(self):
                super().__init__("002", "new_test", "New test migration")

            def up(self, conn: sqlite3.Connection) -> None:
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE new_test_table (id INTEGER)")
                conn.commit()

        new_migration = NewTestMigration()
        runner.register_migration(new_migration)

        executed = runner.run_migrations(conn)
        assert len(executed) == 1
        assert executed[0] == new_migration

        # Test 5: Test migration status
        status = runner.get_migration_status(conn)
        assert status["total_migrations"] == 2
        assert status["applied_count"] == 2
        assert status["pending_count"] == 0
        assert status["is_up_to_date"]

        conn.close()

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Clean up
        Path(db_path).unlink(missing_ok=True)


if __name__ == "__main__":
    success = test_migration_system()
    sys.exit(0 if success else 1)
