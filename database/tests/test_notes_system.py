from unittest.mock import Mock, patch

import pytest

from database.notes_repository import NotesRepository, QueryResult
from database.notes_security import FallbackSecurity, NotesSecurity, SecurityPolicy
from database.notes_service import NotesService, OperationResult
from database.notes_validator import NotesValidator, ValidationResult


pytestmark = pytest.mark.skip(
    reason="Deprecated mock-heavy system tests; superseded by real integration tests hitting SQLite."
)

"""
Tests for Notes System components
Covers NotesService, NotesRepository, NotesSecurity, and NotesValidator
"""


class TestNotesService:
    """Test NotesService functionality"""

    def test_init_with_user(self, mock_db_manager):
        """Test initialization with user name"""
        with patch("database.notes_service.DatabaseManager", return_value=mock_db_manager):
            service = NotesService(user_name="test_user")
            assert service.user_name == "test_user"

    def test_create_note_success(self, mock_db_manager, sample_note):
        """Test successful note creation"""
        with (
            patch("database.notes_service.DatabaseManager", return_value=mock_db_manager),
            patch("database.notes_service.NotesRepository") as mock_repo_class,
            patch("database.notes_service.NotesValidator") as mock_validator_class,
            patch("database.notes_service.NotesSecurity") as mock_security_class,
        ):
            mock_repo = Mock()
            mock_validator = Mock()
            mock_security = Mock()

            mock_repo_class.return_value = mock_repo
            mock_validator_class.return_value = mock_validator
            mock_security_class.return_value = mock_security

            # Mock successful validation and creation
            mock_validator.validate_note_creation.return_value = ValidationResult(valid=True)
            mock_security.can_perform_write_operation.return_value = (True, None)
            mock_repo.create_note.return_value = QueryResult(
                success=True, data={"id": "test-note-1"}
            )

            service = NotesService(user_name="test_user")

            result = service.create_note(title="Test Note", content="Test Content", tags=["test"])

            assert result.success is True
            assert result.data["id"] == "test-note-1"

    def test_create_note_validation_failure(self, mock_db_manager):
        """Test note creation with validation failure"""
        with (
            patch("database.notes_service.DatabaseManager", return_value=mock_db_manager),
            patch("database.notes_service.NotesValidator") as mock_validator_class,
        ):
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator

            # Mock validation failure
            mock_validator.validate_note_creation.return_value = ValidationResult(
                valid=False, errors=["Title is required"]
            )

            service = NotesService(user_name="test_user")

            result = service.create_note(title="", content="Content")

            assert result.success is False
            assert "Title is required" in result.errors

    def test_create_note_security_denied(self, mock_db_manager):
        """Test note creation when security check fails"""
        with (
            patch("database.notes_service.DatabaseManager", return_value=mock_db_manager),
            patch("database.notes_service.NotesValidator") as mock_validator_class,
            patch("database.notes_service.NotesSecurity") as mock_security_class,
        ):
            mock_validator = Mock()
            mock_security = Mock()

            mock_validator_class.return_value = mock_validator
            mock_security_class.return_value = mock_security

            # Mock validation success but security failure
            mock_validator.validate_note_creation.return_value = ValidationResult(valid=True)
            mock_security.can_perform_write_operation.return_value = (False, "Permission denied")

            service = NotesService(user_name="test_user")

            result = service.create_note(title="Test", content="Content")

            assert result.success is False
            assert "Permission denied" in result.message

    def test_update_note_success(self, mock_db_manager):
        """Test successful note update"""
        with (
            patch("database.notes_service.DatabaseManager", return_value=mock_db_manager),
            patch("database.notes_service.NotesRepository") as mock_repo_class,
            patch("database.notes_service.NotesValidator") as mock_validator_class,
            patch("database.notes_service.NotesSecurity") as mock_security_class,
        ):
            mock_repo = Mock()
            mock_validator = Mock()
            mock_security = Mock()

            mock_repo_class.return_value = mock_repo
            mock_validator_class.return_value = mock_validator
            mock_security_class.return_value = mock_security

            # Mock successful validation and update
            mock_validator.validate_note_update.return_value = ValidationResult(valid=True)
            mock_security.can_perform_write_operation.return_value = (True, None)
            mock_repo.update_note.return_value = QueryResult(success=True)

            service = NotesService(user_name="test_user")

            result = service.update_note(note_id="test-note-1", updates={"title": "Updated Title"})

            assert result.success is True

    def test_delete_note_success(self, mock_db_manager):
        """Test successful note deletion"""
        with (
            patch("database.notes_service.DatabaseManager", return_value=mock_db_manager),
            patch("database.notes_service.NotesRepository") as mock_repo_class,
            patch("database.notes_service.NotesSecurity") as mock_security_class,
        ):
            mock_repo = Mock()
            mock_security = Mock()

            mock_repo_class.return_value = mock_repo
            mock_security_class.return_value = mock_security

            # Mock successful security check and deletion
            mock_security.can_perform_write_operation.return_value = (True, None)
            mock_repo.soft_delete_note.return_value = QueryResult(success=True)

            service = NotesService(user_name="test_user")

            result = service.delete_note("test-note-1")

            assert result.success is True

    def test_search_notes_success(self, mock_db_manager):
        """Test successful note search"""
        with (
            patch("database.notes_service.DatabaseManager", return_value=mock_db_manager),
            patch("database.notes_service.NotesRepository") as mock_repo_class,
            patch("database.notes_service.NotesValidator") as mock_validator_class,
        ):
            mock_repo = Mock()
            mock_validator = Mock()

            mock_repo_class.return_value = mock_repo
            mock_validator_class.return_value = mock_validator

            # Mock successful validation and search
            mock_validator.validate_search_query.return_value = ValidationResult(valid=True)
            mock_repo.search_notes.return_value = QueryResult(success=True, data=[{"id": "note-1"}])

            service = NotesService(user_name="test_user")

            result = service.search_notes(query="test query")

            assert result.success is True
            assert len(result.data) == 1

    def test_get_notes_by_tag_success(self, mock_db_manager):
        """Test getting notes by tag"""
        with (
            patch("database.notes_service.DatabaseManager", return_value=mock_db_manager),
            patch("database.notes_service.NotesRepository") as mock_repo_class,
        ):
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo

            mock_repo.get_notes_by_tag.return_value = QueryResult(
                success=True, data=[{"id": "note-1"}]
            )

            service = NotesService(user_name="test_user")

            result = service.get_notes_by_tag("test-tag")

            assert result.success is True

    def test_rename_tag_success(self, mock_db_manager):
        """Test successful tag renaming"""
        with (
            patch("database.notes_service.DatabaseManager", return_value=mock_db_manager),
            patch("database.notes_service.NotesRepository") as mock_repo_class,
            patch("database.notes_service.NotesSecurity") as mock_security_class,
        ):
            mock_repo = Mock()
            mock_security = Mock()

            mock_repo_class.return_value = mock_repo
            mock_security_class.return_value = mock_security

            mock_security.can_perform_write_operation.return_value = (True, None)
            mock_repo.update_tag_in_notes.return_value = QueryResult(success=True)

            service = NotesService(user_name="test_user")

            result = service.rename_tag("old-tag", "new-tag")

            assert result.success is True

    def test_assign_notes_to_project_success(self, mock_db_manager):
        """Test successful note assignment to project"""
        with (
            patch("database.notes_service.DatabaseManager", return_value=mock_db_manager),
            patch("database.notes_service.NotesRepository") as mock_repo_class,
            patch("database.notes_service.NotesValidator") as mock_validator_class,
            patch("database.notes_service.NotesSecurity") as mock_security_class,
        ):
            mock_repo = Mock()
            mock_validator = Mock()
            mock_security = Mock()

            mock_repo_class.return_value = mock_repo
            mock_validator_class.return_value = mock_validator
            mock_security_class.return_value = mock_security

            mock_validator.validate_bulk_operation.return_value = ValidationResult(valid=True)
            mock_security.can_perform_write_operation.return_value = (True, None)
            mock_repo.bulk_update_project.return_value = QueryResult(success=True)

            service = NotesService(user_name="test_user")

            result = service.assign_notes_to_project(["note-1", "note-2"], "project-1")

            assert result.success is True


