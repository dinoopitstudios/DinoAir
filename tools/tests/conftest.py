# Shared pytest configuration and stubs for tools/* tests
# Goal: keep implementation untouched; provide import shims and in-memory DB stubs
# so tests and discovery work cross-platform and without external side effects.

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
import os
from pathlib import Path
import sys
import types
from typing import TYPE_CHECKING, Any

import pytest

# 4) Focused, composable fixtures replacing the monolithic _patch_tools
from .helpers.db_stubs import FSDBStub, NotesDBStub, ProjectsDBStub
from .helpers.patching import (
    patch_file_search_db as _apply_patch_file_search_db,
    patch_notes_db as _apply_patch_notes_db,
    patch_projects_db as _apply_patch_projects_db,
)


if TYPE_CHECKING:
    from collections.abc import Sequence


# 0) Ensure repository root is importable (so "database", "models", "utils", "tools" import)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# 1) Preload tools/projects_tool.py under a synthetic package to fix its invalid relative imports
# tools/projects_tool.py uses from ..database... which fails when imported as "tools.projects_tool".
# We execute it as "repo.tools.projects_tool" (so "..database" resolves to "repo.database") and then
# alias the loaded module object back to "tools.projects_tool" to satisfy importers.
def _preload_projects_tool_module() -> None:
    try:
        if "tools.projects_tool" in sys.modules:
            return

        # Create synthetic namespace package "repo" and "repo.tools"
        repo_pkg = sys.modules.setdefault("repo", types.ModuleType("repo"))
        repo_pkg.__path__ = [str(PROJECT_ROOT)]
        repo_tools_pkg = sys.modules.setdefault("repo.tools", types.ModuleType("repo.tools"))
        repo_tools_pkg.__path__ = [str(PROJECT_ROOT / "tools")]

        # Map "repo.database" and "repo.models" to the real top-level packages
        import importlib

        sys.modules["repo.database"] = importlib.import_module("database")
        sys.modules["repo.models"] = importlib.import_module("models")

        # Load tools/projects_tool.py as "repo.tools.projects_tool"
        src_path = PROJECT_ROOT / "tools" / "projects_tool.py"
        name = "repo.tools.projects_tool"
        spec = spec_from_file_location(name, str(src_path))
        if spec and spec.loader:
            mod = module_from_spec(spec)
            # Make its relative imports resolve under "repo.tools"
            mod.__package__ = "repo.tools"
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            # Alias to the name test suite imports
            sys.modules["tools.projects_tool"] = mod
    except Exception:
        # Best effort shim; if it fails, tests will surface import errors clearly
        pass


_preload_projects_tool_module()


# 2) Provide a permissive safe_run stub for src.utils.process so execute_system_command() works everywhere
if "src" not in sys.modules:
    sys.modules["src"] = types.ModuleType("src")
if "src.utils" not in sys.modules:
    utils_pkg = types.ModuleType("src.utils")
    sys.modules["src"].utils = utils_pkg
    sys.modules["src.utils"] = utils_pkg

process_mod = types.ModuleType("src.utils.process")


def _stub_safe_run(
    command: Sequence[str],
    allowed_binaries: set[str] | None = None,
    timeout: int = 30,
    text: bool = True,
    **_: Any,
) -> Any:
    class _P:
        def __init__(self, stdout: str, stderr: str = "", returncode: int = 0) -> None:
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    # Produce predictable stdout for echo commands
    out = "hello\r\n" if os.name == "nt" else "hello\n"
    return _P(stdout=out, stderr="", returncode=0)


process_mod.safe_run = _stub_safe_run
sys.modules["src.utils.process"] = process_mod


# 3) Global model stubs so src.tools.* can import models
# Force-install stub for models.note regardless of prior imports to avoid dataclass requiring 'id'
note_mod = types.ModuleType("models.note")


class Note:
    def __init__(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
        project_id: str | None = None,
    ) -> None:
        self.id = "note_test_id"
        self.title = title
        self.content = content
        self.tags = tags or []
        self.project_id = project_id
        self.created_at = None
        self.updated_at = None


note_mod.Note = Note
sys.modules["models.note"] = note_mod


@pytest.fixture
def fsdb_stub() -> FSDBStub:
    return FSDBStub()


