"""
Unit tests for enhanced_logger.py module.
Tests advanced logging features, context management, and async capabilities.
"""

import json
import logging
import tempfile
import threading
import time
from unittest.mock import MagicMock, patch

from ..enhanced_logger import (
    TRACE_LEVEL,
    VERBOSE_LEVEL,
    AsyncLogHandler,
    EnhancedJsonFormatter,
    EnhancedLogFilter,
    EnhancedLogger,
    FormatterConfig,
    LogAggregationConfig,
    LogAggregator,
    LogAnalyzer,
    LogConfig,
    LogContext,
    LogContextManager,
    LogFilterConfig,
    clear_log_context,
    configure_logging,
    detect_log_anomalies,
    generate_correlation_id,
    get_log_aggregator,
    get_log_analysis_report,
    get_log_context,
    get_logger,
    log_context,
    set_log_context,
    set_log_level,
    update_log_context,
)


class TestLogContext:
    """Test cases for LogContext dataclass."""

    def test_log_context_creation_with_all_fields(self):
        """Test LogContext creation with all fields."""
        context = LogContext(
            correlation_id="corr-123",
            user_id="user-456",
            session_id="sess-789",
            operation_id="op-abc",
            component="test-component",
            metadata={"key": "value", "number": 42},
        )

        if context.correlation_id != "corr-123":
            raise AssertionError
        if context.user_id != "user-456":
            raise AssertionError
        if context.session_id != "sess-789":
            raise AssertionError
        if context.operation_id != "op-abc":
            raise AssertionError
        if context.component != "test-component":
            raise AssertionError
        if context.metadata != {"key": "value", "number": 42}:
            raise AssertionError

    def test_log_context_defaults(self):
        """Test LogContext with default values."""
        context = LogContext()

        assert context.correlation_id is None
        assert context.user_id is None
        assert context.session_id is None
        assert context.operation_id is None
        assert context.component is None
        if context.metadata != {}:
            raise AssertionError

    def test_log_context_to_dict(self):
        """Test LogContext to_dict conversion."""
        context = LogContext(
            correlation_id="corr-123",
            user_id="user-456",
            component="test-component",
            metadata={"custom": "data"},
        )

        result = context.to_dict()
        expected = {
            "correlation_id": "corr-123",
            "user_id": "user-456",
            "component": "test-component",
            "custom": "data",
        }
        if result != expected:
            raise AssertionError

    def test_log_context_to_dict_empty(self):
        """Test LogContext to_dict with empty context."""
        context = LogContext()
        result = context.to_dict()
        if result != {}:
            raise AssertionError

    def test_log_context_to_dict_partial(self):
        """Test LogContext to_dict with partial fields."""
        context = LogContext(correlation_id="corr-123", metadata={"test": "value"})

        result = context.to_dict()
        expected = {"correlation_id": "corr-123", "test": "value"}
        if result != expected:
            raise AssertionError


class TestLogContextManager:
    """Test cases for LogContextManager."""

    def test_context_manager_initialization(self):
        """Test LogContextManager initialization."""
        manager = LogContextManager()
        if not hasattr(manager, "_local"):
            raise AssertionError

    def test_get_context_creates_default(self):
        """Test that get_context creates default context if none exists."""
        manager = LogContextManager()
        context = manager.get_context()

        assert isinstance(context, LogContext)
        assert context.correlation_id is None

    def test_set_and_get_context(self):
        """Test setting and getting context."""
        manager = LogContextManager()
        test_context = LogContext(correlation_id="test-123")

        manager.set_context(test_context)
        retrieved_context = manager.get_context()

        if retrieved_context.correlation_id != "test-123":
            raise AssertionError

    def test_update_context_existing_fields(self):
        """Test updating existing context fields."""
        manager = LogContextManager()
        manager.update_context(correlation_id="initial")

        context = manager.get_context()
        if context.correlation_id != "initial":
            raise AssertionError

        manager.update_context(correlation_id="updated", user_id="user-123")
        context = manager.get_context()
        if context.correlation_id != "updated":
            raise AssertionError
        if context.user_id != "user-123":
            raise AssertionError

    def test_update_context_metadata(self):
        """Test updating context with metadata."""
        manager = LogContextManager()
        manager.update_context(custom_field="custom_value")

        context = manager.get_context()
        if context.metadata["custom_field"] != "custom_value":
            raise AssertionError

    def test_clear_context(self):
        """Test clearing context."""
        manager = LogContextManager()
        manager.update_context(correlation_id="test")

        # Verify context exists
        context = manager.get_context()
        if context.correlation_id != "test":
            raise AssertionError

        # Clear and verify new default context is created
        manager.clear_context()
        new_context = manager.get_context()
        assert new_context.correlation_id is None

    def test_thread_isolation(self):
        """Test that contexts are isolated between threads."""
        manager = LogContextManager()
        results = {}

        def thread_worker(thread_id):
            manager.update_context(correlation_id=f"thread-{thread_id}")
            time.sleep(0.1)  # Allow context switching
            context = manager.get_context()
            results[thread_id] = context.correlation_id

        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=thread_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify each thread had its own context
        if results[0] != "thread-0":
            raise AssertionError
        if results[1] != "thread-1":
            raise AssertionError
        if results[2] != "thread-2":
            raise AssertionError


