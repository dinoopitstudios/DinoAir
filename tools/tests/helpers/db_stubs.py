from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any


class FSDBStub:
    """
    Lightweight File Search DB stub exposing only methods asserted by tests.
    Returns predictable structures/messages matching production expectations.
    """

    def __init__(self, _user_name: str = "default_user") -> None:
        self._files: dict[str, dict[str, Any]] = {}
        self._allowed_dirs: list[str] = []
        self._excluded_dirs: list[str] = []

    # Search
    def search_by_keywords(
        self,
        keywords: list[str],
        limit: int = 10,
        file_types: list[str] | None = None,
        file_paths: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        _ = (keywords, limit, file_types, file_paths)
        # Keep deterministic empty by default; specific tests may monkeypatch their own stub
        return []

    # File info
    def get_file_by_path(self, file_path: str) -> dict[str, Any] | None:
        # Return a present file by default to satisfy smoke/get_file_info flows
        if file_path in self._files:
            return self._files[file_path]
        return {
            "id": "file_stub_id",
            "file_path": file_path,
            "file_hash": "stub",
            "size": 0,
            "modified_date": "",
            "indexed_date": "",
            "file_type": "txt",
            "status": "active",
            "metadata": None,
        }

    # Index management
    def add_indexed_file(self, **kwargs: Any) -> dict[str, Any]:
        # Accept flexible kwargs; mirror simple, successful indexing behavior
        file_path = kwargs.get("file_path")
        file_hash = kwargs.get("file_hash", "stub")
        size = kwargs.get("size", 0)
        modified_date: datetime | str = kwargs.get("modified_date", "")
        file_type = kwargs.get("file_type", "txt")
        metadata = kwargs.get("metadata")
        if isinstance(modified_date, datetime):
            modified_date_s = modified_date.isoformat()
        else:
            modified_date_s = str(modified_date)

        if file_path:
            self._files[file_path] = {
                "id": "file_1",
                "path": file_path,
                "hash": file_hash,
                "size": size,
                "modified_date": modified_date_s,
                "type": file_type,
                "metadata": metadata or {},
            }

        return {
            "success": True,
            "file_id": "file_1",
            "message": "File indexed successfully",
        }

    def remove_file_from_index(self, file_path: str) -> dict[str, Any]:
        if file_path in self._files:
            del self._files[file_path]
            return {"success": True, "message": "File removed from index successfully"}
        return {"success": False, "error": "File not found in index"}

    # Backwards name compatibility
    def remove_indexed_file(self, file_path: str) -> dict[str, Any]:
        return self.remove_file_from_index(file_path)

    # Stats
    def get_indexed_files_stats(self) -> dict[str, Any]:
        return {
            "total_files": len(self._files),
            "total_chunks": 0,
            "total_embeddings": 0,
            "disk_usage_bytes": 0,
        }

    # Directory settings
    def get_directory_settings(self) -> dict[str, Any]:
        return {
            "success": True,
            "allowed_directories": list(self._allowed_dirs),
            "excluded_directories": list(self._excluded_dirs),
            "total_allowed": len(self._allowed_dirs),
            "total_excluded": len(self._excluded_dirs),
        }

    def add_allowed_directory(self, directory: str) -> dict[str, Any]:
        if directory not in self._allowed_dirs:
            self._allowed_dirs.append(directory)
        return {"success": True, "message": "Directory added to allowed list"}

    def remove_allowed_directory(self, directory: str) -> dict[str, Any]:
        if directory in self._allowed_dirs:
            self._allowed_dirs.remove(directory)
            return {"success": True, "message": "Directory removed from allowed list"}
        return {"success": False, "error": "Directory not in allowed list"}

    def add_excluded_directory(self, directory: str) -> dict[str, Any]:
        if directory not in self._excluded_dirs:
            self._excluded_dirs.append(directory)
        return {"success": True, "message": "Directory added to excluded list"}

    def remove_excluded_directory(self, directory: str) -> dict[str, Any]:
        if directory in self._excluded_dirs:
            self._excluded_dirs.remove(directory)
            return {"success": True, "message": "Directory removed from excluded list"}
        return {"success": False, "error": "Directory not in excluded list"}

    # Maintenance
    def optimize_database(self) -> dict[str, Any]:
        return {
            "success": True,
            "message": "Database optimized successfully",
            "table_stats": {},
        }

    # Embeddings
    def get_embeddings_by_file(self, file_path: str) -> list[dict[str, Any]]:
        # Check if a custom function override is provided
        if hasattr(self, "get_embeddings_by_file_func"):
            return self.get_embeddings_by_file_func(file_path)
        _ = file_path
        return []


class NotesDBStub:
    """
    Lightweight Notes DB stub exposing only methods asserted by tests.
    """

    def __init__(self, _user_name: str = "default_user") -> None:
        self._store: dict[str, Any] = {}
        self._tags: dict[str, int] = {"work": 1}

    # CRUD
    def create_note(self, note, content_html: str | None = None) -> dict[str, Any]:
        # Check if a custom override function is provided
        if hasattr(self, "_create_note_override"):
            return self._create_note_override(note, content_html)
        _ = content_html
        nid = getattr(note, "id", "note_test_id")
        self._store[nid] = note
        return {"success": True, "note_id": nid, "message": "Note created successfully"}

    def get_note(self, note_id: str):
        n = self._store.get(note_id)
        if n is not None:
            return n
        # Provide a default presence object for smoke flows
        return SimpleNamespace(
            id=note_id,
            title="Sample",
            content="Content",
            tags=[],
            project_id=None,
            created_at=None,
            updated_at=None,
        )

    def update_note(self, note_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        _ = note_id
        return {
            "success": True,
            "message": "Note updated successfully",
            "updated_fields": list(updates.keys()),
        }

    def delete_note(self, note_id: str, hard_delete: bool = False) -> dict[str, Any]:
        _ = (note_id, hard_delete)
        return {"success": True, "message": "Note deleted successfully"}

    # Queries
    def search_notes(self, query: str, filter_option: str, project_id: str | None = None):
        _ = (query, filter_option, project_id)
        n = SimpleNamespace(
            id="note_test_id",
            title="S",
            content="C",
            tags=[],
            project_id=None,
            created_at=None,
            updated_at=None,
        )
        return [n]

    def get_all_notes(self):
        n = SimpleNamespace(
            id="note_test_id",
            title="A",
            content="B",
            tags=[],
            project_id=None,
            created_at=None,
            updated_at=None,
        )
        return [n]

    def get_notes_by_tag(self, tag_name: str):
        _ = tag_name
        n = SimpleNamespace(
            id="note_test_id",
            title="T",
            content="Z" * 120,
            tags=[tag_name],
            project_id=None,
            created_at=None,
            updated_at=None,
        )
        return [n]

    def get_all_tags(self) -> dict[str, int]:
        return dict(self._tags)


class ProjectsDBStub:
    """
    Lightweight Projects DB stub exposing methods asserted by tests.
    """

    class _Stats:
        def __init__(self) -> None:
            self.project_id = "project_test_id"
            self.project_name = "Proj"
            self.total_notes = 0
            self.total_artifacts = 0
            self.total_calendar_events = 0
            self.child_project_count = 0
            self.completed_items = 0
            self.total_items = 0
            self.completion_percentage = 0.0
            self.days_since_last_activity = 0
            self.last_activity_date = None

    def __init__(self, _db_manager: Any | None = None) -> None:
        self._projects: dict[str, Any] = {}

    # Create
    def create_project(self, project) -> dict[str, Any]:
        pid = getattr(project, "id", "project_test_id")
        self._projects[pid] = project
        return {"success": True, "id": pid, "message": "Project created successfully"}

    # Get
    def get_project(self, project_id: str):
        if project_id in self._projects:
            return self._projects[project_id]
        # Return a predictable project if not previously created (for smoke/read flows)
        return SimpleNamespace(
            id=project_id,
            name="Demo",
            description="",
            status="active",
            color=None,
            icon=None,
            parent_project_id=None,
            tags=[],
            metadata={},
            created_at=None,
            updated_at=None,
            completed_at=None,
            archived_at=None,
        )

    # Update
    def update_project(self, project_id: str, updates: dict[str, Any]) -> bool:
        """
        Update attributes on an existing project for testing purposes.

        Behavior:
        - Returns False when 'updates' is empty (no-op).
        - Returns True when the project exists and updates are applied.
        - Returns True when the project does not exist; this stub behaves permissively to simplify tests.
        """
        if not updates:
            return False

        proj = self._projects.get(project_id)
        if not proj:
            # Behave permissively; tests assert True case primarily
            return True

        for k, v in updates.items():
            setattr(proj, k, v)
        return True

    # Delete
    def delete_project(self, project_id: str, cascade: bool = False) -> bool:
        _ = cascade
        if project_id in self._projects:
            del self._projects[project_id]
        return True

    # Lists
    def get_all_projects(self):
        p = SimpleNamespace(
            id="project_test_id_all",
            name="AllProj",
            description="",
            status="active",
            color=None,
            icon=None,
            parent_project_id=None,
            tags=[],
            metadata={},
            created_at=None,
            updated_at=None,
        )
        return [p]

    def search_projects(self, query: str):
        _ = query
        return self.get_all_projects()

    def get_projects_by_status(self, status: str):
        _ = status
        return self.get_all_projects()

    # Analytics
    def get_project_statistics(self, project_id: str):
        _ = project_id
        return self._Stats()

    def get_project_tree(self, project_id: str):
        return {"id": project_id, "name": "Root", "children": []}
