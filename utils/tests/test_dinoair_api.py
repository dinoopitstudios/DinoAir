"""
Test suite for DinoAir public API

Tests the stable public API while ensuring internal implementation details
remain hidden. All tests should use the public API only.
"""

import os
import tempfile
import time
import unittest

# Import only from public API
from utils.dinoair_api import (
    PerformanceConfig,
    PerformanceMonitor,
    TelemetryConfig,
    TelemetryManager,
    configure_performance,
    configure_telemetry,
    disable_performance_monitoring,
    disable_telemetry,
    enable_performance_monitoring,
    enable_telemetry,
    export_telemetry,
    get_performance_monitor,
    get_telemetry_manager,
    monitor_performance,
    performance_decorator,
)


class TestPerformanceMonitorAPI(unittest.TestCase):
    """Test the public PerformanceMonitor API."""

    def setUp(self):
        """Set up test environment."""
        self.monitor = PerformanceMonitor()

    def test_basic_operation_monitoring(self):
        """Test basic operation start/end monitoring."""
        operation_id = self.monitor.start_operation("test_operation")
        assert isinstance(operation_id, str)
        if "test_operation" not in operation_id:
            raise AssertionError

        # Wait briefly to ensure measurable duration
        time.sleep(0.01)

        metrics = self.monitor.end_operation(operation_id)
        # Metrics may be None if monitoring disabled, that's OK
        if metrics:
            if metrics.operation != "test_operation":
                raise AssertionError
            if metrics.duration <= 0:
                raise AssertionError

    def test_context_manager_monitoring(self):
        """Test performance monitoring via context manager."""
        with self.monitor.monitor_operation("context_test") as operation_id:
            assert isinstance(operation_id, str)
            time.sleep(0.01)  # Ensure measurable duration

        # Context manager should handle cleanup automatically

    def test_custom_metadata(self):
        """Test operation monitoring with custom metadata."""
        metadata = {"user_id": "test123", "action": "upload"}
        operation_id = self.monitor.start_operation("file_upload", **metadata)

        time.sleep(0.01)
        metrics = self.monitor.end_operation(operation_id)

        if metrics and hasattr(metrics, "metadata"):
            for key, value in metadata.items():
                if getattr(metrics.metadata, key, None) != value:
                    raise AssertionError

    def test_metrics_summary(self):
        """Test getting metrics summary."""
        summary = self.monitor.get_metrics_summary()
        assert isinstance(summary, dict)

    def test_clear_metrics(self):
        """Test clearing all metrics."""
        # Start and end some operations
        op1 = self.monitor.start_operation("op1")
        self.monitor.end_operation(op1)

        # Clear metrics
        self.monitor.clear_metrics()

        # Should not raise exception
        summary = self.monitor.get_metrics_summary()
        assert isinstance(summary, dict)


class TestTelemetryManagerAPI(unittest.TestCase):
    """Test the public TelemetryManager API."""

    def setUp(self):
        """Set up test environment."""
        self.manager = TelemetryManager()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "test_telemetry.json")

    def tearDown(self):
        """Clean up test environment."""
        self.manager.disable()
        if os.path.exists(self.temp_file):
            os.unlink(self.temp_file)
        os.rmdir(self.temp_dir)

    def test_enable_disable_telemetry(self):
        """Test enabling and disabling telemetry."""
        # Test enabling
        self.manager.enable(
            export_format="json", export_destination="file", output_file=self.temp_file
        )

        # Test disabling
        self.manager.disable()

    def test_file_export_configuration(self):
        """Test configuring file export."""
        self.manager.enable(
            export_format="json",
            export_destination="file",
            output_file=self.temp_file,
            export_interval_seconds=1.0,
            max_metrics_per_operation=50,
        )

        metrics_count = self.manager.get_metrics_count()
        assert isinstance(metrics_count, dict)

    def test_console_export_configuration(self):
        """Test configuring console export."""
        self.manager.enable(
            export_format="json", export_destination="console", max_total_metrics=1000
        )

        # Should not raise exception
        self.manager.clear_metrics()

    def test_force_export(self):
        """Test forcing immediate export."""
        self.manager.enable(
            export_format="json", export_destination="file", output_file=self.temp_file
        )

        result = self.manager.force_export()
        assert isinstance(result, bool)

    def test_configure_after_creation(self):
        """Test configuring telemetry after manager creation."""
        # Configure various settings
        self.manager.configure(
            enabled=True, export_format="json", max_metrics_per_operation=200, retention_hours=12.0
        )

        # Should not raise exception
        count = self.manager.get_metrics_count()
        assert isinstance(count, dict)