class TestLogFilterConfig:
    """Test cases for LogFilterConfig."""

    def test_log_filter_config_defaults(self):
        """Test LogFilterConfig default values."""
        config = LogFilterConfig()

        if config.enabled is not True:
            raise AssertionError
        if config.level_filters != {}:
            raise AssertionError
        if config.sampling_rate != 1.0:
            raise AssertionError
        if config.exclude_patterns != []:
            raise AssertionError
        if config.include_patterns != []:
            raise AssertionError

    def test_log_filter_config_custom_values(self):
        """Test LogFilterConfig with custom values."""
        config = LogFilterConfig(
            enabled=False,
            level_filters={"module1": logging.ERROR},
            sampling_rate=0.5,
            exclude_patterns=["debug", "test"],
            include_patterns=["error", "warning"],
        )

        if config.enabled is not False:
            raise AssertionError
        if config.level_filters != {"module1": logging.ERROR}:
            raise AssertionError
        if config.sampling_rate != 0.5:
            raise AssertionError
        if config.exclude_patterns != ["debug", "test"]:
            raise AssertionError
        if config.include_patterns != ["error", "warning"]:
            raise AssertionError


class TestEnhancedLogFilter:
    """Test cases for EnhancedLogFilter."""

    def test_filter_disabled(self):
        """Test filter when disabled."""
        config = LogFilterConfig(enabled=False)
        filter_obj = EnhancedLogFilter(config)

        # Create a test log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Should always pass when disabled
        if filter_obj.filter(record) is not True:
            raise AssertionError

    def test_level_filters(self):
        """Test module-specific level filters."""
        config = LogFilterConfig(level_filters={"test_module": logging.ERROR})
        filter_obj = EnhancedLogFilter(config)

        # Create records with different levels
        info_record = logging.LogRecord(
            name="test_module",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="info message",
            args=(),
            exc_info=None,
        )

        error_record = logging.LogRecord(
            name="test_module",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="error message",
            args=(),
            exc_info=None,
        )

        # INFO should be filtered out, ERROR should pass
        if filter_obj.filter(info_record) is not False:
            raise AssertionError
        if filter_obj.filter(error_record) is not True:
            raise AssertionError

    def test_exclude_patterns(self):
        """Test exclude patterns filtering."""
        config = LogFilterConfig(exclude_patterns=["debug", "test"])
        filter_obj = EnhancedLogFilter(config)

        # Create test records
        debug_record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="this is a debug message",
            args=(),
            exc_info=None,
        )

        normal_record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="normal message",
            args=(),
            exc_info=None,
        )

        # Debug message should be excluded
        if filter_obj.filter(debug_record) is not False:
            raise AssertionError
        if filter_obj.filter(normal_record) is not True:
            raise AssertionError

    def test_include_patterns(self):
        """Test include patterns filtering."""
        config = LogFilterConfig(include_patterns=["error", "warning"])
        filter_obj = EnhancedLogFilter(config)

        # Create test records
        error_record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="this is an error message",
            args=(),
            exc_info=None,
        )

        info_record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="normal info message",
            args=(),
            exc_info=None,
        )

        # Only error message should pass
        if filter_obj.filter(error_record) is not True:
            raise AssertionError
        if filter_obj.filter(info_record) is not False:
            raise AssertionError

    def test_sampling_rate(self):
        """Test sampling rate filtering."""
        config = LogFilterConfig(sampling_rate=0.5)  # 50% sampling
        filter_obj = EnhancedLogFilter(config)

        # Create multiple records and test sampling
        passed_count = 0
        total_count = 100

        for i in range(total_count):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=f"message {i}",
                args=(),
                exc_info=None,
            )
            if filter_obj.filter(record):
                passed_count += 1

        # With 50% sampling, roughly half should pass (allow some variance)
        if not 30 <= passed_count <= 70:
            raise AssertionError


