import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
from types import SimpleNamespace
import unittest


TOOLS_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = TOOLS_ROOT.parent


def _install_stubs():
    """Install lightweight stub modules for external deps used by tools.* modules."""
    # Ensure parent of 'src' is on sys.path for custom module loading
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    # Stub: src.utils.process.safe_run
    src_mod = sys.modules.setdefault("src", types.ModuleType("src"))
    src_mod.__path__ = []  # mark as package
    utils_mod = sys.modules.setdefault("src.utils", types.ModuleType("src.utils"))
    process_mod = sys.modules.setdefault("src.utils.process", types.ModuleType("src.utils.process"))

    def safe_run(_args, allowed_binaries=None, timeout=30, text=True):
        """Stubbed safe_run that always succeeds (used by runtime smoke tests)."""
        _ = (allowed_binaries, timeout, text)
        return SimpleNamespace(stdout="OK", stderr="", returncode=0)

    process_mod.safe_run = safe_run
    src_mod.utils = utils_mod
    utils_mod.process = process_mod

    sys.modules["src"] = src_mod
    sys.modules["src.utils"] = utils_mod
    sys.modules["src.utils.process"] = process_mod

    # Create 'src.tools' package namespace to host our loaded modules
    tools_pkg = sys.modules.setdefault("src.tools", types.ModuleType("src.tools"))
    tools_pkg.__path__ = [str(TOOLS_ROOT)]
    src_mod.tools = tools_pkg

    # models.note and models.project under src.models
    _models_mod = sys.modules.setdefault("src.models", types.ModuleType("src.models"))

    note_mod = types.ModuleType("models.note")

    class Note:
        def __init__(self, title: str, content: str, tags=None, project_id=None):
            self.id = "note_1"
            self.title = title
            self.content = content
            self.tags = tags or []
            self.project_id = project_id
            self.created_at = "2025-01-01T00:00:00"
            self.updated_at = "2025-01-01T00:00:00"

    note_mod.Note = Note
    sys.modules.setdefault("src.models.note", note_mod)

    project_mod = types.ModuleType("models.project")

    class Project:
        def __init__(
            self,
            name: str,
            description: str = "",
            status: str = "active",
            color=None,
            icon=None,
            parent_project_id=None,
            tags=None,
            metadata=None,
        ):
            self.id = "project_1"
            self.name = name
            self.description = description
            self.status = status
            self.color = color
            self.icon = icon
            self.parent_project_id = parent_project_id
            self.tags = tags or []
            self.metadata = metadata or {}
            self.created_at = "2025-01-01T00:00:00"
            self.updated_at = "2025-01-01T00:00:00"
            self.completed_at = None
            self.archived_at = None

    project_mod.Project = Project
    sys.modules.setdefault("src.models.project", project_mod)

    # database under src.database
    _database_mod = sys.modules.setdefault("src.database", types.ModuleType("src.database"))
    notes_db_mod = types.ModuleType("src.database.notes_db")

    class NotesDatabase:
        def __init__(self, _user_name: str = "default_user"):
            self._store = {"note_1": Note("Sample", "Content")}

        def create_note(self, note: Note, content_html=None):
            _ = content_html
            self._store[note.id] = note
            return {"success": True, "note_id": note.id, "message": "Note created"}

        def get_note(self, note_id: str):
            return self._store.get(note_id)

        def update_note(self, note_id: str, updates: dict):
            note = self._store.get(note_id)
            if not note:
                return {"success": False, "error": "Not found"}
            for k, v in updates.items():
                setattr(note, k, v)
            return {
                "success": True,
                "message": "Note updated",
                "updated_fields": list(updates.keys()),
            }

        def delete_note(self, note_id: str, hard_delete: bool = False):
            _ = hard_delete
            self._store.pop(note_id, None)
            return {"success": True, "message": "Note deleted"}

        def search_notes(self, query: str, filter_option: str = "All", project_id=None):
            _ = (query, filter_option, project_id)
            return list(self._store.values())

        def get_all_notes(self):
            return list(self._store.values())

        def get_notes_by_tag(self, tag_name: str):
            _ = tag_name
            return []

        def get_all_tags(self):
            return {"work": 1}

    notes_db_mod.NotesDatabase = NotesDatabase
    sys.modules.setdefault("src.database.notes_db", notes_db_mod)

    # database.initialize_db
    initialize_db_mod = types.ModuleType("src.database.initialize_db")

    class DatabaseManager:
        def __init__(self, _user_name: str = "default_user"):
            """Stub manager: no behavior required for smoke tests."""
            # Intentionally empty for runtime smoke tests

    initialize_db_mod.DatabaseManager = DatabaseManager
    sys.modules.setdefault("src.database.initialize_db", initialize_db_mod)

    # database.projects_db
    projects_db_mod = types.ModuleType("src.database.projects_db")

    class Stats:
        def __init__(self):
            self.project_id = "project_1"
            self.project_name = "Demo"
            self.total_notes = 1
            self.total_artifacts = 0
            self.total_calendar_events = 0
            self.child_project_count = 0
            self.completed_items = 0
            self.total_items = 0
            self.completion_percentage = 0.0
            self.days_since_last_activity = 0
            self.last_activity_date = None

    class ProjectsDatabase:
        def __init__(self, _db_manager: DatabaseManager):
            self._store = {"project_1": Project("Demo")}

        def create_project(self, project: Project):
            self._store[project.id] = project
            return {"success": True, "id": project.id, "message": "Project created"}

        def get_project(self, project_id: str):
            return self._store.get(project_id)

        def update_project(self, _project_id: str, _updates: dict):
            return True

        def delete_project(self, project_id: str, cascade: bool = False):
            _ = cascade
            self._store.pop(project_id, None)
            return True

        def get_all_projects(self):
            return list(self._store.values())

        def search_projects(self, _query: str):
            return list(self._store.values())

        def get_projects_by_status(self, _status: str):
            return list(self._store.values())

        def get_project_statistics(self, _project_id: str):
            return Stats()

        def get_project_tree(self, project_id: str):
            return {"id": project_id, "name": "Demo", "children": []}

    projects_db_mod.ProjectsDatabase = ProjectsDatabase
    sys.modules.setdefault("src.database.projects_db", projects_db_mod)

    # database.file_search_db
    fs_db_mod = types.ModuleType("src.database.file_search_db")

    class FileSearchDB:
        def __init__(self, _user_name: str = "default_user"):
            """Stub DB: no state required for smoke tests."""
            # Intentionally empty for runtime smoke tests

        def search_by_keywords(self, keywords, limit=10, file_types=None, file_paths=None):
            _ = (keywords, limit, file_types, file_paths)
            return []

        def get_file_by_path(self, file_path: str):
            return {"path": file_path, "size": 0, "type": "txt"}

        def add_indexed_file(self, **_kwargs):
            return {"success": True, "file_id": "file_1", "message": "Indexed"}

        def remove_file_from_index(self, _file_path: str):
            return {"success": True, "message": "Removed"}

        def get_indexed_files_stats(self):
            return {"total_files": 1, "total_chunks": 0}

        def get_directory_settings(self):
            return {
                "success": True,
                "allowed_directories": [],
                "excluded_directories": [],
                "total_allowed": 0,
                "total_excluded": 0,
            }

        def add_allowed_directory(self, _directory: str):
            return {"success": True, "message": "Added"}

        def remove_allowed_directory(self, _directory: str):
            return {"success": True, "message": "Removed"}

        def add_excluded_directory(self, _directory: str):
            return {"success": True, "message": "Added"}

        def remove_excluded_directory(self, _directory: str):
            return {"success": True, "message": "Removed"}

        def optimize_database(self):
            return {"success": True, "message": "Optimized", "table_stats": {}}

        def get_embeddings_by_file(self, _file_path: str):
            return []

    fs_db_mod.FileSearchDB = FileSearchDB
    sys.modules.setdefault("src.database.file_search_db", fs_db_mod)


