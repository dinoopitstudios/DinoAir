"""
Unit tests for performance_monitor.py module.
Tests performance monitoring, metrics collection, and decorators.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from ..performance_monitor import (
    PerformanceConfig,
    PerformanceContext,
    PerformanceMetrics,
    PerformanceMonitor,
    configure_performance_monitoring,
    disable_performance_monitoring,
    enable_performance_monitoring,
    get_performance_monitor,
    performance_monitor_decorator,
)


# Prefer public API if available; fall back to legacy-compatible shims
try:
    from ..performance_monitor import end_timer, performance_timer, start_timer
except ImportError:  # Backwards compatibility with private names
    from ..performance_monitor import (
        _end_timer as end_timer,
        _performance_timer as performance_timer,
        _start_timer as start_timer,
    )


class TestPerformanceMetrics:
    """Test cases for PerformanceMetrics dataclass."""

    def test_performance_metrics_creation(self):
        """Test PerformanceMetrics creation with all fields."""
        metrics = PerformanceMetrics(
            operation="test_operation",
            duration=1.5,
            memory_usage=1024,
            cpu_usage=25.5,
            custom_metrics={"requests": 10, "errors": 2},
            timestamp=1234567890.0,
            thread_id=123,
        )

        assert metrics.operation == "test_operation"
        assert metrics.duration == 1.5
        assert metrics.memory_usage == 1024
        assert metrics.cpu_usage == 25.5
        assert metrics.custom_metrics == {"requests": 10, "errors": 2}
        assert metrics.timestamp == 1234567890.0
        assert metrics.thread_id == 123

    def test_performance_metrics_defaults(self):
        """Test PerformanceMetrics with default values."""
        metrics = PerformanceMetrics(operation="test", duration=2.0)

        assert metrics.operation == "test"
        assert metrics.duration == 2.0
        assert metrics.memory_usage is None
        assert metrics.cpu_usage is None
        assert metrics.custom_metrics == {}
        assert isinstance(metrics.timestamp, float)
        assert isinstance(metrics.thread_id, int)

    def test_performance_metrics_post_init(self):
        """Test PerformanceMetrics post-initialization behavior."""
        metrics = PerformanceMetrics(operation="test", duration=1.0)

        # Should set timestamp and thread_id automatically
        assert metrics.timestamp is not None
        assert metrics.thread_id is not None


class TestPerformanceConfig:
    """Test cases for PerformanceConfig dataclass."""

    def test_performance_config_defaults(self):
        """Test PerformanceConfig with default values."""
        config = PerformanceConfig()

        assert config.enabled is True
        assert config.sampling_rate == 1.0
        assert config.memory_threshold_mb is None
        assert config.cpu_threshold_percent is None
        assert config.duration_threshold_seconds is None
        assert config.max_metrics_retained == 1000
        assert config.alert_on_thresholds is True
        assert config.log_level == "INFO"

    def test_performance_config_custom_values(self):
        """Test PerformanceConfig with custom values."""
        config = PerformanceConfig(
            enabled=False,
            sampling_rate=0.5,
            memory_threshold_mb=512.0,
            cpu_threshold_percent=80.0,
            duration_threshold_seconds=5.0,
            max_metrics_retained=500,
            alert_on_thresholds=False,
            log_level="WARNING",
        )

        assert config.enabled is False
        assert config.sampling_rate == 0.5
        assert config.memory_threshold_mb == 512.0
        assert config.cpu_threshold_percent == 80.0
        assert config.duration_threshold_seconds == 5.0
        assert config.max_metrics_retained == 500
        assert config.alert_on_thresholds is False
        assert config.log_level == "WARNING"


class TestPerformanceMonitor:
    """Test cases for PerformanceMonitor class."""

    def test_performance_monitor_initialization(self):
        """Test PerformanceMonitor initialization."""
        config = PerformanceConfig(max_metrics_retained=100)
        monitor = PerformanceMonitor(config)

        assert monitor.config == config
        assert len(monitor._metrics) == 0
        assert len(monitor._active_timers) == 0

    def test_performance_monitor_default_config(self):
        """Test PerformanceMonitor with default config."""
        monitor = PerformanceMonitor()

        assert monitor.config.enabled is True
        assert monitor.config.max_metrics_retained == 1000

    def test_should_sample_enabled_full_rate(self):
        """Test sampling when enabled with full rate."""
        monitor = PerformanceMonitor(PerformanceConfig(enabled=True, sampling_rate=1.0))

        assert monitor._should_sample() is True

    def test_should_sample_disabled(self):
        """Test sampling when disabled."""
        monitor = PerformanceMonitor(PerformanceConfig(enabled=False))

        assert monitor._should_sample() is False

    def test_should_sample_partial_rate(self):
        """Test sampling with partial rate."""
        monitor = PerformanceMonitor(PerformanceConfig(enabled=True, sampling_rate=0.5))

        # With 0.5 sampling rate, should sample approximately half the time
        samples = [monitor._should_sample() for _ in range(100)]
        true_count = sum(samples)

        # Should be roughly 50, but allow some variance
        assert 30 <= true_count <= 70

    @patch("utils.performance_monitor.HAS_PSUTIL", True)
    @patch("utils.performance_monitor.psutil")
    def test_collect_system_metrics_with_psutil(self, mock_psutil):
        """Test collecting system metrics when psutil is available."""
        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(rss=1048576)  # 1MB
        mock_process.cpu_percent.return_value = 15.5
        mock_psutil.Process.return_value = mock_process

        monitor = PerformanceMonitor()
        metrics = monitor._collect_system_metrics()

        assert metrics["memory_mb"] == 1.0  # 1048576 / 1024 / 1024
        assert metrics["cpu_percent"] == 15.5

    @patch("utils.performance_monitor.HAS_PSUTIL", False)
    def test_collect_system_metrics_without_psutil(self):
        """Test collecting system metrics when psutil is not available."""
        monitor = PerformanceMonitor()
        metrics = monitor._collect_system_metrics()

        assert "memory_mb" not in metrics
        assert "cpu_percent" not in metrics

    def test_add_custom_collector(self):
        """Test adding custom metrics collector."""
        monitor = PerformanceMonitor()

        def custom_collector():
            return 42

        monitor.add_custom_collector("test_metric", custom_collector)
        metrics = monitor._collect_system_metrics()

        assert metrics["test_metric"] == 42

    def test_remove_custom_collector(self):
        """Test removing custom metrics collector."""
        monitor = PerformanceMonitor()

        def custom_collector():
            return 42

        monitor.add_custom_collector("test_metric", custom_collector)
        monitor.remove_custom_collector("test_metric")

        metrics = monitor._collect_system_metrics()
        assert "test_metric" not in metrics

    def test_start_operation(self):
        """Test starting an operation."""
        monitor = PerformanceMonitor()

        operation_id = monitor.start_operation("test_operation", user_id=123)

        assert operation_id is not None
        assert operation_id in monitor._active_timers
        assert monitor._active_timers[operation_id]["operation"] == "test_operation"
        assert "user_id" in monitor._active_timers[operation_id]["context"]

    def test_start_operation_disabled(self):
        """Test starting operation when monitoring is disabled."""
        monitor = PerformanceMonitor(PerformanceConfig(enabled=False))

        operation_id = monitor.start_operation("test_operation")

        assert operation_id == ""  # Empty string when disabled

    def test_end_operation(self):
        """Test ending an operation."""
        monitor = PerformanceMonitor()

        # Start operation
        operation_id = monitor.start_operation("test_operation")

        # End operation
        metrics = monitor.end_operation(operation_id)

        assert metrics is not None
        assert metrics.operation == "test_operation"
        assert isinstance(metrics.duration, float)
        assert operation_id not in monitor._active_timers

    def test_end_operation_not_found(self):
        """Test ending non-existent operation."""
        monitor = PerformanceMonitor()

        metrics = monitor.end_operation("nonexistent")

        assert metrics is None

    def test_end_operation_disabled(self):
        """Test ending operation when monitoring is disabled."""
        monitor = PerformanceMonitor(PerformanceConfig(enabled=False))

        metrics = monitor.end_operation("any_id")

        assert metrics is None

    def test_get_metrics_single_operation(self):
        """Test getting metrics for single operation."""
        monitor = PerformanceMonitor()

        # Add some metrics
        metrics1 = PerformanceMetrics("test_op", 1.0, timestamp=1000.0)
        metrics2 = PerformanceMetrics("test_op", 2.0, timestamp=1001.0)

        monitor._metrics["test_op"].append(metrics1)
        monitor._metrics["test_op"].append(metrics2)

        result = monitor.get_metrics("test_op")

        assert result["count"] == 2
        assert result["avg_duration"] == 1.5
        assert result["min_duration"] == 1.0
        assert result["max_duration"] == 2.0
        assert result["total_duration"] == 3.0
        assert result["latest"] == metrics2

    def test_get_metrics_all_operations(self):
        """Test getting metrics for all operations."""
        monitor = PerformanceMonitor()

        # Add metrics for different operations
        monitor._metrics["op1"].append(PerformanceMetrics("op1", 1.0))
        monitor._metrics["op2"].append(PerformanceMetrics("op2", 2.0))

        result = monitor.get_metrics()

        assert "op1" in result
        assert "op2" in result
        assert result["op1"]["count"] == 1
        assert result["op2"]["count"] == 1

    def test_get_metrics_empty_operation(self):
        """Test getting metrics for operation with no data."""
        monitor = PerformanceMonitor()

        result = monitor.get_metrics("nonexistent")

        assert result == {}

    def test_clear_metrics_single_operation(self):
        """Test clearing metrics for single operation."""
        monitor = PerformanceMonitor()

        monitor._metrics["test_op"].append(PerformanceMetrics("test_op", 1.0))
        assert len(monitor._metrics["test_op"]) == 1

        monitor.clear_metrics("test_op")
        assert len(monitor._metrics["test_op"]) == 0

    def test_clear_metrics_all_operations(self):
        """Test clearing all metrics."""
        monitor = PerformanceMonitor()

        monitor._metrics["op1"].append(PerformanceMetrics("op1", 1.0))
        monitor._metrics["op2"].append(PerformanceMetrics("op2", 2.0))

        monitor.clear_metrics()
        assert len(monitor._metrics) == 0

    def test_get_active_operations(self):
        """Test getting list of active operations."""
        monitor = PerformanceMonitor()

        id1 = monitor.start_operation("op1")
        id2 = monitor.start_operation("op2")

        active = monitor.get_active_operations()
        assert id1 in active
        assert id2 in active

    def test_update_config(self):
        """Test updating monitor configuration."""
        monitor = PerformanceMonitor()

        monitor.update_config(enabled=False, sampling_rate=0.5)

        assert monitor.config.enabled is False
        assert monitor.config.sampling_rate == 0.5

    def test_check_thresholds_duration_exceeded(self):
        """Test threshold checking for duration."""
        monitor = PerformanceMonitor(
            PerformanceConfig(duration_threshold_seconds=1.0, alert_on_thresholds=True)
        )

        metrics = PerformanceMetrics("test", 2.0)  # Exceeds threshold

        with patch("utils.performance_monitor.logger") as mock_logger:
            monitor._check_thresholds(metrics)

            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            assert "Duration 2.000s exceeds threshold 1.0s" in call_args[0][1]

    def test_check_thresholds_memory_exceeded(self):
        """Test threshold checking for memory."""
        monitor = PerformanceMonitor(
            PerformanceConfig(memory_threshold_mb=1.0, alert_on_thresholds=True)
        )

        # 2MB exceeds 1MB threshold
        metrics = PerformanceMetrics("test", 1.0, memory_usage=2 * 1024 * 1024)

        with patch("utils.performance_monitor.logger") as mock_logger:
            monitor._check_thresholds(metrics)

            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            assert "Memory 2.0MB exceeds threshold 1.0MB" in call_args[0][1]

    def test_check_thresholds_cpu_exceeded(self):
        """Test threshold checking for CPU."""
        monitor = PerformanceMonitor(
            PerformanceConfig(cpu_threshold_percent=50.0, alert_on_thresholds=True)
        )

        metrics = PerformanceMetrics("test", 1.0, cpu_usage=75.0)  # Exceeds threshold

        with patch("utils.performance_monitor.logger") as mock_logger:
            monitor._check_thresholds(metrics)

            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            assert "CPU 75.0% exceeds threshold 50.0%" in call_args[0][1]

    def test_check_thresholds_no_alerts(self):
        """Test threshold checking when alerts are disabled."""
        monitor = PerformanceMonitor(
            PerformanceConfig(duration_threshold_seconds=1.0, alert_on_thresholds=False)
        )

        metrics = PerformanceMetrics("test", 2.0)  # Would exceed threshold

        with patch("utils.performance_monitor.logger") as mock_logger:
            monitor._check_thresholds(metrics)

            mock_logger.log.assert_not_called()


class TestPerformanceMonitorDecorator:
    """Test cases for performance_monitor_decorator."""

    def test_decorator_basic_usage(self):
        """Test basic decorator usage."""
        monitor = PerformanceMonitor()

        @performance_monitor_decorator(monitor=monitor)
        def test_function():
            time.sleep(0.01)
            return "result"

        result = test_function()

        assert result == "result"
        assert len(monitor._metrics) > 0

    def test_decorator_with_operation_name(self):
        """Test decorator with custom operation name."""
        monitor = PerformanceMonitor()

        @performance_monitor_decorator("custom_operation", monitor=monitor)
        def test_function():
            return "result"

        test_function()

        assert "custom_operation" in monitor._metrics

    def test_decorator_with_context(self):
        """Test decorator with context parameters."""
        monitor = PerformanceMonitor()

        @performance_monitor_decorator("test_op", monitor=monitor, user="test_user")
        def test_function():
            return "result"

        test_function()

        # Check that context was stored
        metrics_list = list(monitor._metrics["test_op"])
        assert len(metrics_list) == 1
        assert metrics_list[0].custom_metrics.get("user") == "test_user"


class TestPerformanceContext:
    """Test cases for PerformanceContext context manager."""

    def test_context_manager_basic_usage(self):
        """Test basic context manager usage."""
        monitor = PerformanceMonitor()

        with PerformanceContext("test_operation", monitor=monitor):
            time.sleep(0.01)

        assert "test_operation" in monitor._metrics
        metrics_list = list(monitor._metrics["test_operation"])
        assert len(metrics_list) == 1
        assert metrics_list[0].duration > 0

    def test_context_manager_with_context(self):
        """Test context manager with context parameters."""
        monitor = PerformanceMonitor()

        with PerformanceContext("test_op", monitor=monitor, request_id="123"):
            pass

        metrics_list = list(monitor._metrics["test_op"])
        assert metrics_list[0].custom_metrics.get("request_id") == "123"

    def test_context_manager_exception_handling(self):
        """Test context manager handles exceptions properly."""
        monitor = PerformanceMonitor()

        with pytest.raises(ValueError):
            with PerformanceContext("failing_operation", monitor=monitor):
                raise ValueError("Test error")

        # Should still record metrics despite exception
        assert "failing_operation" in monitor._metrics


class TestGlobalFunctions:
    """Test cases for global utility functions."""

    def test_get_performance_monitor(self):
        """Test getting global performance monitor."""
        monitor = get_performance_monitor()

        assert isinstance(monitor, PerformanceMonitor)
        assert monitor is get_performance_monitor()  # Same instance

    def test_enable_performance_monitoring(self):
        """Test enabling global performance monitoring."""
        enable_performance_monitoring()

        monitor = get_performance_monitor()
        assert monitor.config.enabled is True

    def test_disable_performance_monitoring(self):
        """Test disabling global performance monitoring."""
        disable_performance_monitoring()

        monitor = get_performance_monitor()
        assert monitor.config.enabled is False

    def test_configure_performance_monitoring(self):
        """Test configuring global performance monitoring."""
        configure_performance_monitoring(sampling_rate=0.5, max_metrics_retained=500)

        monitor = get_performance_monitor()
        assert monitor.config.sampling_rate == 0.5
        assert monitor.config.max_metrics_retained == 500


class TestBackwardsCompatibility:
    """Test cases for backwards compatibility functions."""

    def setup_method(self):
        """Reset global monitor state before each backwards compatibility test."""
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        enable_performance_monitoring()
        configure_performance_monitoring(sampling_rate=1.0)

    def test_start_timer_end_timer(self):
        """Test backwards compatible timer functions."""
        monitor = get_performance_monitor()

        start_timer("legacy_operation")
        time.sleep(0.01)
        end_timer("legacy_operation")

        assert "legacy_operation" in monitor._metrics

    def test_performance_timer_context_manager(self):
        """Test backwards compatible context manager."""
        monitor = get_performance_monitor()

        with performance_timer("legacy_timer"):
            time.sleep(0.01)

        assert "legacy_timer" in monitor._metrics


class TestPerformanceMonitorIntegration:
    """Integration tests for performance monitoring."""

    def test_full_workflow(self):
        """Test complete performance monitoring workflow."""
        monitor = PerformanceMonitor(
            PerformanceConfig(enabled=True, sampling_rate=1.0, max_metrics_retained=10)
        )

        # Start multiple operations
        id1 = monitor.start_operation("operation1", phase="setup")
        time.sleep(0.01)
        monitor.end_operation(id1)

        id2 = monitor.start_operation("operation2", phase="execution")
        time.sleep(0.02)
        monitor.end_operation(id2)

        # Check metrics
        metrics = monitor.get_metrics()

        assert "operation1" in metrics
        assert "operation2" in metrics
        assert metrics["operation1"]["count"] == 1
        assert metrics["operation2"]["count"] == 1
        assert metrics["operation1"]["avg_duration"] > 0
        assert metrics["operation2"]["avg_duration"] > metrics["operation1"]["avg_duration"]

    def test_decorator_and_context_combination(self):
        """Test combining decorator and context manager."""
        monitor = PerformanceMonitor()

        @performance_monitor_decorator("decorated_func", monitor=monitor)
        def decorated_function():
            with PerformanceContext("inner_operation", monitor=monitor):
                time.sleep(0.01)
            return "done"

        result = decorated_function()

        assert result == "done"
        assert "decorated_func" in monitor._metrics
        assert "inner_operation" in monitor._metrics