class TestGlobalFunctions(unittest.TestCase):
    """Test global convenience functions."""

    def test_get_performance_monitor(self):
        """Test getting global performance monitor."""
        monitor = get_performance_monitor()
        assert isinstance(monitor, PerformanceMonitor)

    def test_get_telemetry_manager(self):
        """Test getting global telemetry manager."""
        manager = get_telemetry_manager()
        assert isinstance(manager, TelemetryManager)

    def test_enable_disable_performance_monitoring(self):
        """Test global performance monitoring control."""
        # Test with config
        config = PerformanceConfig(enabled=True, max_metrics_retained=500)
        enable_performance_monitoring(config)
        disable_performance_monitoring()

    def test_enable_disable_telemetry(self):
        """Test global telemetry control."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_file = f.name

        try:
            enable_telemetry(export_format="json", export_destination="file", output_file=temp_file)

            result = export_telemetry()
            assert isinstance(result, bool)

            disable_telemetry()

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_monitor_performance_context(self):
        """Test monitor_performance context manager."""
        with monitor_performance("global_test_operation") as operation_id:
            assert isinstance(operation_id, str)
            time.sleep(0.01)

    def test_performance_decorator(self):
        """Test performance_decorator functionality."""

        @performance_decorator("decorated_function")
        def test_function(x, y):
            time.sleep(0.01)
            return x + y

        result = test_function(2, 3)
        if result != 5:
            raise AssertionError

    def test_performance_decorator_auto_name(self):
        """Test performance decorator with auto-naming."""

        @performance_decorator()
        def another_test_function():
            return "test"

        result = another_test_function()
        if result != "test":
            raise AssertionError

    def test_configure_functions(self):
        """Test global configuration functions."""
        # Should not raise exceptions
        configure_performance(enabled=True, max_metrics_retained=100)
        configure_telemetry(enabled=False, max_total_metrics=500)


class TestConfigurationClasses(unittest.TestCase):
    """Test configuration classes."""

    def test_performance_config_creation(self):
        """Test PerformanceConfig creation."""
        config = PerformanceConfig(
            enabled=True, max_metrics_retained=1000, enable_memory_tracking=True
        )
        assert isinstance(config, PerformanceConfig)

    def test_telemetry_config_creation(self):
        """Test TelemetryConfig creation."""
        config = TelemetryConfig(
            enabled=True, export_format="json", export_destination="file", max_total_metrics=5000
        )
        assert isinstance(config, TelemetryConfig)


class TestAPIStability(unittest.TestCase):
    """Test that the API provides stable interface."""

    def test_all_exports_available(self):
        """Test that all expected exports are available."""
        from utils.dinoair_api import __all__

        expected_exports = {
            "PerformanceMonitor",
            "TelemetryManager",
            "PerformanceConfig",
            "PerformanceMetrics",
            "TelemetryConfig",
            "get_performance_monitor",
            "enable_performance_monitoring",
            "disable_performance_monitoring",
            "monitor_performance",
            "performance_decorator",
            "configure_performance",
            "get_telemetry_manager",
            "enable_telemetry",
            "disable_telemetry",
            "export_telemetry",
            "configure_telemetry",
        }

        for export in expected_exports:
            if export not in __all__:
                raise AssertionError(f"Missing export: {export}")

    def test_no_internal_exports(self):
        """Test that internal functions are not exported."""
        from utils.dinoair_api import __all__

        # Check that no exports start with underscore
        for export in __all__:
            if export.startswith("_"):
                raise AssertionError(f"Internal function exported: {export}")

    def test_graceful_degradation(self):
        """Test that API works even if internal modules fail."""
        # This would require mocking the imports, but at minimum
        # we can test that the classes can be instantiated
        monitor = PerformanceMonitor()
        manager = TelemetryManager()

        # Should not raise exceptions even if backends unavailable
        monitor.start_operation("test")
        manager.get_metrics_count()


class TestIntegration(unittest.TestCase):
    """Test integration between performance monitoring and telemetry."""

    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.telemetry_file = os.path.join(self.temp_dir, "integration_test.json")

    def tearDown(self):
        """Clean up integration test environment."""
        disable_telemetry()
        disable_performance_monitoring()

        if os.path.exists(self.telemetry_file):
            os.unlink(self.telemetry_file)
        os.rmdir(self.temp_dir)

    def test_performance_with_telemetry(self):
        """Test that performance monitoring works with telemetry enabled."""
        # Enable both systems
        enable_performance_monitoring()
        enable_telemetry(
            export_format="json", export_destination="file", output_file=self.telemetry_file
        )

        # Perform monitored operations
        with monitor_performance("integration_test"):
            time.sleep(0.01)

        # Force export to verify telemetry
        result = export_telemetry()
        assert isinstance(result, bool)

    @performance_decorator("integration_decorated_test")
    def _test_decorated_function(self):
        """Helper function for testing decorator integration."""
        time.sleep(0.01)
        return "success"

    def test_decorator_with_telemetry(self):
        """Test that decorated functions work with telemetry."""
        enable_telemetry(export_format="json", export_destination="console")

        result = self._test_decorated_function()
        if result != "success":
            raise AssertionError


if __name__ == "__main__":
    unittest.main()
