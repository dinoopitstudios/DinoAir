"""
Compatibility layer tests for NotesDatabase.
These tests patch the internal NotesService to verify delegation and return-shape mapping.
"""

from unittest.mock import Mock, patch

from database.notes_db import NotesDatabase
from database.notes_service import OperationResult


def _mk_service():
    """Create a mock NotesService with common attributes."""
    svc = Mock()
    # Provide sub-objects used by helper methods
    svc.security = Mock()
    svc.repository = Mock()
    svc.repository.db_manager = Mock()
    svc.repository.db_manager.notes_db_path = "/mock/path/notes.db"
    return svc


def test_init_constructs_service_and_legacy_attrs():
    with patch("database.notes_db.NotesService") as svc_cls:
        svc = _mk_service()
        svc_cls.return_value = svc

        db = NotesDatabase(user_name="test_user")
        svc_cls.assert_called_once_with("test_user")
        assert db._service is svc
        assert db.table_name == "note_list"
        assert db._security is None
        assert db._security_is_fallback is False


def test_helper_methods_delegate_security_and_paths():
    with patch("database.notes_db.NotesService") as svc_cls:
        svc = _mk_service()
        svc.security.can_perform_write_operation.return_value = (True, None)
        svc.security.escape_sql_wildcards.return_value = r"escaped\%text\_"
        svc_cls.return_value = svc

        db = NotesDatabase("test_user")

        # _get_security
        sec = db._get_security()
        assert sec is svc.security

        # _enforce_security_for_write
        allowed, msg = db._enforce_security_for_write("create")
        assert allowed is True
        assert msg is None

        # _escape_sql_wildcards
        assert db._escape_sql_wildcards("text%_") == r"escaped\%text\_"

        # _get_database_path
        assert db._get_database_path() == "/mock/path/notes.db"


def test_create_note_success_and_failure(sample_note):
    with patch("database.notes_db.NotesService") as svc_cls:
        svc = _mk_service()
        svc.create_note.return_value = OperationResult(success=True, data={"id": "n1"})
        svc_cls.return_value = svc

        db = NotesDatabase("test_user")

        ok = db.create_note(sample_note, "html", "proj-1")
        assert ok["success"] is True
        assert ok["id"] == "n1"

        # Failure path
        svc.create_note.return_value = OperationResult(success=False, error="boom")
        fail = db.create_note(sample_note)
        assert fail["success"] is False
        assert fail["error"] == "boom"


def test_get_note_and_get_all_notes_mapping():
    with patch("database.notes_db.NotesService") as svc_cls:
        svc = _mk_service()
        mock_note = Mock()
        svc.get_note.return_value = OperationResult(success=True, data=mock_note)
        svc.get_all_notes.return_value = OperationResult(success=True, data=[mock_note])
        svc_cls.return_value = svc

        db = NotesDatabase("test_user")

        one = db.get_note("note-1")
        assert one is mock_note

        alln = db.get_all_notes()
        assert isinstance(alln, list)
        assert mock_note in alln

        # Failure mapping to default
        svc.get_note.return_value = OperationResult(success=False, error="not found")
        none = db.get_note("missing")
        assert none is None

        svc.get_all_notes.return_value = OperationResult(success=False, error="db down")
        empty = db.get_all_notes()
        assert empty == []


def test_update_and_delete_restore_paths():
    with patch("database.notes_db.NotesService") as svc_cls:
        svc = _mk_service()
        svc.update_note.return_value = OperationResult(success=True, data={"affected_rows": 1})
        svc.delete_note.return_value = OperationResult(success=True, data={"deleted": True})
        svc.restore_note.return_value = OperationResult(success=True, data={"restored": True})
        svc_cls.return_value = svc

        db = NotesDatabase("test_user")

        upd = db.update_note("id1", {"title": "T"})
        assert upd["success"] is True
        assert upd["affected_rows"] == 1

        soft = db.delete_note("id1")
        assert soft["success"] is True
        assert soft["deleted"] is True

        hard = db.delete_note("id1", hard_delete=True)
        assert hard["success"] is True

        rest = db.restore_deleted_note("id1")
        assert rest["success"] is True


def test_search_and_tag_operations_mapping():
    with patch("database.notes_db.NotesService") as svc_cls:
        svc = _mk_service()
        svc.search_notes.return_value = OperationResult(success=True, data=[Mock()])
        svc.get_notes_by_tag.return_value = OperationResult(success=True, data=[Mock()])
        svc.get_all_tags.return_value = OperationResult(success=True, data={"alpha": 2})
        svc.rename_tag.return_value = OperationResult(success=True, data={"affected_notes": 3})
        svc.delete_tag.return_value = OperationResult(success=True, data={"affected_notes": 2})
        svc_cls.return_value = svc

        db = NotesDatabase("test_user")

        assert len(db.search_notes("q", "All", None)) == 1
        assert len(db.get_notes_by_tag("alpha")) == 1
        tags = db.get_all_tags()
        assert tags == {"alpha": 2}

        ren = db.rename_tag("alpha", "omega")
        assert ren["success"] is True
        assert ren["affected_notes"] == 3

        delt = db.delete_tag("beta")
        assert delt["success"] is True
        assert delt["affected_notes"] == 2


def test_project_methods_and_counts_mapping():
    with patch("database.notes_db.NotesService") as svc_cls:
        svc = _mk_service()
        svc.get_notes_by_project.return_value = OperationResult(success=True, data=[Mock()])
        svc.get_notes_without_project.return_value = OperationResult(success=True, data=[Mock()])
        svc.assign_notes_to_project.return_value = OperationResult(success=True)
        svc.remove_notes_from_project.return_value = OperationResult(success=True)
        svc.get_project_notes_count.return_value = OperationResult(success=True, data=5)
        svc.update_note_project.return_value = OperationResult(success=True)
        svc_cls.return_value = svc

        db = NotesDatabase("test_user")

        assert len(db.get_notes_by_project("p1")) == 1
        assert len(db.get_notes_without_project()) == 1
        assert db.assign_notes_to_project(["a", "b"], "p1") is True
        assert db.remove_notes_from_project(["a"]) is True
        assert db.get_project_notes_count("p1") == 5
        assert db.update_note_project("a", None) is True

        # Count default to 0 when None data
        svc.get_project_notes_count.return_value = OperationResult(success=True, data=None)
        assert db.get_project_notes_count("p1") == 0
