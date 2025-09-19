"""
Global Dependency Container and Convenience Functions

This module provides the global dependency container instance and convenience functions
for easy access to the dependency injection system.
"""

import threading
from typing import Any, TypeVar

from .dependency_container import DependencyContainer

T = TypeVar("T")

# Global container instance
_container: DependencyContainer | None = None
_container_lock = threading.Lock()


def get_container() -> DependencyContainer:
    """Get the global dependency container."""
    global _container

    if _container is None:
        with _container_lock:
            if _container is None:
                _container = DependencyContainer()

    return _container


def resolve(name: str) -> Any:
    """Convenience function to resolve from global container."""
    return get_container().resolve(name)


def resolve_type(dependency_type: type[Any]) -> Any:
    """Convenience function to resolve by type from global container."""
    return get_container().resolve_type(dependency_type)