class TestNotesRepository:
    """Test NotesRepository functionality"""

    def test_init_with_user(self, mock_db_manager):
        """Test initialization with user name"""
        with patch("database.notes_repository.DatabaseManager", return_value=mock_db_manager):
            repo = NotesRepository(user_name="test_user")
            assert repo.user_name == "test_user"

    def test_create_note_success(self, mock_db_manager, mock_db_connection):
        """Test successful note creation in repository"""
        with patch("database.notes_repository.DatabaseManager", return_value=mock_db_manager):
            mock_db_manager.get_notes_connection.return_value = mock_db_connection

            repo = NotesRepository(user_name="test_user")

            cursor = mock_db_connection.cursor.return_value
            cursor.lastrowid = 1

            result = repo.create_note(sample_note(), "HTML content")

            assert result.success is True
            assert result.data["id"] == "test-note-1"

    def test_get_note_by_id_success(self, mock_db_manager, mock_db_connection):
        """Test successful note retrieval by ID"""
        with patch("database.notes_repository.DatabaseManager", return_value=mock_db_manager):
            mock_db_manager.get_notes_connection.return_value = mock_db_connection

            repo = NotesRepository(user_name="test_user")

            mock_row = (
                "test-note-1",
                "Test Title",
                "Content",
                "tag1,tag2",
                "project-1",
                "2024-01-01",
                "2024-01-01",
            )
            cursor = mock_db_connection.cursor.return_value
            cursor.fetchone.return_value = mock_row

            result = repo.get_note_by_id("test-note-1")

            assert result.success is True

    def test_update_note_success(self, mock_db_manager, mock_db_connection):
        """Test successful note update"""
        with patch("database.notes_repository.DatabaseManager", return_value=mock_db_manager):
            mock_db_manager.get_notes_connection.return_value = mock_db_connection

            repo = NotesRepository(user_name="test_user")

            cursor = mock_db_connection.cursor.return_value
            cursor.rowcount = 1

            updates = {"title": "Updated Title"}
            result = repo.update_note("test-note-1", updates)

            assert result.success is True

    def test_search_notes_with_filters(self, mock_db_manager, mock_db_connection):
        """Test note search with various filters"""
        with patch("database.notes_repository.DatabaseManager", return_value=mock_db_manager):
            mock_db_manager.get_notes_connection.return_value = mock_db_connection

            repo = NotesRepository(user_name="test_user")

            mock_rows = [
                (
                    "note-1",
                    "Search Result",
                    "Content",
                    "tag1",
                    "project-1",
                    "2024-01-01",
                    "2024-01-01",
                )
            ]
            cursor = mock_db_connection.cursor.return_value
            cursor.fetchall.return_value = mock_rows

            result = repo.search_notes(
                query="search", tags=["tag1"], project_id="project-1", limit=10
            )

            assert result.success is True
            assert len(result.data) == 1

    def test_get_all_tags_success(self, mock_db_manager, mock_db_connection):
        """Test successful tag retrieval"""
        with patch("database.notes_repository.DatabaseManager", return_value=mock_db_manager):
            mock_db_manager.get_notes_connection.return_value = mock_db_connection

            repo = NotesRepository(user_name="test_user")

            mock_rows = [("tag1", 5), ("tag2", 3)]
            cursor = mock_db_connection.cursor.return_value
            cursor.fetchall.return_value = mock_rows

            result = repo.get_all_tags()

            assert result.success is True
            assert result.data["tag1"] == 5

    def test_bulk_update_project_success(self, mock_db_manager, mock_db_connection):
        """Test successful bulk project update"""
        with patch("database.notes_repository.DatabaseManager", return_value=mock_db_manager):
            mock_db_manager.get_notes_connection.return_value = mock_db_connection

            repo = NotesRepository(user_name="test_user")

            cursor = mock_db_connection.cursor.return_value
            cursor.rowcount = 2

            result = repo.bulk_update_project(["note-1", "note-2"], "project-1")

            assert result.success is True

    def test_bulk_update_project_empty_note_ids(self, mock_db_manager, mock_db_connection):
        """Test bulk_update_project with empty note_ids list returns error and does not update DB"""
        with patch("database.notes_repository.DatabaseManager", return_value=mock_db_manager):
            mock_db_manager.get_notes_connection.return_value = mock_db_connection

            repo = NotesRepository(user_name="test_user")

            result = repo.bulk_update_project([], "project-1")

            assert result.success is False
            assert "note_ids list cannot be empty" in result.error.lower()
            mock_db_connection.cursor.return_value.execute.assert_not_called()

    def test_row_to_note_conversion(self, mock_db_manager):
        """Test database row to note conversion"""
        with patch("database.notes_repository.DatabaseManager", return_value=mock_db_manager):
            repo = NotesRepository(user_name="test_user")

            row = (
                "note-1",
                "Title",
                "Content",
                "tag1,tag2",
                "project-1",
                "2024-01-01",
                "2024-01-01",
            )

            with patch("database.notes_repository.Note") as mock_note_class:
                mock_note = Mock()
                mock_note_class.from_dict.return_value = mock_note

                result = repo._row_to_note(row)

                assert result == mock_note


