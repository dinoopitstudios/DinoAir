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
        if db._service is not svc:
            raise AssertionError
        if db.table_name != "note_list":
            raise AssertionError
        assert db._security is None
        if db._security_is_fallback is not False:
            raise AssertionError


def test_helper_methods_delegate_security_and_paths():
    with patch("database.notes_db.NotesService") as svc_cls:
        svc = _mk_service()
        svc.security.can_perform_write_operation.return_value = (True, None)
        svc.security.escape_sql_wildcards.return_value = r"escaped\%text\_"
        svc_cls.return_value = svc

        db = NotesDatabase("test_user")

        # _get_security
        sec = db._get_security()
        if sec is not svc.security:
            raise AssertionError

        # _enforce_security_for_write
        allowed, msg = db._enforce_security_for_write("create")
        if allowed is not True:
            raise AssertionError
        assert msg is None

        # _escape_sql_wildcards
        if db._escape_sql_wildcards("text%_") != r"escaped\%text\_":
            raise AssertionError

        # _get_database_path
        if db._get_database_path() != "/mock/path/notes.db":
            raise AssertionError


def test_create_note_success_and_failure(sample_note):
    with patch("database.notes_db.NotesService") as svc_cls:
        svc = _mk_service()
        svc.create_note.return_value = OperationResult(success=True, data={"id": "n1"})
        svc_cls.return_value = svc

        db = NotesDatabase("test_user")

        ok = db.create_note(sample_note, "html", "proj-1")
        if ok["success"] is not True:
            raise AssertionError
        if ok["id"] != "n1":
            raise AssertionError

        # Failure path
        svc.create_note.return_value = OperationResult(success=False, error="boom")
        fail = db.create_note(sample_note)
        if fail["success"] is not False:
            raise AssertionError
        if fail["error"] != "boom":
            raise AssertionError


def test_get_note_and_get_all_notes_mapping():
    with patch("database.notes_db.NotesService") as svc_cls:
        svc = _mk_service()
        mock_note = Mock()
        svc.get_note.return_value = OperationResult(success=True, data=mock_note)
        svc.get_all_notes.return_value = OperationResult(success=True, data=[mock_note])
        svc_cls.return_value = svc

        db = NotesDatabase("test_user")

        one = db.get_note("note-1")
        if one is not mock_note:
            raise AssertionError

        alln = db.get_all_notes()
        assert isinstance(alln, list)
        if mock_note not in alln:
            raise AssertionError

        # Failure mapping to default
        svc.get_note.return_value = OperationResult(success=False, error="not found")
        none = db.get_note("missing")
        assert none is None

        svc.get_all_notes.return_value = OperationResult(success=False, error="db down")
        empty = db.get_all_notes()
        if empty != []:
            raise AssertionError


def test_update_and_delete_restore_paths():
    with patch("database.notes_db.NotesService") as svc_cls:
        svc = _mk_service()
        svc.update_note.return_value = OperationResult(success=True, data={"affected_rows": 1})
        svc.delete_note.return_value = OperationResult(success=True, data={"deleted": True})
        svc.restore_note.return_value = OperationResult(success=True, data={"restored": True})
        svc_cls.return_value = svc

        db = NotesDatabase("test_user")

        upd = db.update_note("id1", {"title": "T"})
        if upd["success"] is not True:
            raise AssertionError
        if upd["affected_rows"] != 1:
            raise AssertionError

        soft = db.delete_note("id1")
        if soft["success"] is not True:
            raise AssertionError
        if soft["deleted"] is not True:
            raise AssertionError

        hard = db.delete_note("id1", hard_delete=True)
        if hard["success"] is not True:
            raise AssertionError

        rest = db.restore_deleted_note("id1")
        if rest["success"] is not True:
            raise AssertionError


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
        if tags != {"alpha": 2}:
            raise AssertionError

        ren = db.rename_tag("alpha", "omega")
        if ren["success"] is not True:
            raise AssertionError
        if ren["affected_notes"] != 3:
            raise AssertionError

        delt = db.delete_tag("beta")
        if delt["success"] is not True:
            raise AssertionError
        if delt["affected_notes"] != 2:
            raise AssertionError


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
        if db.assign_notes_to_project(["a", "b"], "p1") is not True:
            raise AssertionError
        if db.remove_notes_from_project(["a"]) is not True:
            raise AssertionError
        if db.get_project_notes_count("p1") != 5:
            raise AssertionError
        if db.update_note_project("a", None) is not True:
            raise AssertionError

        # Count default to 0 when None data
        svc.get_project_notes_count.return_value = OperationResult(success=True, data=None)
        if db.get_project_notes_count("p1") != 0:
            raise AssertionError
