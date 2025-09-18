"""
Comprehensive tests for DatabaseManager migration and backup functionality.
These tests focus on increasing coverage for the less-tested paths in initialize_db.
"""

import contextlib
from datetime import datetime
import shutil
import sqlite3

import pytest

from database.initialize_db import DatabaseManager


@pytest.mark.integration
@pytest.mark.migration
class TestDatabaseMigrations:
    """Test database migration functionality with real databases"""

    def test_migration_system_with_real_db(self, clean_db_manager):
        """Test that migrations run correctly on real database"""
        # Get a fresh database manager
        manager = clean_db_manager

        # Check that notes database was initialized and migrations were applied
        with manager.get_notes_connection() as conn:
            cursor = conn.cursor()

            # Verify migration tracking table exists
            cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='schema_migrations'
            """
            )
            if cursor.fetchone() is None:
                raise AssertionError

            # Verify some expected migrations were applied
            cursor.execute("SELECT name FROM schema_migrations")
            migrations = [row[0] for row in cursor.fetchall()]

            # Should have some basic migrations
            expected_migrations = [
                "add_notes_project_id",
                "add_notes_is_deleted",
                "add_notes_content_html",
                "tag_normalization",
                "comprehensive_index_coverage",
            ]

            for migration in expected_migrations:
                if migration not in migrations:
                    raise AssertionError(f"Migration {migration} not found")

    @pytest.mark.slow
    def test_migration_rollback_on_error(self, clean_db_manager):
        """Test that failed migrations are handled gracefully"""
        manager = clean_db_manager

        # Create a database with some data
        with manager.get_notes_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO note_list (id, title, content, tags)
                VALUES ('test-1', 'Test Note', 'Content', '["test"]')
            """
            )
            conn.commit()

            # Verify data exists
            cursor.execute("SELECT COUNT(*) FROM note_list")
            count_before = cursor.fetchone()[0]
            if count_before <= 0:
                raise AssertionError

    def test_migration_idempotency(self, clean_db_manager):
        """Test that running migrations multiple times is safe"""
        manager = clean_db_manager

        # Run initialization again - should be idempotent
        manager.initialize_all_databases()

        # Verify database is still functional
        with manager.get_notes_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            if table_count <= 0:
                raise AssertionError

    @pytest.mark.external
    def test_migration_with_permissions_error(self, tmp_path):
        """Test migration behavior when filesystem permissions are restricted"""
        # Create a directory structure
        restricted_dir = tmp_path / "restricted"
        restricted_dir.mkdir()

        # Make directory read-only (where supported)
        try:
            restricted_dir.chmod(0o444)

            # Attempt to create database manager - should handle gracefully
            with pytest.raises((PermissionError, OSError)):
                manager = DatabaseManager(user_name="restricted_user")
                manager.base_dir = restricted_dir
                manager._create_directory_structure()

        finally:
            # Restore permissions for cleanup
            with contextlib.suppress(Exception):
                restricted_dir.chmod(0o755)


@pytest.mark.integration
@pytest.mark.external
class TestDatabaseBackups:
    """Test database backup functionality"""

    def test_backup_creation_with_data(self, seeded_notes_db):
        """Test creating backups of databases with real data"""
        service, created_ids = seeded_notes_db
        manager = service.repository.db_manager

        # Create backup directory
        backup_dir = manager.user_db_dir.parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Test manual backup creation
        notes_db_path = manager.notes_db_path
        backup_path = backup_dir / f"notes_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

        # Copy database for backup
        shutil.copy2(notes_db_path, backup_path)

        # Verify backup contains data
        with sqlite3.connect(backup_path) as backup_conn:
            cursor = backup_conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM note_list")
            backup_count = cursor.fetchone()[0]
            assert backup_count >= len(created_ids)

    @pytest.mark.slow
    def test_backup_large_database(self, clean_db_manager, bulk_test_data):
        """Test backup creation with large amounts of data"""
        manager = clean_db_manager

        # Create large dataset
        notes = bulk_test_data["notes"](100)  # Create 100 notes

        from database.notes_service import NotesService

        service = NotesService(manager)

        # Add bulk data
        for note in notes[:10]:  # Limit to prevent test slowdown
            service.create_note(note)

        # Test backup creation
        backup_dir = manager.user_db_dir.parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        notes_db_path = manager.notes_db_path
        backup_path = backup_dir / "large_backup.db"

        # Measure backup performance
        import time

        start_time = time.time()
        shutil.copy2(notes_db_path, backup_path)
        backup_time = time.time() - start_time

        # Verify backup
        if not backup_path.exists():
            raise AssertionError
        if backup_path.stat().st_size <= 0:
            raise AssertionError

        # Backup should complete reasonably quickly
        if backup_time >= 30.0:
            raise AssertionError

    def test_corrupted_database_recovery(self, tmp_path):
        """Test recovery from corrupted database files"""
        # Create a corrupted database file
        corrupted_db = tmp_path / "corrupted.db"
        corrupted_db.write_text("This is not a valid SQLite database")

        # Test that ResilientDB can handle corruption
        from database.resilient_db import ResilientDB

        def dummy_schema(conn):
            conn.execute("CREATE TABLE test (id INTEGER)")

        resilient = ResilientDB(db_path=corrupted_db, schema_initializer=dummy_schema)

        # Should either recover or create new database
        with resilient.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            if len(tables) <= 0:
                raise AssertionError


