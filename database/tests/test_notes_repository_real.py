"""
Real database tests for NotesRepository covering CRUD, tags, projects, soft deletes, search, and error handling.
Uses the real DatabaseManager fixture (db_manager) and real Note model.
"""

from datetime import datetime
from unittest.mock import patch
import uuid

import pytest

from database.notes_repository import NotesRepository
from models.note import Note


def _cleanup_notes(db_manager, ids: list[str]) -> None:
    """Remove test notes from the database by IDs."""
    if not ids:
        return
    with db_manager.get_notes_connection() as conn:
        cur = conn.cursor()
        for nid in ids:
            cur.execute("DELETE FROM note_list WHERE id = ?", (nid,))
        conn.commit()


def _new_note(
    note_id: str | None = None,
    title: str = "Repo Test",
    content: str = "Repo content",
    tags: list[str] | None = None,
    project_id: str | None = None,
) -> Note:
    """Create a Note with timestamps set."""
    nid = note_id or f"repo-{uuid.uuid4().hex[:8]}"
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


@pytest.fixture
def repo(db_manager):
    """Repository bound to real db_manager via patch."""
    with patch("database.notes_repository.DatabaseManager", return_value=db_manager):
        yield NotesRepository(user_name="test_user")


def test_crud_soft_delete_restore(repo, db_manager):
    """End-to-end CRUD, soft delete, and restore using real DB."""
    created_ids: list[str] = []
    try:
        note = _new_note(title="Alpha Title", content="Alpha content body", tags=["alpha", "beta"])
        created_ids.append(note.id)

        # Create
        result = repo.create_note(note, content_html="<p>Alpha</p>")
        assert result.success is True

        # Read single
        got = repo.get_note_by_id(note.id)
        assert got.success is True
        n = got.data
        assert isinstance(n, Note)
        assert n.title == "Alpha Title"
        assert "alpha" in n.tags

        # Update
        upd = repo.update_note(note.id, {"title": "Alpha Updated", "tags": ["alpha", "gamma"]})
        assert upd.success is True

        # Read all
        all_notes = repo.get_all_notes()
        assert all_notes.success is True
        assert any(nn.id == note.id for nn in all_notes.data)

        # Search
        srch = repo.search_notes("Alpha", "All", None)
        assert srch.success is True
        assert any(nn.id == note.id for nn in srch.data)

        # Soft delete
        sd = repo.soft_delete_note(note.id)
        assert sd.success is True
        # Should disappear from active
        all_after = repo.get_all_notes()
        assert all_after.success is True
        assert all(nn.id != note.id for nn in all_after.data)
        # Appears in deleted
        deleted = repo.get_deleted_notes()
        assert deleted.success is True
        assert any(nn.id == note.id for nn in deleted.data)

        # Restore
        rs = repo.restore_note(note.id)
        assert rs.success is True
        all_after_restore = repo.get_all_notes()
        assert any(nn.id == note.id for nn in all_after_restore.data)

        # Hard delete
        hd = repo.hard_delete_note(note.id)
        assert hd.success is True
        created_ids.remove(note.id)
        # Verify gone
        missing = repo.get_note_by_id(note.id)
        assert missing.success is False
    finally:
        _cleanup_notes(db_manager, created_ids)


