from __future__ import annotations

from typing import Any

import pytest

from tools.tests.helpers.db_stubs import ProjectsDBStub

pytestmark = pytest.mark.usefixtures("patch_tools")

try:
    import src.tools.projects_tool as pt
except Exception:
    import tools.projects_tool as pt


def test_create_project_validation_error(_projectsdb_stub: ProjectsDBStub) -> None:
    resp = pt.create_project("")
    if resp["success"] is not False:
        raise AssertionError
    if resp["error"] != "Project name is required":
        raise AssertionError
    if resp["message"] != "Failed to create project: name is required":
        raise AssertionError


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
    if resp["success"] is not True:
        raise AssertionError
    if resp["project_id"] != "project_created_id":
        raise AssertionError
    if resp["message"] != "Project created successfully":
        raise AssertionError
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
        if key not in pd:
            raise AssertionError


def test_get_project_validation_and_paths(projectsdb_stub: ProjectsDBStub) -> None:
    # Validation
    bad = pt.get_project("")
    if bad["success"] is not False:
        raise AssertionError
    if bad["error"] != "project_id is required":
        raise AssertionError
    if bad["message"] != "Failed to get project: project_id is required":
        raise AssertionError

    # Force not-found behavior for unknown IDs
    def _fake_get(pid: str):
        return projectsdb_stub._projects.get(pid)

    projectsdb_stub.get_project = _fake_get  # type: ignore[assignment]

    # Not found
    missing = pt.get_project("nope")
    if missing["success"] is not False:
        raise AssertionError
    if missing["error"] != "Project not found: nope":
        raise AssertionError
    if missing["message"] != "Project with ID 'nope' not found":
        raise AssertionError

    # Success
    p = pt.Project(name="Proj", description="Desc")  # type: ignore[call-arg]
    p.id = "project_test_id"
    projectsdb_stub._projects[p.id] = p

    ok = pt.get_project("project_test_id")
    if ok["success"] is not True:
        raise AssertionError
    if ok["message"] != "Successfully retrieved project: Proj":
        raise AssertionError
    if "project" not in ok:
        raise AssertionError
    assert isinstance(ok["project"], dict)


def test_update_project_validation_and_no_fields(
    _projectsdb_stub: ProjectsDBStub,
) -> None:
    # Validation
    bad = pt.update_project("")
    if bad["success"] is not False:
        raise AssertionError
    if bad["error"] != "project_id is required":
        raise AssertionError
    if bad["message"] != "Failed to update project: project_id is required":
        raise AssertionError

    # No fields specified
    none = pt.update_project("project_test_id")
    if none["success"] is not False:
        raise AssertionError
    if none["error"] != "At least one field must be provided for update":
        raise AssertionError
    if none["message"] != "No fields specified for update":
        raise AssertionError


def test_update_project_success(projectsdb_stub: ProjectsDBStub) -> None:
    p = pt.Project(name="X")  # type: ignore[call-arg]
    p.id = "project_test_id"
    projectsdb_stub._projects[p.id] = p

    ok = pt.update_project("project_test_id", status="completed")
    if ok["success"] is not True:
        raise AssertionError
    if ok["message"] != "Project updated successfully":
        raise AssertionError
    if ok["updated_fields"] != ["status"]:
        raise AssertionError


def test_delete_project_validation_success_and_cascade(
    projectsdb_stub: ProjectsDBStub,
) -> None:
    # Validation
    bad = pt.delete_project("")
    if bad["success"] is not False:
        raise AssertionError
    if bad["error"] != "project_id is required":
        raise AssertionError
    if bad["message"] != "Failed to delete project: project_id is required":
        raise AssertionError

    # Success non-cascade
    p1 = pt.Project(name="A")  # type: ignore[call-arg]
    p1.id = "p1"
    projectsdb_stub._projects[p1.id] = p1
    ok1 = pt.delete_project("p1")
    if ok1["success"] is not True:
        raise AssertionError
    if ok1["message"] != "Project deleted successfully":
        raise AssertionError
    if ok1["cascade"] is not False:
        raise AssertionError

    # Success cascade=True
    p2 = pt.Project(name="B")  # type: ignore[call-arg]
    p2.id = "p2"
    projectsdb_stub._projects[p2.id] = p2
    ok2 = pt.delete_project("p2", cascade=True)
    if ok2["success"] is not True:
        raise AssertionError
    if ok2["message"] != "Project and children deleted successfully":
        raise AssertionError
    if ok2["cascade"] is not True:
        raise AssertionError


