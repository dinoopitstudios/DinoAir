"""
Real integration tests for NotesService orchestrating NotesRepository, NotesValidator, and NotesSecurity.
Uses real DatabaseManager via fixture and the real Note model. Covers CRUD, validation, security, tags, projects, soft deletes.
"""

from datetime import datetime
import os
from unittest.mock import patch
import uuid

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
        assert create_res.success is True
        assert isinstance(create_res.data, dict)
        assert "note_id" in create_res.data

        # Get one
        get_res = service.get_note(note.id)
        assert get_res.success is True
        assert get_res.data.id == note.id

        # Get all
        all_res = service.get_all_notes()
        assert all_res.success is True
        assert any(n.id == note.id for n in all_res.data)

        # Search title only (wildcards escaped internally)
        s1 = service.search_notes("100%", "Title Only")
        assert s1.success is True
        assert any(n.id == note.id for n in s1.data)

        # Search content only
        s2 = service.search_notes("Body_", "Content Only")
        assert s2.success is True
        assert any(n.id == note.id for n in s2.data)

        # Update fields including tags and content_html
        upd_res = service.update_note(
            note.id,
            {
                "title": "Service Alpha Updated",
                "tags": ["alpha", "gamma"],
                "content_html": "<p>updated</p>",
            },
        )
        assert upd_res.success is True
        assert "updated_fields" in upd_res.data

        # By tag
        by_tag = service.get_notes_by_tag("alpha")
        assert by_tag.success is True
        assert any(n.id == note.id for n in by_tag.data)

        # All tags aggregate
        tags = service.get_all_tags()
        assert tags.success is True
        assert isinstance(tags.data, dict)
        assert any(k.lower() in ("alpha", "gamma", "beta") for k in tags.data)

        # Rename tag alpha -> omega across notes
        rtag = service.rename_tag("alpha", "omega")
        assert rtag.success is True
        assert rtag.data["affected_notes"] >= 1

        # Delete tag beta across notes
        dtag = service.delete_tag("beta")
        assert dtag.success is True

        # Project operations
        assign = service.assign_notes_to_project([note.id], "proj-Z")
        assert assign.success is True
        by_proj = service.get_notes_by_project("proj-Z")
        assert by_proj.success is True
        assert any(n.id == note.id for n in by_proj.data)

        # Remove project
        rm_proj = service.remove_notes_from_project([note.id])
        assert rm_proj.success is True
        no_proj = service.get_notes_without_project()
        assert no_proj.success is True
        assert any(n.id == note.id for n in no_proj.data)

        # Soft delete
        soft = service.delete_note(note.id)
        assert soft.success is True
        del_list = service.get_deleted_notes()
        assert del_list.success is True
        assert any(n.id == note.id for n in del_list.data)

        # Restore
        rest = service.restore_note(note.id)
        assert rest.success is True

        # Hard delete
        hard = service.delete_note(note.id, hard_delete=True)
        assert hard.success is True
        created_ids.remove(note.id)
        missing = service.get_note(note.id)
        assert missing.success is False
    finally:
        _cleanup_ids(db_manager, created_ids)


def test_validation_failure_on_create(service, _db_manager):
    """Business validation should fail on empty title."""
    bad = _new_note(title="", content="ok", tags=[])
    res = service.create_note(bad)
    assert res.success is False
    assert "title" in res.error.lower()


def test_security_blocks_writes_without_env(db_manager):
    """When ALLOW_NOTES_FALLBACK_WRITES is not set, fallback security blocks writes."""
    with patch("database.notes_repository.DatabaseManager", return_value=db_manager):
        with patch.dict(os.environ, {}, clear=True):
            svc = NotesService(user_name="test_user")
            note = _new_note(title="Secure Block", content="c")
            res = svc.create_note(note)
            assert res.success is False
            assert "security" in res.error.lower() or "blocked" in res.error.lower()


def test_update_nonexistent_note_returns_error(service):
    """Update should fail cleanly when note does not exist."""
    res = service.update_note("nonexistent-id-xyz", {"title": "Nope"})
    assert res.success is False
    assert "not found" in res.error.lower()
