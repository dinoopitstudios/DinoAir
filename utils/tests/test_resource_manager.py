"""
Unit tests for resource_manager.py module.
Tests resource lifecycle management, shutdown sequencing, and thread safety.
"""

from datetime import datetime
import threading
import time
from unittest.mock import MagicMock, patch

from ..resource_manager import (
    ResourceInfo,
    ResourceManager,
    ResourceState,
    ResourceType,
    get_resource_manager,
    register_resource,
    shutdown_all_resources,
)


class TestResourceType:
    """Test cases for ResourceType enum."""

    def test_resource_type_values(self):
        """Test ResourceType enum values."""
        if ResourceType.DATABASE.value != "database":
            raise AssertionError
        if ResourceType.THREAD.value != "thread":
            raise AssertionError
        if ResourceType.TIMER.value != "timer":
            raise AssertionError
        if ResourceType.WATCHDOG.value != "watchdog":
            raise AssertionError
        if ResourceType.FILE_HANDLE.value != "file_handle":
            raise AssertionError
        if ResourceType.NETWORK.value != "network":
            raise AssertionError
        if ResourceType.GUI_COMPONENT.value != "gui_component":
            raise AssertionError
        if ResourceType.CUSTOM.value != "custom":
            raise AssertionError


class TestResourceState:
    """Test cases for ResourceState enum."""

    def test_resource_state_values(self):
        """Test ResourceState enum values."""
        if ResourceState.INITIALIZING.value != "initializing":
            raise AssertionError
        if ResourceState.ACTIVE.value != "active":
            raise AssertionError
        if ResourceState.SHUTTING_DOWN.value != "shutting_down":
            raise AssertionError
        if ResourceState.SHUTDOWN.value != "shutdown":
            raise AssertionError
        if ResourceState.ERROR.value != "error":
            raise AssertionError


class TestResourceInfo:
    """Test cases for ResourceInfo dataclass."""

    def test_resource_info_creation_full(self):
        """Test ResourceInfo creation with all fields."""
        created_time = datetime.now()
        shutdown_time = datetime.now()

        def cleanup_func():
            pass

        info = ResourceInfo(
            resource_id="test_resource",
            resource_type=ResourceType.DATABASE,
            resource="mock_db_connection",
            cleanup_func=cleanup_func,
            shutdown_timeout=15.0,
            priority=50,
            state=ResourceState.ACTIVE,
            created_at=created_time,
            shutdown_at=shutdown_time,
            dependencies=["dep1", "dep2"],
            metadata={"connection_string": "test://localhost"},
        )

        if info.resource_id != "test_resource":
            raise AssertionError
        if info.resource_type != ResourceType.DATABASE:
            raise AssertionError
        if info.resource != "mock_db_connection":
            raise AssertionError
        if info.cleanup_func != cleanup_func:
            raise AssertionError
        if info.shutdown_timeout != 15.0:
            raise AssertionError
        if info.priority != 50:
            raise AssertionError
        if info.state != ResourceState.ACTIVE:
            raise AssertionError
        if info.created_at != created_time:
            raise AssertionError
        if info.shutdown_at != shutdown_time:
            raise AssertionError
        if info.dependencies != ["dep1", "dep2"]:
            raise AssertionError
        if info.metadata != {"connection_string": "test://localhost"}:
            raise AssertionError

    def test_resource_info_defaults(self):
        """Test ResourceInfo with default values."""
        info = ResourceInfo(
            resource_id="test", resource_type=ResourceType.CUSTOM, resource="test_resource"
        )

        assert info.cleanup_func is None
        if info.shutdown_timeout != 10.0:
            raise AssertionError
        if info.priority != 100:
            raise AssertionError
        if info.state != ResourceState.INITIALIZING:
            raise AssertionError
        assert isinstance(info.created_at, datetime)
        assert info.shutdown_at is None
        if info.dependencies != []:
            raise AssertionError
        if info.metadata != {}:
            raise AssertionError


