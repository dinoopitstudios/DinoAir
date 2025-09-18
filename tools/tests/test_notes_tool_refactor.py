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
    if resp["success"] is not False:
        raise AssertionError
    if resp["error"] != "Both title and content are required":
        raise AssertionError
    if resp["message"] != "Failed to create note: missing required fields":
        raise AssertionError


def test_create_note_success(notesdb_stub: NotesDBStub) -> None:
    # Force legacy id/message
    def _fake_create(note, content_html: str | None = None) -> dict[str, Any]:
        notesdb_stub._store[note.id] = note
        return {
            "success": True,
            "note_id": "note_created_id",
            "message": "Note created successfully",
        }

    # type: ignore[attr-defined]
    notesdb_stub._create_note_override = _fake_create

    resp = nt.create_note("Title", "Body", tags=["a", "b"], project_id="P1")
    if resp["success"] is not True:
        raise AssertionError
    if resp["note_id"] != "note_created_id":
        raise AssertionError
    if resp["message"] != "Note created successfully":
        raise AssertionError
    if "note_data" not in resp:
        raise AssertionError
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
        if key not in resp["note_data"]:
            raise AssertionError


def test_read_note_validation_and_success(notesdb_stub: NotesDBStub) -> None:
    # Validation
    bad = nt.read_note("")
    if bad["success"] is not False:
        raise AssertionError
    if bad["error"] != "note_id is required":
        raise AssertionError
    if bad["message"] != "Failed to read note: note_id is required":
        raise AssertionError

    # Success
    # Ensure a note exists in stub
    note = nt.Note(title="Meeting", content="Discuss items", tags=[], project_id=None)  # type: ignore[call-arg]
    note.id = "note_test_id"
    notesdb_stub._store[note.id] = note

    ok = nt.read_note("note_test_id")
    if ok["success"] is not True:
        raise AssertionError
    if ok["message"] != "Successfully retrieved note: Meeting":
        raise AssertionError
    if "note" not in ok:
        raise AssertionError
    assert isinstance(ok["note"], dict)


def test_read_note_not_found(notesdb_stub: NotesDBStub) -> None:
    # Override to return None for unknown ids
    notesdb_stub.get_note = notesdb_stub._store.get  # type: ignore[assignment]
    missing = nt.read_note("nope")
    if missing["success"] is not False:
        raise AssertionError
    if missing["error"] != "Note not found: nope":
        raise AssertionError
    if missing["message"] != "Note with ID 'nope' not found":
        raise AssertionError


def test_update_note_validation_and_no_fields(notesdb_stub: NotesDBStub) -> None:
    # Validation
    bad = nt.update_note("")
    if bad["success"] is not False:
        raise AssertionError
    if bad["error"] != "note_id is required":
        raise AssertionError
    if bad["message"] != "Failed to update note: note_id is required":
        raise AssertionError

    # No fields specified
    none = nt.update_note("note_test_id")
    if none["success"] is not False:
        raise AssertionError
    if none["error"] != "At least one field must be provided for update":
        raise AssertionError
    if none["message"] != "No fields specified for update":
        raise AssertionError


def test_update_note_success(notesdb_stub: NotesDBStub) -> None:
    note = nt.Note(title="T", content="C", tags=[], project_id=None)  # type: ignore[call-arg]
    note.id = "note_test_id"
    notesdb_stub._store[note.id] = note

    ok = nt.update_note("note_test_id", content="New")
    if ok["success"] is not True:
        raise AssertionError
    if ok["message"] != "Note updated successfully":
        raise AssertionError
    if ok["updated_fields"] != ["content"]:
        raise AssertionError


def test_delete_note_validation_and_success(notesdb_stub: NotesDBStub) -> None:
    # Validation
    bad = nt.delete_note("")
    if bad["success"] is not False:
        raise AssertionError
    if bad["error"] != "note_id is required":
        raise AssertionError
    if bad["message"] != "Failed to delete note: note_id is required":
        raise AssertionError

    # Success
    note = nt.Note(title="T", content="C", tags=[], project_id=None)  # type: ignore[call-arg]
    note.id = "note_test_id"
    notesdb_stub._store[note.id] = note

    ok = nt.delete_note("note_test_id", hard_delete=True)
    if ok["success"] is not True:
        raise AssertionError
    if ok["message"] != "Note deleted successfully":
        raise AssertionError
    if ok["hard_delete"] is not True:
        raise AssertionError


def test_search_notes_validation_and_success(notesdb_stub: NotesDBStub) -> None:
    # Validation
    bad = nt.search_notes("")
    if bad["success"] is not False:
        raise AssertionError
    if bad["error"] != "query is required":
        raise AssertionError
    if bad["message"] != "Failed to search: query is required":
        raise AssertionError

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
    if ok["success"] is not True:
        raise AssertionError
    if ok["message"] != "Found 2 notes matching 'alpha'":
        raise AssertionError
    if ok["count"] != 2:
        raise AssertionError
    assert isinstance(ok["notes"], list)
    assert len(ok["notes"]) == 2
    # preview_len=200 for search_notes
    long_preview = ok["notes"][0]["content"]
    if not long_preview.endswith("..."):
        raise AssertionError
    assert len(long_preview) == 203  # 200 chars + "..."
    short_preview = ok["notes"][1]["content"]
    if short_preview != "short":
        raise AssertionError


def test_list_all_notes_success(notesdb_stub: NotesDBStub) -> None:
    # Provide one very long note (preview_len=100)
    def _fake_all():
        n = nt.Note(title="AllNotes", content=("y" * 150), tags=["work"], project_id=None)  # type: ignore[call-arg]
        n.id = "note_test_id_all"
        return [n]

    notesdb_stub.get_all_notes = _fake_all  # type: ignore[assignment]

    ok = nt.list_all_notes()
    if ok["success"] is not True:
        raise AssertionError
    if ok["message"] != "Retrieved 1 notes":
        raise AssertionError
    if ok["count"] != 1:
        raise AssertionError
    n = ok["notes"][0]
    # preview_len=100 for list_all_notes
    if not n["content"].endswith("..."):
        raise AssertionError
    assert len(n["content"]) == 103  # 100 + "..."


def test_get_notes_by_tag_validation_and_success(_notesdb_stub: NotesDBStub) -> None:
    # Validation
    bad = nt.get_notes_by_tag("")
    if bad["success"] is not False:
        raise AssertionError
    if bad["error"] != "tag_name is required":
        raise AssertionError
    if bad["message"] != "Failed to get notes: tag_name is required":
        raise AssertionError

    # Success (shared stub already returns 120-char content)
    ok = nt.get_notes_by_tag("work")
    if ok["success"] is not True:
        raise AssertionError
    if ok["message"] != "Found 1 notes with tag 'work'":
        raise AssertionError
    if ok["count"] != 1:
        raise AssertionError
    n = ok["notes"][0]
    # preview_len=100 for get_notes_by_tag
    if not n["content"].endswith("..."):
        raise AssertionError
    assert len(n["content"]) == 103  # 100 + "..."


def test_get_all_tags_success(notesdb_stub: NotesDBStub) -> None:
    # Force legacy tag counts
    notesdb_stub.get_all_tags = lambda: {"work": 2, "personal": 1}  # type: ignore[assignment]
    ok = nt.get_all_tags()
    if ok["success"] is not True:
        raise AssertionError
    if ok["tags"] != {"work": 2, "personal": 1}:
        raise AssertionError
    if ok["count"] != 2:
        raise AssertionError
    if ok["message"] != "Retrieved 2 unique tags":
        raise AssertionError
