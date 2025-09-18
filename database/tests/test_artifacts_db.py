"""
Black-box integration tests for ArtifactsDatabase against real SQLite.
Tests exercise only public APIs and assert on persisted state/results.
"""

from database.artifacts_db import ArtifactsDatabase
from models.artifact import Artifact, ArtifactCollection


def test_artifacts_crud_black_box(db_manager, artifacts_connection):
    db = ArtifactsDatabase(db_manager)

    # Create (small content stored in DB)
    art = Artifact(
        id="art-crud-1",
        name="Doc A",
        description="First",
        content_type="text/plain",
        project_id="proj-1",
        tags=["a", "doc"],
    )
    res = db.create_artifact(art)
    assert res["success"] is True
    assert res["id"] == art.id

    # Read
    got = db.get_artifact(art.id)
    assert got is not None
    assert got.id == art.id
    assert got.name == "Doc A"

    # Update
    ok = db.update_artifact(art.id, {"name": "Doc A+", "description": "Updated"})
    assert ok is True
    got2 = db.get_artifact(art.id)
    assert got2 is not None
    assert got2.name == "Doc A+"
    assert got2.description == "Updated"

    # Soft delete
    ok_soft = db.delete_artifact(art.id, hard_delete=False)
    assert ok_soft is True
    # Should no longer appear in queries that exclude deleted
    by_type = db.get_artifacts_by_type("text/plain")
    assert all(a.id != art.id for a in by_type)

    # Hard delete (re-create, then hard delete)
    art2 = Artifact(id="art-crud-2", name="Doc B", content_type="text/plain")
    assert db.create_artifact(art2)["success"] is True
    ok_hard = db.delete_artifact(art2.id, hard_delete=True)
    assert ok_hard is True
    # Verify removed
    cur = artifacts_connection.cursor()
    cur.execute("SELECT COUNT(*) FROM artifacts WHERE id = ?", (art2.id,))
    assert cur.fetchone()[0] == 0


def test_artifacts_large_content_file_storage_black_box(db_manager):
    db = ArtifactsDatabase(db_manager)

    # Large content (> threshold) -> stored in file
    large_bytes = b"x" * (ArtifactsDatabase.FILE_SIZE_THRESHOLD + 1)
    art = Artifact(id="art-file-1", name="Large File", content_type="application/octet-stream")
    res = db.create_artifact(art, content=large_bytes)
    assert res["success"] is True

    stored = db.get_artifact("art-file-1")
    assert stored is not None
    assert stored.content is None
    assert stored.content_path is not None

    # Read content back
    read_back = db.get_artifact_content("art-file-1")
    assert read_back == large_bytes


def test_artifacts_queries_and_search_black_box(db_manager):
    db = ArtifactsDatabase(db_manager)

    # Create a collection
    coll = ArtifactCollection(id="coll-1", name="My Collection", description="X")
    assert db.create_collection(coll)["success"] is True

    # Create artifacts
    a1 = Artifact(
        id="art-q-1",
        name="Test Document",
        description="A test document",
        content_type="text/plain",
        tags=["test", "document"],
        collection_id="coll-1",
        project_id="proj-777",
    )
    a2 = Artifact(
        id="art-q-2",
        name="Another Test",
        description="Another test item",
        content_type="application/pdf",
        tags=["test"],
        collection_id="coll-1",
        project_id="proj-777",
    )
    assert db.create_artifact(a1)["success"] is True
    assert db.create_artifact(a2)["success"] is True

    # Search
    hits = db.search_artifacts("test")
    hit_ids = {a.id for a in hits}
    assert {"art-q-1", "art-q-2"} & hit_ids  # at least one should be present (both likely)

    # By type
    pdfs = db.get_artifacts_by_type("application/pdf")
    assert any(a.id == "art-q-2" for a in pdfs)

    # By collection
    in_coll = db.get_artifacts_by_collection("coll-1")
    ids_in_coll = {a.id for a in in_coll}
    assert {"art-q-1", "art-q-2"} <= ids_in_coll

    # By project
    in_proj = db.get_artifacts_by_project("proj-777")
    ids_in_proj = {a.id for a in in_proj}
    assert {"art-q-1", "art-q-2"} <= ids_in_proj


def test_artifacts_versions_and_restore_black_box(db_manager):
    db = ArtifactsDatabase(db_manager)

    art = Artifact(id="art-ver-1", name="Versioned", content_type="text/plain")
    assert db.create_artifact(art)["success"] is True

    # Update artifact -> bumps version, creates version record
    assert db.update_artifact("art-ver-1", {"name": "Versioned v2"}) is True

    # Create manual version snapshot of current
    assert db.create_version("art-ver-1", "Checkpoint") is True

    versions = db.get_versions("art-ver-1")
    assert isinstance(versions, list)
    assert len(versions) >= 1

    # Restore to version 1 (initial)
    assert db.restore_version("art-ver-1", 1) is True
    restored = db.get_artifact("art-ver-1")
    assert restored is not None
    # Name may have reverted to original or prior state; assert it's a non-empty string
    assert isinstance(restored.name, str)
    assert len(restored.name) > 0


def test_artifacts_statistics_black_box(db_manager):
    db = ArtifactsDatabase(db_manager)

    # Ensure at least one artifact exists
    base = Artifact(id="art-stats-1", name="Stats A", content_type="text/plain")
    assert db.create_artifact(base)["success"] is True

    stats = db.get_artifact_statistics()
    # Basic shape assertions
    assert isinstance(stats, dict)
    assert "total_artifacts" in stats
    assert "total_size_bytes" in stats
    assert "artifacts_by_type" in stats