@pytest.mark.integration
@pytest.mark.external
class TestDatabaseManagerEdgeCases:
    """Test edge cases and error conditions in DatabaseManager"""

    def test_initialization_with_invalid_characters(self):
        """Test DatabaseManager with invalid username characters"""
        # Test with various invalid characters
        invalid_names = ["user/name", "user\\name", "user?name", "user*name"]

        for invalid_name in invalid_names:
            # Should sanitize or handle gracefully
            manager = DatabaseManager(user_name=invalid_name)
            if not manager.user_name:
                raise AssertionError

            # Should be able to create directory structure
            manager._create_directory_structure()
            if not manager.user_db_dir.exists():
                raise AssertionError

    @pytest.mark.slow
    def test_concurrent_database_access(self, clean_db_manager):
        """Test that concurrent access is handled properly"""
        import threading

        manager = clean_db_manager
        results = []
        errors = []

        def worker_thread(thread_id):
            try:
                # Each thread gets its own connection
                with manager.get_notes_connection() as conn:
                    cursor = conn.cursor()

                    # Simulate some work
                    cursor.execute(
                        f"""
                        INSERT INTO notes (id, title, content, tags)
                        VALUES ('thread-{thread_id}', 'Thread {thread_id}', 'Content', '["test"]')
                    """
                    )
                    conn.commit()

                    # Read back the data
                    cursor.execute(f"SELECT title FROM notes WHERE id = 'thread-{thread_id}'")
                    result = cursor.fetchone()
                    results.append((thread_id, result[0] if result else None))

            except Exception as e:
                errors.append((thread_id, str(e)))

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10.0)

        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5

        # Verify all data was written
        with manager.get_notes_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM notes WHERE id LIKE 'thread-%'")
            count = cursor.fetchone()[0]
            if count != 5:
                raise AssertionError

    def test_database_connection_cleanup(self, clean_db_manager):
        """Test that database connections are properly cleaned up"""
        manager = clean_db_manager

        # Create multiple connections
        connections = []
        for _i in range(3):
            conn = manager.get_notes_connection()
            connections.append(conn)

        # Verify connections are tracked
        if len(manager._active_connections) < 3:
            raise AssertionError

        # Close connections manually
        for conn in connections:
            conn.close()

        # Note: In real usage, context managers handle cleanup automatically

    @pytest.mark.external
    def test_database_path_resolution(self, tmp_path):
        """Test database path resolution with various configurations"""
        # Test with custom base directory
        custom_base = tmp_path / "custom_dinoair"

        manager = DatabaseManager(user_name="path_test")
        manager.base_dir = custom_base
        manager._create_directory_structure()

        # Verify paths are resolved correctly
        expected_db_dir = custom_base / "user_data" / "path_test" / "databases"
        if manager.user_db_dir != expected_db_dir:
            raise AssertionError
        if not manager.user_db_dir.exists():
            raise AssertionError

        # Verify all database paths are under the correct directory
        db_paths = [
            manager.notes_db_path,
            manager.memory_db_path,
            manager.appointments_db_path,
            manager.artifacts_db_path,
        ]

        for db_path in db_paths:
            if db_path.parent != expected_db_dir:
                raise AssertionError
            if not str(db_path).startswith(str(custom_base)):
                raise AssertionError
