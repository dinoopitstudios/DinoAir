"""
Schema index coverage tests.

Purpose:
- Assert presence of critical indexes defined in SCHEMA_DDLS to cover common filters.
- These are black-box checks against real SQLite databases initialized by DatabaseManager.
- Tests are intentionally resilient: they verify expected indexes exist without enforcing uniqueness or compound specifics beyond current schema.

Notes:
- DatabaseManager.initialize_all_databases() is invoked by the session-scoped db_manager fixture in conftest.py.
- Resource cleanup is handled by the autouse cleanup fixture calling DatabaseManager.clean_memory_database().
"""

import sqlite3

import pytest

from database.initialize_db import DatabaseManager


def _index_names_for_table(conn: sqlite3.Connection, table: str) -> set[str]:
    """
    Return the set of index names for a given table using PRAGMA index_list.
    """
    cur = conn.cursor()
    rows = cur.execute(f"PRAGMA index_list('{table}')").fetchall()
    # row format: (seq, name, unique, origin, partial)
    return {row[1] for row in rows} if rows else set()


@pytest.mark.integration
def test_notes_indexes_present(db_manager: DatabaseManager):
    # notes.db schema table: note_list
    conn = db_manager.get_notes_connection()
    idx = _index_names_for_table(conn, "note_list")

    # Expected indexes from SCHEMA_DDLS["notes"] - comprehensive coverage
    expected = {
        # Single-column indexes
        "idx_notes_title",
        "idx_notes_tags",
        "idx_notes_created",
        "idx_notes_updated",
        "idx_notes_project",
        "idx_notes_is_deleted",
        # Compound indexes for common query patterns
        "idx_notes_active_updated",  # is_deleted + updated_at DESC
        "idx_notes_active_title",  # is_deleted + title
        "idx_notes_active_tags",  # is_deleted + tags (partial)
        "idx_notes_project_active",  # is_deleted + project_id + updated_at DESC
        "idx_notes_has_tags",  # is_deleted WHERE tags not null/empty (partial)
        "idx_notes_project_title",  # is_deleted + project_id + title
    }

    missing = expected - idx
    if missing:
        raise AssertionError(f"Missing note_list indexes: {sorted(missing)}")


@pytest.mark.integration
def test_notes_index_coverage_query_patterns(db_manager: DatabaseManager):
    """Test that indexes cover common query patterns efficiently"""
    conn = db_manager.get_notes_connection()
    cursor = conn.cursor()

    # Test compound index usage with EXPLAIN QUERY PLAN
    test_queries = [
        # Most common: get active notes ordered by updated_at
        (
            "SELECT * FROM note_list WHERE is_deleted = 0 ORDER BY updated_at DESC",
            "idx_notes_active_updated",
        ),
        # Search by title in active notes
        (
            "SELECT * FROM note_list WHERE is_deleted = 0 AND title LIKE 'test%'",
            "idx_notes_active_title",
        ),
        # Get notes by project ordered by date
        (
            "SELECT * FROM note_list WHERE is_deleted = 0 AND project_id = 'proj1' ORDER BY updated_at DESC",
            "idx_notes_project_active",
        ),
        # Search within project
        (
            "SELECT * FROM note_list WHERE is_deleted = 0 AND project_id = 'proj1' AND title LIKE 'test%'",
            "idx_notes_project_title",
        ),
    ]

    for query, expected_index in test_queries:
        cursor.execute(f"EXPLAIN QUERY PLAN {query}")
        plan = cursor.fetchall()
        plan_text = " ".join([str(row) for row in plan])

        # Check if the expected index is mentioned in the query plan
        if expected_index not in plan_text:
            raise AssertionError(
                f"Query '{query[:50]}...' should use index {expected_index}, but plan was: {plan_text}"
            )


@pytest.mark.integration
def test_projects_indexes_present(db_manager: DatabaseManager):
    # projects.db schema table: projects
    conn = db_manager.get_projects_connection()
    idx = _index_names_for_table(conn, "projects")

    expected = {
        "idx_projects_name",
        "idx_projects_status",
        "idx_projects_parent",
        "idx_projects_created",
        "idx_projects_tags",
    }

    missing = expected - idx
    if missing:
        raise AssertionError(f"Missing projects indexes: {sorted(missing)}")


@pytest.mark.integration
def test_artifacts_indexes_present(db_manager: DatabaseManager):
    # artifacts.db schema tables: artifacts, artifact_versions, artifact_collections, artifact_permissions
    conn = db_manager.get_artifacts_connection()

    artifacts_idx = _index_names_for_table(conn, "artifacts")
    expected_artifacts = {
        "idx_artifacts_name",
        "idx_artifacts_type",
        "idx_artifacts_status",
        "idx_artifacts_collection",
        "idx_artifacts_project",
        "idx_artifacts_created",
        "idx_artifacts_tags",
    }
    missing_artifacts = expected_artifacts - artifacts_idx
    if missing_artifacts:
        raise AssertionError(f"Missing artifacts indexes: {sorted(missing_artifacts)}")

    versions_idx = _index_names_for_table(conn, "artifact_versions")
    expected_versions = {
        "idx_versions_artifact",
        "idx_versions_number",
    }
    missing_versions = expected_versions - versions_idx
    if missing_versions:
        raise AssertionError(f"Missing artifact_versions indexes: {sorted(missing_versions)}")

    collections_idx = _index_names_for_table(conn, "artifact_collections")
    expected_collections = {
        "idx_collections_name",
        "idx_collections_parent",
    }
    missing_collections = expected_collections - collections_idx
    if missing_collections:
        raise AssertionError(
            f"Missing artifact_collections indexes: {sorted(missing_collections)}"
        )

    permissions_idx = _index_names_for_table(conn, "artifact_permissions")
    expected_permissions = {
        "idx_permissions_artifact",
        "idx_permissions_user",
    }
    missing_permissions = expected_permissions - permissions_idx
    if missing_permissions:
        raise AssertionError(
            f"Missing artifact_permissions indexes: {sorted(missing_permissions)}"
        )


@pytest.mark.integration
def test_file_search_indexes_present(db_manager: DatabaseManager):
    # file_search.db schema tables: indexed_files, file_chunks, file_embeddings, search_settings
    conn = db_manager.get_file_search_connection()

    files_idx = _index_names_for_table(conn, "indexed_files")
    expected_files = {
        "idx_indexed_files_path",
        "idx_indexed_files_status",
        "idx_indexed_files_type",
    }
    missing_files = expected_files - files_idx
    if missing_files:
        raise AssertionError(f"Missing indexed_files indexes: {sorted(missing_files)}")

    chunks_idx = _index_names_for_table(conn, "file_chunks")
    expected_chunks = {
        "idx_file_chunks_file_id",
        "idx_file_chunks_content",
    }
    missing_chunks = expected_chunks - chunks_idx
    if missing_chunks:
        raise AssertionError(f"Missing file_chunks indexes: {sorted(missing_chunks)}")

    embeddings_idx = _index_names_for_table(conn, "file_embeddings")
    expected_embeddings = {
        "idx_file_embeddings_chunk_id",
    }
    missing_embeddings = expected_embeddings - embeddings_idx
    if missing_embeddings:
        raise AssertionError(f"Missing file_embeddings indexes: {sorted(missing_embeddings)}")

    settings_idx = _index_names_for_table(conn, "search_settings")
    expected_settings = {
        "idx_search_settings_name",
    }
    missing_settings = expected_settings - settings_idx
    if missing_settings:
        raise AssertionError(f"Missing search_settings indexes: {sorted(missing_settings)}")