def _import_under_src_tools(module_name: str, file_path: Path):
    """Import a module from file as if it were under 'src.tools.*' to satisfy relative imports."""
    full_name = f"src.tools.{module_name}"
    spec = importlib.util.spec_from_file_location(full_name, str(file_path))
    if not spec:
        raise AssertionError
    if not spec.loader:
        raise AssertionError
    module = importlib.util.module_from_spec(spec)
    # Ensure parent packages exist
    if "src" not in sys.modules:
        sys.modules["src"] = types.ModuleType("src")
        sys.modules["src"].__path__ = []
    if "src.tools" not in sys.modules:
        sys.modules["src.tools"] = types.ModuleType("src.tools")
        sys.modules["src.tools"].__path__ = [str(TOOLS_ROOT)]
    sys.modules[full_name] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


class TestToolRuntimeSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _install_stubs()
        # Load tools.basic_tools as src.tools.basic_tools so relative imports work
        basic_tools_mod = _import_under_src_tools("basic_tools", TOOLS_ROOT / "basic_tools.py")
        cls.AVAILABLE_TOOLS = basic_tools_mod.AVAILABLE_TOOLS

    def test_smoke_call_each_tool(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            # Prepare a small file for read_text_file and add_file_to_index
            txt_path = tdir / "sample.txt"
            txt_path.write_text("hello", encoding="utf-8")

            # Minimal invocations per tool
            calls = {
                # Core utilities
                "add_two_numbers": lambda f: f(1, 2),
                "get_current_time": lambda f: f(),
                "list_directory_contents": lambda f: f(str(tdir)),
                "read_text_file": lambda f: f(str(txt_path)),
                "execute_system_command": lambda f: f("echo hello"),
                "create_json_data": lambda f: f({"x": 1}, str(tdir / "out.json")),
                # Notes
                "create_note": lambda f: f("title", "content"),
                "read_note": lambda f: f("note_1"),
                "update_note": lambda f: f("note_1", content="updated"),
                "delete_note": lambda f: f("note_1"),
                "search_notes": lambda f: f("query", "All"),
                "list_all_notes": lambda f: f(),
                "get_notes_by_tag": lambda f: f("work"),
                "get_all_tags": lambda f: f(),
                # File Search
                "search_files_by_keywords": lambda f: f(["hello"], limit=1),
                "get_file_info": lambda f: f(str(txt_path)),
                "add_file_to_index": lambda f: f(str(txt_path)),
                "remove_file_from_index": lambda f: f(str(txt_path)),
                "get_search_statistics": lambda f: f(),
                "manage_search_directories": lambda f: f("get_settings", ""),
                "optimize_search_database": lambda f: f(),
                "get_file_embeddings": lambda f: f(str(txt_path)),
                # Projects
                "create_project": lambda f: f("Demo"),
                "get_project": lambda f: f("project_1"),
                "update_project": lambda f: f("project_1", status="active"),
                "delete_project": lambda f: f("project_1"),
                "list_all_projects": lambda f: f(),
                "search_projects": lambda f: f("demo"),
                "get_projects_by_status": lambda f: f("active"),
                "get_project_statistics": lambda f: f("project_1"),
                "get_project_tree": lambda f: f("project_1"),
            }

            # Ensure all expected tools are present
            missing = [name for name in calls if name not in self.AVAILABLE_TOOLS]
            if missing:
                raise AssertionError(f"Tools missing from AVAILABLE_TOOLS: {missing}")

            # Execute each tool and assert success
            failures = {}
            for name, func in calls.items():
                tool_fn = self.AVAILABLE_TOOLS.get(name)
                try:
                    result = func(tool_fn)
                    ok = isinstance(result, dict) and result.get("success", False) is True
                    if not ok:
                        failures[name] = result
                except Exception as e:  # noqa: BLE001  # nosec B110 - broad on purpose for smoke test aggregation
                    failures[name] = f"Exception: {e}"

            if failures:
                raise AssertionError(f"Smoke failures: {failures}")

            # Extended negative-path smoke checks: verify graceful failures on bad inputs
            bad_calls = {
                # Core utilities (error cases)
                "list_directory_contents__missing": lambda f: f(str(tdir / "does_not_exist")),
                "list_directory_contents__file": lambda f: f(str(txt_path)),
                "read_text_file__missing": lambda f: f(str(tdir / "nope.txt")),
                "execute_system_command__empty": lambda f: f(""),
                "execute_system_command__bad_syntax": lambda f: f('echo "unclosed'),
                "create_json_data__non_serializable": lambda f: f({"x": {1}}),
                # Notes (error cases)
                "create_note__missing_title": lambda f: f("", "content"),
                "create_note__missing_content": lambda f: f("title", ""),
                "read_note__missing": lambda f: f(""),
                "update_note__no_fields": lambda f: f("note_1"),
                "delete_note__missing": lambda f: f(""),
                "search_notes__missing_query": lambda f: f(""),
                "get_notes_by_tag__missing": lambda f: f(""),
                # File Search (error cases compatible with stubs)
                "search_files_by_keywords__empty": lambda f: f([]),
                "get_file_info__empty": lambda f: f(""),
                "add_file_to_index__missing_file": lambda f: f(str(tdir / "nope.txt")),
                "remove_file_from_index__empty": lambda f: f(""),
                "manage_search_directories__invalid_action": lambda f: f("invalid", ""),
                "manage_search_directories__missing_dir": lambda f: f("add_allowed", ""),
                "get_file_embeddings__empty": lambda f: f(""),
                # Projects (error cases)
                "create_project__missing_name": lambda f: f(""),
                "get_project__missing": lambda f: f(""),
                "update_project__no_fields": lambda f: f("project_1"),
                "delete_project__missing": lambda f: f(""),
                "search_projects__missing_query": lambda f: f(""),
                "get_projects_by_status__missing": lambda f: f(""),
                "get_project_statistics__missing": lambda f: f(""),
                "get_project_tree__missing": lambda f: f(""),
            }

            failures_bad = {}
            for case_name, func in bad_calls.items():
                tool_name = case_name.split("__")[0]
                tool_fn = self.AVAILABLE_TOOLS.get(tool_name)
                try:
                    result = func(tool_fn)
                    is_failure = isinstance(result, dict) and result.get("success") is False
                    has_error = isinstance(result, dict) and (
                        "error" in result or "message" in result
                    )
                    if not (is_failure and has_error):
                        failures_bad[case_name] = result
                except Exception as e:  # noqa: BLE001,BLE001  # nosec B110
                    # Even on exceptions, we consider this a test failure: functions should catch and return error structure
                    failures_bad[case_name] = f"Exception: {e}"

            if failures_bad:
                raise AssertionError(f"Negative-path smoke failures: {failures_bad}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
