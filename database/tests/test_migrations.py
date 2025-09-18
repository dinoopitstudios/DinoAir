"""
Tests for the database migration system.
"""

from pathlib import Path
import sqlite3
import tempfile

import pytest

from database.migrations.base import (
    BaseMigration,
    MigrationError,
    MigrationRecord,
    ensure_migrations_table,
    get_applied_migrations,
    is_migration_applied,
    record_migration,
)
from database.migrations.runner import MigrationRunner


class TestMigration(BaseMigration):
    """Test migration for unit tests."""

    def __init__(self, version: str = "001", name: str = "test_migration"):
        super().__init__(version, name, "Test migration for unit tests")

    def up(self, conn: sqlite3.Connection) -> None:
        """Create a test table."""
        cursor = conn.cursor()
        table_name = f"test_table_{self.name}"
        cursor.execute(f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY, name TEXT)")
        conn.commit()

    def down(self, conn: sqlite3.Connection) -> None:
        """Drop the test table."""
        cursor = conn.cursor()
        table_name = f"test_table_{self.name}"
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()


class TestFailingMigration(BaseMigration):
    """Migration that always fails for testing error handling."""

    def __init__(self):
        super().__init__("999", "failing_migration", "Migration that fails")

    def up(self, conn: sqlite3.Connection) -> None:
        """Always raise an error."""
        raise sqlite3.Error("Intentional test error")


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    yield conn
    conn.close()

    # Clean up
    Path(db_path).unlink(missing_ok=True)


class TestMigrationBase:
    """Test base migration functionality."""

    def test_migration_creation(self):
        """Test creating a migration instance."""
        migration = TestMigration("001", "test_migration")

        assert migration.version == "001"
        assert migration.name == "test_migration"
        assert migration.full_name == "001_test_migration"
        assert migration.description == "Test migration for unit tests"

    def test_migration_string_representation(self):
        """Test migration string representations."""
        migration = TestMigration("001", "test_migration")

        assert str(migration) == "Migration(001_test_migration)"
        assert repr(migration) == "Migration(version='001', name='test_migration')"


