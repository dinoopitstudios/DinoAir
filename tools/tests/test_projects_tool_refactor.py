from __future__ import annotations

from typing import Any

import pytest
from tools.tests.helpers.db_stubs import ProjectsDBStub


pytestmark = pytest.mark.usefixtures("patch_tools")

try:
    import src.tools.projects_tool as pt
except Exception:
    import tools.projects_tool as pt


def test_create_project_validation_error(projectsdb_stub: ProjectsDBStub) -> None:
    resp = pt.create_project("")
    assert resp["success"] is False
    assert resp["error"] == "Project name is required"
    assert resp["message"] == "Failed to create project: name is required"


def test_create_project_success() -> None:
    # Custom stub to override create_project behavior
    class CustomProjectsDBStub(ProjectsDBStub):
        def create_project(self, project):
            self._projects[project.id] = project
            return {
                "success": True,
                "id": "project_created_id",
                "message": "Project created successfully",
            }

    CustomProjectsDBStub()

    resp = pt.create_project("Website Redesign", description="Redesign")
    assert resp["success"] is True
    assert resp["project_id"] == "project_created_id"
    assert resp["message"] == "Project created successfully"
    pd = resp["project_data"]
    # Exact keys per implementation
    for key in (
        "id",
        "name",
        "description",
        "status",
        "color",
        "icon",
        "parent_project_id",
        "tags",
        "metadata",
        "created_at",
        "updated_at",
    ):
        assert key in pd


def test_get_project_validation_and_paths(projectsdb_stub: ProjectsDBStub) -> None:
    # Validation
    bad = pt.get_project("")
    assert bad["success"] is False
    assert bad["error"] == "project_id is required"
    assert bad["message"] == "Failed to get project: project_id is required"

    # Force not-found behavior for unknown IDs
    def _fake_get(pid: str):
        return projectsdb_stub._projects.get(pid)

    projectsdb_stub.get_project = _fake_get  # type: ignore[assignment]

    # Not found
    missing = pt.get_project("nope")
    assert missing["success"] is False
    assert missing["error"] == "Project not found: nope"
    assert missing["message"] == "Project with ID 'nope' not found"

    # Success
    p = pt.Project(name="Proj", description="Desc")  # type: ignore[call-arg]
    p.id = "project_test_id"
    projectsdb_stub._projects[p.id] = p

    ok = pt.get_project("project_test_id")
    assert ok["success"] is True
    assert ok["message"] == "Successfully retrieved project: Proj"
    assert "project" in ok
    assert isinstance(ok["project"], dict)


def test_update_project_validation_and_no_fields(
    projectsdb_stub: ProjectsDBStub,
) -> None:
    # Validation
    bad = pt.update_project("")
    assert bad["success"] is False
    assert bad["error"] == "project_id is required"
    assert bad["message"] == "Failed to update project: project_id is required"

    # No fields specified
    none = pt.update_project("project_test_id")
    assert none["success"] is False
    assert none["error"] == "At least one field must be provided for update"
    assert none["message"] == "No fields specified for update"


def test_update_project_success(projectsdb_stub: ProjectsDBStub) -> None:
    p = pt.Project(name="X")  # type: ignore[call-arg]
    p.id = "project_test_id"
    projectsdb_stub._projects[p.id] = p

    ok = pt.update_project("project_test_id", status="completed")
    assert ok["success"] is True
    assert ok["message"] == "Project updated successfully"
    assert ok["updated_fields"] == ["status"]


def test_delete_project_validation_success_and_cascade(
    projectsdb_stub: ProjectsDBStub,
) -> None:
    # Validation
    bad = pt.delete_project("")
    assert bad["success"] is False
    assert bad["error"] == "project_id is required"
    assert bad["message"] == "Failed to delete project: project_id is required"

    # Success non-cascade
    p1 = pt.Project(name="A")  # type: ignore[call-arg]
    p1.id = "p1"
    projectsdb_stub._projects[p1.id] = p1
    ok1 = pt.delete_project("p1")
    assert ok1["success"] is True
    assert ok1["message"] == "Project deleted successfully"
    assert ok1["cascade"] is False

    # Success cascade=True
    p2 = pt.Project(name="B")  # type: ignore[call-arg]
    p2.id = "p2"
    projectsdb_stub._projects[p2.id] = p2
    ok2 = pt.delete_project("p2", cascade=True)
    assert ok2["success"] is True
    assert ok2["message"] == "Project and children deleted successfully"
    assert ok2["cascade"] is True


