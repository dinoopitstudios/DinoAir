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
        assert ResourceType.DATABASE.value == "database"
        assert ResourceType.THREAD.value == "thread"
        assert ResourceType.TIMER.value == "timer"
        assert ResourceType.WATCHDOG.value == "watchdog"
        assert ResourceType.FILE_HANDLE.value == "file_handle"
        assert ResourceType.NETWORK.value == "network"
        assert ResourceType.GUI_COMPONENT.value == "gui_component"
        assert ResourceType.CUSTOM.value == "custom"


class TestResourceState:
    """Test cases for ResourceState enum."""

    def test_resource_state_values(self):
        """Test ResourceState enum values."""
        assert ResourceState.INITIALIZING.value == "initializing"
        assert ResourceState.ACTIVE.value == "active"
        assert ResourceState.SHUTTING_DOWN.value == "shutting_down"
        assert ResourceState.SHUTDOWN.value == "shutdown"
        assert ResourceState.ERROR.value == "error"


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

        assert info.resource_id == "test_resource"
        assert info.resource_type == ResourceType.DATABASE
        assert info.resource == "mock_db_connection"
        assert info.cleanup_func == cleanup_func
        assert info.shutdown_timeout == 15.0
        assert info.priority == 50
        assert info.state == ResourceState.ACTIVE
        assert info.created_at == created_time
        assert info.shutdown_at == shutdown_time
        assert info.dependencies == ["dep1", "dep2"]
        assert info.metadata == {"connection_string": "test://localhost"}

    def test_resource_info_defaults(self):
        """Test ResourceInfo with default values."""
        info = ResourceInfo(
            resource_id="test", resource_type=ResourceType.CUSTOM, resource="test_resource"
        )

        assert info.cleanup_func is None
        assert info.shutdown_timeout == 10.0
        assert info.priority == 100
        assert info.state == ResourceState.INITIALIZING
        assert isinstance(info.created_at, datetime)
        assert info.shutdown_at is None
        assert info.dependencies == []
        assert info.metadata == {}


