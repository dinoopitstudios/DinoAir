"""
Unit tests for NotesValidator covering business rule validation, warnings, and edge cases.
Aligns with current implementation fields (is_valid, errors, warnings).
"""

from database.notes_validator import NotesValidator


def test_validate_note_creation_valid_minimal():
    """Valid creation with normal inputs should pass and may include no warnings."""
    v = NotesValidator()
    res = v.validate_note_creation("Hello", "World", ["tag1", "tag2"])
    if res.is_valid is not True:
        raise AssertionError
    if res.errors != []:
        raise AssertionError
    assert isinstance(res.warnings, list)


def test_validate_note_creation_empty_title_error():
    """Empty or whitespace-only title should error."""
    v = NotesValidator()
    res = v.validate_note_creation("   ", "x", [])
    if res.is_valid is not False:
        raise AssertionError
    if not any("title" in e.lower() for e in res.errors):
        raise AssertionError


def test_validate_note_creation_short_title_warning():
    """Title shorter than 3 chars should be a warning, not an error."""
    v = NotesValidator()
    res = v.validate_note_creation("Hi", "x", [])
    if res.is_valid is not True:
        raise AssertionError
    if not any("short" in w.lower() for w in res.warnings):
        raise AssertionError


def test_validate_note_creation_content_too_long_error():
    """Content exceeding 50,000 characters should error."""
    v = NotesValidator()
    long_content = "A" * 50001
    res = v.validate_note_creation("Valid", long_content, [])
    if res.is_valid is not False:
        raise AssertionError
    if not any("content exceeds" in e.lower() for e in res.errors):
        raise AssertionError


def test_validate_note_creation_many_tags_warning_and_duplicates_warning():
    """More than 20 tags yields a warning; duplicate tags (case-insensitive) yields a warning."""
    v = NotesValidator()
    tags = [f"t{i}" for i in range(21)]
    # add a duplicate differing only by case
    tags.append("Dup")
    tags.append("dup")
    res = v.validate_note_creation("Valid", "ok", tags)
    if res.is_valid is not True:
        raise AssertionError
    warns = " ".join(res.warnings).lower()
    if "many tags" not in warns:
        raise AssertionError
    if "duplicate tags" not in warns:
        raise AssertionError


def test_validate_note_update_valid_full():
    """Valid update with allowed fields only should pass."""
    v = NotesValidator()
    res = v.validate_note_update(
        {
            "title": "Updated",
            "content": "Updated body",
            "tags": ["a", "b"],
            "content_html": "<p>x</p>",
            "project_id": "proj-1",
        }
    )
    if res.is_valid is not True:
        raise AssertionError
    if res.errors != []:
        raise AssertionError


def test_validate_note_update_unknown_fields_error():
    """Unknown fields should error."""
    v = NotesValidator()
    res = v.validate_note_update({"bogus": 1, "title": "T"})
    if res.is_valid is not False:
        raise AssertionError
    if not any("unknown fields" in e.lower() for e in res.errors):
        raise AssertionError
    # Ensure unknown field is mentioned
    if "bogus" not in " ".join(res.errors):
        raise AssertionError


def test_validate_note_update_field_type_errors():
    """Type validations for title/content/tags/project_id."""
    v = NotesValidator()

    # title must be str and non-empty when provided
    r1 = v.validate_note_update({"title": ""})
    if r1.is_valid is not False:
        raise AssertionError
    if not any("title cannot be empty" in e.lower() for e in r1.errors):
        raise AssertionError

    r2 = v.validate_note_update({"title": 123})
    if r2.is_valid is not False:
        raise AssertionError
    if not any("title must be a string" in e.lower() for e in r2.errors):
        raise AssertionError

    # content must be str when provided
    r3 = v.validate_note_update({"content": 42})
    if r3.is_valid is not False:
        raise AssertionError
    if not any("content must be a string" in e.lower() for e in r3.errors):
        raise AssertionError

    # tags must be list of strings
    r4 = v.validate_note_update({"tags": "not-a-list"})
    if r4.is_valid is not False:
        raise AssertionError
    if not any("tags must be a list" in e.lower() for e in r4.errors):
        raise AssertionError

    r5 = v.validate_note_update({"tags": ["ok", 123]})
    if r5.is_valid is not False:
        raise AssertionError
    if not any("all tags must be strings" in e.lower() for e in r5.errors):
        raise AssertionError

    # project_id must be str or None
    r6 = v.validate_note_update({"project_id": 999})
    if r6.is_valid is not False:
        raise AssertionError
    if not any("project id must be a string or none" in e.lower() for e in r6.errors):
        raise AssertionError


def test_validate_search_query_valid_and_warnings():
    """Valid search with long query should warn but still pass."""
    v = NotesValidator()
    long_query = "X" * 501
    res = v.validate_search_query(long_query, "All")
    if res.is_valid is not True:
        raise AssertionError
    if not any("very long" in w.lower() for w in res.warnings):
        raise AssertionError


def test_validate_search_query_errors():
    """Empty query and invalid filter should error."""
    v = NotesValidator()
    # Empty query
    r1 = v.validate_search_query("   ", "All")
    if r1.is_valid is not False:
        raise AssertionError
    if not any("cannot be empty" in e.lower() for e in r1.errors):
        raise AssertionError
    # Invalid filter
    r2 = v.validate_search_query("q", "Nonexistent")
    if r2.is_valid is not False:
        raise AssertionError
    if not any("invalid filter" in e.lower() for e in r2.errors):
        raise AssertionError


def test_validate_bulk_operation_happy_path_and_warnings():
    """Bulk operation with many IDs should pass with warnings."""
    v = NotesValidator()
    ids = [f"id{i}" for i in range(101)]  # 101 triggers warning
    res = v.validate_bulk_operation(ids, "assign_project")
    if res.is_valid is not True:
        raise AssertionError
    if not any("many notes" in w.lower() for w in res.warnings):
        raise AssertionError


def test_validate_bulk_operation_errors_for_empty_dups_and_operation():
    """Empty IDs, duplicate IDs, and invalid op should error."""
    v = NotesValidator()

    # Empty IDs
    r1 = v.validate_bulk_operation([], "assign_project")
    if r1.is_valid is not False:
        raise AssertionError
    if not any("no note ids" in e.lower() for e in r1.errors):
        raise AssertionError

    # Duplicate IDs
    r2 = v.validate_bulk_operation(["a", "a", "b"], "assign_project")
    if r2.is_valid is not False:
        raise AssertionError
    if not any("duplicate" in e.lower() for e in r2.errors):
        raise AssertionError

    # Invalid operation
    r3 = v.validate_bulk_operation(["a"], "bad_op")
    if r3.is_valid is not False:
        raise AssertionError
    if not any("invalid operation" in e.lower() for e in r3.errors):
        raise AssertionError
