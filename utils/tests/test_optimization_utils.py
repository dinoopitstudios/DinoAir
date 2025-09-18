"""Comprehensive tests for utils.optimization_utils module."""

import threading
import time
from unittest.mock import Mock

import pytest

from utils.optimization_utils import (
    BatchUpdateManager,
    ComponentState,
    DebouncedEventHandler,
    LazyComponentManager,
    LazyImporter,
    ObjectPool,
    OptimizedPatterns,
    SignalConnectionManager,
    StringBuilder,
    batch_update_manager,
    batch_widget_update,
    build_string,
    debounce_event,
    debounced_event_handler,
    execute_batch_updates,
    get_batch_update_manager,
    get_debounced_event_handler,
    get_lazy_component_manager,
    get_signal_connection_manager,
    lazy_component_manager,
    operation_timer,
    safe_string_join,
    signal_connection_manager,
)
from utils.performance_monitor import get_performance_monitor


class TestOptimizedPatterns:
    """Tests for OptimizedPatterns regex utility class."""

    def test_function_pattern_matching(self):
        """Test function pattern matching."""
        code_with_function = "def my_function(arg1, arg2):"
        code_without_function = "class MyClass:"

        match = OptimizedPatterns.match_function(code_with_function)
        assert match is not None
        assert "def my_function" in match.group()

        match = OptimizedPatterns.match_function(code_without_function)
        assert match is None

    def test_email_validation(self):
        """Test email validation pattern."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "test+tag@example.co.uk",
        ]
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "test@",
            "test@domain",
        ]

        for email in valid_emails:
            assert OptimizedPatterns.match_email(email), f"Should validate {email}"

        for email in invalid_emails:
            assert not OptimizedPatterns.match_email(email), f"Should not validate {email}"

    def test_url_validation(self):
        """Test URL validation pattern."""
        valid_urls = [
            "http://example.com",
            "https://www.example.com/path",
            "https://subdomain.example.org/path?query=value",
        ]
        invalid_urls = [
            "ftp://example.com",
            "not-a-url",
            "http://",
            "https://",
        ]

        for url in valid_urls:
            assert OptimizedPatterns.match_url(url), f"Should validate {url}"

        for url in invalid_urls:
            assert not OptimizedPatterns.match_url(url), f"Should not validate {url}"

    def test_file_extension_extraction(self):
        """Test file extension extraction."""
        test_cases = [
            ("file.txt", "txt"),
            ("document.pdf", "pdf"),
            ("script.py", "py"),
            ("archive.tar.gz", "gz"),
            ("no_extension", None),
            ("", None),
        ]

        for filename, expected in test_cases:
            result = OptimizedPatterns.extract_file_extension(filename)
            assert result == expected, f"Expected {expected} for {filename}, got {result}"


class TestStringBuilder:
    """Tests for StringBuilder utility class."""

    def test_string_builder_initialization(self):
        """Test StringBuilder initialization."""
        builder = StringBuilder()
        assert len(builder) == 0
        assert builder.build() == ""

    def test_string_builder_append(self):
        """Test basic string appending."""
        builder = StringBuilder()
        builder.append("Hello")
        builder.append(" ")
        builder.append("World")

        assert len(builder) == 11
        assert builder.build() == "Hello World"

    def test_string_builder_append_line(self):
        """Test appending with newlines."""
        builder = StringBuilder()
        builder.append_line("Line 1")
        builder.append_line("Line 2")
        builder.append_line()  # Empty line

        expected = "Line 1\nLine 2\n\n"
        assert builder.build() == expected

    def test_string_builder_format(self):
        """Test formatted string appending."""
        builder = StringBuilder()
        builder.append_format("Hello {}", "World")
        builder.append_format(" - Count: {count}", count=42)

        assert builder.build() == "Hello World - Count: 42"

    def test_string_builder_clear(self):
        """Test clearing the builder."""
        builder = StringBuilder()
        builder.append("Some text")
        assert len(builder) > 0

        builder.clear()
        assert len(builder) == 0
        assert builder.build() == ""

    def test_string_builder_chaining(self):
        """Test method chaining."""
        result = (
            StringBuilder().append("Hello").append(" ").append("World").append_line("!").build()
        )

        assert result == "Hello World!\n"


class TestObjectPool:
    """Tests for ObjectPool utility class."""

    def test_object_pool_creation(self):
        """Test object pool with factory function."""

        def string_factory():
            return "new_string"

        pool = ObjectPool(string_factory, max_size=5)

        # First get should create new object
        obj1 = pool.get()
        assert obj1 == "new_string"

        # Put it back and get again
        pool.put(obj1)
        obj2 = pool.get()
        assert obj2 == "new_string"
        assert pool.size() == 0  # Should be empty after get

    def test_object_pool_max_size(self):
        """Test object pool respects max size."""

        def list_factory():
            return []

        pool = ObjectPool(list_factory, max_size=2)

        # Fill pool to capacity
        obj1 = pool.get()
        obj2 = pool.get()
        obj3 = pool.get()

        pool.put(obj1)
        pool.put(obj2)
        assert pool.size() == 2

        # Third put should be ignored (exceeds max_size)
        pool.put(obj3)
        assert pool.size() == 2

    def test_object_pool_cleanup(self):
        """Test object pool with cleanup function."""
        cleanup_called = []

        def list_factory():
            return [1, 2, 3]

        def cleanup_func(obj):
            obj.clear()
            cleanup_called.append(True)

        pool = ObjectPool(list_factory, max_size=2, cleanup_func=cleanup_func)

        obj = pool.get()
        assert obj == [1, 2, 3]

        pool.put(obj)
        assert len(cleanup_called) == 1
        assert obj == []  # Should be cleared

    def test_object_pool_thread_safety(self):
        """Test object pool thread safety."""

        def int_factory():
            return 42

        pool = ObjectPool(int_factory, max_size=10)
        errors = []
        results = []

        def worker():
            try:
                for _ in range(50):
                    obj = pool.get()
                    results.append(obj)
                    pool.put(obj)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors
        assert len(results) == 200
        assert all(r == 42 for r in results)


class TestLazyImporter:
    """Tests for LazyImporter utility class."""

    def test_lazy_importer_module_import(self):
        """Test lazy module importing."""
        importer = LazyImporter()

        # Import a standard library module
        math_module = importer.get_module("math")
        assert hasattr(math_module, "sqrt")
        assert math_module.sqrt(4) == 2.0

    def test_lazy_importer_class_import(self):
        """Test lazy class importing."""
        importer = LazyImporter()

        # Import a standard library class
        thread_class = importer.get_class("threading", "Thread")
        assert thread_class is threading.Thread

    def test_lazy_importer_caching(self):
        """Test lazy importer caches modules."""
        importer = LazyImporter()

        # Get same module twice
        module1 = importer.get_module("os")
        module2 = importer.get_module("os")

        # Should be the same object (cached)
        assert module1 is module2

    def test_lazy_importer_clear_cache(self):
        """Test clearing the import cache."""
        importer = LazyImporter()

        # Import and cache a module
        importer.get_module("sys")

        # Clear cache
        importer.clear_cache()

        # Import again - should be fresh import
        sys_module = importer.get_module("sys")
        assert hasattr(sys_module, "version")


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_build_string_empty(self):
        """Test build_string with empty input."""
        assert build_string() == ""

    def test_build_string_single(self):
        """Test build_string with single string."""
        assert build_string("hello") == "hello"

    def test_build_string_multiple(self):
        """Test build_string with multiple strings."""
        result = build_string("Hello", " ", "World", "!")
        assert result == "Hello World!"

    def test_safe_string_join_basic(self):
        """Test safe_string_join with valid strings."""
        parts = ["hello", "world", "test"]
        result = safe_string_join(parts, " ")
        assert result == "hello world test"

    def test_safe_string_join_with_none(self):
        """Test safe_string_join filters None values."""
        parts = ["hello", None, "world", None, "test"]
        result = safe_string_join(parts, " ")
        assert result == "hello world test"

    def test_safe_string_join_with_numbers(self):
        """Test safe_string_join converts non-strings."""
        parts = [1, 2.5, True, "test"]
        result = safe_string_join(parts, ",")
        assert result == "1,2.5,True,test"

    def test_operation_timer_context_manager(self):
        """Test operation_timer context manager."""
        monitor = get_performance_monitor()

        with operation_timer("test_operation", monitor):
            time.sleep(0.01)

        # Should complete without error
        assert True


class TestComponentState:
    """Tests for ComponentState enum."""

    def test_component_state_values(self):
        """Test ComponentState enum values."""
        assert ComponentState.UNINITIALIZED.value == "uninitialized"
        assert ComponentState.INITIALIZING.value == "initializing"
        assert ComponentState.INITIALIZED.value == "initialized"
        assert ComponentState.ERROR.value == "error"


class TestLazyComponentManager:
    """Tests for LazyComponentManager."""

    def test_component_registration(self):
        """Test component registration."""
        manager = LazyComponentManager()

        def factory():
            return "test_component"

        manager.register_component("test", factory)

        # Component should not be initialized yet
        assert len(manager._components) == 1
        assert manager._components["test"].state == ComponentState.UNINITIALIZED

    def test_component_initialization(self):
        """Test component lazy initialization."""
        manager = LazyComponentManager()

        def factory():
            return {"initialized": True}

        manager.register_component("test", factory)

        # Get component - should initialize it
        component = manager.get_component("test")
        assert component == {"initialized": True}
        assert manager._components["test"].state == ComponentState.INITIALIZED

    def test_component_dependency_resolution(self):
        """Test component dependency resolution."""
        manager = LazyComponentManager()
        results = []

        def dep_factory():
            results.append("dependency")
            return "dep_component"

        def main_factory():
            results.append("main")
            return "main_component"

        manager.register_component("dependency", dep_factory)
        manager.register_component("main", main_factory, dependencies=["dependency"])

        # Get main component - should initialize dependency first
        main = manager.get_component("main")
        assert main == "main_component"
        assert results == ["dependency", "main"]

    def test_component_circular_dependency_detection(self):
        """Test circular dependency detection."""
        manager = LazyComponentManager()

        def factory_a():
            return manager.get_component("b")

        def factory_b():
            return manager.get_component("a")

        manager.register_component("a", factory_a, dependencies=["b"])
        manager.register_component("b", factory_b, dependencies=["a"])

        with pytest.raises(RuntimeError, match="Circular dependency"):
            manager.get_component("a")

    def test_component_preloading(self):
        """Test component preloading."""
        manager = LazyComponentManager()

        def factory():
            return "preloaded_component"

        manager.register_component("test", factory)

        # Preload components
        manager.preload_components(["test"])

        # Should already be initialized
        assert manager._components["test"].state == ComponentState.INITIALIZED
        assert manager._components["test"].instance == "preloaded_component"

    def test_initialization_metrics(self):
        """Test initialization metrics."""
        manager = LazyComponentManager()

        manager.register_component("comp1", lambda: "test1")
        manager.register_component("comp2", lambda: "test2")

        # Initialize one component
        manager.get_component("comp1")

        metrics = manager.get_initialization_metrics()
        assert metrics["total_components"] == 2
        assert metrics["initialized_components"] == 1
        assert "comp1" in metrics["initialization_order"]


class TestSignalConnectionManager:
    """Tests for SignalConnectionManager."""

    def test_signal_connection_success(self):
        """Test successful signal connection."""
        manager = SignalConnectionManager()

        # Mock signal and slot
        mock_signal = Mock()
        mock_signal.connect.return_value = "connection_object"
        mock_slot = Mock()

        result = manager.connect_signal(mock_signal, mock_slot, "test_connection")

        assert result is True
        mock_signal.connect.assert_called_once_with(mock_slot)

    def test_signal_connection_validation_failure(self):
        """Test signal connection with invalid signal."""
        manager = SignalConnectionManager()

        # Object without connect method
        invalid_signal = object()
        mock_slot = Mock()

        result = manager.connect_signal(invalid_signal, mock_slot)
        assert result is False

    def test_signal_group_disconnection(self):
        """Test disconnecting signal groups."""
        manager = SignalConnectionManager()

        # Create mock signals
        signals = []
        for i in range(3):
            mock_signal = Mock()
            mock_signal.connect.return_value = f"connection_{i}"
            mock_signal.disconnect = Mock()
            signals.append(mock_signal)

        # Connect signals to same group
        for i, signal in enumerate(signals):
            manager.connect_signal(signal, Mock(), f"conn_{i}", group="test_group")

        # Disconnect group
        count = manager.disconnect_group("test_group")
        assert count == 3

        # All signals should be disconnected
        for signal in signals:
            signal.disconnect.assert_called_once()

    def test_signal_connection_stats(self):
        """Test signal connection statistics."""
        manager = SignalConnectionManager()

        mock_signal = Mock()
        mock_signal.connect.return_value = "connection"

        # Connect some signals
        manager.connect_signal(mock_signal, Mock(), "conn1", group="group1")
        manager.connect_signal(mock_signal, Mock(), "conn2", group="group1")
        manager.connect_signal(mock_signal, Mock(), "conn3", group="group2")

        stats = manager.get_connection_stats()
        assert stats["total_connections"] == 3
        assert stats["connection_groups"] == 2
        assert stats["group_details"]["group1"] == 2
        assert stats["group_details"]["group2"] == 1


class TestDebouncedEventHandler:
    """Tests for DebouncedEventHandler."""

    def test_debounced_event_execution(self):
        """Test debounced event execution."""
        handler = DebouncedEventHandler(delay_ms=50)
        results = []

        def callback(value):
            results.append(value)

        # Trigger same event multiple times quickly
        handler.debounce("test_event", callback, "first")
        handler.debounce("test_event", callback, "second")
        handler.debounce("test_event", callback, "third")

        # Only the last one should execute after delay
        time.sleep(0.1)
        assert results == ["third"]

    def test_debounced_event_cancellation(self):
        """Test debounced event cancellation."""
        handler = DebouncedEventHandler(delay_ms=100)
        results = []

        def callback():
            results.append("executed")

        handler.debounce("test_event", callback)

        # Cancel before execution
        cancelled = handler.cancel_event("test_event")
        assert cancelled is True

        time.sleep(0.15)
        assert results == []  # Should not execute

    def test_debounced_multiple_events(self):
        """Test multiple independent debounced events."""
        handler = DebouncedEventHandler(delay_ms=50)
        results = []

        def callback1():
            results.append("event1")

        def callback2():
            results.append("event2")

        handler.debounce("event1", callback1)
        handler.debounce("event2", callback2)

        time.sleep(0.1)
        assert "event1" in results
        assert "event2" in results


class TestBatchUpdateManager:
    """Tests for BatchUpdateManager."""

    def test_batch_update_queuing(self):
        """Test batch update queuing."""
        manager = BatchUpdateManager()
        results = []

        def update1():
            results.append("update1")

        def update2():
            results.append("update2")

        manager.batch_update(update1)
        manager.batch_update(update2)

        assert manager.get_queue_size() == 2
        assert results == []  # Not executed yet

    def test_batch_update_execution(self):
        """Test batch update execution."""
        manager = BatchUpdateManager()
        results = []

        def update1():
            results.append("update1")

        def update2():
            results.append("update2")

        manager.batch_update(update1)
        manager.batch_update(update2)
        manager.execute_batch()

        assert results == ["update1", "update2"]
        assert manager.get_queue_size() == 0

    def test_batch_update_with_parent_widget(self):
        """Test batch update with parent widget."""
        # Mock widget
        mock_widget = Mock()
        mock_widget.setUpdatesEnabled = Mock()
        mock_widget.update = Mock()

        manager = BatchUpdateManager(mock_widget)

        def update_func():
            pass

        manager.batch_update(update_func)
        manager.execute_batch()

        # Should disable/enable updates and call update
        mock_widget.setUpdatesEnabled.assert_any_call(False)
        mock_widget.setUpdatesEnabled.assert_any_call(True)
        mock_widget.update.assert_called_once()

    def test_batch_update_queue_clearing(self):
        """Test clearing the update queue."""
        manager = BatchUpdateManager()

        manager.batch_update(lambda: None)
        manager.batch_update(lambda: None)

        assert manager.get_queue_size() == 2

        cleared_count = manager.clear_queue()
        assert cleared_count == 2
        assert manager.get_queue_size() == 0


class TestGlobalInstances:
    """Tests for global instances and accessor functions."""

    def test_global_instances_exist(self):
        """Test that global instances are created."""
        assert lazy_component_manager is not None
        assert signal_connection_manager is not None
        assert debounced_event_handler is not None
        assert batch_update_manager is not None

    def test_accessor_functions(self):
        """Test global accessor functions."""
        assert get_lazy_component_manager() is lazy_component_manager
        assert get_signal_connection_manager() is signal_connection_manager
        assert get_debounced_event_handler() is debounced_event_handler
        assert get_batch_update_manager() is batch_update_manager

    def test_convenience_functions(self):
        """Test convenience wrapper functions."""
        # Test debounce_event function
        results = []

        def callback():
            results.append("executed")

        debounce_event("test", callback)
        time.sleep(0.1)

        # Should execute without error
        assert True

    def test_batch_widget_update_function(self):
        """Test batch_widget_update convenience function."""
        mock_widget = Mock()
        results = []

        def update():
            results.append("updated")

        batch_widget_update(mock_widget, update)
        execute_batch_updates()

        assert results == ["updated"]


class TestIntegrationScenarios:
    """Integration tests combining multiple optimization features."""

    @pytest.mark.integration
    def test_full_optimization_workflow(self):
        """Test complete optimization workflow."""
        # Use StringBuilder with ObjectPool
        builder_pool = ObjectPool(StringBuilder, max_size=5)

        builder = builder_pool.get()
        builder.clear()
        builder.append("Hello").append(" ").append("World")
        result = builder.build()

        assert result == "Hello World"
        builder_pool.put(builder)

    @pytest.mark.integration
    def test_lazy_loading_with_components(self):
        """Test lazy loading integration."""
        manager = LazyComponentManager()

        def create_expensive_resource():
            time.sleep(0.01)  # Simulate expensive operation
            return {"data": "expensive_resource"}

        manager.register_component("expensive", create_expensive_resource)

        # Component should not be created yet
        assert manager._components["expensive"].state == ComponentState.UNINITIALIZED

        # Access should trigger creation
        resource = manager.get_component("expensive")
        assert resource["data"] == "expensive_resource"
        assert manager._components["expensive"].state == ComponentState.INITIALIZED

    @pytest.mark.boundary
    def test_error_handling_boundaries(self):
        """Test error handling at component boundaries."""
        manager = LazyComponentManager()

        def failing_factory():
            raise RuntimeError("Initialization failed")

        manager.register_component("failing", failing_factory)

        with pytest.raises(RuntimeError, match="Failed to initialize component"):
            manager.get_component("failing")

        assert manager._components["failing"].state == ComponentState.ERROR

    @pytest.mark.slow
    def test_performance_characteristics(self):
        """Test performance characteristics of optimization utilities."""
        # Test pattern matching performance
        code_samples = [f"def function_{i}(arg):" for i in range(1000)]

        start_time = time.perf_counter()
        for code in code_samples:
            OptimizedPatterns.match_function(code)
        end_time = time.perf_counter()

        # Should complete quickly (less than 0.1 seconds for 1000 patterns)
        assert (end_time - start_time) < 0.1

    @pytest.mark.bulk
    def test_bulk_operations(self):
        """Test bulk operations with optimization utilities."""
        # Create many components rapidly
        manager = LazyComponentManager()

        for i in range(100):
            manager.register_component(f"comp_{i}", lambda i=i: f"component_{i}")

        # Preload all at once
        component_names = [f"comp_{i}" for i in range(100)]
        manager.preload_components(component_names)

        # Verify all are initialized
        metrics = manager.get_initialization_metrics()
        assert metrics["initialized_components"] == 100
