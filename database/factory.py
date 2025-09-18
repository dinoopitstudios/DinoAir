"""
NotesServiceFactory - Factory for creating notes services with dependency injection.
Implements the factory pattern solution for breaking circular dependencies.
Phase 4A Sprint 1 - Step 2.1
"""

import threading

from utils.logger import Logger


class NotesServiceFactory:
    """
    Factory for creating notes services with proper dependency injection.
    Eliminates circular dependencies by breaking direct imports.
    """

    def __init__(self):
        """Initialize factory."""
        self.logger = Logger()

    def create_notes_service(self, user_name: str | None = None):
        """
        Create fully configured notes service with all dependencies.

        This method breaks circular dependencies by importing at runtime.

        Args:
            user_name: Optional user name for user-specific database operations

        Returns:
            Configured NotesService instance with all dependencies injected
        """
        try:
            # Import at runtime to avoid circular dependencies
            from .notes_service import NotesService

            # Create service - the dependency injection happens in NotesService.__init__
            return NotesService(user_name)

        except Exception as e:
            self.logger.error(f"Failed to create notes service: {str(e)}")
            raise

    def create_database_manager(self, user_name: str | None = None):
        """
        Create database manager instance.

        Args:
            user_name: Optional user name for user-specific database

        Returns:
            DatabaseManager instance
        """
        from .initialize_db import DatabaseManager

        return DatabaseManager(user_name)

    def create_notes_repository(self, user_name: str | None = None):
        """
        Create notes repository with optional user specification.

        Args:
            user_name: Optional user name for user-specific database

        Returns:
            NotesRepository instance
        """
        from .notes_repository import NotesRepository

        return NotesRepository(user_name)

    def create_notes_security(self):
        """
        Create notes security validator.

        Returns:
            NotesSecurity instance
        """
        from .notes_security import NotesSecurity

        return NotesSecurity()

    def create_notes_validator(self):
        """
        Create notes data validator.

        Returns:
            NotesValidator instance
        """
        from .notes_validator import NotesValidator

        return NotesValidator()


# Global factory instance for backward compatibility
_global_factory: NotesServiceFactory | None = None
_factory_lock = threading.Lock()


def get_notes_service_factory() -> NotesServiceFactory:
    """
    Get global notes service factory instance.
    Thread-safe singleton using double-checked locking pattern.

    Returns:
        Global NotesServiceFactory instance
    """
    global _global_factory
    if _global_factory is None:
        with _factory_lock:
            if _global_factory is None:
                _global_factory = NotesServiceFactory()
    return _global_factory


def create_notes_service(user_name: str | None = None):
    """
    Convenience function to create notes service using global factory.
    This breaks circular dependencies by using runtime imports.

    Args:
        user_name: Optional user name for user-specific database operations

    Returns:
        Configured NotesService instance
    """
    factory = get_notes_service_factory()
    return factory.create_notes_service(user_name)