class TestNotesSecurity:
    """Test NotesSecurity functionality"""

    def test_init_loads_policy(self, mock_db_manager):
        """Test initialization loads security policy"""
        with patch("database.notes_security.DatabaseManager", return_value=mock_db_manager):
            security = NotesSecurity(user_name="test_user")

            # Should have loaded a policy
            assert hasattr(security, "_policy")
            assert isinstance(security._policy, SecurityPolicy | FallbackSecurity)

    def test_can_perform_write_operation_allowed(self, mock_db_manager):
        """Test write operation permission check - allowed"""
        with (
            patch("database.notes_security.DatabaseManager", return_value=mock_db_manager),
            patch("database.notes_security.NotesSecurity._load_security_policy") as mock_load,
        ):
            mock_policy = Mock()
            mock_policy.validate_note_data.return_value = {"valid": True}
            mock_load.return_value = mock_policy

            security = NotesSecurity(user_name="test_user")

            result, message = security.can_perform_write_operation("create")

            assert result is True
            assert message is None

    def test_can_perform_write_operation_denied(self, mock_db_manager):
        """Test write operation permission check - denied"""
        with (
            patch("database.notes_security.DatabaseManager", return_value=mock_db_manager),
            patch("database.notes_security.NotesSecurity._load_security_policy") as mock_load,
        ):
            mock_policy = Mock()
            mock_policy.validate_note_data.return_value = {
                "valid": False,
                "error": "Security violation",
            }
            mock_load.return_value = mock_policy

            security = NotesSecurity(user_name="test_user")

            result, message = security.can_perform_write_operation("create")

            assert result is False
            assert message == "Security violation"


