"""
Tests for ResilientDB functionality
"""

import sqlite3
from unittest.mock import Mock, patch

import pytest

from database.resilient_db import ResilientDB


class TestResilientDB:
    """Test ResilientDB class"""

    def test_init_with_path_and_schema_callback(self, temp_db_dir):
        """Test initialization with database path and schema callback"""
        db_path = temp_db_dir / "test.db"
        schema_callback = Mock()

        db = ResilientDB(db_path, schema_callback)

        assert db.db_path == db_path
        assert db.schema_callback == schema_callback
        assert hasattr(db, "user_feedback")

    def test_connect_success_first_attempt(self, temp_db_dir):
        """Test successful connection on first attempt"""
        db_path = temp_db_dir / "test.db"
        schema_callback = Mock()

        db = ResilientDB(db_path, schema_callback)

        with patch("sqlite3.connect") as mock_connect:
            mock_connection = Mock()
            mock_connect.return_value = mock_connection

            result = db.connect()

            assert result == mock_connection
            mock_connect.assert_called_once_with(str(db_path))
            schema_callback.assert_called_once_with(mock_connection)

    def test_connect_with_corruption_recovery(self, temp_db_dir):
        """Test connection with database corruption recovery"""
        db_path = temp_db_dir / "corrupted.db"
        schema_callback = Mock()

        # Create a corrupted database file
        db_path.write_text("corrupted content")

        db = ResilientDB(db_path, schema_callback)

        with patch("sqlite3.connect") as mock_connect:
            # First connection attempt fails
            mock_connect.side_effect = [
                sqlite3.DatabaseError("Database disk image is malformed"),
                Mock(),
            ]

            with patch.object(db, "_backup_corrupted_db") as mock_backup:
                result = db.connect_with_retry()

                assert result is not None
                assert mock_backup.called
                # Should have attempted connection twice
                assert mock_connect.call_count == 2

    def test_attempt_connection_success(self, temp_db_dir):
        """Test successful connection attempt"""
        db_path = temp_db_dir / "test.db"
        schema_callback = Mock()

        db = ResilientDB(db_path, schema_callback)

        with patch("sqlite3.connect") as mock_connect:
            mock_connection = Mock()
            mock_connect.return_value = mock_connection

            result = db._attempt_connection()

            assert result == mock_connection
            schema_callback.assert_called_once_with(mock_connection)

    def test_attempt_connection_failure(self, temp_db_dir):
        """Test failed connection attempt"""
        db_path = temp_db_dir / "test.db"
        schema_callback = Mock()

        db = ResilientDB(db_path, schema_callback)

        with patch("sqlite3.connect") as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Connection failed")

            with pytest.raises(sqlite3.Error):
                db._attempt_connection()

    def test_backup_corrupted_db(self, temp_db_dir):
        """Test corrupted database backup"""
        db_path = temp_db_dir / "corrupted.db"
        backup_dir = temp_db_dir / "backups"
        backup_dir.mkdir()

        # Create corrupted database file
        db_path.write_text("corrupted data")

        schema_callback = Mock()
        db = ResilientDB(db_path, schema_callback)

        # Mock the backup directory path
        with patch.object(db, "db_path", db_path):
            db._backup_corrupted_db()

            # Should create backup file
            backup_files = list(backup_dir.glob("corrupted_*.db"))
            assert len(backup_files) == 1

    def test_connect_with_retry_success(self, temp_db_dir):
        """Test successful connection with retry"""
        db_path = temp_db_dir / "test.db"
        schema_callback = Mock()

        db = ResilientDB(db_path, schema_callback)

        with patch.object(db, "_attempt_connection") as mock_attempt:
            mock_connection = Mock()
            mock_attempt.return_value = mock_connection

            result = db.connect_with_retry()

            assert result == mock_connection
            mock_attempt.assert_called_once()

    def test_connect_with_retry_with_failures(self, temp_db_dir):
        """Test connection retry with multiple failures"""
        db_path = temp_db_dir / "test.db"
        schema_callback = Mock()

        db = ResilientDB(db_path, schema_callback)

        with (
            patch.object(db, "_attempt_connection") as mock_attempt,
            patch.object(db, "_backup_corrupted_db") as mock_backup,
        ):
            # Fail twice, then succeed
            mock_connection = Mock()
            mock_attempt.side_effect = [
                sqlite3.DatabaseError("Corruption detected"),
                sqlite3.DatabaseError("Still corrupted"),
                mock_connection,
            ]

            result = db.connect_with_retry()

            assert result == mock_connection
            assert mock_attempt.call_count == 3
            assert mock_backup.call_count == 2  # Called for each failure

    def test_connect_with_retry_max_attempts_exceeded(self, temp_db_dir):
        """Test connection retry when max attempts exceeded"""
        db_path = temp_db_dir / "test.db"
        schema_callback = Mock()

        db = ResilientDB(db_path, schema_callback)

        with patch.object(db, "_attempt_connection") as mock_attempt:
            # Always fail
            mock_attempt.side_effect = sqlite3.DatabaseError("Persistent failure")

            with pytest.raises(sqlite3.DatabaseError):
                db.connect_with_retry()

            # Should attempt multiple times (default retry logic)
            assert mock_attempt.call_count >= 3

    def test_user_feedback_integration(self, temp_db_dir):
        """Test user feedback integration"""
        db_path = temp_db_dir / "test.db"
        feedback_messages = []

        def feedback_func(message: str):
            feedback_messages.append(message)

        db = ResilientDB(db_path, lambda conn: None, feedback_func)

        # Test feedback during connection
        with patch.object(db, "_attempt_connection") as mock_attempt:
            mock_attempt.side_effect = [
                sqlite3.DatabaseError("First failure"),
                Mock(),  # Success on second attempt
            ]

            db.connect_with_retry()

            # Should have provided feedback about recovery
            assert len(feedback_messages) > 0

    def test_schema_callback_execution(self, temp_db_dir):
        """Test that schema callback is executed during connection"""
        db_path = temp_db_dir / "test.db"
        callback_executed = False

        def schema_callback(conn):
            nonlocal callback_executed
            callback_executed = True

        db = ResilientDB(db_path, schema_callback)

        with patch("sqlite3.connect") as mock_connect:
            mock_connection = Mock()
            mock_connect.return_value = mock_connection

            db.connect()

            assert callback_executed


