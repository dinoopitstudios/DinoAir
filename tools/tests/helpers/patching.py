from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Iterable

    import pytest


def _safe_patch(monkeypatch: pytest.MonkeyPatch, target: str, value: Any) -> None:
    """
    Best-effort patch that no-ops if the target cannot be imported/resolved.

    Wraps monkeypatch.setattr(target, value, raising=False) to avoid raising when
    modules or attributes are absent during particular test runs.
    """
    try:
        # Use dotted-path patching; do not raise if target is missing
        monkeypatch.setattr(target, value, raising=False)  # type: ignore[arg-type]
    except (ImportError, AttributeError, ModuleNotFoundError):
        # Graceful no-op, preserving current tolerant behavior
        pass
    except Exception:
        # Maintain today's permissive behavior for any unexpected import/attr issues
        pass


def _patch_many(monkeypatch: pytest.MonkeyPatch, targets: Iterable[str], value: Any) -> None:
    for t in targets:
        _safe_patch(monkeypatch, t, value)


def patch_file_search_db(monkeypatch: pytest.MonkeyPatch, stub: Any) -> None:
    """
    Patch factory functions so file_search tool uses the provided stub.

    - tools.common.db.get_file_search_db
    - src.tools.file_search_tool.get_file_search_db (if module is present)
    - tools.file_search_tool.get_file_search_db (direct import path)
    - repo.tools.file_search_tool.get_file_search_db (preloaded alias)
    """

    def value(user_name="default_user"):
        return stub

    targets = (
        "tools.common.db.get_file_search_db",
        "src.tools.file_search_tool.get_file_search_db",
        "tools.file_search_tool.get_file_search_db",
        "repo.tools.file_search_tool.get_file_search_db",
    )
    _patch_many(monkeypatch, targets, value)


def patch_notes_db(monkeypatch: pytest.MonkeyPatch, stub: Any) -> None:
    """
    Patch factory functions so notes tool uses the provided stub.

    - tools.common.db.get_notes_db
    - src.tools.notes_tool.get_notes_db (if module is present)
    - tools.notes_tool.get_notes_db (direct import path)
    - repo.tools.notes_tool.get_notes_db (preloaded alias)
    """

    def value(user_name="default_user"):
        return stub

    targets = (
        "tools.common.db.get_notes_db",
        "src.tools.notes_tool.get_notes_db",
        "tools.notes_tool.get_notes_db",
        "repo.tools.notes_tool.get_notes_db",
    )
    _patch_many(monkeypatch, targets, value)


def patch_projects_db(monkeypatch: pytest.MonkeyPatch, stub: Any) -> None:
    """
    Patch factory functions so projects tool uses the provided stub.

    - tools.common.db.get_projects_db
    - src.tools.projects_tool.get_projects_db (if module is present)
    - tools.projects_tool.get_projects_db (direct import path)
    - repo.tools.projects_tool.get_projects_db (preloaded alias)
    """

    def value(user_name="default_user"):
        return stub

    targets = (
        "tools.common.db.get_projects_db",
        "src.tools.projects_tool.get_projects_db",
        "tools.projects_tool.get_projects_db",
        "repo.tools.projects_tool.get_projects_db",
    )
    _patch_many(monkeypatch, targets, value)