class TestFallbackSecurity:
    """Test FallbackSecurity policy"""

    def test_validate_note_data_valid(self):
        """Test validation with valid note data"""
        policy = FallbackSecurity()

        result = policy.validate_note_data(
            title="Valid Title", content="Valid content", tags=["tag1", "tag2"]
        )

        assert result["valid"] is True
        assert result["sanitized_title"] == "Valid Title"

    def test_validate_note_data_invalid_title(self):
        """Test validation with invalid title"""
        policy = FallbackSecurity()

        result = policy.validate_note_data(
            title="",
            content="Valid content",
            tags=["tag1"],  # Invalid
        )

        assert result["valid"] is False
        assert "title" in result["error"].lower()

    def test_validate_note_data_xss_attempt(self):
        """Test validation with XSS attempt"""
        policy = FallbackSecurity()

        result = policy.validate_note_data(
            title="Safe Title",
            content="<script>alert('xss')</script>Malicious content",
            tags=["safe"],
        )

        assert result["valid"] is False
        assert "sanitized_content" in result

    def test_escape_sql_wildcards(self):
        """Test SQL wildcard escaping"""
        policy = FallbackSecurity()

        escaped = policy.escape_sql_wildcards("test%query_")
        assert escaped == "test\\%query\\_"


class TestNotesValidator:
    """Test NotesValidator functionality"""

    def test_validate_note_creation_success(self):
        """Test successful note creation validation"""
        validator = NotesValidator()

        result = validator.validate_note_creation(
            title="Valid Title", content="Valid content", tags=["tag1", "tag2"]
        )

        assert result.valid is True
        assert result.sanitized_title == "Valid Title"

    def test_validate_note_creation_missing_title(self):
        """Test note creation validation with missing title"""
        validator = NotesValidator()

        result = validator.validate_note_creation(title="", content="Valid content", tags=["tag1"])

        assert result.valid is False
        assert "title" in str(result.errors).lower()

    def test_validate_note_creation_too_long_title(self):
        """Test note creation validation with overly long title"""
        validator = NotesValidator()

        long_title = "A" * 201  # Exceeds max length
        result = validator.validate_note_creation(
            title=long_title, content="Valid content", tags=["tag1"]
        )

        assert result.valid is False
        assert "title" in str(result.errors).lower()

    def test_validate_note_update_success(self):
        """Test successful note update validation"""
        validator = NotesValidator()

        updates = {"title": "Updated Title", "content": "Updated content", "tags": ["new", "tags"]}

        result = validator.validate_note_update(updates)

        assert result.valid is True

    def test_validate_note_update_invalid_field(self):
        """Test note update validation with invalid field"""
        validator = NotesValidator()

        updates = {"invalid_field": "value", "title": "Valid Title"}

        result = validator.validate_note_update(updates)

        assert result.valid is False
        assert "invalid_field" in str(result.errors).lower()

    def test_validate_search_query_success(self):
        """Test successful search query validation"""
        validator = NotesValidator()

        result = validator.validate_search_query("valid query", "content")

        assert result.valid is True

    def test_validate_search_query_too_long(self):
        """Test search query validation with overly long query"""
        validator = NotesValidator()

        long_query = "A" * 501  # Exceeds max length
        result = validator.validate_search_query(long_query, "content")

        assert result.valid is False
        assert "query" in str(result.errors).lower()

    def test_validate_bulk_operation_success(self):
        """Test successful bulk operation validation"""
        validator = NotesValidator()

        result = validator.validate_bulk_operation(
            note_ids=["note-1", "note-2", "note-3"], operation="assign_project"
        )

        assert result.valid is True

    def test_validate_bulk_operation_empty_ids(self):
        """Test bulk operation validation with empty note IDs"""
        validator = NotesValidator()

        result = validator.validate_bulk_operation(note_ids=[], operation="assign_project")

        assert result.valid is False
        assert "note_ids" in str(result.errors).lower()


