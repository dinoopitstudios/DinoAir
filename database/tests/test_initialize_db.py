"""
Tests for DatabaseManager initialization and management functionality
"""

import os
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from database.initialize_db import (
    DB_FILES,
    SCHEMA_DDLS,
    DatabaseManager,
    _ensure_dir,
    _exec_ddl_batch,
    initialize_user_databases,
)


class TestDatabaseManager:
    """Test DatabaseManager class functionality"""

    def test_init_default_user(self, temp_db_dir):
        """Test initialization with default user"""
        with patch.dict(os.environ, {}, clear=True):
            manager = DatabaseManager()
            if manager.user_name not in ["default_user", "test_user"]:
                raise AssertionError
            assert isinstance(manager.base_dir, Path)
            assert isinstance(manager.user_db_dir, Path)

    def test_init_with_user_name(self, temp_db_dir):
        """Test initialization with specific user name"""
        manager = DatabaseManager(user_name="test_user")
        if manager.user_name != "test_user":
            raise AssertionError

    def test_init_pytest_environment(self, temp_db_dir):
        """Test initialization detects pytest environment"""
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_function"}):
            manager = DatabaseManager()
            if "test_user" not in str(manager.user_db_dir):
                raise AssertionError

    def test_directory_structure_creation(self, temp_db_dir):
        """Test that directory structure is created correctly"""
        manager = DatabaseManager(user_name="test_user")

        # Check main directories exist
        if not manager.user_db_dir.exists():
            raise AssertionError
        if not (manager.user_db_dir.parent / "exports").exists():
            raise AssertionError
        if not (manager.user_db_dir.parent / "backups").exists():
            raise AssertionError
        if not (manager.user_db_dir.parent / "temp").exists():
            raise AssertionError
        if not (manager.user_db_dir.parent / "artifacts").exists():
            raise AssertionError

    @patch("database.initialize_db._ensure_dir")
    def test_directory_creation_failure(self, mock_ensure_dir, temp_db_dir):
        """Test handling of directory creation failures"""
        mock_ensure_dir.side_effect = PermissionError("Permission denied")

        with pytest.raises(PermissionError):
            DatabaseManager(user_name="test_user")

    def test_database_path_attributes(self, temp_db_dir):
        """Test that all database path attributes are set correctly"""
        manager = DatabaseManager(user_name="test_user")

        expected_paths = {
            "notes_db_path": "notes.db",
            "memory_db_path": "memory.db",
            "user_tools_db_path": "user_tools.db",
            "chat_history_db_path": "chat_history.db",
            "appointments_db_path": "appointments.db",
            "artifacts_db_path": "artifacts.db",
            "file_search_db_path": "file_search.db",
            "projects_db_path": "projects.db",
            "timers_db_path": "timers.db",
        }

        for attr, filename in expected_paths.items():
            if not hasattr(manager, attr):
                raise AssertionError
            path = getattr(manager, attr)
            if path.name != filename:
                raise AssertionError
            if path.parent != manager.user_db_dir:
                raise AssertionError

    @patch("database.initialize_db.ResilientDB")
    def test_get_connection_success(self, mock_resilient_db, temp_db_dir):
        """Test successful connection retrieval"""
        mock_conn = Mock()
        mock_db_instance = Mock()
        mock_db_instance.connect_with_retry.return_value = mock_conn
        mock_resilient_db.return_value = mock_db_instance

        manager = DatabaseManager(user_name="test_user")
        conn = manager.get_notes_connection()

        if conn != mock_conn:
            raise AssertionError
        mock_resilient_db.assert_called_once()
        mock_db_instance.connect_with_retry.assert_called_once()

    @patch("database.initialize_db.ResilientDB")
    def test_get_connection_tracks_connection(self, mock_resilient_db, temp_db_dir):
        """Test that connections are tracked for cleanup"""
        mock_conn = Mock()
        mock_db_instance = Mock()
        mock_db_instance.connect_with_retry.return_value = mock_conn
        mock_resilient_db.return_value = mock_db_instance

        manager = DatabaseManager(user_name="test_user")
        conn = manager.get_notes_connection()

        if conn not in manager._active_connections:
            raise AssertionError

    def test_all_connection_methods_exist(self, temp_db_dir):
        """Test that all expected connection methods exist"""
        manager = DatabaseManager(user_name="test_user")

        expected_methods = [
            "get_notes_connection",
            "get_memory_connection",
            "get_user_tools_connection",
            "get_chat_history_connection",
            "get_appointments_connection",
            "get_artifacts_connection",
            "get_file_search_connection",
            "get_projects_connection",
            "get_timers_connection",
        ]

        for method_name in expected_methods:
            if not hasattr(manager, method_name):
                raise AssertionError
            method = getattr(manager, method_name)
            if not callable(method):
                raise AssertionError

    @patch("database.initialize_db.ResilientDB")
    def test_initialize_all_databases_success(self, mock_resilient_db, temp_db_dir):
        """Test successful initialization of all databases"""
        mock_conn = Mock()
        mock_db_instance = Mock()
        mock_db_instance.connect_with_retry.return_value = mock_conn
        mock_resilient_db.return_value = mock_db_instance

        manager = DatabaseManager(user_name="test_user")
        manager.initialize_all_databases()

        # Should be called once for each database in DB_FILES
        assert mock_resilient_db.call_count == len(DB_FILES)

        # All connections should be closed
        assert mock_conn.close.call_count == len(DB_FILES)

    @patch("database.initialize_db.ResilientDB")
    def test_initialize_all_databases_handles_errors(self, mock_resilient_db, temp_db_dir):
        """Test error handling during database initialization"""
        mock_db_instance = Mock()
        mock_db_instance.connect_with_retry.side_effect = sqlite3.Error("Connection failed")
        mock_resilient_db.return_value = mock_db_instance

        manager = DatabaseManager(user_name="test_user")

        with pytest.raises(sqlite3.Error):
            manager.initialize_all_databases()

    def test_connection_cleanup(self, temp_db_dir):
        """Test that connections are properly cleaned up"""
        manager = DatabaseManager(user_name="test_user")

        # Mock some connections
        mock_conn1 = Mock()
        mock_conn2 = Mock()
        manager._active_connections = [mock_conn1, mock_conn2]

        manager._cleanup_connections()

        mock_conn1.close.assert_called_once()
        mock_conn2.close.assert_called_once()
        assert len(manager._active_connections) == 0

    def test_connection_cleanup_handles_errors(self, temp_db_dir):
        """Test that connection cleanup handles errors gracefully"""
        manager = DatabaseManager(user_name="test_user")

        # Mock connections with one that raises error on close
        mock_conn1 = Mock()
        mock_conn2 = Mock()
        mock_conn2.close.side_effect = Exception("Close failed")
        manager._active_connections = [mock_conn1, mock_conn2]

        # Should not raise exception
        manager._cleanup_connections()

        mock_conn1.close.assert_called_once()
        mock_conn2.close.assert_called_once()

    @patch("shutil.copy2")
    def test_backup_databases_success(self, mock_copy2, temp_db_dir):
        """Test successful database backup"""
        manager = DatabaseManager(user_name="test_user")

        # Create some mock database files
        for filename in DB_FILES.values():
            db_path = manager.user_db_dir / filename
            db_path.touch()

        manager.backup_databases()

        # Should call copy2 for each existing database file
        assert mock_copy2.call_count == len(DB_FILES)

    @patch("shutil.copy2")
    def test_backup_databases_handles_missing_files(self, mock_copy2, temp_db_dir):
        """Test backup handles missing database files gracefully"""
        manager = DatabaseManager(user_name="test_user")

        # Don't create any files - they should be skipped
        manager.backup_databases()

        # Should not call copy2 if no files exist
        mock_copy2.assert_not_called()

    @patch("database.initialize_db.ResilientDB")
    def test_clean_memory_database_success(self, mock_resilient_db, temp_db_dir):
        """Test successful memory database cleanup"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.rowcount = 5  # Simulate deleted rows
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)

        mock_db_instance = Mock()
        mock_db_instance.connect_with_retry.return_value = mock_conn
        mock_resilient_db.return_value = mock_db_instance

        manager = DatabaseManager(user_name="test_user")
        manager.clean_memory_database(watchdog_retention_days=7)

        # Verify cleanup operations were called
        if mock_cursor.execute.call_count < 4:
            raise AssertionError
        mock_conn.commit.assert_called_once()

    @patch("database.initialize_db.ResilientDB")
    def test_clean_memory_database_custom_retention(self, mock_resilient_db, temp_db_dir):
        """Test memory cleanup with custom retention period"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)

        mock_db_instance = Mock()
        mock_db_instance.connect_with_retry.return_value = mock_conn
        mock_resilient_db.return_value = mock_db_instance

        manager = DatabaseManager(user_name="test_user")
        manager.clean_memory_database(watchdog_retention_days=30)

        # Verify the custom retention was used
        calls = mock_cursor.execute.call_args_list
        # Find the call that deletes old metrics
        delete_call = None
        for call in calls:
            if "DELETE FROM watchdog_metrics" in str(call):
                delete_call = call
                break

        assert delete_call is not None
        # The cutoff date should be calculated with 30 days retention

    def test_schema_setup_calls_ddl_batch(self, temp_db_dir):
        """Test that schema setup calls DDL batch execution"""
        with patch("database.initialize_db._exec_ddl_batch") as mock_exec_ddl:
            manager = DatabaseManager(user_name="test_user")

            mock_conn = Mock()
            manager._setup_schema("notes", mock_conn)

            mock_exec_ddl.assert_called_once_with(mock_conn, SCHEMA_DDLS["notes"])

    def test_notes_migration_adds_project_id_column(self, temp_db_dir):
        """Test that fallback notes migration adds project_id column when missing"""
        # Note: This tests the fallback migration method, new migrations use the migration system
        manager = DatabaseManager(user_name="test_user")

        mock_conn = Mock()
        mock_cursor = Mock()

        # Mock table exists but missing project_id column
        mock_cursor.fetchall.side_effect = [
            [("note_list",)],  # Tables exist
            [
                ("id",),
                ("title",),
                ("content",),
                ("tags",),
                ("created_at",),
                ("updated_at",),
            ],  # Columns without project_id
        ]
        mock_conn.cursor.return_value = mock_cursor

        manager._apply_notes_project_id_migration(mock_conn)

        # Should check table existence and columns
        if mock_cursor.execute.call_count < 2:
            raise AssertionError
        mock_conn.commit.assert_called_once()

    def test_notes_migration_skips_when_column_exists(self, temp_db_dir):
        """Test that fallback notes migration skips when project_id column already exists"""
        # Note: This tests the fallback migration method, new migrations use the migration system
        manager = DatabaseManager(user_name="test_user")

        mock_conn = Mock()
        mock_cursor = Mock()

        # Mock table exists with project_id column
        mock_cursor.fetchall.side_effect = [
            [("note_list",)],  # Tables exist
            [
                ("id",),
                ("title",),
                ("content",),
                ("tags",),
                ("project_id",),
                ("created_at",),
                ("updated_at",),
            ],  # Columns with project_id
        ]
        mock_conn.cursor.return_value = mock_cursor

        manager._apply_notes_project_id_migration(mock_conn)

        # Should not execute ALTER TABLE
        alter_calls = [
            call for call in mock_cursor.execute.call_args_list if "ALTER TABLE" in str(call)
        ]
        assert len(alter_calls) == 0
        mock_conn.commit.assert_not_called()

    def test_exec_ddl_batch_executes_all_statements(self):
        """Test that DDL batch executes all statements and commits"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor

        ddls = [
            "CREATE TABLE test1 (id INTEGER)",
            "CREATE INDEX idx_test1 ON test1(id)",
            "ALTER TABLE test1 ADD COLUMN name TEXT",
        ]

        _exec_ddl_batch(mock_conn, ddls)

        assert mock_cursor.execute.call_count == len(ddls)
        mock_conn.commit.assert_called_once()

    def test_ensure_dir_creates_directory(self):
        """Test that _ensure_dir creates directory structure"""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            test_path = Path("/test/path")
            _ensure_dir(test_path)

            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestInitializeUserDatabases:
    """Test the convenience function for database initialization"""

    @patch("database.initialize_db.DatabaseManager")
    def test_initialize_user_databases_success(self, mock_db_manager_class):
        """Test successful user database initialization"""
        mock_manager = Mock()
        mock_db_manager_class.return_value = mock_manager

        result = initialize_user_databases("test_user", print)

        if result != mock_manager:
            raise AssertionError
        # Function now consistently passes all 3 parameters to DatabaseManager
        mock_db_manager_class.assert_called_once_with("test_user", print, None)
        mock_manager.initialize_all_databases.assert_called_once()

    @patch("database.initialize_db.DatabaseManager")
    def test_initialize_user_databases_no_feedback(self, mock_db_manager_class):
        """Test initialization without feedback function"""
        mock_manager = Mock()
        mock_db_manager_class.return_value = mock_manager

        result = initialize_user_databases("test_user")

        if result != mock_manager:
            raise AssertionError
        # Function now consistently passes all 3 parameters to DatabaseManager
        mock_db_manager_class.assert_called_once_with("test_user", print, None)


class TestConstants:
    """Test module constants"""

    def test_db_files_contains_all_databases(self):
        """Test that DB_FILES contains all expected databases"""
        expected_dbs = {
            "notes",
            "memory",
            "user_tools",
            "chat_history",
            "appointments",
            "artifacts",
            "file_search",
            "projects",
            "timers",
        }
        if set(DB_FILES.keys()) != expected_dbs:
            raise AssertionError

    def test_schema_ddls_contains_all_databases(self):
        """Test that SCHEMA_DDLS contains schemas for all databases"""
        expected_dbs = set(DB_FILES.keys())
        if set(SCHEMA_DDLS.keys()) != expected_dbs:
            raise AssertionError

    def test_schema_ddls_are_lists_of_strings(self):
        """Test that all SCHEMA_DDLS values are lists of strings"""
        for _db_key, ddls in SCHEMA_DDLS.items():
            assert isinstance(ddls, list)
            if not all(isinstance(ddl, str) for ddl in ddls):
                raise AssertionError
            if len(ddls) <= 0:
                raise AssertionError


@pytest.mark.integration
class TestDatabaseManagerIntegration:
    """Integration tests for DatabaseManager"""

    def test_full_initialization_workflow(self, temp_db_dir):
        """Test complete initialization workflow"""
        manager = DatabaseManager(user_name="integration_test")

        # This would actually create database files in temp directory
        manager.initialize_all_databases()

        # Check that all database files were created
        for filename in DB_FILES.values():
            db_path = manager.user_db_dir / filename
            if not db_path.exists():
                raise AssertionError(f"Database file {filename} was not created")

    def test_connection_workflow(self, temp_db_dir):
        """Test full connection workflow"""
        manager = DatabaseManager(user_name="integration_test")
        manager.initialize_all_databases()

        # Test that we can get connections for all databases
        connections = []
        try:
            connections.append(manager.get_notes_connection())
            connections.append(manager.get_memory_connection())
            connections.append(manager.get_appointments_connection())
            connections.append(manager.get_artifacts_connection())
            connections.append(manager.get_projects_connection())

            # Verify connections are valid SQLite connections
            for conn in connections:
                assert isinstance(conn, sqlite3.Connection)
                # Try a simple query
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result != (1,):
                    raise AssertionError

        finally:
            # Cleanup
            manager._cleanup_connections()


@pytest.mark.slow
class TestDatabaseManagerPerformance:
    """Performance tests for DatabaseManager"""

    def test_bulk_connection_creation(self, temp_db_dir):
        """Test creating multiple connections quickly"""
        import time

        manager = DatabaseManager(user_name="perf_test")
        manager.initialize_all_databases()

        start_time = time.time()

        # Create connections for all databases
        connections = []
        for _ in range(10):  # Multiple rounds
            connections.extend(
                [
                    manager.get_notes_connection(),
                    manager.get_memory_connection(),
                    manager.get_appointments_connection(),
                ]
            )

        creation_time = time.time() - start_time

        # Should complete within reasonable time
        if creation_time >= 2.0:
            raise AssertionError(f"Connection creation took {creation_time:.2f}s")

        # Cleanup
        manager._cleanup_connections()