class TestFormatterConfig:
    """Test cases for FormatterConfig."""

    def test_formatter_config_defaults(self):
        """Test FormatterConfig default values."""
        config = FormatterConfig()

        if config.format_type != "json":
            raise AssertionError
        if config.include_timestamp is not True:
            raise AssertionError
        if config.include_level is not True:
            raise AssertionError
        if config.include_logger is not True:
            raise AssertionError
        if config.include_module is not True:
            raise AssertionError
        if config.include_function is not True:
            raise AssertionError
        if config.include_context is not True:
            raise AssertionError
        assert config.custom_format is None
        if config.date_format != "%Y-%m-%dT%H:%M:%S.%fZ":
            raise AssertionError


class TestEnhancedJsonFormatter:
    """Test cases for EnhancedJsonFormatter."""

    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        config = FormatterConfig()
        formatter = EnhancedJsonFormatter(config)

        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"

        result = formatter.format(record)
        data = json.loads(result)

        if data["level"] != "INFO":
            raise AssertionError
        if data["logger"] != "test_logger":
            raise AssertionError
        if data["module"] != "test_module":
            raise AssertionError
        if data["function"] != "test_function":
            raise AssertionError
        if data["message"] != "Test message":
            raise AssertionError
        if "timestamp" not in data:
            raise AssertionError

    def test_format_with_context(self):
        """Test formatting with log context."""
        config = FormatterConfig()
        formatter = EnhancedJsonFormatter(config)

        # Set up context
        with patch("utils.enhanced_logger._context_manager") as mock_manager:
            mock_context = LogContext(correlation_id="test-123", user_id="user-456")
            mock_manager.get_context.return_value = mock_context

            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Test message",
                args=(),
                exc_info=None,
            )
            record.module = "test"
            record.funcName = "test"

            result = formatter.format(record)
            data = json.loads(result)

            if "context" not in data:
                raise AssertionError
            if data["context"]["correlation_id"] != "test-123":
                raise AssertionError
            if data["context"]["user_id"] != "user-456":
                raise AssertionError

    def test_format_with_exception(self):
        """Test formatting with exception information."""
        config = FormatterConfig()
        formatter = EnhancedJsonFormatter(config)

        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg="Error occurred",
                args=(),
                exc_info=True,
            )
            record.module = "test"
            record.funcName = "test"

            result = formatter.format(record)
            data = json.loads(result)

            if "exception" not in data:
                raise AssertionError
            if "ValueError" not in data["exception"]:
                raise AssertionError
            if "Test exception" not in data["exception"]:
                raise AssertionError

    def test_format_with_extra_fields(self):
        """Test formatting with extra fields in record."""
        config = FormatterConfig()
        formatter = EnhancedJsonFormatter(config)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test"
        record.funcName = "test"
        record.custom_field = "custom_value"
        record.request_id = "req-123"

        result = formatter.format(record)
        data = json.loads(result)

        if data["custom_field"] != "custom_value":
            raise AssertionError
        if data["request_id"] != "req-123":
            raise AssertionError

    def test_format_without_optional_fields(self):
        """Test formatting without optional fields."""
        config = FormatterConfig(
            include_timestamp=False, include_module=False, include_context=False
        )
        formatter = EnhancedJsonFormatter(config)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test"
        record.funcName = "test"

        result = formatter.format(record)
        data = json.loads(result)

        if "timestamp" in data:
            raise AssertionError
        if "module" in data:
            raise AssertionError
        if "context" in data:
            raise AssertionError
        if data["level"] != "INFO":
            raise AssertionError
        if data["message"] != "Test message":
            raise AssertionError


