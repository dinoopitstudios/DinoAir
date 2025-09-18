"""
Focused unit tests for NotesService to drive high branch coverage.
We patch repository, validator, and security to exercise success/failure paths.
"""

import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from database.notes_service import NotesService, OperationResult
from models.note import Note


pytestmark = pytest.mark.skip(
    reason="Deprecated mock-heavy unit tests; superseded by real integration tests hitting SQLite."
)


def make_note(id_="svc-unit-1", title="T", content="C", tags=None, project_id=None):
    return Note(id=id_, title=title, content=content, tags=tags or [], project_id=project_id)


@pytest.fixture
def svc():
    # Allow fallback writes to avoid blocking
    with patch.dict(os.environ, {"ALLOW_NOTES_FALLBACK_WRITES": "1"}, clear=False):
        # Patch collaborators on construction
        with (
            patch("database.notes_service.NotesRepository") as repo_cls,
            patch("database.notes_service.NotesSecurity") as sec_cls,
            patch("database.notes_service.NotesValidator") as val_cls,
        ):
            repo = Mock()
            sec = Mock()
            val = Mock()
            repo_cls.return_value = repo
            sec_cls.return_value = sec
            val_cls.return_value = val

            # Default permissive behavior; individual tests will override as needed
            val.validate_note_creation.return_value = Mock(is_valid=True, errors=[], warnings=[])
            val.validate_note_update.return_value = Mock(is_valid=True, errors=[], warnings=[])
            val.validate_search_query.return_value = Mock(is_valid=True, errors=[], warnings=[])
            val.validate_bulk_operation.return_value = Mock(is_valid=True, errors=[], warnings=[])

            sec.validate_note_data.return_value = {"valid": True, "errors": []}
            sec.can_perform_write_operation.return_value = (True, None)
            sec.escape_sql_wildcards.side_effect = lambda s: s  # passthrough for unit target

            repo.create_note.return_value = OperationResult(success=True, data={"note_id": "n1"})
            repo.get_note_by_id.return_value = OperationResult(success=True, data=make_note())
            repo.get_all_notes.return_value = OperationResult(success=True, data=[make_note()])
            repo.update_note.return_value = SimpleNamespace(success=True, affected_rows=1)
            repo.soft_delete_note.return_value = SimpleNamespace(success=True, affected_rows=1)
            repo.hard_delete_note.return_value = SimpleNamespace(success=True, affected_rows=1)
            repo.restore_note.return_value = SimpleNamespace(success=True, affected_rows=1)
            repo.search_notes.return_value = OperationResult(success=True, data=[make_note()])
            repo.get_notes_by_tag.return_value = OperationResult(success=True, data=[make_note()])
            repo.get_all_tags.return_value = OperationResult(success=True, data={"alpha": 2})
            repo.update_tag_in_notes.return_value = OperationResult(
                success=True, data={"affected_notes": 3}
            )
            repo.remove_tag_from_notes.return_value = OperationResult(
                success=True, data={"affected_notes": 2}
            )
            repo.get_notes_by_project.return_value = OperationResult(
                success=True, data=[make_note(project_id="p")]
            )
            repo.get_notes_without_project.return_value = OperationResult(
                success=True, data=[make_note()]
            )
            repo.bulk_update_project.return_value = SimpleNamespace(success=True, affected_rows=1)
            repo.get_project_notes_count.return_value = OperationResult(success=True, data=5)

            service = NotesService(user_name="u")
            # Attach mocks for direct access if needed
            service.repository = repo
            service.security = sec
            service.validator = val
            yield service


def test_create_note_security_validation_fails(svc: NotesService):
    svc.validator.validate_note_creation.return_value = Mock(is_valid=True, errors=[], warnings=[])
    svc.security.validate_note_data.return_value = {"valid": False, "errors": ["bad content"]}
    result = svc.create_note(make_note("X"))
    assert result.success is False
    assert "security" in result.error.lower()


def test_create_note_permission_denied(svc: NotesService):
    svc.validator.validate_note_creation.return_value = Mock(is_valid=True, errors=[], warnings=[])
    svc.security.validate_note_data.return_value = {"valid": True, "errors": []}
    svc.security.can_perform_write_operation.return_value = (False, "Denied")
    result = svc.create_note(make_note("Y"))
    assert result.success is False
    assert "denied" in result.error.lower()


def test_create_note_repo_error_propagates(svc: NotesService):
    svc.repository.create_note.return_value = OperationResult(success=False, error="db error")
    result = svc.create_note(make_note("Z"))
    assert result.success is False
    assert "db error" in result.error.lower()


def test_update_note_validation_errors_and_repo_not_found(svc: NotesService):
    # Business validation fails
    svc.validator.validate_note_update.return_value = Mock(
        is_valid=False, errors=["bad title"], warnings=[]
    )
    result = svc.update_note("nope", {"title": ""})
    assert result.success is False
    assert "bad title" in result.error.lower()

    # Repo says note not found
    svc.validator.validate_note_update.return_value = Mock(is_valid=True, errors=[], warnings=[])
    svc.repository.get_note_by_id.return_value = OperationResult(success=False, error="missing")
    result = svc.update_note("missing", {"title": "ok"})
    assert result.success is False
    assert "not found" in result.error.lower()


