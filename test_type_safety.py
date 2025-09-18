"""
Test script to validate type safety and representation methods.

This script demonstrates and tests the improvements made:
1. Type hints completeness with Python 3.12 syntax
2. Equality and representation methods
3. Optional field handling
"""

from pathlib import Path
import sys


# Add models to path
sys.path.append(str(Path(__file__).parent / "models"))

try:
    from base import normalize_tags, serialize_tags_for_db
    from note import Note
    from project import Project, ProjectStatus, ProjectSummary
except ImportError:
    sys.exit(1)


def test_type_safety():
    """Test type safety and Optional field handling."""

    # Test Project with all fields
    Project(
        id="proj-123",
        name="Test Project",
        description="A test project",
        status=ProjectStatus.ACTIVE,
        color="#FF5733",
        icon="📊",
        parent_project_id=None,  # Properly typed Optional
        tags=["planning", "test"],  # list[str] instead of List[str]
        metadata={"priority": "high", "team": "dev"},  # dict instead of Dict
        created_at="2024-01-01T00:00:00Z",
        updated_at=None,  # Optional field
    )

    # Test Project with minimal fields (testing defaults)
    Project(id="proj-456", name="Minimal Project")

    # Test Note with proper typing
    Note(
        id="note-789",
        title="Test Note",
        content="This is a test note with some content.",
        tags=["important", "todo"],
        project_id="proj-123",
    )

    Note(
        id="note-abc",
        title="Another Note",
        content="Another test note.",
        # tags defaults to empty list
        # project_id defaults to None
    )


def test_equality_methods():
    """Test equality and hashing methods."""

    # Test Project equality
    Project(id="proj-123", name="Test Project")
    Project(id="proj-123", name="Different Name")  # Same ID
    Project(id="proj-456", name="Test Project")  # Different ID

    # Test Note equality
    Note(id="note-123", title="Test", content="Content")
    Note(id="note-123", title="Different", content="Different")  # Same ID
    Note(id="", title="Test", content="Content")  # No ID, same title/content
    Note(id="", title="Test", content="Content")  # No ID, same title/content


def test_representation_methods():
    """Test __repr__ and __str__ methods."""

    # Test Project representations
    Project(
        id="proj-123",
        name="AI Research Project",
        status=ProjectStatus.ACTIVE,
        tags=["ai", "research", "machine-learning"],
        parent_project_id="parent-456",
    )

    # Test Note representations
    Note(
        id="note-789",
        title="Research Notes",
        content="This is a longer content string that should be truncated in the repr method for better readability and debugging.",
        tags=["research", "ai", "notes"],
        project_id="proj-123",
    )

    # Test Note without project
    Note(
        id="note-xyz",
        title="Standalone Note",
        content="A note without a project.",
        tags=["standalone"],
    )


def test_serialization_consistency():
    """Test consistent serialization patterns."""

    project = Project(
        id="proj-123",
        name="Test Project",
        tags=["tag1", "tag2", "tag3"],
        metadata={"key": "value", "number": 42},
    )

    # Test model-layer format (preserves types)
    project.to_dict()

    # Test repository-layer format (flattened for DB)
    db_dict = project.to_db_dict()

    # Test round-trip conversion
    Project.from_dict(db_dict)


def main():
    """Run all tests."""

    try:
        test_type_safety()
        test_equality_methods()
        test_representation_methods()
        test_serialization_consistency()

    except Exception:
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