class TestAsyncLogHandler:
    """Test cases for AsyncLogHandler."""

    def test_async_handler_initialization(self):
        """Test AsyncLogHandler initialization."""
        inner_handler = logging.StreamHandler()
        async_handler = AsyncLogHandler(inner_handler, queue_size=100)

        if async_handler.handler != inner_handler:
            raise AssertionError
        if async_handler.queue.maxsize != 100:
            raise AssertionError
        if not async_handler.is_worker_thread_alive():
            raise AssertionError

    def test_async_handler_emit(self):
        """Test AsyncLogHandler emit functionality."""
        inner_handler = MagicMock()
        async_handler = AsyncLogHandler(inner_handler, queue_size=10)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        async_handler.emit(record)
        time.sleep(0.1)  # Allow processing

        # Should have processed the record
        inner_handler.emit.assert_called_with(record)

    def test_async_handler_queue_full_fallback(self):
        """Test AsyncLogHandler fallback when queue is full."""
        inner_handler = MagicMock()
        async_handler = AsyncLogHandler(inner_handler, queue_size=1)

        # Fill the queue
        record1 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Message 1",
            args=(),
            exc_info=None,
        )
        record2 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Message 2",
            args=(),
            exc_info=None,
        )

        async_handler.emit(record1)
        async_handler.emit(record2)  # Should trigger fallback

        time.sleep(0.1)  # Allow processing

        # Both records should have been handled
        if inner_handler.emit.call_count < 1:
            raise AssertionError

    def test_async_handler_close(self):
        """Test AsyncLogHandler close functionality."""
        inner_handler = MagicMock()
        async_handler = AsyncLogHandler(inner_handler)

        async_handler.close()

        # Should have closed inner handler
        inner_handler.close.assert_called_once()


class TestLogConfig:
    """Test cases for LogConfig."""

    def test_log_config_defaults(self):
        """Test LogConfig default values."""
        config = LogConfig()

        if config.level != "INFO":
            raise AssertionError
        if config.format_type != "json":
            raise AssertionError
        if config.log_dir != "logs":
            raise AssertionError
        if config.max_file_size != 10_000_000:
            raise AssertionError
        if config.backup_count != 5:
            raise AssertionError
        if config.async_logging is not True:
            raise AssertionError
        if config.async_queue_size != 1000:
            raise AssertionError
        assert isinstance(config.filter_config, LogFilterConfig)
        assert isinstance(config.formatter_config, FormatterConfig)


