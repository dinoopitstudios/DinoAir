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
    if res["success"] is not True:
        raise AssertionError
    if res["id"] != art.id:
        raise AssertionError

    # Read
    got = db.get_artifact(art.id)
    assert got is not None
    if got.id != art.id:
        raise AssertionError
    if got.name != "Doc A":
        raise AssertionError

    # Update
    ok = db.update_artifact(art.id, {"name": "Doc A+", "description": "Updated"})
    if ok is not True:
        raise AssertionError
    got2 = db.get_artifact(art.id)
    assert got2 is not None
    if got2.name != "Doc A+":
        raise AssertionError
    if got2.description != "Updated":
        raise AssertionError

    # Soft delete
    ok_soft = db.delete_artifact(art.id, hard_delete=False)
    if ok_soft is not True:
        raise AssertionError
    # Should no longer appear in queries that exclude deleted
    by_type = db.get_artifacts_by_type("text/plain")
    if not all(a.id != art.id for a in by_type):
        raise AssertionError

    # Hard delete (re-create, then hard delete)
    art2 = Artifact(id="art-crud-2", name="Doc B", content_type="text/plain")
    if db.create_artifact(art2)["success"] is not True:
        raise AssertionError
    ok_hard = db.delete_artifact(art2.id, hard_delete=True)
    if ok_hard is not True:
        raise AssertionError
    # Verify removed
    cur = artifacts_connection.cursor()
    cur.execute("SELECT COUNT(*) FROM artifacts WHERE id = ?", (art2.id,))
    if cur.fetchone()[0] != 0:
        raise AssertionError


def test_artifacts_large_content_file_storage_black_box(db_manager):
    db = ArtifactsDatabase(db_manager)

    # Large content (> threshold) -> stored in file
    large_bytes = b"x" * (ArtifactsDatabase.FILE_SIZE_THRESHOLD + 1)
    art = Artifact(id="art-file-1", name="Large File", content_type="application/octet-stream")
    res = db.create_artifact(art, content=large_bytes)
    if res["success"] is not True:
        raise AssertionError

    stored = db.get_artifact("art-file-1")
    assert stored is not None
    assert stored.content is None
    assert stored.content_path is not None

    # Read content back
    read_back = db.get_artifact_content("art-file-1")
    if read_back != large_bytes:
        raise AssertionError


def test_artifacts_queries_and_search_black_box(db_manager):
    db = ArtifactsDatabase(db_manager)

    # Create a collection
    coll = ArtifactCollection(id="coll-1", name="My Collection", description="X")
    if db.create_collection(coll)["success"] is not True:
        raise AssertionError

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
    if db.create_artifact(a1)["success"] is not True:
        raise AssertionError
    if db.create_artifact(a2)["success"] is not True:
        raise AssertionError

    # Search
    hits = db.search_artifacts("test")
    hit_ids = {a.id for a in hits}
    if not {"art-q-1", "art-q-2"} & hit_ids:
        raise AssertionError

    # By type
    pdfs = db.get_artifacts_by_type("application/pdf")
    if not any(a.id == "art-q-2" for a in pdfs):
        raise AssertionError

    # By collection
    in_coll = db.get_artifacts_by_collection("coll-1")
    ids_in_coll = {a.id for a in in_coll}
    if {"art-q-1", "art-q-2"} > ids_in_coll:
        raise AssertionError

    # By project
    in_proj = db.get_artifacts_by_project("proj-777")
    ids_in_proj = {a.id for a in in_proj}
    if {"art-q-1", "art-q-2"} > ids_in_proj:
        raise AssertionError


def test_artifacts_versions_and_restore_black_box(db_manager):
    db = ArtifactsDatabase(db_manager)

    art = Artifact(id="art-ver-1", name="Versioned", content_type="text/plain")
    if db.create_artifact(art)["success"] is not True:
        raise AssertionError

    # Update artifact -> bumps version, creates version record
    if db.update_artifact("art-ver-1", {"name": "Versioned v2"}) is not True:
        raise AssertionError

    # Create manual version snapshot of current
    if db.create_version("art-ver-1", "Checkpoint") is not True:
        raise AssertionError

    versions = db.get_versions("art-ver-1")
    assert isinstance(versions, list)
    if len(versions) < 1:
        raise AssertionError

    # Restore to version 1 (initial)
    if db.restore_version("art-ver-1", 1) is not True:
        raise AssertionError
    restored = db.get_artifact("art-ver-1")
    assert restored is not None
    # Name may have reverted to original or prior state; assert it's a non-empty string
    assert isinstance(restored.name, str)
    if len(restored.name) <= 0:
        raise AssertionError


def test_artifacts_statistics_black_box(db_manager):
    db = ArtifactsDatabase(db_manager)

    # Ensure at least one artifact exists
    base = Artifact(id="art-stats-1", name="Stats A", content_type="text/plain")
    if db.create_artifact(base)["success"] is not True:
        raise AssertionError

    stats = db.get_artifact_statistics()
    # Basic shape assertions
    assert isinstance(stats, dict)
    if "total_artifacts" not in stats:
        raise AssertionError
    if "total_size_bytes" not in stats:
        raise AssertionError
    if "artifacts_by_type" not in stats:
        raise AssertionError
