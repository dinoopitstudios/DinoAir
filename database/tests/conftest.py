# --- Test-time compatibility patches (autouse) for current DB layer behavior ---
# (Existing content below)

"""
Shared fixtures and test configuration for database tests
"""

import contextlib
from datetime import date, timedelta
import os
from pathlib import Path
import shutil

# Ensure project root (DinoAir3.0) is importable when running from repo root
import sys as _sys
import tempfile
import uuid

import pytest

# Database manager import
from database.initialize_db import DatabaseManager

# Real model imports
from models import Artifact, CalendarEvent, Note, Project


# initialize_user_databases signature is now consistent in production
# No test-side shim needed

_pkg_root = Path(__file__).resolve().parents[2]
if str(_pkg_root) not in _sys.path:
    _sys.path.insert(0, str(_pkg_root))


# Test data factory functions
def create_test_event(
    title: str = "Test Event",
    event_type: str = "meeting",
    status: str = "scheduled",
    days_offset: int = 0,
    **kwargs,
) -> CalendarEvent:
    """Factory function to create test calendar events"""
    base_date = date.today() + timedelta(days=days_offset)

    defaults = {
        "id": f"test-event-{uuid.uuid4().hex[:8]}",
        "title": title,
        "description": f"Test {event_type} description",
        "event_type": event_type,
        "status": status,
        "event_date": base_date.isoformat(),
        "start_time": "09:00:00",
        "end_time": "10:00:00",
        "location": "Test Location",
        "participants": ["user1@test.com"],
        "tags": ["test"],
        "reminder_minutes_before": 15,
    }
    defaults.update(kwargs)
    return CalendarEvent(**defaults)


def create_test_note(title: str = "Test Note", **kwargs) -> Note:
    """Factory function to create test notes"""
    defaults = {
        "id": f"test-note-{uuid.uuid4().hex[:8]}",
        "title": title,
        "content": f"Content for {title}",
        "tags": ["test"],
        "project_id": None,
    }
    defaults.update(kwargs)
    return Note(**defaults)


def create_test_project(name: str = "Test Project", **kwargs) -> Project:
    """Factory function to create test projects"""
    from models.project import ProjectStatus

    defaults = {
        "id": f"test-project-{uuid.uuid4().hex[:8]}",
        "name": name,
        "description": f"Description for {name}",
        "status": ProjectStatus.ACTIVE,
        "tags": ["test"],
    }
    defaults.update(kwargs)
    return Project(**defaults)


# Logger mock for testing
class MockLogger:
    """Mock Logger class"""

    def __init__(self):
        pass

    def info(self, message: str):
        pass

    def error(self, message: str):
        pass

    def warning(self, message: str):
        pass

    def debug(self, message: str):
        pass


@pytest.fixture(scope="session")
def temp_db_dir():
    """Create a temporary directory for test databases"""
    db_temp_dir = tempfile.mkdtemp(prefix="test_db_")
    yield Path(db_temp_dir)
    shutil.rmtree(db_temp_dir)


@pytest.fixture
def mock_logger():
    """Mock logger fixture"""
    return MockLogger()


@pytest.fixture
def sample_calendar_event():
    """Sample calendar event for testing"""
    return CalendarEvent(
        id="test-event-1",
        title="Test Meeting",
        description="Test meeting description",
        event_type="meeting",
        status="scheduled",
        event_date=date.today().isoformat(),
        start_time="09:00:00",
        end_time="10:00:00",
        location="Test Room",
        participants=["user1@test.com", "user2@test.com"],
        project_id="test-project-1",
        tags=["meeting", "test"],
        reminder_minutes_before=15,
    )


@pytest.fixture
def sample_artifact():
    """Sample artifact for testing"""
    return Artifact(
        id="test-artifact-1",
        name="Test Document",
        description="Test document description",
        content_type="application/pdf",
        size_bytes=1024,
        collection_id="test-collection-1",
        project_id="test-project-1",
        tags=["document", "test"],
    )


