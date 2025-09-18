from datetime import date, datetime, time

import pytest

from models.calendar_event import CalendarEvent
from models.project import Project, ProjectStatistics, ProjectStatus, ProjectSummary


def test_project_from_dict_and_to_dict_tags_and_status():
    data = {
        "id": "p1",
        "name": "Proj",
        "description": "Desc",
        "status": "completed",
        "tags": ["a", "b"],
        "metadata": {"k": "v"},
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-02T00:00:00",
        "completed_at": "2024-01-03T00:00:00",
        "archived_at": None,
    }
    p = Project.from_dict(data)
    # tags should be joined into comma-separated string by from_dict
    assert isinstance(p.tags, str)
    if p.tags != "a,b":
        raise AssertionError
    # status enum conversion
    if p.status != ProjectStatus.COMPLETED:
        raise AssertionError
    # to_dict should serialize status to value and preserve tags as string
    out = p.to_dict()
    if out["status"] != "completed":
        raise AssertionError
    if out["tags"] != "a,b":
        raise AssertionError
    if out["metadata"] != {"k": "v"}:
        raise AssertionError


def test_project_summary_from_project():
    p = Project(id="p2", name="Name")
    s = ProjectSummary.from_project(p)
    if s.project_id != "p2":
        raise AssertionError
    if s.project_name != "Name":
        raise AssertionError
    if s.total_item_count != 0:
        raise AssertionError


def test_project_statistics_calculations_and_robustness():
    ps = ProjectStatistics(
        project_id="p3",
        project_name="N",
        total_notes=2,
        total_artifacts=3,
        total_items=10,
        completed_items=4,
        last_activity_date=datetime.now(),
    )
    ps.calculate_days_since_activity()
    assert ps.days_since_activity is not None
    ps.calculate_completion_percentage()
    if ps.completion_percentage != pytest.approx(40.0):
        raise AssertionError

    # Robustness: invalid last_activity_date string should not raise and set None
    ps2 = ProjectStatistics(project_id="p4", project_name="N", last_activity_date="not-a-date")  # type: ignore[assignment]
    ps2.calculate_days_since_activity()
    assert ps2.days_since_activity is None

    # Robustness: divide by zero guarded
    ps3 = ProjectStatistics(project_id="p5", project_name="N", total_items=0, completed_items=1)
    ps3.calculate_completion_percentage()
    if ps3.completion_percentage != 0.0:
        raise AssertionError


def test_calendar_event_from_dict_participants_and_to_dict_flatten():
    raw = {
        "id": "e1",
        "title": "T",
        "participants": "a@x,b@y",  # string should be split
        "tags": ["t1", "t2"],
        "all_day": False,
        "start_time": "09:30:00",
        "event_date": "2024-02-01",
    }
    ev = CalendarEvent.from_dict(raw)
    if ev.participants != ["a@x", "b@y"]:
        raise AssertionError
    # to_dict should join participants into CSV string
    out = ev.to_dict()
    if out["participants"] != "a@x,b@y":
        raise AssertionError
    # preserve tags list and other fields
    if ev.tags != ["t1", "t2"]:
        raise AssertionError
    if out["event_date"] != "2024-02-01":
        raise AssertionError


@pytest.mark.parametrize(
    ("event_date", "all_day", "start_time", "expected_time"),
    [
        ("2024-02-01", True, None, time(0, 0)),
        ("2024-02-01", False, None, time(0, 0)),
        ("2024-02-01", False, "07:05", time(7, 5)),
        ("2024-02-01", False, "07:05:06", time(7, 5, 6)),
    ],
    ids=["all_day_defaults_midnight", "no_start_defaults_midnight", "hh_mm", "hh_mm_ss"],
)
def test_calendar_event_get_datetime(event_date, all_day, start_time, expected_time):
    ev = CalendarEvent(
        id="e2", title="T", event_date=event_date, all_day=all_day, start_time=start_time
    )
    dt = ev.get_datetime()
    assert dt is not None
    if dt.date() != date.fromisoformat(event_date):
        raise AssertionError
    if dt.time() != expected_time:
        raise AssertionError


def test_calendar_event_get_datetime_invalid_safe():
    # Missing date -> None
    ev = CalendarEvent(id="e3", title="T", event_date=None)
    if ev.get_datetime() is not None:
        raise AssertionError
    # Malformed time -> None (guarded by exception handling)
    ev2 = CalendarEvent(id="e4", title="T", event_date="2024-01-01", start_time="99:99:99")
    if ev2.get_datetime() is not None:
        raise AssertionError