class TestMigrationTable:
    """Test migration tracking table functionality."""

    def test_ensure_migrations_table(self, temp_db):
        """Test creating the migrations table."""
        ensure_migrations_table(temp_db)

        cursor = temp_db.cursor()
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='schema_migrations'
        """
        )

        assert cursor.fetchone() is not None

    def test_record_migration(self, temp_db):
        """Test recording a migration as applied."""
        ensure_migrations_table(temp_db)
        migration = TestMigration("001", "test_migration")

        record_migration(temp_db, migration)

        cursor = temp_db.cursor()
        cursor.execute(
            """
            SELECT version, name, description
            FROM schema_migrations
            WHERE version = ? AND name = ?
        """,
            (migration.version, migration.name),
        )

        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "001"
        assert row[1] == "test_migration"
        assert row[2] == "Test migration for unit tests"

    def test_is_migration_applied(self, temp_db):
        """Test checking if a migration has been applied."""
        ensure_migrations_table(temp_db)
        migration = TestMigration("001", "test_migration")

        # Should not be applied initially
        assert not is_migration_applied(temp_db, migration)

        # Record it as applied
        record_migration(temp_db, migration)

        # Should now be applied
        assert is_migration_applied(temp_db, migration)

    def test_get_applied_migrations(self, temp_db):
        """Test getting all applied migrations."""
        ensure_migrations_table(temp_db)

        migration1 = TestMigration("001", "first_migration")
        migration2 = TestMigration("002", "second_migration")

        record_migration(temp_db, migration1)
        record_migration(temp_db, migration2)

        applied = get_applied_migrations(temp_db)

        assert len(applied) == 2
        assert applied[0].version == "001"
        assert applied[0].name == "first_migration"
        assert applied[1].version == "002"
        assert applied[1].name == "second_migration"


class TestMigrationRunner:
    """Test migration runner functionality."""

    def test_runner_creation(self):
        """Test creating a migration runner."""
        runner = MigrationRunner("test_db")

        assert runner.db_key == "test_db"
        assert len(runner.migrations) == 0

    def test_register_migration(self):
        """Test registering migrations."""
        runner = MigrationRunner("test_db")
        migration = TestMigration("001", "test_migration")

        runner.register_migration(migration)

        assert len(runner.migrations) == 1
        assert runner.migrations[0] == migration

    def test_register_migrations_sorted(self):
        """Test that migrations are sorted by version."""
        runner = MigrationRunner("test_db")

        migration3 = TestMigration("003", "third")
        migration1 = TestMigration("001", "first")
        migration2 = TestMigration("002", "second")

        runner.register_migrations([migration3, migration1, migration2])

        assert len(runner.migrations) == 3
        assert runner.migrations[0].version == "001"
        assert runner.migrations[1].version == "002"
        assert runner.migrations[2].version == "003"

    def test_get_pending_migrations(self, temp_db):
        """Test getting pending migrations."""
        runner = MigrationRunner("test_db")
        migration1 = TestMigration("001", "first")
        migration2 = TestMigration("002", "second")

        runner.register_migrations([migration1, migration2])

        # All should be pending initially
        pending = runner.get_pending_migrations(temp_db)
        assert len(pending) == 2

        # Record one as applied
        record_migration(temp_db, migration1)

        # Only one should be pending now
        pending = runner.get_pending_migrations(temp_db)
        assert len(pending) == 1
        assert pending[0].version == "002"

    def test_run_migrations_success(self, temp_db):
        """Test successful migration execution."""
        runner = MigrationRunner("test_db")
        migration = TestMigration("001", "test_migration")

        runner.register_migration(migration)

        executed = runner.run_migrations(temp_db)

        assert len(executed) == 1
        assert executed[0] == migration

        # Check that table was created
        cursor = temp_db.cursor()
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='test_table'
        """
        )
        assert cursor.fetchone() is not None

        # Check that migration was recorded
        assert is_migration_applied(temp_db, migration)

    def test_run_migrations_already_applied(self, temp_db):
        """Test running migrations when all are already applied."""
        runner = MigrationRunner("test_db")
        migration = TestMigration("001", "test_migration")

        runner.register_migration(migration)
        ensure_migrations_table(temp_db)
        record_migration(temp_db, migration)

        executed = runner.run_migrations(temp_db)

        assert len(executed) == 0

    def test_run_migrations_dry_run(self, temp_db):
        """Test dry run mode."""
        runner = MigrationRunner("test_db")
        migration = TestMigration("001", "test_migration")

        runner.register_migration(migration)

        executed = runner.run_migrations(temp_db, dry_run=True)

        # Should return migrations that would be executed
        assert len(executed) == 1
        assert executed[0] == migration

        # But should not actually execute them
        cursor = temp_db.cursor()
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='test_table'
        """
        )
        assert cursor.fetchone() is None

        # Should not record migration
        assert not is_migration_applied(temp_db, migration)

    def test_run_migrations_target_version(self, temp_db):
        """Test running migrations up to a target version."""
        runner = MigrationRunner("test_db")

        migration1 = TestMigration("001", "first")
        migration2 = TestMigration("002", "second")
        migration3 = TestMigration("003", "third")

        runner.register_migrations([migration1, migration2, migration3])

        executed = runner.run_migrations(temp_db, target_version="002")

        # Should only execute first two migrations
        assert len(executed) == 2
        assert executed[0].version == "001"
        assert executed[1].version == "002"

        # Third should still be pending
        pending = runner.get_pending_migrations(temp_db)
        assert len(pending) == 1
        assert pending[0].version == "003"

    def test_run_migrations_failure(self, temp_db):
        """Test migration failure handling."""
        runner = MigrationRunner("test_db")

        good_migration = TestMigration("001", "good")
        bad_migration = TestFailingMigration()

        runner.register_migrations([good_migration, bad_migration])

        with pytest.raises(MigrationError) as exc_info:
            runner.run_migrations(temp_db)

        assert "Failed to execute migration 999_failing_migration" in str(exc_info.value)

        # Good migration should have been applied
        assert is_migration_applied(temp_db, good_migration)

        # Bad migration should not be recorded as applied
        assert not is_migration_applied(temp_db, bad_migration)

    def test_get_migration_status(self, temp_db):
        """Test getting migration status."""
        runner = MigrationRunner("test_db")

        migration1 = TestMigration("001", "first")
        migration2 = TestMigration("002", "second")

        runner.register_migrations([migration1, migration2])

        # Initially all pending
        status = runner.get_migration_status(temp_db)
        assert status["total_migrations"] == 2
        assert status["applied_count"] == 0
        assert status["pending_count"] == 2
        assert not status["is_up_to_date"]

        # Apply one migration
        record_migration(temp_db, migration1)

        status = runner.get_migration_status(temp_db)
        assert status["total_migrations"] == 2
        assert status["applied_count"] == 1
        assert status["pending_count"] == 1
        assert not status["is_up_to_date"]

        # Apply second migration
        record_migration(temp_db, migration2)

        status = runner.get_migration_status(temp_db)
        assert status["total_migrations"] == 2
        assert status["applied_count"] == 2
        assert status["pending_count"] == 0
        assert status["is_up_to_date"]

    def test_rollback_migration(self, temp_db):
        """Test rolling back a migration."""
        runner = MigrationRunner("test_db")
        migration = TestMigration("001", "test_migration")

        runner.register_migration(migration)

        # Apply the migration
        migration.up(temp_db)
        ensure_migrations_table(temp_db)
        record_migration(temp_db, migration)

        # Verify it's applied
        assert is_migration_applied(temp_db, migration)

        # Rollback the migration
        runner.rollback_migration(temp_db, "001", "test_migration")

        # Should no longer be recorded as applied
        assert not is_migration_applied(temp_db, migration)

        # Table should be gone
        cursor = temp_db.cursor()
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='test_table'
        """
        )
        assert cursor.fetchone() is None

    def test_rollback_migration_not_found(self, temp_db):
        """Test rolling back a migration that doesn't exist."""
        runner = MigrationRunner("test_db")

        with pytest.raises(MigrationError) as exc_info:
            runner.rollback_migration(temp_db, "999", "nonexistent")

        assert "Migration 999_nonexistent not found" in str(exc_info.value)

    def test_rollback_migration_not_applied(self, temp_db):
        """Test rolling back a migration that hasn't been applied."""
        runner = MigrationRunner("test_db")
        migration = TestMigration("001", "test_migration")

        runner.register_migration(migration)

        with pytest.raises(MigrationError) as exc_info:
            runner.rollback_migration(temp_db, "001", "test_migration")

        assert "Migration 001_test_migration is not applied" in str(exc_info.value)


class TestMigrationRecord:
    """Test migration record functionality."""

    def test_migration_record_creation(self):
        """Test creating a migration record."""
        from datetime import datetime

        applied_at = datetime.now()
        record = MigrationRecord("001", "test_migration", applied_at, "Test migration")

        assert record.version == "001"
        assert record.name == "test_migration"
        assert record.applied_at == applied_at
        assert record.description == "Test migration"
        assert record.full_name == "001_test_migration"

    def test_migration_record_from_row(self):
        """Test creating a migration record from a database row."""
        from datetime import datetime

        applied_at = datetime.now()
        row = ("001", "test_migration", applied_at.isoformat(), "Test migration", None)

        record = MigrationRecord.from_row(row)

        assert record.version == "001"
        assert record.name == "test_migration"
        assert record.applied_at.replace(microsecond=0) == applied_at.replace(microsecond=0)
        assert record.description == "Test migration"