def test_list_all_projects_success(_projectsdb_stub: ProjectsDBStub) -> None:
    resp = pt.list_all_projects()
    if resp["success"] is not True:
        raise AssertionError
    if resp["message"] != "Retrieved 1 projects":
        raise AssertionError
    if resp["count"] != 1:
        raise AssertionError
    if "projects" not in resp:
        raise AssertionError
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
        if key not in proj:
            raise AssertionError


def test_search_projects_validation_and_success(
    _projectsdb_stub: ProjectsDBStub,
) -> None:
    # Validation
    bad = pt.search_projects("")
    if bad["success"] is not False:
        raise AssertionError
    if bad["error"] != "query is required":
        raise AssertionError
    if bad["message"] != "Failed to search: query is required":
        raise AssertionError

    ok = pt.search_projects("proj")
    if ok["success"] is not True:
        raise AssertionError
    if ok["message"] != "Found 1 projects matching 'proj'":
        raise AssertionError
    if ok["count"] != 1:
        raise AssertionError
    if "projects" not in ok:
        raise AssertionError
    assert isinstance(ok["projects"], list)


def test_get_projects_by_status_validation_and_success(
    _projectsdb_stub: ProjectsDBStub,
) -> None:
    # Validation
    bad = pt.get_projects_by_status("")
    if bad["success"] is not False:
        raise AssertionError
    if bad["error"] != "status is required":
        raise AssertionError
    if bad["message"] != "Failed to get projects: status is required":
        raise AssertionError

    ok = pt.get_projects_by_status("active")
    if ok["success"] is not True:
        raise AssertionError
    if ok["status"] != "active":
        raise AssertionError
    if ok["message"] != "Found 1 active projects":
        raise AssertionError
    if ok["count"] != 1:
        raise AssertionError


def test_get_project_statistics_validation_and_success(
    _projectsdb_stub: ProjectsDBStub,
) -> None:
    # Validation
    bad = pt.get_project_statistics("")
    if bad["success"] is not False:
        raise AssertionError
    if bad["error"] != "project_id is required":
        raise AssertionError
    if bad["message"] != "Failed to get statistics: project_id is required":
        raise AssertionError

    ok = pt.get_project_statistics("project_test_id")
    if ok["success"] is not True:
        raise AssertionError
    if ok["message"] != "Statistics retrieved for project 'Proj'":
        raise AssertionError
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
        if key not in stats:
            raise AssertionError


def test_get_project_tree_validation_success_and_not_found(
    projectsdb_stub: ProjectsDBStub,
) -> None:
    # Validation
    bad = pt.get_project_tree("")
    if bad["success"] is not False:
        raise AssertionError
    if bad["error"] != "project_id is required":
        raise AssertionError
    if bad["message"] != "Failed to get tree: project_id is required":
        raise AssertionError

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
    if ok["success"] is not True:
        raise AssertionError
    if ok["message"] != "Project tree retrieved successfully":
        raise AssertionError
    if "tree" not in ok:
        raise AssertionError
    assert isinstance(ok["tree"], dict)

    # Not found
    nf = pt.get_project_tree("missing")
    if nf["success"] is not False:
        raise AssertionError
    if nf["error"] != "Project not found: missing":
        raise AssertionError
    if nf["message"] != "Cannot build tree for non-existent project":
        raise AssertionError
