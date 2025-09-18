#!/usr/bin/env python3
"""
Simple index validation script to verify comprehensive index coverage
"""

import os
import sqlite3
import sys


def check_database_indexes(db_path: str) -> None:
    """Check if all expected indexes are present in the database"""

    expected_indexes = [
        # Single column indexes
        "idx_notes_is_deleted",
        "idx_notes_updated_at",
        "idx_notes_created_at",
        "idx_notes_project_id",
        # Compound indexes (order matters for query optimization)
        "idx_notes_is_deleted_updated_at",
        "idx_notes_is_deleted_project_id_updated_at",
        "idx_notes_is_deleted_title",
        "idx_notes_is_deleted_project_id_title",
        "idx_notes_project_id_updated_at",
        "idx_notes_title_updated_at",
        # Partial indexes for specific use cases
        "idx_notes_active_tags",
        "idx_notes_has_tags",
        "idx_notes_no_project",
    ]

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Get all indexes on note_list table
            cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='index' AND tbl_name='note_list'
                ORDER BY name
            """
            )

            existing_indexes = [row[0] for row in cursor.fetchall()]

            # Check for missing indexes
            missing_indexes = set(expected_indexes) - set(existing_indexes)
            if missing_indexes:
                for idx in sorted(missing_indexes):
                    pass

            # Check for unexpected indexes
            unexpected_indexes = set(existing_indexes) - set(expected_indexes)
            if unexpected_indexes:
                for idx in sorted(unexpected_indexes):
                    pass

            # Show all existing indexes
            for idx in sorted(existing_indexes):
                # Get index details
                cursor.execute(f"PRAGMA index_info('{idx}')")
                [row[2] for row in cursor.fetchall()]

                # Get index SQL
                cursor.execute(
                    """
                    SELECT sql FROM sqlite_master
                    WHERE type='index' AND name=?
                """,
                    (idx,),
                )
                sql_result = cursor.fetchone()
                sql = sql_result[0] if sql_result else "AUTO INDEX"

                # Show partial index conditions
                if "WHERE" in sql:
                    sql.split("WHERE", 1)[1].strip().rstrip(")")

            # Test a few key query patterns

            test_queries = [
                (
                    "Active notes by date",
                    "SELECT * FROM note_list WHERE is_deleted = 0 ORDER BY updated_at DESC LIMIT 10",
                ),
                (
                    "Project notes",
                    "SELECT * FROM note_list WHERE is_deleted = 0 AND project_id = 'test' ORDER BY updated_at DESC",
                ),
                (
                    "Title search",
                    "SELECT * FROM note_list WHERE is_deleted = 0 AND title LIKE '%test%'",
                ),
                (
                    "Tagged notes",
                    "SELECT * FROM note_list WHERE is_deleted = 0 AND tags IS NOT NULL AND tags != ''",
                ),
            ]

            for _description, query in test_queries:
                cursor.execute(f"EXPLAIN QUERY PLAN {query}")
                plan = cursor.fetchall()
                for step in plan:
                    detail = step[3] if len(step) > 3 else str(step)
                    if "USING INDEX" in detail:
                        pass
                    else:
                        pass

    except Exception:
        return False

    return True


def main():
    """Main validation function"""

    # Check for notes database
    base_dir = os.path.join(os.path.dirname(__file__), "user_data", "databases")
    notes_db = os.path.join(base_dir, "notes.db")

    if not os.path.exists(notes_db):
        return False

    success = check_database_indexes(notes_db)

    if success:
        pass
    else:
        pass

    return success


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