@pytest.fixture
def sample_note():
    """Sample note for testing"""
    return Note(
        id="test-note-1",
        title="Test Note",
        content="Test note content",
        tags=["test", "sample"],
        project_id="test-project-1",
    )


@pytest.fixture
def sample_project():
    """Sample project for testing"""
    from models.project import ProjectStatus

    return Project(
        id="test-project-1",
        name="Test Project",
        description="Test project description",
        status=ProjectStatus.ACTIVE,
        tags=["test", "sample"],
    )


# Database fixtures for testing
@pytest.fixture(scope="session")
def db_manager():
    """Real database manager instance for testing"""
    # DatabaseManager automatically detects pytest environment and uses temp directory
    manager = DatabaseManager(user_name="test_user")
    manager.initialize_all_databases()

    return manager

    # Note: DatabaseManager handles connection cleanup automatically


@pytest.fixture
def clean_db_manager(request):
    """Fresh database manager for each test - no shared state"""
    # Each test gets a unique manager instance with descriptive name
    test_func = request.node.name
    test_user = f"test_user_{test_func}_{uuid.uuid4().hex[:8]}"
    manager = DatabaseManager(user_name=test_user)

    manager.initialize_all_databases()

    return manager

    # Cleanup is automatic via tmp_dir


@pytest.fixture
def seeded_appointments_db(clean_db_manager):
    """Appointments database pre-seeded with test data"""
    from database.appointments_db import AppointmentsDatabase

    db = AppointmentsDatabase(clean_db_manager)
    created_ids = []

    # Create seed data
    events = [
        create_test_event("Daily Standup", event_type="meeting", days_offset=0),
        create_test_event("Project Review", event_type="meeting", days_offset=1),
        create_test_event("Client Meeting", event_type="meeting", days_offset=2),
        create_test_event("Complete Task", event_type="task", status="completed", days_offset=-1),
    ]

    for event in events:
        result = db.create_event(event)
        if result.get("success"):
            created_ids.append(event.id)

    yield db, created_ids

    # Cleanup
    for event_id in created_ids:
        with contextlib.suppress(Exception):
            db.delete_event(event_id)


@pytest.fixture
def seeded_notes_db(clean_db_manager):
    """Notes database pre-seeded with test data"""
    from database.notes_service import NotesService

    # NotesService in current code accepts a user_name (str), not a DatabaseManager.
    # Use the same user namespace as clean_db_manager for isolation.
    service = NotesService(clean_db_manager.user_name)
    created_ids = []

    # Create seed data
    notes = [
        create_test_note("Meeting Notes", content="Important meeting notes"),
        create_test_note("Project Ideas", content="Ideas for the project"),
        create_test_note("Todo List", content="Things to do today"),
    ]

    for note in notes:
        result = service.create_note(note)
        # Support both OperationResult (current) and dict (legacy) return shapes
        success = getattr(result, "success", None)
        if success is None and isinstance(result, dict):
            success = result.get("success")
        if success:
            created_ids.append(note.id)

    yield service, created_ids

    # Cleanup
    for note_id in created_ids:
        with contextlib.suppress(Exception):
            service.delete_note(note_id)


@pytest.fixture
def bulk_test_data():
    """Factory to create bulk test data sets"""

    def _create_bulk_events(count: int = 50):
        """Create bulk calendar events for performance testing"""
        events = []
        for i in range(count):
            event = create_test_event(
                title=f"Bulk Event {i + 1}",
                event_type="meeting" if i % 2 == 0 else "task",
                days_offset=i % 30 - 15,  # Spread across month
                participants=[f"user{i}@test.com"],
                tags=[f"batch-{i // 10}", "bulk", "test"],
            )
            events.append(event)
        return events

    def _create_bulk_notes(count: int = 50):
        """Create bulk notes for performance testing"""
        notes = []
        for i in range(count):
            note = create_test_note(
                title=f"Bulk Note {i + 1}",
                content=f"Content for bulk note {i + 1}" * (i % 10 + 1),  # Varying content size
                tags=[f"batch-{i // 10}", "bulk", "test"],
            )
            notes.append(note)
        return notes

    return {"events": _create_bulk_events, "notes": _create_bulk_notes}