class TestOperationResult:
    """Test OperationResult dataclass"""

    def test_operation_result_success(self):
        """Test successful operation result"""
        result = OperationResult(
            success=True, data={"id": "test-note-1"}, message="Operation completed"
        )

        assert result.success is True
        assert result.data["id"] == "test-note-1"
        assert result.message == "Operation completed"
        assert result.errors == []

    def test_operation_result_failure(self):
        """Test failed operation result"""
        result = OperationResult(
            success=False, errors=["Validation error", "Security error"], message="Operation failed"
        )

        assert result.success is False
        assert len(result.errors) == 2
        assert result.message == "Operation failed"


class TestQueryResult:
    """Test QueryResult dataclass"""

    def test_query_result_success(self):
        """Test successful query result"""
        result = QueryResult(
            success=True, data=[{"id": "note-1"}, {"id": "note-2"}], message="Query successful"
        )

        assert result.success is True
        assert len(result.data) == 2

    def test_query_result_with_count(self):
        """Test query result with count"""
        result = QueryResult(success=True, data=[{"id": "note-1"}], count=1, total=10)

        assert result.count == 1
        assert result.total == 10


class TestValidationResult:
    """Test ValidationResult dataclass"""

    def test_validation_result_success(self):
        """Test successful validation result"""
        result = ValidationResult(
            valid=True, sanitized_title="Clean Title", sanitized_content="Clean content"
        )

        assert result.valid is True
        assert result.sanitized_title == "Clean Title"
        assert result.errors == []

    def test_validation_result_failure(self):
        """Test failed validation result"""
        result = ValidationResult(
            valid=False, errors=["Title required", "Content too long"], sanitized_title=""
        )

        assert result.valid is False
        assert len(result.errors) == 2