class TestResourceManager:
    """Test cases for ResourceManager class."""

    def test_resource_manager_initialization(self):
        """Test ResourceManager initialization."""
        manager = ResourceManager()

        assert len(manager.list_resources()) == 0
        if manager._shutdown_initiated is not False:
            raise AssertionError

    def test_register_resource_basic(self):
        """Test basic resource registration."""
        manager = ResourceManager()
        resource = "test_resource"

        manager.register_resource(
            resource_id="test_id", resource=resource, resource_type=ResourceType.CUSTOM
        )

        info = manager.get_resource_info("test_id")
        assert info is not None
        if info.resource_id != "test_id":
            raise AssertionError
        if info.resource != resource:
            raise AssertionError
        if info.resource_type != ResourceType.CUSTOM:
            raise AssertionError
        if info.state != ResourceState.ACTIVE:
            raise AssertionError

    def test_register_resource_with_cleanup(self):
        """Test resource registration with cleanup function."""
        manager = ResourceManager()
        resource = MagicMock()
        cleanup_called = []

        def cleanup_func():
            cleanup_called.append(True)

        manager.register_resource(
            resource_id="test_id",
            resource=resource,
            resource_type=ResourceType.CUSTOM,
            cleanup_func=cleanup_func,
            shutdown_timeout=5.0,
            priority=50,
        )

        info = manager.get_resource_info("test_id")
        if info.cleanup_func != cleanup_func:
            raise AssertionError
        if info.shutdown_timeout != 5.0:
            raise AssertionError
        if info.priority != 50:
            raise AssertionError

    def test_register_resource_with_dependencies(self):
        """Test resource registration with dependencies."""
        manager = ResourceManager()

        manager.register_resource(
            resource_id="test_id",
            resource="test_resource",
            resource_type=ResourceType.CUSTOM,
            dependencies=["dep1", "dep2"],
            metadata={"key": "value"},
        )

        info = manager.get_resource_info("test_id")
        if info.dependencies != ["dep1", "dep2"]:
            raise AssertionError
        if info.metadata != {"key": "value"}:
            raise AssertionError

    def test_register_during_shutdown(self):
        """Test that registration is blocked during shutdown."""
        manager = ResourceManager()
        manager._shutdown_initiated = True

        with patch("utils.resource_manager.logger") as mock_logger:
            manager.register_resource(
                resource_id="test_id", resource="test_resource", resource_type=ResourceType.CUSTOM
            )

            mock_logger.warning.assert_called()

        # Resource should not be registered
        info = manager.get_resource_info("test_id")
        assert info is None

    def test_unregister_resource(self):
        """Test resource unregistration."""
        manager = ResourceManager()
        resource = MagicMock()

        manager.register_resource(
            resource_id="test_id", resource=resource, resource_type=ResourceType.CUSTOM
        )

        # Verify resource is registered
        if manager.get_resource("test_id") != resource:
            raise AssertionError

        # Unregister
        success = manager.unregister_resource("test_id")

        if success is not True:
            raise AssertionError
        if manager.get_resource("test_id") is not None:
            raise AssertionError

    def test_unregister_nonexistent_resource(self):
        """Test unregistering non-existent resource."""
        manager = ResourceManager()

        success = manager.unregister_resource("nonexistent")

        if success is not False:
            raise AssertionError

    def test_get_resource(self):
        """Test getting registered resource."""
        manager = ResourceManager()
        resource = "test_resource"

        manager.register_resource(
            resource_id="test_id", resource=resource, resource_type=ResourceType.CUSTOM
        )

        retrieved = manager.get_resource("test_id")
        if retrieved != resource:
            raise AssertionError

    def test_get_nonexistent_resource(self):
        """Test getting non-existent resource."""
        manager = ResourceManager()

        resource = manager.get_resource("nonexistent")
        assert resource is None

    def test_list_resources(self):
        """Test listing all resources."""
        manager = ResourceManager()

        # Register multiple resources
        manager.register_resource("db", "database", ResourceType.DATABASE)
        manager.register_resource("timer", "timer_obj", ResourceType.TIMER)
        manager.register_resource("thread", "thread_obj", ResourceType.THREAD)

        resources = manager.list_resources()
        assert len(resources) == 3

        resource_ids = [r.resource_id for r in resources]
        if "db" not in resource_ids:
            raise AssertionError
        if "timer" not in resource_ids:
            raise AssertionError
        if "thread" not in resource_ids:
            raise AssertionError

    def test_list_resources_by_type(self):
        """Test listing resources filtered by type."""
        manager = ResourceManager()

        # Register different types
        manager.register_resource("db1", "database1", ResourceType.DATABASE)
        manager.register_resource("db2", "database2", ResourceType.DATABASE)
        manager.register_resource("timer1", "timer1", ResourceType.TIMER)

        # Filter by database type
        db_resources = manager.list_resources(ResourceType.DATABASE)
        assert len(db_resources) == 2

        db_ids = [r.resource_id for r in db_resources]
        if "db1" not in db_ids:
            raise AssertionError
        if "db2" not in db_ids:
            raise AssertionError

    def test_get_resource_status(self):
        """Test getting resource manager status."""
        manager = ResourceManager()

        # Register resources with different types and states
        manager.register_resource("db", "database", ResourceType.DATABASE)
        manager.register_resource("timer", "timer", ResourceType.TIMER)

        status = manager.get_resource_status()

        if status["total_resources"] != 2:
            raise AssertionError
        if status["shutdown_initiated"] is not False:
            raise AssertionError
        if "resources_by_type" not in status:
            raise AssertionError
        if "resources_by_state" not in status:
            raise AssertionError
        if status["resources_by_type"]["database"] != 1:
            raise AssertionError
        if status["resources_by_type"]["timer"] != 1:
            raise AssertionError
        if status["resources_by_state"]["active"] != 2:
            raise AssertionError

    def test_shutdown_single_resource_with_cleanup(self):
        """Test shutting down single resource with cleanup function."""
        manager = ResourceManager()
        cleanup_called = []

        def cleanup_func():
            cleanup_called.append(True)

        manager.register_resource(
            resource_id="test_id",
            resource="test_resource",
            resource_type=ResourceType.CUSTOM,
            cleanup_func=cleanup_func,
        )

        # Get resource info for direct shutdown test
        info = manager.get_resource_info("test_id")
        assert info is not None

        # Shutdown the resource
        success = manager._shutdown_single_resource(info)

        if success is not True:
            raise AssertionError
        if cleanup_called != [True]:
            raise AssertionError
        if info.state != ResourceState.SHUTDOWN:
            raise AssertionError
        assert isinstance(info.shutdown_at, datetime)

    def test_shutdown_single_resource_with_methods(self):
        """Test shutting down resource with standard cleanup methods."""
        manager = ResourceManager()

        # Create mock resource with cleanup methods
        resource = MagicMock()
        resource.close = MagicMock()

        manager.register_resource(
            resource_id="test_id", resource=resource, resource_type=ResourceType.CUSTOM
        )

        info = manager.get_resource_info("test_id")
        success = manager._shutdown_single_resource(info)

        if success is not True:
            raise AssertionError
        resource.close.assert_called_once()
        if info.state != ResourceState.SHUTDOWN:
            raise AssertionError

    def test_shutdown_single_resource_methods_priority(self):
        """Test shutdown method priority (close > shutdown > stop > quit)."""
        manager = ResourceManager()

        # Test close method
        resource_close = MagicMock()
        resource_close.close = MagicMock()
        resource_close.shutdown = MagicMock()

        manager.register_resource("close_test", resource_close, ResourceType.CUSTOM)
        info = manager.get_resource_info("close_test")
        manager._shutdown_single_resource(info)

        resource_close.close.assert_called_once()
        resource_close.shutdown.assert_not_called()

    def test_shutdown_single_resource_error(self):
        """Test error handling during resource shutdown."""
        manager = ResourceManager()

        def failing_cleanup():
            raise RuntimeError("Cleanup failed")

        manager.register_resource(
            resource_id="test_id",
            resource="test_resource",
            resource_type=ResourceType.CUSTOM,
            cleanup_func=failing_cleanup,
        )

        info = manager.get_resource_info("test_id")

        with patch("utils.resource_manager.logger") as mock_logger:
            success = manager._shutdown_single_resource(info)

            if success is not False:
                raise AssertionError
            if info.state != ResourceState.ERROR:
                raise AssertionError
            mock_logger.error.assert_called()

    def test_calculate_shutdown_order(self):
        """Test calculation of shutdown order."""
        manager = ResourceManager()

        # Register resources with different priorities
        manager.register_resource("gui", "gui_component", ResourceType.GUI_COMPONENT)  # Priority 10
        manager.register_resource("timer", "timer_obj", ResourceType.TIMER)  # Priority 20
        manager.register_resource("db", "database", ResourceType.DATABASE)  # Priority 70

        shutdown_order = manager._calculate_shutdown_order()

        # Should be ordered by priority (lower = first)
        assert len(shutdown_order) == 3
        if shutdown_order[0].resource_id != "gui":
            raise AssertionError
        if shutdown_order[1].resource_id != "timer":
            raise AssertionError
        if shutdown_order[2].resource_id != "db":
            raise AssertionError

    def test_shutdown_all_resources(self):
        """Test shutting down all resources."""
        manager = ResourceManager()
        cleanup_calls = []

        def cleanup1():
            cleanup_calls.append("cleanup1")

        def cleanup2():
            cleanup_calls.append("cleanup2")

        # Register multiple resources
        manager.register_resource(
            "resource1", "res1", ResourceType.CUSTOM, cleanup_func=cleanup1, priority=10
        )
        manager.register_resource(
            "resource2", "res2", ResourceType.CUSTOM, cleanup_func=cleanup2, priority=20
        )

        success = manager.shutdown_all_resources()

        if success is not True:
            raise AssertionError
        if manager._shutdown_initiated is not True:
            raise AssertionError
        if "cleanup1" not in cleanup_calls:
            raise AssertionError
        if "cleanup2" not in cleanup_calls:
            raise AssertionError

    def test_shutdown_all_resources_timeout(self):
        """Test shutdown with timeout."""
        manager = ResourceManager()

        def slow_cleanup():
            time.sleep(2.0)  # Longer than timeout

        manager.register_resource(
            "slow_resource",
            "resource",
            ResourceType.CUSTOM,
            cleanup_func=slow_cleanup,
            shutdown_timeout=0.1,
        )

        start_time = time.time()
        manager.shutdown_all_resources(timeout=0.5)
        end_time = time.time()

        # Should complete quickly due to timeout
        if (end_time - start_time) >= 1.0:
            raise AssertionError
        # May or may not be successful depending on timing

    def test_shutdown_already_in_progress(self):
        """Test shutdown when already in progress."""
        manager = ResourceManager()
        manager._shutdown_initiated = True

        with patch("utils.resource_manager.logger") as mock_logger:
            success = manager.shutdown_all_resources()

            if success is not True:
                raise AssertionError
            mock_logger.warning.assert_called()

    def test_force_shutdown_resource(self):
        """Test force shutdown of specific resource."""
        manager = ResourceManager()
        cleanup_called = []

        def cleanup_func():
            cleanup_called.append(True)

        manager.register_resource(
            "test_resource", "resource", ResourceType.CUSTOM, cleanup_func=cleanup_func
        )

        success = manager.force_shutdown_resource("test_resource")

        if success is not True:
            raise AssertionError
        if cleanup_called != [True]:
            raise AssertionError

    def test_force_shutdown_nonexistent_resource(self):
        """Test force shutdown of non-existent resource."""
        manager = ResourceManager()

        success = manager.force_shutdown_resource("nonexistent")

        if success is not False:
            raise AssertionError

    def test_wait_for_shutdown(self):
        """Test waiting for shutdown completion."""
        manager = ResourceManager()

        def delayed_shutdown():
            time.sleep(0.1)
            manager._shutdown_event.set()

        # Start background shutdown
        thread = threading.Thread(target=delayed_shutdown)
        thread.start()

        # Wait for shutdown
        success = manager.wait_for_shutdown(timeout=1.0)

        thread.join()
        if success is not True:
            raise AssertionError

    def test_wait_for_shutdown_timeout(self):
        """Test waiting for shutdown with timeout."""
        manager = ResourceManager()

        # Wait without setting shutdown event
        success = manager.wait_for_shutdown(timeout=0.1)

        if success is not False:
            raise AssertionError


