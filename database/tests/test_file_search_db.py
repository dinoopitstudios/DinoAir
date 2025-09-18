"""
Black-box integration tests for FileSearchDB against real SQLite.
Tests exercise only public APIs and assert persisted state/results.
"""

from datetime import datetime
from uuid import uuid4

from database.file_search_db import FileSearchDB


def _new_db():
    # Unique user per test to ensure isolation
    return FileSearchDB(user_name=f"fs_{uuid4().hex}")


def test_create_tables_and_index_file_black_box():
    db = _new_db()

    # Add a file to the index
    fp = "/test/a.txt"
    res = db.add_indexed_file(
        file_path=fp,
        file_hash="h1",
        size=10,
        modified_date=datetime.now(),
        file_type="text/plain",
        metadata={"k": "v"},
    )
    assert isinstance(res, dict)
    assert res.get("success") is True
    assert "file_id" in res
    res["file_id"]

    # Retrieve by path
    got = db.get_file_by_path(fp)
    assert got is not None
    assert got["file_path"] == fp
    assert got["file_hash"] == "h1"
    assert got["file_type"] == "text/plain"


def test_chunk_and_embedding_roundtrip_black_box():
    db = _new_db()

    # Index file
    fp = "/idx/one.txt"
    res = db.add_indexed_file(
        file_path=fp,
        file_hash="hash-one",
        size=123,
        modified_date=datetime.now(),
        file_type="text/plain",
    )
    assert res["success"] is True
    file_id = res["file_id"]

    # Add chunk
    cres = db.add_chunk(
        file_id=file_id,
        chunk_index=0,
        content="some test content",
        start_pos=0,
        end_pos=18,
        metadata={"part": 0},
    )
    assert cres["success"] is True
    chunk_id = cres["chunk_id"]

    # Add embedding
    eres = db.add_embedding(
        chunk_id=chunk_id, embedding_vector=[0.1, 0.2, 0.3], model_name="model-x"
    )
    assert eres["success"] is True

    # Query embeddings for file
    by_file = db.get_embeddings_by_file(fp)
    assert isinstance(by_file, list)
    assert len(by_file) >= 1
    ids = {row["chunk_id"] for row in by_file}
    assert chunk_id in ids

    # Query all embeddings (should include our record)
    all_emb = db.get_all_embeddings()
    assert any(row["chunk_id"] == chunk_id for row in all_emb)


def test_keyword_search_black_box():
    db = _new_db()

    # Seed file and chunk with keyword
    fp = "/kw/file.txt"
    res = db.add_indexed_file(
        file_path=fp,
        file_hash="kw1",
        size=11,
        modified_date=datetime.now(),
        file_type="text/plain",
    )
    assert res["success"]
    file_id = res["file_id"]

    assert db.add_chunk(
        file_id=file_id,
        chunk_index=0,
        content="This contains keyword FooBar and more.",
        start_pos=0,
        end_pos=38,
    )["success"]

    # Search keyword (case-insensitive)
    results = db.search_by_keywords(["foobar"])
    assert isinstance(results, list)
    assert any(r["file_path"] == fp for r in results)


def test_batch_and_clear_embeddings_black_box():
    db = _new_db()

    # Seed file and two chunks
    fp = "/batch/file.txt"
    res = db.add_indexed_file(
        file_path=fp,
        file_hash="bh1",
        size=50,
        modified_date=datetime.now(),
        file_type="text/plain",
    )
    assert res["success"]
    file_id = res["file_id"]

    assert db.add_chunk(file_id=file_id, chunk_index=0, content="c0", start_pos=0, end_pos=2)[
        "success"
    ]
    assert db.add_chunk(file_id=file_id, chunk_index=1, content="c1", start_pos=3, end_pos=5)[
        "success"
    ]

    emb_payload = [
        {"chunk_id": f"{file_id}_chunk_0", "embedding_vector": [0.1, 0.2], "model_name": "m"},
        {"chunk_id": f"{file_id}_chunk_1", "embedding_vector": [0.3, 0.4], "model_name": "m"},
    ]
    bres = db.batch_add_embeddings(emb_payload)
    assert bres["success"] is True
    assert bres["embeddings_added"] >= 1

    # Clear and verify
    cres = db.clear_embeddings_for_file(fp)
    assert cres["success"] is True
    after = db.get_embeddings_by_file(fp)
    assert after == []


def test_settings_management_black_box():
    db = _new_db()

    # Update setting and read back
    set_res = db.update_search_settings("allowed_directories", ["/a", "/b"])
    assert set_res["success"] is True

    one = db.get_search_settings("allowed_directories")
    assert one["success"] is True
    assert one["setting_name"] == "allowed_directories"
    assert one["setting_value"] == ["/a", "/b"]

    # Get both lists via helper
    dirs = db.get_directory_settings()
    assert dirs["success"] is True
    assert "allowed_directories" in dirs
    assert isinstance(dirs["allowed_directories"], list)


def test_stats_and_remove_file_black_box():
    db = _new_db()

    fp = "/rm/file.txt"
    res = db.add_indexed_file(
        file_path=fp,
        file_hash="rmh",
        size=5,
        modified_date=datetime.now(),
        file_type="text/plain",
    )
    assert res["success"]

    stats = db.get_indexed_files_stats()
    assert isinstance(stats, dict)
    assert "total_files" in stats

    # Remove file and confirm gone
    rres = db.remove_file_from_index(fp)
    assert rres["success"] is True
    assert db.get_file_by_path(fp) is None


def test_optimize_database_black_box():
    db = _new_db()
    res = db.optimize_database()
    assert res["success"] is True
    assert "table_stats" in res
    assert isinstance(res["table_stats"], dict)
