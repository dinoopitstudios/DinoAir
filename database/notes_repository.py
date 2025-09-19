"""
NotesRepository - Pure database operations for notes management.
Handles all SQLite database interactions without business logic.
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from models.note import Note
from utils.logger import Logger

from .initialize_db import DatabaseManager


@dataclass
class QueryResult:
    """Standardized result for database operations"""

    success: bool
    data: Any = None
    error: str = ""
    affected_rows: int = 0


class NotesRepository:
    """
    Pure database repository for notes operations.
    No business logic, security, or validation - just database CRUD.
    """

    def __init__(self, user_name: str | None = None):
        self.logger = Logger()
        self.db_manager = DatabaseManager(user_name)
        self.table_name = "note_list"
        self._ensure_database_ready()

    def _ensure_database_ready(self) -> None:
        """Ensure database schema is up to date (migrations now handle column additions)"""
        # Database schema updates are now handled by the migration system
        # in DatabaseManager._run_notes_migrations()
        # This method is kept for backward compatibility but no longer performs schema changes
        self.logger.debug("Database schema managed by migration system")

    def _execute_query_safe(self, query: str, params: tuple[Any, ...] = ()) -> QueryResult:
        """Execute a query with proper connection management and return results"""
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                # Fetch results immediately before connection closes
                if query.strip().upper().startswith(("SELECT", "PRAGMA")):
                    if "COUNT(" in query.upper():
                        # For count queries, return single value
                        result = cursor.fetchone()
                        data = result[0] if result else 0
                    else:
                        # For other SELECT queries, return all rows
                        data = cursor.fetchall()
                else:
                    # For non-SELECT queries (shouldn't happen in query methods)
                    data = cursor.rowcount

                return QueryResult(success=True, data=data)
        except Exception as e:
            self.logger.error(f"Database query error: {str(e)}")
            return QueryResult(success=False, error=str(e))

    def _execute_write(self, query: str, params: tuple[Any, ...] = ()) -> QueryResult:
        """Execute a write operation with transaction handling"""
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return QueryResult(success=True, affected_rows=cursor.rowcount)
        except Exception as e:
            self.logger.error(f"Database write error: {str(e)}")
            return QueryResult(success=False, error=str(e))

    @staticmethod
    def _row_to_note(row: sqlite3.Row) -> Note:
        """Convert database row to Note object"""
        note = Note(
            id=row[0],
            title=row[1],
            content=row[2],
            tags=json.loads(row[4]) if row[4] else [],
            project_id=row[7],
        )
        # Preserve original timestamps
        note.created_at = row[5]
        note.updated_at = row[6]
        # Add content_html as custom attribute
        note.content_html = row[3]
        return note

    @staticmethod
    def _normalize_tags(tags: list[str]) -> list[str]:
        """
        Normalize tags for consistent storage and searching.

        Args:
            tags: List of tag strings

        Returns:
            List of normalized tags (lowercase, deduplicated, stripped)
        """
        if not tags:
            return []

        normalized_tags = []
        seen = set()

        for tag in tags:
            if isinstance(tag, str):
                tag_normalized = tag.lower().strip()
                if tag_normalized and tag_normalized not in seen:
                    normalized_tags.append(tag_normalized)
                    seen.add(tag_normalized)

        return normalized_tags

    def _has_json1_support(self) -> bool:
        """Check if SQLite installation supports JSON1 extension"""
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT json_valid('[]')")
                return True
        except sqlite3.OperationalError:
            return False

    def create_note(self, note: Note, content_html: str | None = None) -> QueryResult:
        """Insert a new note into the database"""
        # Normalize tags before storage
        normalized_tags = NotesRepository._normalize_tags(note.tags) if note.tags else []
        tags_json = json.dumps(normalized_tags)

        query = f"""
            INSERT INTO {self.table_name}
            (id, title, content, content_html, tags, created_at, updated_at, is_deleted, project_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            note.id,
            note.title,
            note.content,
            content_html,
            tags_json,
            note.created_at,
            note.updated_at,
            0,
            note.project_id,
        )

        result = self._execute_write(query, params)
        if result.success:
            self.logger.info(f"Created note with ID: {note.id}")
        return result

    def get_note_by_id(self, note_id: str) -> QueryResult:
        """Retrieve a single note by ID"""
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    SELECT id, title, content, content_html, tags, created_at, updated_at, project_id
                    FROM {self.table_name}
                    WHERE id = ? AND is_deleted = 0
                    """,
                    (note_id,),
                )

                row = cursor.fetchone()
                if row:
                    note = NotesRepository._row_to_note(row)
                    return QueryResult(success=True, data=note)
                return QueryResult(success=False, error="Note not found")

        except Exception as e:
            self.logger.error(f"Error retrieving note {note_id}: {str(e)}")
            return QueryResult(success=False, error=str(e))

    def get_all_notes(self) -> QueryResult:
        """Retrieve all non-deleted notes"""
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    SELECT id, title, content, content_html, tags, created_at, updated_at, project_id
                    FROM {self.table_name}
                    WHERE is_deleted = 0
                    ORDER BY updated_at DESC
                    """
                )

                notes = [NotesRepository._row_to_note(row) for row in cursor.fetchall()]
                self.logger.info(f"Retrieved {len(notes)} notes")
                return QueryResult(success=True, data=notes)

        except Exception as e:
            self.logger.error(f"Error retrieving all notes: {str(e)}")
            return QueryResult(success=False, error=str(e))

    def update_note(self, note_id: str, updates: dict[str, Any]) -> QueryResult:
        """Update a note with the provided field updates"""
        update_fields: list[str] = []
        params: list[Any] = []

        field_mappings = {
            "title": "title = ?",
            "content": "content = ?",
            "tags": "tags = ?",
            "content_html": "content_html = ?",
            "project_id": "project_id = ?",
        }

        for field, sql_template in field_mappings.items():
            if field in updates:
                update_fields.append(sql_template)
                if field == "tags":
                    # Normalize tags before storage
                    normalized_tags = (
                        NotesRepository._normalize_tags(updates[field]) if updates[field] else []
                    )
                    params.append(json.dumps(normalized_tags))
                else:
                    params.append(updates[field])

        if not update_fields:
            return QueryResult(success=False, error="No valid fields to update")

        # Always update the updated_at timestamp
        update_fields.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(note_id)

        query = f"""
            UPDATE {self.table_name}
            SET {", ".join(update_fields)}
            WHERE id = ? AND is_deleted = 0
        """

        result = self._execute_write(query, tuple(params))
        if result.success and result.affected_rows > 0:
            self.logger.info(f"Updated note: {note_id}")
        return result

    def soft_delete_note(self, note_id: str) -> QueryResult:
        """Soft delete a note"""
        query = f"""
            UPDATE {self.table_name}
            SET is_deleted = 1, updated_at = ?
            WHERE id = ? AND is_deleted = 0
        """
        params = (datetime.now().isoformat(), note_id)

        result = self._execute_write(query, params)
        if result.success and result.affected_rows > 0:
            self.logger.info(f"Soft deleted note: {note_id}")
        return result

    def hard_delete_note(self, note_id: str) -> QueryResult:
        """Permanently delete a note"""
        # Security: Use parameterized query with validated table name
        if self.table_name != "note_list":  # Validate expected table name
            return QueryResult(False, None, "Invalid table name")

        query = "DELETE FROM note_list WHERE id = ?"
        result = self._execute_write(query, (note_id,))
        if result.success:
            self.logger.info(f"Hard deleted note: {note_id}")
        return result

    def restore_note(self, note_id: str) -> QueryResult:
        """Restore a soft-deleted note"""
        query = f"""
            UPDATE {self.table_name}
            SET is_deleted = 0, updated_at = ?
            WHERE id = ? AND is_deleted = 1
        """
        params = (datetime.now().isoformat(), note_id)

        result = self._execute_write(query, params)
        if result.success and result.affected_rows > 0:
            self.logger.info(f"Restored note: {note_id}")
        return result

    def get_deleted_notes(self) -> QueryResult:
        """Get all soft-deleted notes"""
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    SELECT id, title, content, content_html, tags, created_at, updated_at, project_id
                    FROM {self.table_name}
                    WHERE is_deleted = 1
                    ORDER BY updated_at DESC
                    """
                )

                notes = [NotesRepository._row_to_note(row) for row in cursor.fetchall()]
                self.logger.info(f"Retrieved {len(notes)} deleted notes")
                return QueryResult(success=True, data=notes)

        except Exception as e:
            self.logger.error(f"Error retrieving deleted notes: {str(e)}")
            return QueryResult(success=False, error=str(e))

    def search_notes(
        self, query: str, filter_option: str = "All", project_id: str | None = None
    ) -> QueryResult:
        """Search notes with various filter options"""
        try:
            # Build WHERE clause based on filter option
            if filter_option == "Title Only":
                where_clause = "title LIKE ? ESCAPE '\\'"
                params = (f"%{query}%",)
            elif filter_option == "Content Only":
                where_clause = "content LIKE ? ESCAPE '\\'"
                params = (f"%{query}%",)
            elif filter_option == "Tags Only":
                where_clause = "tags LIKE ? ESCAPE '\\'"
                params = (f"%{query}%",)
            else:  # "All"
                where_clause = """
                    (title LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\' OR tags LIKE ? ESCAPE '\\')
                """
                params = (f"%{query}%", f"%{query}%", f"%{query}%")

            # Add project filtering if specified
            project_clause = ""
            if project_id is not None:
                project_clause = "AND project_id = ?"
                params = params + (project_id,)

            full_query = f"""
                SELECT id, title, content, content_html, tags, created_at, updated_at, project_id
                FROM {self.table_name}
                WHERE is_deleted = 0 AND {where_clause} {project_clause}
                ORDER BY updated_at DESC
            """

            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(full_query, params)
                notes = [NotesRepository._row_to_note(row) for row in cursor.fetchall()]

            self.logger.info(f"Search found {len(notes)} notes for query: '{query}'")
            return QueryResult(success=True, data=notes)

        except Exception as e:
            self.logger.error(f"Error searching notes: {str(e)}")
            return QueryResult(success=False, error=str(e))

    def get_notes_by_tag(self, tag: str) -> QueryResult:
        """Get all notes with a specific tag using efficient JSON1 queries"""
        try:
            # Normalize the search tag for consistent matching
            normalized_tag = tag.lower().strip()
            if not normalized_tag:
                return QueryResult(success=True, data=[])

            if self._has_json1_support():
                # Use efficient JSON1 query with EXISTS and json_each
                with self.db_manager.get_notes_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        f"""
                        SELECT id, title, content, content_html, tags, created_at, updated_at, project_id
                        FROM {self.table_name}
                        WHERE is_deleted = 0
                        AND EXISTS (
                            SELECT 1 FROM json_each(tags)
                            WHERE value = ?
                        )
                        ORDER BY updated_at DESC
                        """,
                        (normalized_tag,),
                    )

                    notes = [NotesRepository._row_to_note(row) for row in cursor.fetchall()]
            else:
                # Fallback to LIKE query with post-filtering for systems without JSON1
                tag_pattern = f'%"{normalized_tag}"%'
                with self.db_manager.get_notes_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        f"""
                        SELECT id, title, content, content_html, tags, created_at, updated_at, project_id
                        FROM {self.table_name}
                        WHERE is_deleted = 0 AND tags LIKE ? ESCAPE '\\'
                        ORDER BY updated_at DESC
                        """,
                        (tag_pattern,),
                    )

                    notes = []
                    for row in cursor.fetchall():
                        note = NotesRepository._row_to_note(row)
                        # Double-check that the normalized tag is actually in the list
                        if normalized_tag in (note.tags or []):
                            notes.append(note)

            self.logger.info(
                f"Found {len(notes)} notes with tag: '{tag}' (normalized: '{normalized_tag}')"
            )
            return QueryResult(success=True, data=notes)

        except Exception as e:
            self.logger.error(f"Error getting notes by tag '{tag}': {str(e)}")
            return QueryResult(success=False, error=str(e))

    def get_all_tags(self) -> QueryResult:
        """Get all unique tags with their usage counts"""
        try:
            # Security: Use parameterized query with validated table name
            if self.table_name != "note_list":  # Validate expected table name
                return QueryResult(False, None, "Invalid table name")

            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT tags FROM note_list WHERE is_deleted = 0")

                tag_counts = {}
                for row in cursor.fetchall():
                    if row[0]:
                        tags = json.loads(row[0])
                        for tag in tags:
                            tag_lower = tag.lower()
                            if tag_lower in tag_counts:
                                tag_counts[tag_lower]["count"] += 1
                            else:
                                tag_counts[tag_lower] = {"tag": tag, "count": 1}

            # Convert to simple dict preserving original case
            result = {data["tag"]: data["count"] for data in tag_counts.values()}
            self.logger.info(f"Retrieved {len(result)} unique tags")
            return QueryResult(success=True, data=result)

        except Exception as e:
            self.logger.error(f"Error retrieving all tags: {str(e)}")
            return QueryResult(success=False, error=str(e))

    def update_tag_in_notes(self, old_tag: str, new_tag: str) -> QueryResult:
        """Rename a tag across all notes"""
        try:
            # Normalize tags for consistent searching
            old_tag_normalized = old_tag.lower().strip()
            new_tag_normalized = new_tag.lower().strip()

            if not old_tag_normalized or not new_tag_normalized:
                return QueryResult(False, None, "Tag names cannot be empty")

            # Security: Use validated table name
            if self.table_name != "note_list":
                return QueryResult(False, None, "Invalid table name")

            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, tags FROM note_list WHERE is_deleted = 0")

                affected_notes = 0
                for row in cursor.fetchall():
                    note_id = row[0]
                    tags = json.loads(row[1]) if row[1] else []

                    # Search for normalized tag and replace with normalized new tag
                    updated_tags = []
                    tag_found = False
                    for tag in tags:
                        if isinstance(tag, str) and tag.lower() == old_tag_normalized:
                            updated_tags.append(new_tag_normalized)
                            tag_found = True
                        else:
                            updated_tags.append(tag)

                    if tag_found:
                        # Update the note
                        # Security: Use validated table name
                        if self.table_name != "note_list":
                            continue

                        update_result = self._execute_write(
                            "UPDATE note_list SET tags = ?, updated_at = ? WHERE id = ?",
                            (json.dumps(updated_tags), datetime.now().isoformat(), note_id),
                        )
                        if update_result.success:
                            affected_notes += 1

            self.logger.info(f"Renamed tag '{old_tag}' to '{new_tag}' in {affected_notes} notes")
            return QueryResult(success=True, data={"affected_notes": affected_notes})

        except Exception as e:
            self.logger.error(f"Error renaming tag: {str(e)}")
            return QueryResult(success=False, error=str(e))

    def remove_tag_from_notes(self, tag_to_remove: str) -> QueryResult:
        """Remove a tag from all notes"""
        try:
            # Normalize tag for consistent searching
            tag_normalized = tag_to_remove.lower().strip()
            if not tag_normalized:
                return QueryResult(False, None, "Tag name cannot be empty")

            # Security: Use validated table name
            if self.table_name != "note_list":
                return QueryResult(False, None, "Invalid table name")

            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, tags FROM note_list WHERE is_deleted = 0")

                affected_notes = 0
                for row in cursor.fetchall():
                    note_id = row[0]
                    tags = json.loads(row[1]) if row[1] else []

                    # Remove normalized tag
                    original_count = len(tags)
                    updated_tags = [
                        tag
                        for tag in tags
                        if isinstance(tag, str) and tag.lower() != tag_normalized
                    ]

                    if len(updated_tags) < original_count:
                        # Update the note
                        # Security: Use validated table name
                        if self.table_name != "note_list":
                            continue

                        update_result = self._execute_write(
                            "UPDATE note_list SET tags = ?, updated_at = ? WHERE id = ?",
                            (json.dumps(updated_tags), datetime.now().isoformat(), note_id),
                        )
                        if update_result.success:
                            affected_notes += 1

            self.logger.info(f"Deleted tag '{tag_to_remove}' from {affected_notes} notes")
            return QueryResult(success=True, data={"affected_notes": affected_notes})

        except Exception as e:
            self.logger.error(f"Error deleting tag: {str(e)}")
            return QueryResult(success=False, error=str(e))

    def get_notes_by_project(self, project_id: str) -> QueryResult:
        """Get all notes for a specific project"""
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    SELECT id, title, content, content_html, tags, created_at, updated_at, project_id
                    FROM {self.table_name}
                    WHERE is_deleted = 0 AND project_id = ?
                    ORDER BY updated_at DESC
                    """,
                    (project_id,),
                )

                notes = [NotesRepository._row_to_note(row) for row in cursor.fetchall()]
                self.logger.info(f"Retrieved {len(notes)} notes for project: {project_id}")
                return QueryResult(success=True, data=notes)

        except Exception as e:
            self.logger.error(f"Error retrieving notes for project {project_id}: {str(e)}")
            return QueryResult(success=False, error=str(e))

    def get_notes_without_project(self) -> QueryResult:
        """Get all notes not associated with any project"""
        try:
            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    SELECT id, title, content, content_html, tags, created_at, updated_at, project_id
                    FROM {self.table_name}
                    WHERE is_deleted = 0 AND (project_id IS NULL OR project_id = '')
                    ORDER BY updated_at DESC
                    """
                )

                notes = [NotesRepository._row_to_note(row) for row in cursor.fetchall()]
                self.logger.info(f"Retrieved {len(notes)} notes without project association")
                return QueryResult(success=True, data=notes)

        except Exception as e:
            self.logger.error(f"Error retrieving notes without project: {str(e)}")
            return QueryResult(success=False, error=str(e))

    def bulk_update_project(self, note_ids: list[str], project_id: str | None) -> QueryResult:
        """Assign multiple notes to a project or remove project association"""
        try:
            if not note_ids:
                return QueryResult(success=False, error="No note IDs provided")

            placeholders = ",".join(["?"] * len(note_ids))
            params: list[Any] = [project_id, datetime.now().isoformat()] + note_ids

            query = f"""
                UPDATE {self.table_name}
                SET project_id = ?, updated_at = ?
                WHERE id IN ({placeholders}) AND is_deleted = 0
            """

            result = self._execute_write(query, tuple(params))
            if result.success:
                action = "assigned to" if project_id else "removed from"
                self.logger.info(f"{result.affected_rows} notes {action} project {project_id}")
            return result

        except Exception as e:
            self.logger.error(f"Error bulk updating project: {str(e)}")
            return QueryResult(success=False, error=str(e))

    def get_project_notes_count(self, project_id: str) -> QueryResult:
        """Get the count of notes associated with a project"""
        try:
            # Security: Use validated table name
            if self.table_name != "note_list":
                return QueryResult(False, None, "Invalid table name")

            with self.db_manager.get_notes_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM note_list WHERE is_deleted = 0 AND project_id = ?",
                    (project_id,),
                )

                count = cursor.fetchone()[0]
                return QueryResult(success=True, data=count)

        except Exception as e:
            self.logger.error(f"Error counting notes for project {project_id}: {str(e)}")
            return QueryResult(success=False, error=str(e))