class TestResourceManagerIntegration:
    """Integration test cases for ResourceManager."""

    def test_disposable_resource_lifecycle(self):
        """Test complete lifecycle of disposable resource."""
        manager = ResourceManager()

        class DisposableResource:
            def __init__(self):
                self.disposed = False

            def dispose(self):
                self.disposed = True

        resource = DisposableResource()

        # Register with dispose method as cleanup
        manager.register_resource(
            "disposable", resource, ResourceType.CUSTOM, cleanup_func=resource.dispose
        )

        # Verify resource is active
        info = manager.get_resource_info("disposable")
        if info.state != ResourceState.ACTIVE:
            raise AssertionError
        if resource.disposed:
            raise AssertionError

        # Shutdown
        success = manager.shutdown_all_resources()

        if success is not True:
            raise AssertionError
        if resource.disposed is not True:
            raise AssertionError

    def test_complex_dependency_shutdown(self):
        """Test shutdown with complex resource dependencies."""
        manager = ResourceManager()

        cleanup_order = []

        def create_cleanup_func(name):
            def cleanup():
                cleanup_order.append(name)

            return cleanup

        # Register resources with dependencies
        # GUI -> Timer -> Database (GUI depends on Timer, Timer depends on Database)
        manager.register_resource(
            "database",
            "db",
            ResourceType.DATABASE,
            cleanup_func=create_cleanup_func("database"),
            priority=70,
        )

        manager.register_resource(
            "timer",
            "timer",
            ResourceType.TIMER,
            cleanup_func=create_cleanup_func("timer"),
            priority=20,
            dependencies=["database"],
        )

        manager.register_resource(
            "gui",
            "gui",
            ResourceType.GUI_COMPONENT,
            cleanup_func=create_cleanup_func("gui"),
            priority=10,
            dependencies=["timer"],
        )

        success = manager.shutdown_all_resources()

        if success is not True:
            raise AssertionError
        # Should shutdown in priority order (lower priority first)
        if cleanup_order != ["gui", "timer", "database"]:
            raise AssertionError

    def test_resource_with_standard_methods(self):
        """Test resource with standard cleanup methods."""
        manager = ResourceManager()

        class ResourceWithMethods:
            def __init__(self):
                self.closed = False
                self.shutdown_called = False
                self.stopped = False

            def close(self):
                self.closed = True

            def shutdown(self):
                self.shutdown_called = True

            def stop(self):
                self.stopped = True

        # Test close method priority
        resource1 = ResourceWithMethods()
        manager.register_resource("res1", resource1, ResourceType.CUSTOM)

        info1 = manager.get_resource_info("res1")
        manager._shutdown_single_resource(info1)

        if resource1.closed is not True:
            raise AssertionError
        if resource1.shutdown_called is not False:
            raise AssertionError

        # Test shutdown method when close not available
        class ResourceWithShutdown:
            def __init__(self):
                self.shutdown_called = False

            def shutdown(self):
                self.shutdown_called = True

        resource2 = ResourceWithShutdown()
        manager.register_resource("res2", resource2, ResourceType.CUSTOM)

        info2 = manager.get_resource_info("res2")
        manager._shutdown_single_resource(info2)

        if resource2.shutdown_called is not True:
            raise AssertionError

    def test_concurrent_resource_operations(self):
        """Test concurrent resource operations."""
        manager = ResourceManager()
        results = {}

        def register_worker(thread_id):
            try:
                manager.register_resource(
                    f"resource_{thread_id}", f"resource_object_{thread_id}", ResourceType.CUSTOM
                )
                results[thread_id] = "success"
            except Exception as e:
                results[thread_id] = str(e)

        # Start multiple registration threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=register_worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All registrations should succeed
        assert len(results) == 5
        for result in results.values():
            if result != "success":
                raise AssertionError

        # Verify all resources were registered
        resources = manager.list_resources()
        assert len(resources) == 5

    def test_performance_under_load(self):
        """Test performance with many resources."""
        manager = ResourceManager()

        # Register many resources
        start_time = time.time()
        for i in range(100):
            manager.register_resource(
                f"resource_{i}",
                f"object_{i}",
                ResourceType.CUSTOM,
                priority=i % 10,  # Vary priorities
            )

        registration_time = time.time() - start_time

        # Registration should be fast
        if registration_time >= 1.0:
            raise AssertionError

        # Shutdown should also be reasonably fast
        shutdown_start = time.time()
        success = manager.shutdown_all_resources(timeout=5.0)
        shutdown_time = time.time() - shutdown_start

        if success is not True:
            raise AssertionError
        if shutdown_time >= 5.0:
            raise AssertionError

    def test_resource_metadata_persistence(self):
        """Test that resource metadata is maintained."""
        manager = ResourceManager()

        metadata = {"connection_string": "test://localhost:5432/db", "pool_size": 10, "timeout": 30}

        manager.register_resource(
            "database", "db_connection", ResourceType.DATABASE, metadata=metadata
        )

        info = manager.get_resource_info("database")
        if info.metadata != metadata:
            raise AssertionError

        # Metadata should persist after state changes
        manager._shutdown_single_resource(info)
        if info.metadata != metadata:
            raise AssertionError


