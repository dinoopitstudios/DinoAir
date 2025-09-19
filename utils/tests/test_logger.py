"""
Unit tests for logger.py module.
Tests logging functionality, singleton behavior, and convenience functions.
"""

import logging
import tempfile
from unittest.mock import MagicMock, patch

import utils.logger

from ..logger import Logger, log_critical, log_debug, log_error, log_info, log_warning


class TestLogger:
    """Test cases for Logger class."""

    def test_singleton_behavior(self):
        """Test that Logger follows singleton pattern."""
        logger1 = Logger()
        logger2 = Logger()

        if logger1 is not logger2:
            raise AssertionError
        if logger1._instance is not logger2._instance:
            raise AssertionError

    def test_initialization_once(self):
        """Test that initialization only happens once."""
        # Reset singleton state for test
        Logger._instance = None
        Logger._initialized = False
        with patch("utils.logger.Logger.setup_logging") as mock_setup:
            Logger()
            Logger()

            # setup_logging should only be called once
            mock_setup.assert_called_once()

    def test_setup_logging_basic_config(self):
        """Test basic logging setup when structured logging is not configured."""
        with (
            patch("logging.getLogger") as mock_get_logger,
            patch("pathlib.Path.mkdir"),
            patch("logging.basicConfig") as mock_basic_config,
        ):
            # Mock root logger to not have structured logging configured
            mock_root = MagicMock()
            mock_root._dinoair_structured_logging_configured = False
            mock_root.name = "DinoAir"  # Set mock name
            mock_get_logger.return_value = mock_root

            logger = Logger()
            logger.setup_logging()

            # Should call basicConfig
            mock_basic_config.assert_called_once()
            if logger.logger.name != "DinoAir":
                raise AssertionError

    def test_setup_logging_structured_already_configured(self):
        """Test that setup respects existing structured logging configuration."""
        with patch("logging.getLogger") as mock_get_logger:
            # Mock root logger to have structured logging configured
            mock_root = MagicMock()
            mock_root._dinoair_structured_logging_configured = True
            mock_root.name = "DinoAir"  # Set mock name
            mock_get_logger.return_value = mock_root

            logger = Logger()
            logger.setup_logging()

            # Should not call basicConfig, just get namespaced logger
            if logger.logger.name != "DinoAir":
                raise AssertionError

    def test_logging_methods(self):
        """Test all logging level methods."""
        logger = Logger()
        logger.logger = MagicMock()

        test_message = "Test message"

        logger.info(test_message)
        logger.logger.info.assert_called_with(test_message)

        logger.warning(test_message)
        logger.logger.warning.assert_called_with(test_message)

        logger.error(test_message)
        logger.logger.error.assert_called_with(test_message)

        logger.debug(test_message)
        logger.logger.debug.assert_called_with(test_message)

        logger.critical(test_message)
        logger.logger.critical.assert_called_with(test_message)

    def test_log_directory_creation(self):
        """Test that log directory is created during setup."""
        with (
            tempfile.TemporaryDirectory(),
            patch.object(utils.logger, "Path") as mock_path_class,
            patch("logging.basicConfig"),
            patch("logging.getLogger") as mock_get_logger,
        ):
            # Mock root logger
            mock_root = MagicMock()
            mock_root._dinoair_structured_logging_configured = False
            mock_get_logger.return_value = mock_root

            # Mock Path to use temp directory
            mock_path = MagicMock()
            mock_path.parent = mock_path  # Chain to itself to avoid issues
            mock_path.__truediv__ = lambda self, other: mock_path  # Mock / operator
            mock_path.mkdir = MagicMock()
            mock_path_class.return_value = mock_path

            logger = Logger()
            logger.setup_logging()

            # Should create log directory
            mock_path.mkdir.assert_called_with(exist_ok=True)


class TestConvenienceFunctions:
    """Test cases for convenience logging functions."""

    @patch("utils.logger.Logger")
    def test_log_info(self, mock_logger_class: MagicMock):
        """Test log_info convenience function."""
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger

        test_message = "Info message"
        log_info(test_message)

        mock_logger.info.assert_called_with(test_message)

    @patch("utils.logger.Logger")
    def test_log_warning(self, mock_logger_class: MagicMock):
        """Test log_warning convenience function."""
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger

        test_message = "Warning message"
        log_warning(test_message)

        mock_logger.warning.assert_called_with(test_message)

    @patch("utils.logger.Logger")
    def test_log_error(self, mock_logger_class: MagicMock):
        """Test log_error convenience function."""
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger

        test_message = "Error message"
        log_error(test_message)

        mock_logger.error.assert_called_with(test_message)

    @patch("utils.logger.Logger")
    def test_log_debug(self, mock_logger_class: MagicMock):
        """Test log_debug convenience function."""
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger

        test_message = "Debug message"
        log_debug(test_message)

        mock_logger.debug.assert_called_with(test_message)

    @patch("utils.logger.Logger")
    def test_log_critical(self, mock_logger_class: MagicMock):
        """Test log_critical convenience function."""
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger

        test_message = "Critical message"
        log_critical(test_message)

        mock_logger.critical.assert_called_with(test_message)


class TestLoggerIntegration:
    """Integration tests for logger functionality."""

    def test_logger_with_string_handler(self):
        """Test logger with string handler for testing."""
        import io

        # Create logger with string handler
        logger = Logger()
        # Clear existing handlers to isolate the test
        logger.logger.handlers.clear()
        string_handler = logging.StreamHandler(io.StringIO())
        string_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        string_handler.setFormatter(formatter)

        # Add handler to logger
        logger.logger.addHandler(string_handler)
        logger.logger.setLevel(logging.DEBUG)
        logger.logger.propagate = False  # Prevent propagation to root handlers

        # Test logging
        test_message = "Integration test message"
        logger.info(test_message)

        # Check output
        output = string_handler.stream.getvalue()
        if "INFO:" not in output:
            raise AssertionError
        if test_message not in output:
            raise AssertionError

    def test_multiple_logger_instances_same_object(self):
        """Test that multiple Logger() calls return same instance."""
        logger1 = Logger()
        logger2 = Logger()
        logger3 = Logger()

        if not logger1 is logger2 is logger3:
            raise AssertionError
        if not id(logger1) == id(logger2) == id(logger3):
            raise AssertionError
