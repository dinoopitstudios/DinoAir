"""
Black-box integration tests for ProjectsDatabase against real SQLite.
All tests exercise public APIs and assert persisted DB state/results.
"""

import pytest

from database.projects_db import ProjectsDatabase
from models.project import Project, ProjectStatus


def test_projects_crud_black_box(db_manager, _projects_connection, sample_project):
    db = ProjectsDatabase(db_manager)

    # Create
    res = db.create_project(sample_project)
    if res["success"] is not True:
        raise AssertionError
    if res["id"] != sample_project.id:
        raise AssertionError

    # Read
    got = db.get_project(sample_project.id)
    assert got is not None
    if got.id != sample_project.id:
        raise AssertionError
    if got.name != sample_project.name:
        raise AssertionError

    # Update
    if (
        db.update_project(
            sample_project.id, {"name": "Updated Name", "status": ProjectStatus.COMPLETED.value}
        )
        is not True
    ):
        raise AssertionError
    updated = db.get_project(sample_project.id)
    assert updated is not None
    if updated.name != "Updated Name":
        raise AssertionError
    if updated.status != ProjectStatus.COMPLETED.value:
        raise AssertionError

    # Delete
    if db.delete_project(sample_project.id) is not True:
        raise AssertionError
    if db.get_project(sample_project.id) is not None:
        raise AssertionError


def test_projects_hierarchy_and_tree_black_box(db_manager, projects_connection):
    db = ProjectsDatabase(db_manager)

    parent = Project(id="proj-parent", name="Parent")
    child = Project(id="proj-child", name="Child", parent_project_id="proj-parent")

    if db.create_project(parent)["success"] is not True:
        raise AssertionError
    if db.create_project(child)["success"] is not True:
        raise AssertionError

    # Verify child is linked to parent in DB
    cur = projects_connection.cursor()
    cur.execute("SELECT parent_project_id FROM projects WHERE id = ?", (child.id,))
    row = cur.fetchone()
    assert row is not None
    if row[0] != parent.id:
        raise AssertionError

    # Tree should include the child
    tree = db.get_project_tree(parent.id)
    assert isinstance(tree, dict)
    if tree["id"] != parent.id:
        raise AssertionError
    if tree["name"] != parent.name:
        raise AssertionError
    if "children" not in tree:
        raise AssertionError
    assert isinstance(tree["children"], list)
    if not any(c["id"] == child.id for c in tree["children"]):
        raise AssertionError


def test_projects_search_and_filters_black_box(db_manager, _projects_connection):
    db = ProjectsDatabase(db_manager)

    a = Project(id="proj-a", name="Alpha", description="first", tags=["one", "alpha"])
    b = Project(id="proj-b", name="Beta", description="second", tags=["two", "beta"])
    c = Project(
        id="proj-c",
        name="Gamma",
        description="third",
        tags=["two", "gamma"],
        status=ProjectStatus.ARCHIVED,
    )

    if db.create_project(a)["success"] is not True:
        raise AssertionError
    if db.create_project(b)["success"] is not True:
        raise AssertionError
    if db.create_project(c)["success"] is not True:
        raise AssertionError

    # Search by name/description/tags (LIKE prefilter + exact tag filter)
    results = db.search_projects("Alpha")
    if not any(p.id == "proj-a" for p in results):
        raise AssertionError

    by_status = db.get_projects_by_status(ProjectStatus.ARCHIVED.value)
    if not any(p.id == "proj-c" for p in by_status):
        raise AssertionError

    by_tag_two = db.get_projects_by_tag("two")
    ids = {p.id for p in by_tag_two}
    if "proj-b" not in ids:
        raise AssertionError
    if "proj-c" not in ids:
        raise AssertionError


def test_delete_cascade_black_box(db_manager, _projects_connection):
    db = ProjectsDatabase(db_manager)

    root = Project(id="root-x", name="Root X")
    child = Project(id="child-x1", name="Child X1", parent_project_id="root-x")
    grandchild = Project(id="grand-x1", name="Grand X1", parent_project_id="child-x1")

    if db.create_project(root)["success"] is not True:
        raise AssertionError
    if db.create_project(child)["success"] is not True:
        raise AssertionError
    if db.create_project(grandchild)["success"] is not True:
        raise AssertionError

    # Sanity: all exist
    if db.get_project(root.id) is None:
        raise AssertionError
    if db.get_project(child.id) is None:
        raise AssertionError
    if db.get_project(grandchild.id) is None:
        raise AssertionError

    # Cascade delete
    if db.delete_project(root.id, cascade=True) is not True:
        raise AssertionError

    # All removed
    if db.get_project(root.id) is not None:
        raise AssertionError
    if db.get_project(child.id) is not None:
        raise AssertionError
    if db.get_project(grandchild.id) is not None:
        raise AssertionError


def test_update_rejects_invalid_parent_black_box(db_manager):
    db = ProjectsDatabase(db_manager)

    proj = Project(id="solo-1", name="Solo")
    if db.create_project(proj)["success"] is not True:
        raise AssertionError

    # Attempt to set non-existent parent
    ok = db.update_project("solo-1", {"parent_project_id": "no-such-parent"})
    if ok is not False:
        raise AssertionError


@pytest.mark.parametrize(
    ("status", "expected_count"),
    [
        (ProjectStatus.ACTIVE.value, 2),
        (ProjectStatus.COMPLETED.value, 1),
        (ProjectStatus.ARCHIVED.value, 1),
    ],
    ids=["active", "completed", "archived"],
)
def test_get_projects_by_status_param_matrix_black_box(db_manager, status, expected_count):
    db = ProjectsDatabase(db_manager)

    # Create a minimal set of projects with mixed statuses
    p1 = Project(id=f"s-{status}-1", name=f"{status}-1", status=status)
    p2 = Project(id=f"s-{status}-2", name=f"{status}-2", status=status)
    # Also create projects of other statuses to ensure filtering
    other1 = Project(id="s-other-1", name="other-1", status=ProjectStatus.ACTIVE)
    other2 = Project(id="s-other-2", name="other-2", status=ProjectStatus.ARCHIVED)
    other3 = Project(id="s-other-3", name="other-3", status=ProjectStatus.COMPLETED)

    # Persist, but only ensure exactly expected_count of the target status exist
    if db.create_project(p1)["success"] is not True:
        raise AssertionError
    if expected_count >= 2:
        if db.create_project(p2)["success"] is not True:
            raise AssertionError

    if db.create_project(other1)["success"] is not True:
        raise AssertionError
    if db.create_project(other2)["success"] is not True:
        raise AssertionError
    if db.create_project(other3)["success"] is not True:
        raise AssertionError

    results = db.get_projects_by_status(status)
    assert len([p for p in results if p.status == status]) == expected_count