class TestGlobalResourceManager:
    """Test cases for global resource manager functions."""

    def test_get_resource_manager_singleton(self):
        """Test that global resource manager is singleton."""
        rm1 = get_resource_manager()
        rm2 = get_resource_manager()

        if rm1 is not rm2:
            raise AssertionError
        assert isinstance(rm1, ResourceManager)

    def test_register_resource_convenience(self):
        """Test convenience resource registration function."""
        # Clear any existing resources
        manager = get_resource_manager()

        register_resource(
            "test_resource", "test_object", ResourceType.CUSTOM, shutdown_timeout=15.0
        )

        info = manager.get_resource_info("test_resource")
        assert info is not None
        if info.resource_id != "test_resource":
            raise AssertionError
        if info.shutdown_timeout != 15.0:
            raise AssertionError

    def test_shutdown_all_resources_convenience(self):
        """Test convenience shutdown function."""
        # Register a test resource
        register_resource("test", "test_obj", ResourceType.CUSTOM)

        success = shutdown_all_resources(timeout=10.0)

        if success is not True:
            raise AssertionError

    def test_global_manager_thread_safety(self):
        """Test thread safety of global manager access."""
        results = {}

        def worker(thread_id):
            manager = get_resource_manager()
            results[thread_id] = id(manager)

        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should get the same manager instance
        unique_ids = set(results.values())
        assert len(unique_ids) == 1


