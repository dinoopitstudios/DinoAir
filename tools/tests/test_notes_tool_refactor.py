from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest


if TYPE_CHECKING:
    from tools.tests.helpers.db_stubs import NotesDBStub


pytestmark = pytest.mark.usefixtures("patch_tools")

try:
    import src.tools.notes_tool as nt
except Exception:
    import tools.notes_tool as nt


def test_create_note_validation_error(notesdb_stub: NotesDBStub) -> None:
    resp = nt.create_note("", "")
    assert resp["success"] is False
    assert resp["error"] == "Both title and content are required"
    assert resp["message"] == "Failed to create note: missing required fields"


def test_create_note_success(notesdb_stub: NotesDBStub) -> None:
    # Force legacy id/message
    def _fake_create(note, content_html: str | None = None) -> dict[str, Any]:
        notesdb_stub._store[note.id] = note
        return {
            "success": True,
            "note_id": "note_created_id",
            "message": "Note created successfully",
        }

    notesdb_stub._create_note_override = _fake_create  # type: ignore[attr-defined]

    resp = nt.create_note("Title", "Body", tags=["a", "b"], project_id="P1")
    assert resp["success"] is True
    assert resp["note_id"] == "note_created_id"
    assert resp["message"] == "Note created successfully"
    assert "note_data" in resp
    assert isinstance(resp["note_data"], dict)
    for key in (
        "id",
        "title",
        "content",
        "tags",
        "project_id",
        "created_at",
        "updated_at",
    ):
        assert key in resp["note_data"]


def test_read_note_validation_and_success(notesdb_stub: NotesDBStub) -> None:
    # Validation
    bad = nt.read_note("")
    assert bad["success"] is False
    assert bad["error"] == "note_id is required"
    assert bad["message"] == "Failed to read note: note_id is required"

    # Success
    # Ensure a note exists in stub
    note = nt.Note(title="Meeting", content="Discuss items", tags=[], project_id=None)  # type: ignore[call-arg]
    note.id = "note_test_id"
    notesdb_stub._store[note.id] = note

    ok = nt.read_note("note_test_id")
    assert ok["success"] is True
    assert ok["message"] == "Successfully retrieved note: Meeting"
    assert "note" in ok
    assert isinstance(ok["note"], dict)


def test_read_note_not_found(notesdb_stub: NotesDBStub) -> None:
    # Override to return None for unknown ids
    notesdb_stub.get_note = notesdb_stub._store.get  # type: ignore[assignment]
    missing = nt.read_note("nope")
    assert missing["success"] is False
    assert missing["error"] == "Note not found: nope"
    assert missing["message"] == "Note with ID 'nope' not found"


def test_update_note_validation_and_no_fields(notesdb_stub: NotesDBStub) -> None:
    # Validation
    bad = nt.update_note("")
    assert bad["success"] is False
    assert bad["error"] == "note_id is required"
    assert bad["message"] == "Failed to update note: note_id is required"

    # No fields specified
    none = nt.update_note("note_test_id")
    assert none["success"] is False
    assert none["error"] == "At least one field must be provided for update"
    assert none["message"] == "No fields specified for update"


def test_update_note_success(notesdb_stub: NotesDBStub) -> None:
    note = nt.Note(title="T", content="C", tags=[], project_id=None)  # type: ignore[call-arg]
    note.id = "note_test_id"
    notesdb_stub._store[note.id] = note

    ok = nt.update_note("note_test_id", content="New")
    assert ok["success"] is True
    assert ok["message"] == "Note updated successfully"
    assert ok["updated_fields"] == ["content"]


def test_delete_note_validation_and_success(notesdb_stub: NotesDBStub) -> None:
    # Validation
    bad = nt.delete_note("")
    assert bad["success"] is False
    assert bad["error"] == "note_id is required"
    assert bad["message"] == "Failed to delete note: note_id is required"

    # Success
    note = nt.Note(title="T", content="C", tags=[], project_id=None)  # type: ignore[call-arg]
    note.id = "note_test_id"
    notesdb_stub._store[note.id] = note

    ok = nt.delete_note("note_test_id", hard_delete=True)
    assert ok["success"] is True
    assert ok["message"] == "Note deleted successfully"
    assert ok["hard_delete"] is True


def test_search_notes_validation_and_success(notesdb_stub: NotesDBStub) -> None:
    # Validation
    bad = nt.search_notes("")
    assert bad["success"] is False
    assert bad["error"] == "query is required"
    assert bad["message"] == "Failed to search: query is required"

    # Provide two results matching legacy expectations (preview_len=200)
    def _fake_search(query: str, filter_option: str, project_id: str | None):
        long_content = "x" * 250
        n1 = nt.Note(title="Alpha", content=long_content, tags=["work"], project_id=None)  # type: ignore[call-arg]
        n1.id = "note_test_id"
        n2 = nt.Note(title="Beta", content="short", tags=["personal"], project_id=None)  # type: ignore[call-arg]
        n2.id = "note_test_id_2"
        return [n1, n2]

    notesdb_stub.search_notes = _fake_search  # type: ignore[assignment]

    ok = nt.search_notes("alpha", "All")
    assert ok["success"] is True
    assert ok["message"] == "Found 2 notes matching 'alpha'"
    assert ok["count"] == 2
    assert isinstance(ok["notes"], list)
    assert len(ok["notes"]) == 2
    # preview_len=200 for search_notes
    long_preview = ok["notes"][0]["content"]
    assert long_preview.endswith("...")
    assert len(long_preview) == 203  # 200 chars + "..."
    short_preview = ok["notes"][1]["content"]
    assert short_preview == "short"  # unchanged when below preview_len


def test_list_all_notes_success(notesdb_stub: NotesDBStub) -> None:
    # Provide one very long note (preview_len=100)
    def _fake_all():
        n = nt.Note(title="AllNotes", content=("y" * 150), tags=["work"], project_id=None)  # type: ignore[call-arg]
        n.id = "note_test_id_all"
        return [n]

    notesdb_stub.get_all_notes = _fake_all  # type: ignore[assignment]

    ok = nt.list_all_notes()
    assert ok["success"] is True
    assert ok["message"] == "Retrieved 1 notes"
    assert ok["count"] == 1
    n = ok["notes"][0]
    # preview_len=100 for list_all_notes
    assert n["content"].endswith("...")
    assert len(n["content"]) == 103  # 100 + "..."


def test_get_notes_by_tag_validation_and_success(notesdb_stub: NotesDBStub) -> None:
    # Validation
    bad = nt.get_notes_by_tag("")
    assert bad["success"] is False
    assert bad["error"] == "tag_name is required"
    assert bad["message"] == "Failed to get notes: tag_name is required"

    # Success (shared stub already returns 120-char content)
    ok = nt.get_notes_by_tag("work")
    assert ok["success"] is True
    assert ok["message"] == "Found 1 notes with tag 'work'"
    assert ok["count"] == 1
    n = ok["notes"][0]
    # preview_len=100 for get_notes_by_tag
    assert n["content"].endswith("...")
    assert len(n["content"]) == 103  # 100 + "..."


def test_get_all_tags_success(notesdb_stub: NotesDBStub) -> None:
    # Force legacy tag counts
    notesdb_stub.get_all_tags = lambda: {"work": 2, "personal": 1}  # type: ignore[assignment]
    ok = nt.get_all_tags()
    assert ok["success"] is True
    assert ok["tags"] == {"work": 2, "personal": 1}
    assert ok["count"] == 2
    assert ok["message"] == "Retrieved 2 unique tags"