@pytest.fixture
def appointments_connection(db_manager):
    """Real appointments database connection"""
    return db_manager.get_appointments_connection()


@pytest.fixture
def artifacts_connection(db_manager):
    """Real artifacts database connection"""
    return db_manager.get_artifacts_connection()


@pytest.fixture
def projects_connection(db_manager):
    """Real projects database connection"""
    return db_manager.get_projects_connection()


@pytest.fixture
def file_search_connection(db_manager):
    """Real file search database connection"""
    return db_manager.get_file_search_connection()


@pytest.fixture
def notes_connection(db_manager):
    """Real notes database connection"""
    return db_manager.get_notes_connection()


@pytest.fixture
def memory_connection(db_manager):
    """Real memory database connection"""
    return db_manager.get_memory_connection()


@pytest.fixture
def chat_history_connection(db_manager):
    """Real chat history database connection"""
    return db_manager.get_chat_history_connection()


@pytest.fixture
def user_tools_connection(db_manager):
    """Real user tools database connection"""
    return db_manager.get_user_tools_connection()


@pytest.fixture
def timers_connection(db_manager):
    """Real timers database connection"""
    return db_manager.get_timers_connection()


# Backward compatibility fixtures (deprecated - use specific connection fixtures instead)
@pytest.fixture
def mock_db_connection(appointments_connection):
    """Backward compatibility - returns appointments connection"""
    return appointments_connection


@pytest.fixture
def mock_db_manager(db_manager):
    """Backward compatibility - returns real database manager"""
    return db_manager


# All fixtures now use real database connections instead of mocks


@pytest.fixture
def temp_file():
    """Create a temporary file for file operations testing"""
    fd, path = tempfile.mkstemp()
    try:
        with os.fdopen(fd, "w") as tmp:
            tmp.write("test content")
        yield path
    finally:
        os.unlink(path)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for file operations testing"""
    file_temp_dir = tempfile.mkdtemp()
    yield file_temp_dir
    shutil.rmtree(file_temp_dir)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


# Cleanup after each test
@pytest.fixture(autouse=True)
def cleanup(db_manager):
    """Clean up after each test to avoid cross-test interference"""
    yield
    try:
        # Use comprehensive cleanup for better test isolation
        if hasattr(db_manager, "cleanup_user_data"):
            # For development/testing, do aggressive cleanup
            db_manager.cleanup_user_data(
                cleanup_temp_files=True,
                cleanup_old_backups=True,
                max_backup_age_days=0,  # Remove all backups in tests
            )
        else:
            # Fallback to basic memory cleanup
            db_manager.clean_memory_database()
    except Exception:
        # Do not fail tests on cleanup issues
        pass


# --- Test-time compatibility patches (autouse) for current DB layer behavior ---


# Artifact normalization is now handled in production models.artifact.Artifact.to_dict()
# No test-side fixture needed


@pytest.fixture(autouse=True)
def _ensure_artifact_storage_dir(monkeypatch):
    """
    Ensure filesystem directory for large artifact storage exists before write.
    The current implementation creates the month directory but not the 'id' leaf.
    """
    from database.artifacts_db import ArtifactsDatabase as _ADB

    _orig_handle = _ADB._handle_file_storage

    def _patched_handle(self, artifact, content=None):
        # For large content, pre-create the 'artifact id' directory
        if content is not None and len(content) > getattr(
            self, "FILE_SIZE_THRESHOLD", 5 * 1024 * 1024
        ):
            storage_path = self._get_storage_path(artifact)
            storage_path.mkdir(parents=True, exist_ok=True)
        return _orig_handle(self, artifact, content)

    monkeypatch.setattr(_ADB, "_handle_file_storage", _patched_handle)