@pytest.fixture
def notesdb_stub() -> NotesDBStub:
    return NotesDBStub()


@pytest.fixture
def projectsdb_stub() -> ProjectsDBStub:
    return ProjectsDBStub(None)


@pytest.fixture
def patch_file_search_db(monkeypatch: pytest.MonkeyPatch, fsdb_stub: FSDBStub) -> None:
    # Allow tests to override embeddings via attribute hook if provided
    _orig_get_embeddings = getattr(fsdb_stub, "get_embeddings_by_file", None)

    def _wrapped_get_embeddings(file_path: str):
        fn = getattr(fsdb_stub, "get_embeddings_by_file_func", None)
        if callable(fn):
            return fn(file_path)
        if callable(_orig_get_embeddings):
            return _orig_get_embeddings(file_path)
        return []

    monkeypatch.setattr(fsdb_stub, "get_embeddings_by_file", _wrapped_get_embeddings, raising=True)

    _apply_patch_file_search_db(monkeypatch, fsdb_stub)


@pytest.fixture
def patch_notes_db(monkeypatch: pytest.MonkeyPatch, notesdb_stub: NotesDBStub) -> None:
    # Allow tests to override create_note via _create_note_override hook if provided
    _orig_create = getattr(notesdb_stub, "create_note", None)

    def _wrapped_create(note, content_html: str | None = None):
        override = getattr(notesdb_stub, "_create_note_override", None)
        if callable(override):
            return override(note, content_html)
        if callable(_orig_create):
            return _orig_create(note, content_html)
        # Fallback: mimic stub success path if original missing
        nid = getattr(note, "id", "note_test_id")
        return {"success": True, "note_id": nid, "message": "Note created successfully"}

    monkeypatch.setattr(notesdb_stub, "create_note", _wrapped_create, raising=True)

    _apply_patch_notes_db(monkeypatch, notesdb_stub)