def test_list_all_projects_success(projectsdb_stub: ProjectsDBStub) -> None:
    resp = pt.list_all_projects()
    assert resp["success"] is True
    assert resp["message"] == "Retrieved 1 projects"
    assert resp["count"] == 1
    assert "projects" in resp
    assert isinstance(resp["projects"], list)
    proj = resp["projects"][0]
    for key in (
        "id",
        "name",
        "description",
        "status",
        "color",
        "icon",
        "parent_project_id",
        "tags",
        "created_at",
        "updated_at",
    ):
        assert key in proj


def test_search_projects_validation_and_success(
    projectsdb_stub: ProjectsDBStub,
) -> None:
    # Validation
    bad = pt.search_projects("")
    assert bad["success"] is False
    assert bad["error"] == "query is required"
    assert bad["message"] == "Failed to search: query is required"

    ok = pt.search_projects("proj")
    assert ok["success"] is True
    assert ok["message"] == "Found 1 projects matching 'proj'"
    assert ok["count"] == 1
    assert "projects" in ok
    assert isinstance(ok["projects"], list)


def test_get_projects_by_status_validation_and_success(
    projectsdb_stub: ProjectsDBStub,
) -> None:
    # Validation
    bad = pt.get_projects_by_status("")
    assert bad["success"] is False
    assert bad["error"] == "status is required"
    assert bad["message"] == "Failed to get projects: status is required"

    ok = pt.get_projects_by_status("active")
    assert ok["success"] is True
    assert ok["status"] == "active"
    assert ok["message"] == "Found 1 active projects"
    assert ok["count"] == 1


def test_get_project_statistics_validation_and_success(
    projectsdb_stub: ProjectsDBStub,
) -> None:
    # Validation
    bad = pt.get_project_statistics("")
    assert bad["success"] is False
    assert bad["error"] == "project_id is required"
    assert bad["message"] == "Failed to get statistics: project_id is required"

    ok = pt.get_project_statistics("project_test_id")
    assert ok["success"] is True
    assert ok["message"] == "Statistics retrieved for project 'Proj'"
    stats = ok["statistics"]
    for key in (
        "project_id",
        "project_name",
        "total_notes",
        "total_artifacts",
        "total_calendar_events",
        "child_project_count",
        "completed_items",
        "total_items",
        "completion_percentage",
        "days_since_last_activity",
        "last_activity_date",
    ):
        assert key in stats


def test_get_project_tree_validation_success_and_not_found(
    projectsdb_stub: ProjectsDBStub,
) -> None:
    # Validation
    bad = pt.get_project_tree("")
    assert bad["success"] is False
    assert bad["error"] == "project_id is required"
    assert bad["message"] == "Failed to get tree: project_id is required"

    # Adapt stub behavior to legacy expectations
    def _fake_tree(project_id: str) -> dict[str, Any] | None:
        if project_id == "root":
            return {
                "id": "root",
                "name": "Root",
                "children": [{"id": "c1", "name": "Child", "children": []}],
            }
        return None

    projectsdb_stub.get_project_tree = _fake_tree  # type: ignore[assignment]

    # Success
    ok = pt.get_project_tree("root")
    assert ok["success"] is True
    assert ok["message"] == "Project tree retrieved successfully"
    assert "tree" in ok
    assert isinstance(ok["tree"], dict)

    # Not found
    nf = pt.get_project_tree("missing")
    assert nf["success"] is False
    assert nf["error"] == "Project not found: missing"
    assert nf["message"] == "Cannot build tree for non-existent project"