def test_update_note_security_denied_and_no_rows_updated(svc: NotesService):
    # Existing note resolves ok
    svc.repository.get_note_by_id.return_value = OperationResult(
        success=True, data=make_note(title="Old", content="C", tags=["t"])
    )
    # Security validation fails
    svc.security.validate_note_data.return_value = {"valid": False, "errors": ["nope"]}
    res = svc.update_note("id1", {"title": "bad"})
    assert res.success is False
    assert "security" in res.error.lower()

    # Security allowed but repo affects 0 rows
    svc.security.validate_note_data.return_value = {"valid": True, "errors": []}
    svc.security.can_perform_write_operation.return_value = (True, None)
    svc.repository.update_note.return_value = SimpleNamespace(success=True, affected_rows=0)
    res2 = svc.update_note("id1", {"title": "ok"})
    assert res2.success is False


def test_delete_and_restore_permission_denied(svc: NotesService):
    svc.security.can_perform_write_operation.return_value = (False, "no")
    res = svc.delete_note("id1")
    assert res.success is False
    assert "no" in res.error.lower()

    svc.security.can_perform_write_operation.return_value = (False, "stop")
    res2 = svc.restore_note("id1")
    assert res2.success is False
    assert "stop" in res2.error.lower()


def test_search_validation_and_repo_failure(svc: NotesService):
    svc.validator.validate_search_query.return_value = Mock(
        is_valid=False, errors=["empty"], warnings=[]
    )
    res = svc.search_notes("", "All")
    assert res.success is False
    assert "empty" in res.error.lower()

    svc.validator.validate_search_query.return_value = Mock(
        is_valid=True, errors=[], warnings=["warn"]
    )
    svc.repository.search_notes.return_value = OperationResult(success=False, error="oops")
    res2 = svc.search_notes("q", "All")
    assert res2.success is False
    assert "oops" in res2.error.lower()


def test_tag_operations_permission_denied_and_repo_failure(svc: NotesService):
    svc.security.can_perform_write_operation.return_value = (False, "deny")
    r1 = svc.rename_tag("a", "b")
    assert r1.success is False
    assert "deny" in r1.error.lower()

    svc.security.can_perform_write_operation.return_value = (True, None)
    svc.repository.update_tag_in_notes.return_value = OperationResult(success=False, error="bad")
    r2 = svc.rename_tag("a", "b")
    assert r2.success is False
    assert "bad" in r2.error.lower()

    svc.security.can_perform_write_operation.return_value = (False, "deny2")
    d1 = svc.delete_tag("x")
    assert d1.success is False
    assert "deny2" in d1.error.lower()

    svc.security.can_perform_write_operation.return_value = (True, None)
    svc.repository.remove_tag_from_notes.return_value = OperationResult(success=False, error="err")
    d2 = svc.delete_tag("x")
    assert d2.success is False
    assert "err" in d2.error.lower()


def test_project_bulk_ops_validation_permission_and_repo_failure(svc: NotesService):
    svc.validator.validate_bulk_operation.return_value = Mock(
        is_valid=False, errors=["ids"], warnings=[]
    )
    a1 = svc.assign_notes_to_project([], "p")
    assert a1.success is False
    assert "ids" in a1.error.lower()

    svc.validator.validate_bulk_operation.return_value = Mock(is_valid=True, errors=[], warnings=[])
    svc.security.can_perform_write_operation.return_value = (False, "block")
    a2 = svc.assign_notes_to_project(["a"], "p")
    assert a2.success is False
    assert "block" in a2.error.lower()

    svc.security.can_perform_write_operation.return_value = (True, None)
    svc.repository.bulk_update_project.return_value = OperationResult(success=False, error="fail")
    a3 = svc.assign_notes_to_project(["a"], "p")
    assert a3.success is False
    assert "fail" in a3.error.lower()

    # remove_notes_from_project similar
    svc.validator.validate_bulk_operation.return_value = Mock(
        is_valid=False, errors=["ids2"], warnings=[]
    )
    r1 = svc.remove_notes_from_project([])
    assert r1.success is False
    assert "ids2" in r1.error.lower()

    svc.validator.validate_bulk_operation.return_value = Mock(is_valid=True, errors=[], warnings=[])
    svc.security.can_perform_write_operation.return_value = (False, "block2")
    r2 = svc.remove_notes_from_project(["a"])
    assert r2.success is False
    assert "block2" in r2.error.lower()

    svc.security.can_perform_write_operation.return_value = (True, None)
    svc.repository.bulk_update_project.return_value = OperationResult(success=False, error="err2")
    r3 = svc.remove_notes_from_project(["a"])
    assert r3.success is False
    assert "err2" in r3.error.lower()
