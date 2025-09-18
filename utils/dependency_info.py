"""
Dependency Information Data Structures

This module defines data structures and utilities for managing dependency information
in the dependency injection system.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .dependency_enums import LifecycleState, Scope


def _empty_str_list() -> list[str]:
    """Typed empty list factory to satisfy static type checkers."""
    return []


@dataclass
class DependencyInfo:
    """Information about a registered dependency."""

    name: str
    dependency_type: type[Any]
    factory: Callable[..., Any] | None = None
    instance: Any | None = None
    scope: Scope = Scope.SINGLETON
    dependencies: list[str] = field(default_factory=_empty_str_list)
    state: LifecycleState = LifecycleState.REGISTERED
    initialization_order: int = 100  # Higher = later