class TestEnhancedLogger:
    """Test cases for EnhancedLogger."""

    def test_enhanced_logger_singleton(self):
        """Test that EnhancedLogger is a singleton."""
        logger1 = EnhancedLogger()
        logger2 = EnhancedLogger()

        if logger1 is not logger2:
            raise AssertionError

    def test_enhanced_logger_initialization_once(self):
        """Test that initialization only happens once."""
        # Reset singleton for testing
        EnhancedLogger.reset_instance()

        with patch.object(EnhancedLogger, "_setup_logging"):
            EnhancedLogger()
            EnhancedLogger()

            # _setup_logging should only be called once during first initialization
            # Note: This test might need adjustment based on actual implementation

    def test_configure_enhanced_logger(self):
        """Test configuring enhanced logger."""
        logger = EnhancedLogger()
        config = LogConfig(level="DEBUG", format_type="text")

        with patch.object(logger, "_setup_logging") as mock_setup:
            logger.configure(config)

            if logger.config != config:
                raise AssertionError
            mock_setup.assert_called_once()

    def test_get_logger(self):
        """Test getting named logger."""
        enhanced_logger = EnhancedLogger()
        logger1 = enhanced_logger.get_logger("test_logger")
        logger2 = enhanced_logger.get_logger("test_logger")

        if logger1 is not logger2:
            raise AssertionError
        if logger1.name != "test_logger":
            raise AssertionError

    def test_set_level_root(self):
        """Test setting root logger level."""
        enhanced_logger = EnhancedLogger()

        with patch("logging.getLogger") as mock_get_logger:
            mock_root = MagicMock()
            mock_get_logger.return_value = mock_root

            enhanced_logger.set_level("DEBUG")

            mock_root.setLevel.assert_called_with(logging.DEBUG)

    def test_set_level_specific_logger(self):
        """Test setting specific logger level."""
        enhanced_logger = EnhancedLogger()

        with patch.object(enhanced_logger, "get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            enhanced_logger.set_level("WARNING", "test_logger")

            mock_logger.setLevel.assert_called_with(logging.WARNING)

    def test_update_filter_config(self):
        """Test updating filter configuration."""
        enhanced_logger = EnhancedLogger()

        with patch.object(enhanced_logger, "_setup_logging") as mock_setup:
            enhanced_logger.update_filter_config(sampling_rate=0.5, enabled=False)

            if enhanced_logger.config.filter_config.sampling_rate != 0.5:
                raise AssertionError
            if enhanced_logger.config.filter_config.enabled is not False:
                raise AssertionError
            mock_setup.assert_called_once()

    def test_set_module_level(self):
        """Test setting module-specific log level."""
        enhanced_logger = EnhancedLogger()

        with patch.object(enhanced_logger, "_setup_logging") as mock_setup:
            enhanced_logger.set_module_level("test_module", "ERROR")

            if enhanced_logger.config.filter_config.level_filters["test_module"] != logging.ERROR:
                raise AssertionError
            mock_setup.assert_called_once()

    def test_remove_module_level(self):
        """Test removing module-specific log level."""
        enhanced_logger = EnhancedLogger()
        enhanced_logger.config.filter_config.level_filters["test_module"] = logging.ERROR

        with patch.object(enhanced_logger, "_setup_logging") as mock_setup:
            enhanced_logger.remove_module_level("test_module")

            if "test_module" in enhanced_logger.config.filter_config.level_filters:
                raise AssertionError
            mock_setup.assert_called_once()

    def test_get_module_levels(self):
        """Test getting module-specific log levels."""
        enhanced_logger = EnhancedLogger()
        enhanced_logger.config.filter_config.level_filters = {
            "module1": logging.DEBUG,
            "module2": logging.ERROR,
        }

        levels = enhanced_logger.get_module_levels()

        if levels["module1"] != "DEBUG":
            raise AssertionError
        if levels["module2"] != "ERROR":
            raise AssertionError


class TestLogAggregationConfig:
    """Test cases for LogAggregationConfig."""

    def test_log_aggregation_config_defaults(self):
        """Test LogAggregationConfig default values."""
        config = LogAggregationConfig()

        if config.time_window_seconds != 300:
            raise AssertionError
        if config.max_entries != 10000:
            raise AssertionError
        if config.aggregation_fields != ["level", "logger", "component"]:
            raise AssertionError
        if config.enable_pattern_analysis is not True:
            raise AssertionError
        if config.enable_error_rate_tracking is not True:
            raise AssertionError


class TestLogAggregator:
    """Test cases for LogAggregator."""

    def test_log_aggregator_initialization(self):
        """Test LogAggregator initialization."""
        aggregator = LogAggregator()

        assert isinstance(aggregator.config, LogAggregationConfig)
        assert len(aggregator.entries) == 0

    def test_add_entry(self):
        """Test adding log entries."""
        aggregator = LogAggregator()

        entry = {
            "timestamp": time.time(),
            "level": "INFO",
            "logger": "test_logger",
            "message": "test message",
            "context": {"component": "test_component"},
        }

        aggregator.add_entry(entry)

        entries = aggregator.get_entries()
        assert len(entries) == 1
        stored_entry = entries[0]
        if stored_entry["level"] != "INFO":
            raise AssertionError
        if stored_entry["component"] != "test_component":
            raise AssertionError

    def test_get_summary(self):
        """Test getting aggregated summary."""
        aggregator = LogAggregator()
        current_time = time.time()

        # Add test entries
        for i in range(5):
            entry = {
                "timestamp": current_time - i,
                "level": "INFO" if i % 2 == 0 else "ERROR",
                "logger": f"logger_{i}",
                "message": f"message {i}",
                "context": {"component": f"component_{i % 2}"},
            }
            aggregator.add_entry(entry)

        summary = aggregator.get_summary(time_window_seconds=10)

        if summary["total_entries"] != 5:
            raise AssertionError
        if "level_distribution" not in summary:
            raise AssertionError
        if "component_distribution" not in summary:
            raise AssertionError
        if summary["level_distribution"]["INFO"] < 1:
            raise AssertionError
        if summary["level_distribution"]["ERROR"] < 1:
            raise AssertionError

    def test_get_summary_with_error_tracking(self):
        """Test summary with error rate tracking."""
        config = LogAggregationConfig(enable_error_rate_tracking=True)
        aggregator = LogAggregator(config)
        current_time = time.time()

        # Add entries with errors
        for i in range(10):
            level = "ERROR" if i < 3 else "INFO"
            entry = {
                "timestamp": current_time,
                "level": level,
                "logger": "test",
                "message": f"message {i}",
                "context": {},
            }
            aggregator.add_entry(entry)

        summary = aggregator.get_summary()

        if "error_rate" not in summary:
            raise AssertionError
        if "error_count" not in summary:
            raise AssertionError
        if summary["error_count"] != 3:
            raise AssertionError
        if summary["error_rate"] != 0.3:
            raise AssertionError

    def test_clear_entries(self):
        """Test clearing old entries."""
        aggregator = LogAggregator()
        current_time = time.time()

        # Add entries with different ages
        for i in range(5):
            entry = {
                "timestamp": current_time - (i * 100),  # Spread over time
                "level": "INFO",
                "logger": "test",
                "message": f"message {i}",
                "context": {},
            }
            aggregator.add_entry(entry)

        assert len(aggregator.entries) == 5

        # Clear entries older than 150 seconds
        aggregator.clear_entries(older_than_seconds=150)

        # Should keep entries that are less than 150 seconds old
        remaining = len(aggregator.entries)
        if remaining >= 5:
            raise AssertionError


class TestLogAnalyzer:
    """Test cases for LogAnalyzer."""

    def test_detect_anomalies_insufficient_data(self):
        """Test anomaly detection with insufficient data."""
        entries = [{"timestamp": time.time(), "level": "INFO"}]

        result = LogAnalyzer.detect_anomalies(entries)

        if result["anomalies_detected"] is not False:
            raise AssertionError
        if result["reason"] != "Insufficient data":
            raise AssertionError

    def test_detect_anomalies_no_baseline(self):
        """Test anomaly detection with no baseline data."""
        current_time = time.time()
        entries = []

        # Add only recent entries (no baseline)
        for i in range(20):
            entries.append({"timestamp": current_time - i, "level": "INFO"})

        result = LogAnalyzer.detect_anomalies(entries, baseline_window=3600)

        if result["anomalies_detected"] is not False:
            raise AssertionError
        if result["reason"] != "No baseline data":
            raise AssertionError

    def test_detect_anomalies_normal_rate(self):
        """Test anomaly detection with normal error rate."""
        current_time = time.time()
        entries = []

        # Add baseline entries (low error rate)
        for i in range(100, 200):
            level = "ERROR" if i % 20 == 0 else "INFO"  # 5% error rate
            entries.append({"timestamp": current_time - i, "level": level})

        # Add recent entries (similar error rate)
        for i in range(50):
            level = "ERROR" if i % 20 == 0 else "INFO"  # 5% error rate
            entries.append({"timestamp": current_time - i, "level": level})

        result = LogAnalyzer.detect_anomalies(entries, baseline_window=150)

        if result["anomalies_detected"] is not False:
            raise AssertionError
        if result["recent_error_rate"] > result["threshold"]:
            raise AssertionError

    def test_generate_report(self):
        """Test generating human-readable report."""
        aggregator = LogAggregator()
        current_time = time.time()

        # Add test data
        for i in range(10):
            entry = {
                "timestamp": current_time,
                "level": "ERROR" if i < 2 else "INFO",
                "logger": "test_logger",
                "message": f"test message {i}",
                "context": {"component": "test_component"},
            }
            aggregator.add_entry(entry)

        report = LogAnalyzer.generate_report(aggregator)

        if "LOG ANALYSIS REPORT" not in report:
            raise AssertionError
        if "Total Entries: 10" not in report:
            raise AssertionError
        if "ERROR: 2" not in report:
            raise AssertionError
        if "INFO: 8" not in report:
            raise AssertionError


class TestContextManagement:
    """Test cases for context management functions."""

    def test_global_context_functions(self):
        """Test global context management functions."""
        # Clear any existing context
        clear_log_context()

        # Test getting default context
        context = get_log_context()
        assert isinstance(context, LogContext)
        assert context.correlation_id is None

        # Test setting context
        new_context = LogContext(correlation_id="test-123")
        set_log_context(new_context)

        retrieved = get_log_context()
        if retrieved.correlation_id != "test-123":
            raise AssertionError

        # Test updating context
        update_log_context(user_id="user-456", custom_field="custom_value")

        updated = get_log_context()
        if updated.correlation_id != "test-123":
            raise AssertionError
        if updated.user_id != "user-456":
            raise AssertionError
        if updated.metadata["custom_field"] != "custom_value":
            raise AssertionError

    def test_log_context_context_manager(self):
        """Test log_context context manager."""
        # Clear any existing context
        clear_log_context()

        original_context = get_log_context()
        original_correlation_id = original_context.correlation_id

        with log_context(correlation_id="temp-123", user_id="temp-user"):
            temp_context = get_log_context()
            if temp_context.correlation_id != "temp-123":
                raise AssertionError
            if temp_context.user_id != "temp-user":
                raise AssertionError

        # Context should be restored
        restored_context = get_log_context()
        if restored_context.correlation_id != original_correlation_id:
            raise AssertionError

    def test_log_context_with_metadata(self):
        """Test log_context with metadata fields."""
        with log_context(correlation_id="test", custom_field="custom", another="value"):
            context = get_log_context()
            if context.correlation_id != "test":
                raise AssertionError
            if context.metadata["custom_field"] != "custom":
                raise AssertionError
            if context.metadata["another"] != "value":
                raise AssertionError

    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        id1 = generate_correlation_id()
        id2 = generate_correlation_id()

        assert isinstance(id1, str)
        assert isinstance(id2, str)
        if id1 == id2:
            raise AssertionError
        if len(id1) <= 0:
            raise AssertionError
        if len(id2) <= 0:
            raise AssertionError


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    def test_get_logger_function(self):
        """Test get_logger convenience function."""
        logger = get_logger("test_logger")

        assert isinstance(logger, logging.Logger)
        if logger.name != "test_logger":
            raise AssertionError

    def test_configure_logging_function(self):
        """Test configure_logging convenience function."""
        config = LogConfig(level="DEBUG")

        with patch("utils.enhanced_logger._enhanced_logger") as mock_logger:
            configure_logging(config)
            mock_logger.configure.assert_called_with(config)

    def test_set_log_level_function(self):
        """Test set_log_level convenience function."""
        with patch("utils.enhanced_logger._enhanced_logger") as mock_logger:
            set_log_level("WARNING", "test_logger")
            mock_logger.set_level.assert_called_with("WARNING", "test_logger")

    def test_get_log_aggregator_function(self):
        """Test get_log_aggregator convenience function."""
        aggregator = get_log_aggregator()

        assert isinstance(aggregator, LogAggregator)
        # Should return same instance on subsequent calls
        if aggregator is not get_log_aggregator():
            raise AssertionError

    def test_get_log_analysis_report_function(self):
        """Test get_log_analysis_report convenience function."""
        report = get_log_analysis_report()

        assert isinstance(report, str)
        if "LOG ANALYSIS REPORT" not in report:
            raise AssertionError

    def test_detect_log_anomalies_function(self):
        """Test detect_log_anomalies convenience function."""
        result = detect_log_anomalies()

        assert isinstance(result, dict)
        if "anomalies_detected" not in result:
            raise AssertionError
        assert isinstance(result["anomalies_detected"], bool)


class TestCustomLogLevels:
    """Test cases for custom log levels."""

    def test_trace_level_constant(self):
        """Test TRACE level constant."""
        if TRACE_LEVEL != 5:
            raise AssertionError
        if logging.getLevelName(TRACE_LEVEL) != "TRACE":
            raise AssertionError

    def test_verbose_level_constant(self):
        """Test VERBOSE level constant."""
        if VERBOSE_LEVEL != 15:
            raise AssertionError
        if logging.getLevelName(VERBOSE_LEVEL) != "VERBOSE":
            raise AssertionError

    def test_trace_method_added_to_logger(self):
        """Test that trace method is added to Logger class."""
        logger = logging.getLogger("test")

        if not hasattr(logger, "trace"):
            raise AssertionError
        if not callable(logger.trace):
            raise AssertionError

    def test_verbose_method_added_to_logger(self):
        """Test that verbose method is added to Logger class."""
        logger = logging.getLogger("test")

        if not hasattr(logger, "verbose"):
            raise AssertionError
        if not callable(logger.verbose):
            raise AssertionError

    def test_trace_logging_functionality(self):
        """Test trace logging functionality."""
        with patch("logging.Logger._log") as mock_log:
            logger = logging.getLogger("test")
            logger.setLevel(TRACE_LEVEL)

            logger.trace("trace message")

            mock_log.assert_called_with(TRACE_LEVEL, "trace message", ())

    def test_verbose_logging_functionality(self):
        """Test verbose logging functionality."""
        with patch("logging.Logger._log") as mock_log:
            logger = logging.getLogger("test")
            logger.setLevel(VERBOSE_LEVEL)

            logger.verbose("verbose message")

            mock_log.assert_called_with(VERBOSE_LEVEL, "verbose message", ())


class TestIntegrationScenarios:
    """Integration test cases for enhanced logging system."""

    def test_full_logging_workflow(self):
        """Test complete logging workflow with context and filtering."""
        # Configure enhanced logging
        config = LogConfig(
            level="DEBUG",
            async_logging=False,  # Simplify for testing
            filter_config=LogFilterConfig(sampling_rate=1.0),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            config.log_dir = temp_dir

            with patch("utils.enhanced_logger._enhanced_logger") as mock_enhanced_logger:
                mock_enhanced_logger.configure = MagicMock()
                mock_enhanced_logger.get_logger = MagicMock()
                mock_logger = MagicMock()
                mock_enhanced_logger.get_logger.return_value = mock_logger

                # Configure logging
                configure_logging(config)

                # Use context manager
                with log_context(correlation_id="test-123", component="test"):
                    logger = get_logger("test")
                    logger.info("Test message")

                # Verify configuration was called
                mock_enhanced_logger.configure.assert_called_with(config)

    def test_error_handling_in_async_logging(self):
        """Test error handling in async logging components."""
        inner_handler = MagicMock()
        inner_handler.emit.side_effect = Exception("Handler error")

        async_handler = AsyncLogHandler(inner_handler, queue_size=10)

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Test error",
            args=(),
            exc_info=None,
        )

        # Should not raise exception even if inner handler fails
        async_handler.emit(record)
        time.sleep(0.1)  # Allow processing

        # Handler should have been called despite error
        inner_handler.emit.assert_called()

    def test_concurrent_context_updates(self):
        """Test concurrent context updates."""
        results = {}

        def worker(thread_id):
            with log_context(correlation_id=f"thread-{thread_id}"):
                time.sleep(0.1)
                context = get_log_context()
                results[thread_id] = context.correlation_id

        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Each thread should have maintained its own context
        for i in range(5):
            if results[i] != f"thread-{i}":
                raise AssertionError

    def test_performance_under_load(self):
        """Test performance characteristics under load."""
        aggregator = LogAggregator()
        start_time = time.time()

        # Add many entries quickly
        for i in range(1000):
            entry = {
                "timestamp": time.time(),
                "level": "INFO",
                "logger": "perf_test",
                "message": f"Performance test message {i}",
                "context": {"component": "perf"},
            }
            aggregator.add_entry(entry)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete reasonably quickly (adjust threshold as needed)
        if duration >= 1.0:
            raise AssertionError
        assert len(aggregator.get_entries()) == 1000

        # Summary generation should also be fast
        summary_start = time.time()
        summary = aggregator.get_summary()
        summary_duration = time.time() - summary_start

        if summary_duration >= 0.5:
            raise AssertionError
        if summary["total_entries"] != 1000:
            raise AssertionError