class TestResourceManager:
    """Test cases for ResourceManager class."""

    def test_resource_manager_initialization(self):
        """Test ResourceManager initialization."""
        manager = ResourceManager()

        assert len(manager.list_resources()) == 0
        assert manager._shutdown_initiated is False

    def test_register_resource_basic(self):
        """Test basic resource registration."""
        manager = ResourceManager()
        resource = "test_resource"

        manager.register_resource(
            resource_id="test_id", resource=resource, resource_type=ResourceType.CUSTOM
        )

        info = manager.get_resource_info("test_id")
        assert info is not None
        assert info.resource_id == "test_id"
        assert info.resource == resource
        assert info.resource_type == ResourceType.CUSTOM
        assert info.state == ResourceState.ACTIVE

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
        assert info.cleanup_func == cleanup_func
        assert info.shutdown_timeout == 5.0
        assert info.priority == 50

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
        assert info.dependencies == ["dep1", "dep2"]
        assert info.metadata == {"key": "value"}

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
        assert manager.get_resource("test_id") == resource

        # Unregister
        success = manager.unregister_resource("test_id")

        assert success is True
        assert manager.get_resource("test_id") is None

    def test_unregister_nonexistent_resource(self):
        """Test unregistering non-existent resource."""
        manager = ResourceManager()

        success = manager.unregister_resource("nonexistent")

        assert success is False

    def test_get_resource(self):
        """Test getting registered resource."""
        manager = ResourceManager()
        resource = "test_resource"

        manager.register_resource(
            resource_id="test_id", resource=resource, resource_type=ResourceType.CUSTOM
        )

        retrieved = manager.get_resource("test_id")
        assert retrieved == resource

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
        assert "db" in resource_ids
        assert "timer" in resource_ids
        assert "thread" in resource_ids

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
        assert "db1" in db_ids
        assert "db2" in db_ids

    def test_get_resource_status(self):
        """Test getting resource manager status."""
        manager = ResourceManager()

        # Register resources with different types and states
        manager.register_resource("db", "database", ResourceType.DATABASE)
        manager.register_resource("timer", "timer", ResourceType.TIMER)

        status = manager.get_resource_status()

        assert status["total_resources"] == 2
        assert status["shutdown_initiated"] is False
        assert "resources_by_type" in status
        assert "resources_by_state" in status
        assert status["resources_by_type"]["database"] == 1
        assert status["resources_by_type"]["timer"] == 1
        assert status["resources_by_state"]["active"] == 2

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

        assert success is True
        assert cleanup_called == [True]
        assert info.state == ResourceState.SHUTDOWN
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

        assert success is True
        resource.close.assert_called_once()
        assert info.state == ResourceState.SHUTDOWN

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

            assert success is False
            assert info.state == ResourceState.ERROR
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
        assert shutdown_order[0].resource_id == "gui"
        assert shutdown_order[1].resource_id == "timer"
        assert shutdown_order[2].resource_id == "db"

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

        assert success is True
        assert manager._shutdown_initiated is True
        assert "cleanup1" in cleanup_calls
        assert "cleanup2" in cleanup_calls

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
        assert (end_time - start_time) < 1.0
        # May or may not be successful depending on timing

    def test_shutdown_already_in_progress(self):
        """Test shutdown when already in progress."""
        manager = ResourceManager()
        manager._shutdown_initiated = True

        with patch("utils.resource_manager.logger") as mock_logger:
            success = manager.shutdown_all_resources()

            assert success is True
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

        assert success is True
        assert cleanup_called == [True]

    def test_force_shutdown_nonexistent_resource(self):
        """Test force shutdown of non-existent resource."""
        manager = ResourceManager()

        success = manager.force_shutdown_resource("nonexistent")

        assert success is False

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
        assert success is True

    def test_wait_for_shutdown_timeout(self):
        """Test waiting for shutdown with timeout."""
        manager = ResourceManager()

        # Wait without setting shutdown event
        success = manager.wait_for_shutdown(timeout=0.1)

        assert success is False


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
        assert info.state == ResourceState.ACTIVE
        assert not resource.disposed

        # Shutdown
        success = manager.shutdown_all_resources()

        assert success is True
        assert resource.disposed is True

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

        assert success is True
        # Should shutdown in priority order (lower priority first)
        assert cleanup_order == ["gui", "timer", "database"]

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

        assert resource1.closed is True
        assert resource1.shutdown_called is False  # Should not call lower priority methods

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

        assert resource2.shutdown_called is True

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
            assert result == "success"

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
        assert registration_time < 1.0

        # Shutdown should also be reasonably fast
        shutdown_start = time.time()
        success = manager.shutdown_all_resources(timeout=5.0)
        shutdown_time = time.time() - shutdown_start

        assert success is True
        assert shutdown_time < 5.0

    def test_resource_metadata_persistence(self):
        """Test that resource metadata is maintained."""
        manager = ResourceManager()

        metadata = {"connection_string": "test://localhost:5432/db", "pool_size": 10, "timeout": 30}

        manager.register_resource(
            "database", "db_connection", ResourceType.DATABASE, metadata=metadata
        )

        info = manager.get_resource_info("database")
        assert info.metadata == metadata

        # Metadata should persist after state changes
        manager._shutdown_single_resource(info)
        assert info.metadata == metadata


class TestGlobalResourceManager:
    """Test cases for global resource manager functions."""

    def test_get_resource_manager_singleton(self):
        """Test that global resource manager is singleton."""
        rm1 = get_resource_manager()
        rm2 = get_resource_manager()

        assert rm1 is rm2
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
        assert info.resource_id == "test_resource"
        assert info.shutdown_timeout == 15.0

    def test_shutdown_all_resources_convenience(self):
        """Test convenience shutdown function."""
        # Register a test resource
        register_resource("test", "test_obj", ResourceType.CUSTOM)

        success = shutdown_all_resources(timeout=10.0)

        assert success is True

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

            assert success is True
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

            assert success is False
            assert info.state == ResourceState.ERROR
            mock_logger.error.assert_called()

    def test_empty_resource_manager_shutdown(self):
        """Test shutting down empty resource manager."""
        manager = ResourceManager()

        success = manager.shutdown_all_resources()

        assert success is True
        assert manager._shutdown_initiated is True

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
        assert info.state == ResourceState.ACTIVE

        # Shutdown should change state
        manager._shutdown_single_resource(info)
        assert info.state == ResourceState.SHUTDOWN

    def test_resource_timing_information(self):
        """Test that timing information is properly recorded."""
        manager = ResourceManager()

        created_before = datetime.now()
        manager.register_resource("test", "resource", ResourceType.CUSTOM)
        created_after = datetime.now()

        info = manager.get_resource_info("test")

        # Created time should be between before and after
        assert created_before <= info.created_at <= created_after
        assert info.shutdown_at is None

        # Shutdown and check timing
        shutdown_before = datetime.now()
        manager._shutdown_single_resource(info)
        shutdown_after = datetime.now()

        assert info.shutdown_at is not None
        assert shutdown_before <= info.shutdown_at <= shutdown_after
