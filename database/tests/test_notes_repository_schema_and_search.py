"""
Additional real-database tests for NotesRepository focusing on schema readiness and search/project filters.
No mocks of repository logic; uses real SQLite via db_manager fixture.
"""

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest

from database.notes_repository import NotesRepository
from models.note import Note


def _new_note(
    title: str = "Alpha 123",
    content: str = "Body content",
    tags: list[str] | None = None,
    project_id: str | None = None,
) -> Note:
    nid = f"repo-{uuid.uuid4().hex[:10]}"
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
def repo(db_manager):
    # Bind repository to real db_manager connection factory
    with patch("database.notes_repository.DatabaseManager", return_value=db_manager):
        yield NotesRepository(user_name="test_user")


def test_schema_contains_is_deleted_and_content_html(_repo, db_manager):
    # The repository ensures these columns exist on init (via _ensure_database_ready)
    with db_manager.get_notes_connection() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(note_list)")
        cols = [r[1] for r in cur.fetchall()]
    if "is_deleted" not in cols:
        raise AssertionError("Expected is_deleted column to be present")
    if "content_html" not in cols:
        raise AssertionError("Expected content_html column to be present")


def test_search_with_project_filter_is_respected(repo, db_manager):
    created: list[str] = []
    try:
        n_proj_a = _new_note(title="Alpha 123", content="A_Body", tags=["a"], project_id="proj-A")
        n_proj_b = _new_note(title="Alpha 123", content="B_Body", tags=["b"], project_id="proj-B")
        for n in (n_proj_a, n_proj_b):
            if not repo.create_note(n, content_html=f"<p>{n.title}</p>").success:
                raise AssertionError
            created.append(n.id)

        # Search by title with project filter: should return only the note in that project
        res_a = repo.search_notes("Alpha 123", "Title Only", project_id="proj-A")
        if res_a.success is not True:
            raise AssertionError
        ids_a = {nn.id for nn in res_a.data}
        if n_proj_a.id not in ids_a:
            raise AssertionError
        if n_proj_b.id in ids_a:
            raise AssertionError

        res_b = repo.search_notes("Alpha 123", "Title Only", project_id="proj-B")
        if res_b.success is not True:
            raise AssertionError
        ids_b = {nn.id for nn in res_b.data}
        if n_proj_b.id not in ids_b:
            raise AssertionError
        if n_proj_a.id in ids_b:
            raise AssertionError

        # Search across all (no project filter) should find both
        res_all = repo.search_notes("Alpha 123", "All", None)
        if res_all.success is not True:
            raise AssertionError
        ids_all = {nn.id for nn in res_all.data}
        if not {n_proj_a.id, n_proj_b.id}.issubset(ids_all):
            raise AssertionError
    finally:
        _cleanup_ids(db_manager, created)


def test_get_notes_by_tag_is_case_sensitive_membership(repo, db_manager):
    created: list[str] = []
    try:
        n1 = _new_note(title="Tag Case", tags=["Alpha", "beta"])
        n2 = _new_note(title="Tag Other", tags=["omega"])
        for n in (n1, n2):
            if not repo.create_note(n).success:
                raise AssertionError
            created.append(n.id)

        # Lowercase query should NOT match 'Alpha' (repository behavior is case-sensitive)
        res_lower = repo.get_notes_by_tag("alpha")
        if res_lower.success is not True:
            raise AssertionError
        ids_lower = {nn.id for nn in res_lower.data}
        if n1.id in ids_lower:
            raise AssertionError

        # Exact-case query must match stored tag
        res_exact = repo.get_notes_by_tag("Alpha")
        if res_exact.success is not True:
            raise AssertionError
        ids_exact = {nn.id for nn in res_exact.data}
        if n1.id not in ids_exact:
            raise AssertionError
        if n2.id in ids_exact:
            raise AssertionError
    finally:
        _cleanup_ids(db_manager, created)