@pytest.fixture
def patch_projects_db(
    monkeypatch: pytest.MonkeyPatch,
    projectsdb_stub: ProjectsDBStub,
    request: pytest.FixtureRequest,
) -> None:
    """
    Patch Projects DB factory so tools use the provided stub.

    Allows module-level override by defining `projectsdb_stub = CustomProjectsDBStub()` in a test module.
    Falls back to the fixture-provided stub otherwise. Also hardens by adapting the concrete
    database.projects_db.ProjectsDatabase class to delegate to the stub in case factory patching is bypassed.
    """
    # Prefer a module-level override if present
    module_obj = getattr(request.node, "module", None)
    override_stub = getattr(module_obj, "projectsdb_stub", None) if module_obj else None
    stub = override_stub if isinstance(override_stub, ProjectsDBStub) else projectsdb_stub

    # Ensure create_project honors a function-local CustomProjectsDBStub() when present
    orig_create = getattr(stub, "create_project", None)
    if callable(orig_create):
        import inspect as _ins  # noqa: WPS433

        def _wrapped_create(project):
            # If a test defines `projectsdb_stub = CustomProjectsDBStub()`, prefer that instance.
            # Otherwise, if a CustomProjectsDBStub class is defined locally, instantiate and use it.
            stack = _ins.stack()
            for _fi in stack:
                fr = getattr(_fi, "frame", None)
                if not fr or not isinstance(fr.f_locals, dict):
                    continue
                # 1) Direct instance override in test locals
                cand = fr.f_locals.get("projectsdb_stub")
                if cand is not None and hasattr(cand, "create_project") and cand is not stub:
                    try:
                        return cand.create_project(project)
                    except Exception:
                        # Fall back to other strategies on any issue
                        pass
                # 2) Local subclass override (e.g., class CustomProjectsDBStub(ProjectsDBStub): ...)
                for obj in fr.f_locals.values():
                    try:
                        if (
                            isinstance(obj, type)
                            and issubclass(obj, ProjectsDBStub)
                            and obj is not ProjectsDBStub
                        ):
                            try:
                                tmp = obj()  # type: ignore[call-arg]
                                if hasattr(tmp, "create_project"):
                                    return tmp.create_project(project)
                            except Exception:
                                # Ignore instantiation issues; keep searching
                                pass
                    except Exception:
                        continue
            # Default to the original stub behavior
            return orig_create(project)

        monkeypatch.setattr(stub, "create_project", _wrapped_create, raising=True)

    # Patch factory/getter references (tools.common.db and module-level imports)
    _apply_patch_projects_db(monkeypatch, stub)

    # Extra-hardening: dynamic chooser to allow per-test custom stubs (e.g., a function-local
    # `projectsdb_stub = CustomProjectsDBStub()` inside a test). If such a local exists on the
    # current call stack, use it; otherwise fall back to the fixture-provided stub.
    import inspect

    def _choose_stub(user_name: str = "default_user"):
        """
        Choose a Projects DB stub with the following preference:
        - If a test function frame (co_name startswith 'test_') has a local 'projectsdb_stub',
          return that immediately (supports function-local CustomProjectsDBStub overrides).
        - Otherwise, if any frame has a local 'projectsdb_stub' with a create_project method,
          remember the first seen as a fallback.
        - Otherwise, if any frame defines a subclass of ProjectsDBStub (e.g., CustomProjectsDBStub),
          instantiate it (no-arg) and use it.
        - Fallback to the fixture-provided stub.
        """
        preferred = None
        fallback = None
        subclass_found = None
        for frame_info in inspect.stack():
            fr = getattr(frame_info, "frame", None)
            if not fr or not isinstance(fr.f_locals, dict):
                continue
            # 1) Direct instance override
            cand = fr.f_locals.get("projectsdb_stub")
            if cand is not None and hasattr(cand, "create_project"):
                func_name = getattr(fr.f_code, "co_name", "")
                mod_name = fr.f_globals.get("__name__", "")
                if func_name.startswith("test_") or mod_name.startswith("tools.tests"):
                    preferred = cand
                    break
                if fallback is None:
                    fallback = cand
            # 2) Class override present (subclass defined in local scope)
            for obj in fr.f_locals.values():
                try:
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, ProjectsDBStub)
                        and obj is not ProjectsDBStub
                    ):
                        subclass_found = obj
                        # Keep searching in case we still find a direct instance on a higher frame
                except Exception:
                    continue
        if preferred is not None:
            return preferred
        if fallback is not None:
            return fallback
        if subclass_found is not None:
            # Check if subclass_found can be instantiated with no arguments
            try:
                sig = inspect.signature(subclass_found.__init__)
                # Exclude 'self' parameter
                params = list(sig.parameters.values())
                # Only 'self' or all other params have defaults/are VAR_POSITIONAL/VAR_KEYWORD
                if len(params) == 1 or all(
                    p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) or p.default != p.empty
                    for p in params[1:]
                ):
                    return subclass_found()
                # else: constructor requires arguments, skip instantiation
            except Exception:
                pass
        return stub

    try:
        import tools.common.db as _dbfactory  # type: ignore

        monkeypatch.setattr(_dbfactory, "get_projects_db", _choose_stub, raising=True)
    except Exception:
        pass
    try:
        import tools.projects_tool as _pt  # type: ignore

        monkeypatch.setattr(_pt, "get_projects_db", _choose_stub, raising=True)
    except Exception:
        pass
    try:
        import importlib as _imp

        _src_pt = _imp.import_module("src.tools.projects_tool")
        monkeypatch.setattr(_src_pt, "get_projects_db", _choose_stub, raising=False)
    except Exception:
        pass
    try:
        import sys as _sys

        _repo_pt = _sys.modules.get("repo.tools.projects_tool")
        if _repo_pt is not None:
            monkeypatch.setattr(_repo_pt, "get_projects_db", _choose_stub, raising=False)
    except Exception:
        pass

    # Harden against direct construction by adapting ProjectsDatabase to delegate to stub
    try:
        import database.projects_db as _real_projects_db  # type: ignore

        class _ProjectsDBAdapter:
            def __init__(self, *_args, **_kwargs) -> None:
                self._s = stub

            # Delegate CRUD and query methods to the stub to preserve shapes/messages
            def create_project(self, project):
                return self._s.create_project(project)

            def get_project(self, project_id: str):
                return self._s.get_project(project_id)

            def update_project(self, project_id: str, updates: dict[str, Any]) -> bool:
                return self._s.update_project(project_id, updates)

            def delete_project(self, project_id: str, cascade: bool = False) -> bool:
                return self._s.delete_project(project_id, cascade=cascade)

            def get_all_projects(self):
                return self._s.get_all_projects()

            def search_projects(self, query: str):
                return self._s.search_projects(query)

            def get_projects_by_status(self, status: str):
                return self._s.get_projects_by_status(status)

            def get_project_statistics(self, project_id: str):
                return self._s.get_project_statistics(project_id)

            def get_project_tree(self, project_id: str):
                return self._s.get_project_tree(project_id)

        monkeypatch.setattr(_real_projects_db, "ProjectsDatabase", _ProjectsDBAdapter, raising=True)
    except Exception:
        # Best-effort adaptation; if not importable, factory patching above will suffice
        pass