@pytest.mark.integration
class TestNotesSystemIntegration:
    """Integration tests for the complete notes system"""

    def test_full_note_lifecycle(self, mock_db_manager):
        """Test complete note lifecycle through service layer"""
        with (
            patch("database.notes_service.DatabaseManager", return_value=mock_db_manager),
            patch("database.notes_service.NotesRepository") as mock_repo_class,
            patch("database.notes_service.NotesValidator") as mock_validator_class,
            patch("database.notes_service.NotesSecurity") as mock_security_class,
        ):
            mock_repo = Mock()
            mock_validator = Mock()
            mock_security = Mock()

            mock_repo_class.return_value = mock_repo
            mock_validator_class.return_value = mock_validator
            mock_security_class.return_value = mock_security

            service = NotesService(user_name="test_user")

            # Setup mocks for successful operations
            mock_validator.validate_note_creation.return_value = ValidationResult(valid=True)
            mock_security.can_perform_write_operation.return_value = (True, None)
            mock_repo.create_note.return_value = QueryResult(success=True, data={"id": "note-1"})
            mock_repo.get_note_by_id.return_value = QueryResult(success=True, data={"id": "note-1"})
            mock_validator.validate_note_update.return_value = ValidationResult(valid=True)
            mock_repo.update_note.return_value = QueryResult(success=True)
            mock_repo.soft_delete_note.return_value = QueryResult(success=True)

            # Create
            create_result = service.create_note("Test Note", "Content", ["tag"])
            assert create_result.success is True

            # Read
            get_result = service.get_note("note-1")
            assert get_result.success is True

            # Update
            update_result = service.update_note("note-1", {"title": "Updated"})
            assert update_result.success is True

            # Delete
            delete_result = service.delete_note("note-1")
            assert delete_result.success is True

    def test_notes_service_error_handling(self, mock_db_manager):
        """Test error handling in notes service"""
        with (
            patch("database.notes_service.DatabaseManager", return_value=mock_db_manager),
            patch("database.notes_service.NotesRepository") as mock_repo_class,
        ):
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo

            service = NotesService(user_name="test_user")

            # Test repository error propagation
            mock_repo.create_note.side_effect = Exception("Database error")

            result = service.create_note("Test", "Content")

            assert result.success is False
            assert "Database error" in result.message


# Parametrized tests for various scenarios
@pytest.mark.parametrize(
    ("operation", "expected_result"),
    [("create", True), ("update", True), ("delete", True), ("invalid", False)],
)
def test_security_operations_parametrized(mock_db_manager, operation, expected_result):
    """Parametrized test for security operations"""
    with (
        patch("database.notes_security.DatabaseManager", return_value=mock_db_manager),
        patch("database.notes_security.NotesSecurity._load_security_policy") as mock_load,
    ):
        mock_policy = Mock()
        if expected_result:
            mock_policy.validate_note_data.return_value = {"valid": True}
        else:
            mock_policy.validate_note_data.return_value = {"valid": False, "error": "Denied"}

        mock_load.return_value = mock_policy

        security = NotesSecurity(user_name="test_user")

        result, _ = security.can_perform_write_operation(operation)

        assert result == expected_result


def test_validation_edge_cases():
    """Test validation edge cases"""
    validator = NotesValidator()

    # Test with None values
    result = validator.validate_note_creation(None, None, None)
    assert result.valid is False

    # Test with empty content
    result = validator.validate_note_creation("Title", "", [])
    assert result.valid is True  # Empty content should be allowed

    # Test with special characters in title
    result = validator.validate_note_creation("Title@#$%", "Content", [])
    assert result.valid is True  # Special chars should be allowed

    # Test bulk operation with duplicates
    result = validator.validate_bulk_operation(["id1", "id1", "id2"], "test")
    assert result.valid is True  # Duplicates should be allowed
