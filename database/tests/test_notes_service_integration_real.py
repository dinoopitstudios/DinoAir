"""
Real integration tests for NotesService orchestrating NotesRepository, NotesValidator, and NotesSecurity.
Uses real DatabaseManager via fixture and the real Note model. Covers CRUD, validation, security, tags, projects, soft deletes.
"""

import os
import uuid
from datetime import datetime
from unittest.mock import patch

import pytest

from database.notes_service import NotesService
from models.note import Note


def _new_note(
    title: str = "Svc Title",
    content: str = "Svc content",
    tags: list[str] | None = None,
    project_id: str | None = None,
) -> Note:
    nid = f"svc-{uuid.uuid4().hex[:10]}"
    now = datetime.now().isoformat()
    return Note(
        id=nid,
        title=title,
        content=content,
        tags=tags or [],
        project_id=project_id,
        created_at=now,
        updated_at=now,
    )


def _cleanup_ids(db_manager, ids: list[str]) -> None:
    if not ids:
        return
    with db_manager.get_notes_connection() as conn:
        cur = conn.cursor()
        for nid in ids:
            cur.execute("DELETE FROM note_list WHERE id = ?", (nid,))
        conn.commit()


@pytest.fixture
def service(db_manager):
    # Patch repository's DatabaseManager to use the real db_manager fixture
    with patch("database.notes_repository.DatabaseManager", return_value=db_manager):
        # Allow fallback security write operations
        with patch.dict(os.environ, {"ALLOW_NOTES_FALLBACK_WRITES": "1"}, clear=False):
            yield NotesService(user_name="test_user")


@pytest.mark.integration
def test_full_workflow_create_read_update_search_delete_restore_harddelete(service, db_manager):
    created_ids: list[str] = []
    try:
        note = _new_note(
            title="Service Alpha 100% match", content="Body_with_underscore", tags=["alpha", "beta"]
        )
        created_ids.append(note.id)

        # Create (with project and html)
        create_res = service.create_note(note, content_html="<p>alpha</p>", project_id="proj-A")
        if create_res.success is not True:
            raise AssertionError
        assert isinstance(create_res.data, dict)
        if "note_id" not in create_res.data:
            raise AssertionError

        # Get one
        get_res = service.get_note(note.id)
        if get_res.success is not True:
            raise AssertionError
        if get_res.data.id != note.id:
            raise AssertionError

        # Get all
        all_res = service.get_all_notes()
        if all_res.success is not True:
            raise AssertionError
        if not any(n.id == note.id for n in all_res.data):
            raise AssertionError

        # Search title only (wildcards escaped internally)
        s1 = service.search_notes("100%", "Title Only")
        if s1.success is not True:
            raise AssertionError
        if not any(n.id == note.id for n in s1.data):
            raise AssertionError

        # Search content only
        s2 = service.search_notes("Body_", "Content Only")
        if s2.success is not True:
            raise AssertionError
        if not any(n.id == note.id for n in s2.data):
            raise AssertionError

        # Update fields including tags and content_html
        upd_res = service.update_note(
            note.id,
            {
                "title": "Service Alpha Updated",
                "tags": ["alpha", "gamma"],
                "content_html": "<p>updated</p>",
            },
        )
        if upd_res.success is not True:
            raise AssertionError
        if "updated_fields" not in upd_res.data:
            raise AssertionError

        # By tag
        by_tag = service.get_notes_by_tag("alpha")
        if by_tag.success is not True:
            raise AssertionError
        if not any(n.id == note.id for n in by_tag.data):
            raise AssertionError

        # All tags aggregate
        tags = service.get_all_tags()
        if tags.success is not True:
            raise AssertionError
        assert isinstance(tags.data, dict)
        if not any(k.lower() in ("alpha", "gamma", "beta") for k in tags.data):
            raise AssertionError

        # Rename tag alpha -> omega across notes
        rtag = service.rename_tag("alpha", "omega")
        if rtag.success is not True:
            raise AssertionError
        if rtag.data["affected_notes"] < 1:
            raise AssertionError

        # Delete tag beta across notes
        dtag = service.delete_tag("beta")
        if dtag.success is not True:
            raise AssertionError

        # Project operations
        assign = service.assign_notes_to_project([note.id], "proj-Z")
        if assign.success is not True:
            raise AssertionError
        by_proj = service.get_notes_by_project("proj-Z")
        if by_proj.success is not True:
            raise AssertionError
        if not any(n.id == note.id for n in by_proj.data):
            raise AssertionError

        # Remove project
        rm_proj = service.remove_notes_from_project([note.id])
        if rm_proj.success is not True:
            raise AssertionError
        no_proj = service.get_notes_without_project()
        if no_proj.success is not True:
            raise AssertionError
        if not any(n.id == note.id for n in no_proj.data):
            raise AssertionError

        # Soft delete
        soft = service.delete_note(note.id)
        if soft.success is not True:
            raise AssertionError
        del_list = service.get_deleted_notes()
        if del_list.success is not True:
            raise AssertionError
        if not any(n.id == note.id for n in del_list.data):
            raise AssertionError

        # Restore
        rest = service.restore_note(note.id)
        if rest.success is not True:
            raise AssertionError

        # Hard delete
        hard = service.delete_note(note.id, hard_delete=True)
        if hard.success is not True:
            raise AssertionError
        created_ids.remove(note.id)
        missing = service.get_note(note.id)
        if missing.success is not False:
            raise AssertionError
    finally:
        _cleanup_ids(db_manager, created_ids)


def test_validation_failure_on_create(service, _db_manager):
    """Business validation should fail on empty title."""
    bad = _new_note(title="", content="ok", tags=[])
    res = service.create_note(bad)
    if res.success is not False:
        raise AssertionError
    if "title" not in res.error.lower():
        raise AssertionError


def test_security_blocks_writes_without_env(db_manager):
    """When ALLOW_NOTES_FALLBACK_WRITES is not set, fallback security blocks writes."""
    with patch("database.notes_repository.DatabaseManager", return_value=db_manager):
        with patch.dict(os.environ, {}, clear=True):
            svc = NotesService(user_name="test_user")
            note = _new_note(title="Secure Block", content="c")
            res = svc.create_note(note)
            if res.success is not False:
                raise AssertionError
            if not ("security" in res.error.lower() or "blocked" in res.error.lower()):
                raise AssertionError


def test_update_nonexistent_note_returns_error(service):
    """Update should fail cleanly when note does not exist."""
    res = service.update_note("nonexistent-id-xyz", {"title": "Nope"})
    if res.success is not False:
        raise AssertionError
    if "not found" not in res.error.lower():
        raise AssertionError