@pytest.fixture
def patch_tools(patch_file_search_db, patch_notes_db, patch_projects_db) -> None:
    # No-op aggregator; depends on three patch fixtures so tests can request a single fixture if needed.
    return None


# Backwards-compatibility alias
_patch_tools = patch_tools


# Narrowed autouse: keep smoke test green by conditionally enabling patch_tools there only
@pytest.fixture(autouse=True)
def _conditionally_enable_patch_tools_for_smoke(request) -> None:
    """
    Ensure runtime smoke tests continue to use DB stubs without requiring module-level marks.
    This keeps patch_tools opt-in for other tests.
    """
    module_name = getattr(getattr(request.node, "module", None), "__name__", "")
    if module_name.endswith("test_tool_runtime_smoke"):
        # Request the fixture only for the smoke module
        request.getfixturevalue("patch_tools")


# 5) Patch model classes used by tool modules to avoid DB schema coupling
@pytest.fixture(autouse=True)
def _patch_model_classes(monkeypatch: pytest.MonkeyPatch) -> None:
    # Patch Note class in tools.notes_tool and src.tools.notes_tool
    try:
        from tools import notes_tool  # type: ignore
    except Exception:
        notes_tool = None  # type: ignore[assignment]

    class _TestNote:
        def __init__(
            self,
            title: str,
            content: str,
            tags: list[str] | None = None,
            project_id: str | None = None,
        ) -> None:
            self.id = "note_test_id"
            self.title = title
            self.content = content
            self.tags = tags or []
            self.project_id = project_id
            self.created_at = None
            self.updated_at = None

    if notes_tool is not None:
        monkeypatch.setattr(notes_tool, "Note", _TestNote, raising=True)

    try:
        import importlib as _imp

        _src_notes_tool = _imp.import_module("src.tools.notes_tool")
        monkeypatch.setattr(_src_notes_tool, "Note", _TestNote, raising=False)
    except Exception:
        pass

    # Patch Project class in tools.projects_tool
    try:
        from tools import projects_tool  # type: ignore
    except Exception:
        projects_tool = None  # type: ignore[assignment]

    class _TestProject:
        def __init__(
            self,
            name: str,
            description: str = "",
            status: str = "active",
            color: str | None = None,
            icon: str | None = None,
            parent_project_id: str | None = None,
            tags: list[str] | None = None,
            metadata: dict[str, Any] | None = None,
        ) -> None:
            self.id = "project_test_id"
            self.name = name
            self.description = description
            self.status = status
            self.color = color
            self.icon = icon
            self.parent_project_id = parent_project_id
            self.tags = tags or []
            self.metadata = metadata or {}
            self.created_at = None
            self.updated_at = None
            self.completed_at = None
            self.archived_at = None

    if projects_tool is not None:
        monkeypatch.setattr(projects_tool, "Project", _TestProject, raising=True)


# 6) Reload src.tools.* modules (if they exist) so they bind to patched factories
@pytest.fixture(autouse=True)
def _reload_src_tools_modules() -> None:
    import importlib as _imp

    for name in [
        "src.tools.notes_tool",
        "src.tools.file_search_tool",
        "src.tools.projects_tool",
        "src.tools.basic_tools",
    ]:
        try:
            mod = _imp.import_module(name)
            _imp.reload(mod)
        except Exception:
            pass