def test_tags_aggregate_and_mutations(repo, db_manager):
    """Create multiple notes; verify tag counts, rename and delete tags."""
    ids: list[str] = []
    try:
        n1 = _new_note(title="Tags A", tags=["alpha", "beta"])
        n2 = _new_note(title="Tags B", tags=["alpha"])
        n3 = _new_note(title="Tags C", tags=["beta", "delta"])
        for n in (n1, n2, n3):
            ids.append(n.id)
            assert repo.create_note(n).success

        # Aggregate
        tags = repo.get_all_tags()
        assert tags.success is True
        # Case preserved in result keys (original case), counts aggregated case-insensitively
        # We inserted 'alpha' twice
        assert tags.data.get("alpha", 0) == 2
        # 'beta' twice too
        assert tags.data.get("beta", 0) == 2

        # Rename tag alpha -> omega
        ren = repo.update_tag_in_notes("alpha", "omega")
        assert ren.success is True
        assert isinstance(ren.data, dict)
        assert ren.data["affected_notes"] >= 2

        # Verify rename took effect
        with db_manager.get_notes_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT tags FROM note_list WHERE is_deleted = 0")
            rows = [r[0] for r in cur.fetchall()]
        assert any('"omega"' in (r or "") for r in rows)
        assert all('"alpha"' not in (r or "") for r in rows)

        # Remove tag beta
        rm = repo.remove_tag_from_notes("beta")
        assert rm.success is True
        assert rm.data["affected_notes"] >= 1

        # Verify removal
        with db_manager.get_notes_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT tags FROM note_list WHERE is_deleted = 0")
            rows = [r[0] for r in cur.fetchall()]
        assert all('"beta"' not in (r or "") for r in rows)
    finally:
        _cleanup_notes(db_manager, ids)


def test_project_association_and_counts(repo, db_manager):
    """Assign/remove projects and verify filtering and counts."""
    ids: list[str] = []
    try:
        n1 = _new_note(title="Proj 1", tags=["p"], project_id=None)
        n2 = _new_note(title="Proj 2", tags=["p"], project_id=None)
        for n in (n1, n2):
            ids.append(n.id)
            assert repo.create_note(n).success

        # Assign to project X
        bulk = repo.bulk_update_project([n1.id, n2.id], "proj-X")
        assert bulk.success is True

        # Count
        cnt = repo.get_project_notes_count("proj-X")
        assert cnt.success is True
        assert cnt.data >= 2

        # Filter by project
        by_proj = repo.get_notes_by_project("proj-X")
        assert by_proj.success
        assert all(nn.project_id == "proj-X" for nn in by_proj.data)

        # Remove project (set None)
        bulk_rm = repo.bulk_update_project([n1.id, n2.id], None)
        assert bulk_rm.success is True

        # Without project
        no_proj = repo.get_notes_without_project()
        assert no_proj.success is True
        assert any(nn.id in (n1.id, n2.id) for nn in no_proj.data)
    finally:
        _cleanup_notes(db_manager, ids)


def test_search_filters_and_sql_wildcards(repo, db_manager):
    """Ensure search supports filters and LIKE with escaped wildcards."""
    ids: list[str] = []
    try:
        n1 = _new_note(title="Title 100% match", content="Body_underscore", tags=["x"])
        n2 = _new_note(title="Other", content="Nothing to see", tags=["y"])
        for n in (n1, n2):
            ids.append(n.id)
            assert repo.create_note(n).success

        # Title only
        t_only = repo.search_notes("100%", "Title Only", None)
        assert t_only.success is True
        assert any(nn.id == n1.id for nn in t_only.data)

        # Content only
        c_only = repo.search_notes("Body_", "Content Only", None)
        assert c_only.success is True
        assert any(nn.id == n1.id for nn in c_only.data)

        # Tags only (search JSON text)
        tags_only = repo.search_notes("x", "Tags Only", None)
        assert tags_only.success is True
        assert any(nn.id == n1.id for nn in tags_only.data)

        # All
        allf = repo.search_notes("Other", "All", None)
        assert allf.success is True
        assert any(nn.id == n2.id for nn in allf.data)
    finally:
        _cleanup_notes(db_manager, ids)


def test_update_note_validation_error(repo, db_manager):
    """Repository should reject updates with no valid fields."""
    n = _new_note(title="Update Invalid")
    try:
        assert repo.create_note(n).success
        bad = repo.update_note(n.id, {"not_a_field": "value"})
        assert bad.success is False
        assert "No valid fields" in bad.error
    finally:
        _cleanup_notes(db_manager, [n.id])
