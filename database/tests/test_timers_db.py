"""
Tests for TimersDatabase functionality
"""

import sqlite3
from datetime import datetime

import pytest

from database.timers_db import TimersDatabase


class TestTimersDatabase:
    """Test TimersDatabase class"""

    def test_init_with_db_manager(self, mock_db_manager):
        """Test initialization with database manager"""
        db = TimersDatabase(mock_db_manager)
        if db.db_manager != mock_db_manager:
            raise AssertionError

    def test_create_log_success(self, mock_db_manager, mock_db_connection):
        """Test successful timer log creation"""
        db = TimersDatabase(mock_db_manager)
        mock_db_manager.get_timers_connection.return_value = mock_db_connection

        cursor = mock_db_connection.cursor.return_value
        cursor.lastrowid = 1

        log_data = {
            "task_name": "Test Task",
            "start_time": datetime.now(),
            "end_time": datetime.now(),
            "elapsed_seconds": 3600.0,
        }

        result = db.create_log(**log_data)

        if result["success"] is not True:
            raise AssertionError
        cursor.execute.assert_called_once()
        mock_db_connection.commit.assert_called_once()

    def test_create_log_with_none_values(self, mock_db_manager, mock_db_connection):
        """Test timer log creation with None values"""
        db = TimersDatabase(mock_db_manager)
        mock_db_manager.get_timers_connection.return_value = mock_db_connection

        cursor = mock_db_connection.cursor.return_value
        cursor.lastrowid = 1

        # Test with None end_time and elapsed_seconds
        log_data = {
            "task_name": "Incomplete Task",
            "start_time": datetime.now(),
            "end_time": None,
            "elapsed_seconds": None,
        }

        result = db.create_log(**log_data)

        if result["success"] is not True:
            raise AssertionError

    def test_create_log_database_error(self, mock_db_manager, mock_db_connection):
        """Test timer log creation with database error"""
        db = TimersDatabase(mock_db_manager)
        mock_db_manager.get_timers_connection.return_value = mock_db_connection

        # Mock database error
        mock_db_connection.cursor.side_effect = sqlite3.Error("Insert failed")

        log_data = {
            "task_name": "Test Task",
            "start_time": datetime.now(),
            "end_time": datetime.now(),
            "elapsed_seconds": 100.0,
        }

        result = db.create_log(**log_data)

        if result["success"] is not False:
            raise AssertionError

    def test_get_connection(self, mock_db_manager, mock_db_connection):
        """Test getting database connection"""
        db = TimersDatabase(mock_db_manager)
        mock_db_manager.get_timers_connection.return_value = mock_db_connection

        conn = db._get_connection()
        if conn != mock_db_connection:
            raise AssertionError
        mock_db_manager.get_timers_connection.assert_called_once()


class TestTimersDatabaseIntegration:
    """Integration tests for TimersDatabase"""

    def test_timer_workflow(self, mock_db_manager, mock_db_connection):
        """Test complete timer logging workflow"""
        db = TimersDatabase(mock_db_manager)
        mock_db_manager.get_timers_connection.return_value = mock_db_connection

        cursor = mock_db_connection.cursor.return_value
        cursor.lastrowid = 1

        # Simulate a timer session
        start_time = datetime.now()

        # Log completed task
        result = db.create_log(
            task_name="Integration Test Task",
            start_time=start_time,
            end_time=start_time,
            elapsed_seconds=300.0,
        )

        if result["success"] is not True:
            raise AssertionError

        # Verify the insert was called with correct parameters
        execute_calls = cursor.execute.call_args_list
        assert len(execute_calls) == 1

        # The SQL should contain INSERT INTO timer_logs
        sql_called = str(execute_calls[0][0][0]).upper()
        if "INSERT" not in sql_called:
            raise AssertionError
        if "TIMER_LOGS" not in sql_called:
            raise AssertionError


@pytest.mark.parametrize("elapsed_seconds", [0.0, 100.5, 3600.0, None])
def test_create_log_with_different_elapsed_times(
    mock_db_manager, mock_db_connection, elapsed_seconds
):
    """Parametrized test for different elapsed times"""
    db = TimersDatabase(mock_db_manager)
    mock_db_manager.get_timers_connection.return_value = mock_db_connection

    cursor = mock_db_connection.cursor.return_value
    cursor.lastrowid = 1

    log_data = {
        "task_name": "Test Task",
        "start_time": datetime.now(),
        "end_time": datetime.now() if elapsed_seconds else None,
        "elapsed_seconds": elapsed_seconds,
    }

    result = db.create_log(**log_data)

    if result["success"] is not True:
        raise AssertionError
    # Should handle None values correctly


def test_timer_log_data_validation(mock_db_manager, mock_db_connection):
    """Test validation of timer log data"""
    db = TimersDatabase(mock_db_manager)
    mock_db_manager.get_timers_connection.return_value = mock_db_connection

    cursor = mock_db_connection.cursor.return_value
    cursor.lastrowid = 1

    # Test with minimal required data
    result = db.create_log(
        task_name="Minimal Task", start_time=datetime.now(), end_time=None, elapsed_seconds=None
    )

    if result["success"] is not True:
        raise AssertionError

    # Test with full data
    result = db.create_log(
        task_name="Full Task",
        start_time=datetime.now(),
        end_time=datetime.now(),
        elapsed_seconds=123.45,
    )

    if result["success"] is not True:
        raise AssertionError


def test_timer_database_error_recovery(mock_db_manager, mock_db_connection):
    """Test error recovery in timer database operations"""
    db = TimersDatabase(mock_db_manager)
    mock_db_manager.get_timers_connection.return_value = mock_db_connection

    # Test connection failure
    mock_db_manager.get_timers_connection.side_effect = Exception("Connection failed")

    log_data = {
        "task_name": "Test Task",
        "start_time": datetime.now(),
        "end_time": datetime.now(),
        "elapsed_seconds": 100.0,
    }

    result = db.create_log(**log_data)

    if result["success"] is not False:
        raise AssertionError