class TestResourceManagerEdgeCases:
    """Test cases for edge cases and error conditions."""

    def test_resource_without_cleanup_methods(self):
        """Test resource without any cleanup methods."""
        manager = ResourceManager()

        class PlainResource:
            pass

        resource = PlainResource()
        manager.register_resource("plain", resource, ResourceType.CUSTOM)

        info = manager.get_resource_info("plain")

        with patch("utils.resource_manager.logger") as mock_logger:
            success = manager._shutdown_single_resource(info)

            if success is not True:
                raise AssertionError
            mock_logger.debug.assert_called()

    def test_resource_cleanup_exception(self):
        """Test resource cleanup that raises exception."""
        manager = ResourceManager()

        class FailingResource:
            def close(self):
                raise RuntimeError("Close failed")

        resource = FailingResource()
        manager.register_resource("failing", resource, ResourceType.CUSTOM)

        info = manager.get_resource_info("failing")

        with patch("utils.resource_manager.logger") as mock_logger:
            success = manager._shutdown_single_resource(info)

            if success is not False:
                raise AssertionError
            if info.state != ResourceState.ERROR:
                raise AssertionError
            mock_logger.error.assert_called()

    def test_empty_resource_manager_shutdown(self):
        """Test shutting down empty resource manager."""
        manager = ResourceManager()

        success = manager.shutdown_all_resources()

        if success is not True:
            raise AssertionError
        if manager._shutdown_initiated is not True:
            raise AssertionError

    def test_duplicate_resource_registration_handling(self):
        """Test handling of duplicate resource registrations."""
        manager = ResourceManager()

        # Register resource
        manager.register_resource("test", "resource1", ResourceType.CUSTOM)

        # Try to register with same ID (should overwrite or handle gracefully)
        # Based on the implementation, this might log a warning but still work
        manager.register_resource("test", "resource2", ResourceType.CUSTOM)

        # Should have one resource with this ID
        info = manager.get_resource_info("test")
        assert info is not None

    def test_resource_state_transitions(self):
        """Test resource state transitions during lifecycle."""
        manager = ResourceManager()

        manager.register_resource("test", "resource", ResourceType.CUSTOM)

        info = manager.get_resource_info("test")

        # Initial state should be ACTIVE (after registration)
        if info.state != ResourceState.ACTIVE:
            raise AssertionError

        # Shutdown should change state
        manager._shutdown_single_resource(info)
        if info.state != ResourceState.SHUTDOWN:
            raise AssertionError

    def test_resource_timing_information(self):
        """Test that timing information is properly recorded."""
        manager = ResourceManager()

        created_before = datetime.now()
        manager.register_resource("test", "resource", ResourceType.CUSTOM)
        created_after = datetime.now()

        info = manager.get_resource_info("test")

        # Created time should be between before and after
        if not created_before <= info.created_at <= created_after:
            raise AssertionError
        assert info.shutdown_at is None

        # Shutdown and check timing
        shutdown_before = datetime.now()
        manager._shutdown_single_resource(info)
        shutdown_after = datetime.now()

        assert info.shutdown_at is not None
        if not shutdown_before <= info.shutdown_at <= shutdown_after:
            raise AssertionError
