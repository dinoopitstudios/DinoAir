from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from tools.tests.helpers.db_stubs import FSDBStub

pytestmark = pytest.mark.usefixtures("patch_tools")

try:
    import src.tools.file_search_tool as fst
except Exception:
    import tools.file_search_tool as fst


def test_search_files_by_keywords_error_empty() -> None:
    resp = fst.search_files_by_keywords([])
    if resp["success"] is not False:
        raise AssertionError
    if resp["error"] != "keywords list is required and cannot be empty":
        raise AssertionError
    if resp["message"] != "Failed to search: no keywords provided":
        raise AssertionError


def test_search_files_by_keywords_success(fsdb_stub: FSDBStub) -> None:
    def _fake_search(keywords, limit=10, file_types=None, file_paths=None):
        return [
            {"chunk_id": "c1", "content": "alpha beta", "relevance_score": 0.9},
            {"chunk_id": "c2", "content": "gamma delta", "relevance_score": 0.8},
            {"chunk_id": "c3", "content": "epsilon zeta", "relevance_score": 0.7},
        ][:limit]

    fsdb_stub.search_by_keywords = _fake_search  # type: ignore[assignment]

    resp = fst.search_files_by_keywords(["alpha", "beta"], limit=2)
    if resp["success"] is not True:
        raise AssertionError
    if resp["count"] != 2:
        raise AssertionError
    assert isinstance(resp["results"], list)
    assert len(resp["results"]) == 2
    if resp["keywords"] != ["alpha", "beta"]:
        raise AssertionError
    if resp["message"] != "Found 2 matching chunks":
        raise AssertionError


def test_get_file_info_not_found(fsdb_stub: FSDBStub) -> None:
    # type: ignore[assignment]
    fsdb_stub.get_file_by_path = fsdb_stub._files.get
    resp = fst.get_file_info("/no/such/file.txt")
    if resp["success"] is not False:
        raise AssertionError
    if resp["error"] != "File not found in index: /no/such/file.txt":
        raise AssertionError
    if resp["message"] != "File '/no/such/file.txt' is not in the search index":
        raise AssertionError


def test_get_file_info_found(fsdb_stub: FSDBStub, tmp_path: Path) -> None:
    # Preload the stub with a file entry via add_indexed_file
    p = tmp_path / "doc.txt"
    p.write_text("data", encoding="utf-8")
    # Simulate indexing through the API to populate stub
    _ = fst.add_file_to_index(str(p), file_type="txt")
    resp = fst.get_file_info(str(p))
    if resp["success"] is not True:
        raise AssertionError
    if "file_info" not in resp:
        raise AssertionError
    assert isinstance(resp["file_info"], dict)
    if resp["message"] != "File information retrieved successfully":
        raise AssertionError


def test_add_file_to_index_nonexistent_path(fsdb_stub: FSDBStub, tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"
    resp = fst.add_file_to_index(str(missing))
    if resp["success"] is not False:
        raise AssertionError
    if resp["error"] != f"File does not exist: {missing}":
        raise AssertionError
    if resp["message"] != f"Cannot index non-existent file: {missing}":
        raise AssertionError


def test_add_file_to_index_directory_instead_of_file(fsdb_stub: FSDBStub, tmp_path: Path) -> None:
    resp = fst.add_file_to_index(str(tmp_path))
    if resp["success"] is not False:
        raise AssertionError
    if resp["error"] != f"Path is not a file: {tmp_path}":
        raise AssertionError
    if resp["message"] != f"Cannot index directory: {tmp_path}":
        raise AssertionError


def test_remove_file_from_index_success_and_failure(fsdb_stub: FSDBStub, tmp_path: Path) -> None:
    # Index a file first
    p = tmp_path / "keep.txt"
    p.write_text("x", encoding="utf-8")
    _ = fst.add_file_to_index(str(p), file_type="txt")

    # Success removal
    ok = fst.remove_file_from_index(str(p))
    if ok["success"] is not True:
        raise AssertionError
    if ok["message"] != "File removed from index successfully":
        raise AssertionError

    # Failure removal
    bad = fst.remove_file_from_index(str(p))
    if bad["success"] is not False:
        raise AssertionError
    if bad["error"] != "File not found in index":
        raise AssertionError
    if bad["message"] != "Failed to remove file: File not found in index":
        raise AssertionError


def test_get_search_statistics_success(fsdb_stub: FSDBStub) -> None:
    resp = fst.get_search_statistics()
    if resp["success"] is not True:
        raise AssertionError
    if "stats" not in resp:
        raise AssertionError
    assert isinstance(resp["stats"], dict)
    if resp["message"] != "Statistics retrieved successfully":
        raise AssertionError


def test_manage_search_directories_invalid_action(fsdb_stub: FSDBStub) -> None:
    resp = fst.manage_search_directories("bogus", "/tmp/dir")
    if resp["success"] is not False:
        raise AssertionError
    if (
        resp["error"] != "Invalid action. Must be one of: ['add_allowed', 'remove_allowed', 'add_excluded', 'remove_excluded', 'get_settings']"
    ):
        raise AssertionError
    if resp["message"] != "Invalid action 'bogus' specified":
        raise AssertionError


def test_manage_search_directories_get_settings(fsdb_stub: FSDBStub) -> None:
    resp = fst.manage_search_directories("get_settings", "")
    if resp["success"] is not True:
        raise AssertionError
    if "settings" not in resp:
        raise AssertionError
    assert isinstance(resp["settings"], dict)
    s = resp["settings"]
    for key in (
        "allowed_directories",
        "excluded_directories",
        "total_allowed",
        "total_excluded",
    ):
        if key not in s:
            raise AssertionError
    if resp["message"] != "Directory settings retrieved successfully":
        raise AssertionError


def test_optimize_search_database_success(fsdb_stub: FSDBStub) -> None:
    resp = fst.optimize_search_database()
    if resp["success"] is not True:
        raise AssertionError
    if "stats" not in resp:
        raise AssertionError
    assert isinstance(resp["stats"], dict)
    if resp["message"] != "Database optimized successfully":
        raise AssertionError


def test_get_file_embeddings_error_missing_path(fsdb_stub: FSDBStub) -> None:
    resp = fst.get_file_embeddings("")
    if resp["success"] is not False:
        raise AssertionError
    if resp["error"] != "file_path is required":
        raise AssertionError
    if resp["message"] != "Failed to get embeddings: file_path is required":
        raise AssertionError


def test_get_file_embeddings_success(fsdb_stub: FSDBStub, tmp_path: Path) -> None:
    # Index a file so stub returns embeddings
    p = tmp_path / "emb.txt"
    p.write_text("x", encoding="utf-8")
    _ = fst.add_file_to_index(str(p), file_type="txt")

    def _fake_embeddings_by_file(file_path: str):
        if file_path in fsdb_stub._files:
            return [
                {"chunk_id": "c1", "embedding": [0.1, 0.2], "content": "alpha"},
                {"chunk_id": "c2", "embedding": [0.3, 0.4], "content": "beta"},
            ]
        return []

    # type: ignore[attr-defined]
    fsdb_stub.get_embeddings_by_file_func = _fake_embeddings_by_file

    resp = fst.get_file_embeddings(str(p))
    if resp["success"] is not True:
        raise AssertionError
    if resp["count"] != 2:
        raise AssertionError
    assert isinstance(resp["embeddings"], list)
    assert len(resp["embeddings"]) == 2
    if resp["message"] != "Found 2 embeddings for file":
        raise AssertionError