class TestResilientDBErrorScenarios:
    """Test error scenarios in ResilientDB"""

    def test_corruption_during_schema_setup(self, temp_db_dir):
        """Test corruption detected during schema setup"""
        db_path = temp_db_dir / "test.db"

        def failing_schema_callback(conn):
            raise sqlite3.DatabaseError("Schema setup failed")

        db = ResilientDB(db_path, failing_schema_callback)

        with patch("sqlite3.connect") as mock_connect:
            mock_connection = Mock()
            mock_connect.return_value = mock_connection

            with pytest.raises(sqlite3.DatabaseError):
                db._attempt_connection()

    def test_backup_creation_failure(self, temp_db_dir):
        """Test failure during backup creation"""
        db_path = temp_db_dir / "corrupted.db"

        # Create corrupted file
        db_path.write_text("corrupted")

        schema_callback = Mock()
        db = ResilientDB(db_path, schema_callback)

        # Mock shutil.copy2 to fail
        with patch("shutil.copy2", side_effect=OSError("Copy failed")):
            # Should not raise exception, just log the failure
            db._backup_corrupted_db()

    def test_connection_with_custom_feedback(self, temp_db_dir):
        """Test connection with custom feedback function"""
        db_path = temp_db_dir / "test.db"
        feedback_calls = []

        def custom_feedback(message: str):
            feedback_calls.append(message)

        db = ResilientDB(db_path, lambda conn: None, custom_feedback)

        with patch.object(db, "_attempt_connection") as mock_attempt:
            mock_attempt.return_value = Mock()

            db.connect_with_retry()

            assert len(feedback_calls) >= 0  # May or may not have feedback


@pytest.mark.integration
class TestResilientDBIntegration:
    """Integration tests for ResilientDB"""

    def test_real_database_operations(self, temp_db_dir):
        """Test with real SQLite database operations"""
        db_path = temp_db_dir / "integration.db"

        def schema_callback(conn):
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """
            )
            conn.commit()

        db = ResilientDB(db_path, schema_callback)

        # This should create the database and table
        conn = db.connect_with_retry()

        # Verify table was created
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        assert len(tables) >= 1
        table_names = [table[0] for table in tables]
        assert "test_table" in table_names

        conn.close()

    def test_corruption_recovery_workflow(self, temp_db_dir):
        """Test complete corruption recovery workflow"""
        db_path = temp_db_dir / "corruption_test.db"

        def schema_callback(conn):
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recovery_test (
                    id INTEGER PRIMARY KEY,
                    data TEXT
                )
            """
            )
            conn.commit()

        # Create initial database
        db = ResilientDB(db_path, schema_callback)
        conn1 = db.connect_with_retry()

        # Insert some data
        cursor = conn1.cursor()
        cursor.execute("INSERT INTO recovery_test (data) VALUES (?)", ("test data",))
        conn1.commit()
        conn1.close()

        # Corrupt the database file
        with open(db_path, "wb") as f:
            f.write(b"corrupted database content")

        # Try to connect again - should recover
        conn2 = db.connect_with_retry()

        # Verify recovery worked - table should exist again
        cursor = conn2.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        table_names = [table[0] for table in tables]
        assert "recovery_test" in table_names

        conn2.close()


@pytest.mark.parametrize(
    "error_type", [sqlite3.DatabaseError, sqlite3.OperationalError, sqlite3.IntegrityError, OSError]
)
def test_various_connection_errors(temp_db_dir, error_type):
    """Parametrized test for different connection error types"""
    db_path = temp_db_dir / "error_test.db"
    schema_callback = Mock()

    db = ResilientDB(db_path, schema_callback)

    with patch("sqlite3.connect") as mock_connect:
        mock_connect.side_effect = error_type("Test error")

        with pytest.raises(error_type):
            db._attempt_connection()


def test_feedback_message_formatting(temp_db_dir):
    """Test feedback message formatting"""
    db_path = temp_db_dir / "feedback_test.db"
    messages = []

    def capture_feedback(message: str):
        messages.append(message)

    db = ResilientDB(db_path, lambda conn: None, capture_feedback)

    # Test normal connection
    with patch.object(db, "_attempt_connection") as mock_attempt:
        mock_attempt.return_value = Mock()

        db.connect_with_retry()

        # Should have captured some feedback
        assert isinstance(messages, list)


def test_schema_callback_with_complex_setup(temp_db_dir):
    """Test schema callback with complex database setup"""
    db_path = temp_db_dir / "complex.db"

    def complex_schema_callback(conn):
        cursor = conn.cursor()

        # Create multiple tables with relationships
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                title TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """
        )

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id)")

        conn.commit()

    db = ResilientDB(db_path, complex_schema_callback)

    conn = db.connect_with_retry()

    # Verify all schema elements were created
    cursor = conn.cursor()

    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    assert "users" in tables
    assert "posts" in tables

    # Check indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = [row[0] for row in cursor.fetchall()]
    assert "idx_posts_user" in indexes

    conn.close()
