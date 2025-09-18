"""
Black-box integration tests for AppointmentsDatabase.

These tests use real database connections and create actual records
to test the database operations, following the pattern established
in the notes service tests.
"""

import uuid
from datetime import date, datetime, timedelta

import pytest

from database.appointments_db import AppointmentsDatabase
from models.calendar_event import CalendarEvent


def _new_calendar_event(
    title="Test Event",
    description="Test Description",
    event_type="meeting",
    status="scheduled",
    event_date=None,
    start_time="09:00:00",
    end_time="10:00:00",
    location="Test Location",
    participants=None,
    tags=None,
    reminder_minutes_before=15,
):
    """Helper function to create a new CalendarEvent with unique ID."""
    event_date = event_date or datetime.now().date().isoformat()

    return CalendarEvent(
        id=f"test-{uuid.uuid4().hex[:8]}",
        title=title,
        description=description,
        event_type=event_type,
        status=status,
        event_date=event_date,
        start_time=start_time,
        end_time=end_time,
        location=location,
        participants=participants or [],
        tags=tags or [],
        reminder_minutes_before=reminder_minutes_before,
    )


def _cleanup_events(db, event_ids):
    """Helper function to clean up created events."""
    for event_id in event_ids:
        try:
            db.delete_event(event_id)
        except (KeyError, ValueError, AttributeError):
            pass  # Ignore cleanup errors


@pytest.mark.integration
def test_appointments_crud_workflow(db_manager):
    """Test complete CRUD operations workflow for calendar events."""
    db = AppointmentsDatabase(db_manager)
    created_ids = []

    try:
        # CREATE - Test event creation
        new_event = _new_calendar_event(
            title="CRUD Test Event",
            description="Testing CRUD operations",
            event_type="meeting",
            location="Conference Room A",
            participants=["alice@test.com", "bob@test.com"],
            tags=["test", "crud"],
            reminder_minutes_before=30,
        )
        created_ids.append(new_event.id)

        create_result = db.create_event(new_event)
        if create_result["success"] is not True:
            raise AssertionError

        # READ - Test event retrieval
        retrieved_event = db.get_event(new_event.id)
        assert retrieved_event is not None
        if retrieved_event.id != new_event.id:
            raise AssertionError
        if retrieved_event.title != "CRUD Test Event":
            raise AssertionError
        if retrieved_event.description != "Testing CRUD operations":
            raise AssertionError
        if retrieved_event.event_type != "meeting":
            raise AssertionError
        if retrieved_event.location != "Conference Room A":
            raise AssertionError
        if retrieved_event.status != "scheduled":
            raise AssertionError

        # UPDATE - Test event modification
        update_data = {
            "title": "Updated CRUD Test Event",
            "description": "Updated description",
            "status": "in_progress",
            "location": "Conference Room B",
        }

        update_result = db.update_event(new_event.id, update_data)
        if update_result is not True:
            raise AssertionError

        # Verify updates
        updated_event = db.get_event(new_event.id)
        if updated_event.title != "Updated CRUD Test Event":
            raise AssertionError
        if updated_event.description != "Updated description":
            raise AssertionError
        if updated_event.status != "in_progress":
            raise AssertionError
        if updated_event.location != "Conference Room B":
            raise AssertionError

        # DELETE - Test event removal
        delete_result = db.delete_event(new_event.id)
        if delete_result is not True:
            raise AssertionError

        # Verify deletion
        deleted_event = db.get_event(new_event.id)
        assert deleted_event is None

        # Remove from cleanup list since already deleted
        created_ids.remove(new_event.id)

    finally:
        _cleanup_events(db, created_ids)


@pytest.mark.integration
def test_appointments_query_operations(db_manager):
    """Test various query operations and search functionality."""
    db = AppointmentsDatabase(db_manager)
    created_ids = []

    try:
        # Create test events with different properties
        today = date.today()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)

        events_data = [
            {
                "title": "Daily Standup",
                "event_type": "meeting",
                "event_date": today.isoformat(),
                "tags": ["daily", "standup", "team"],
                "status": "scheduled",
            },
            {
                "title": "Project Review",
                "event_type": "meeting",
                "event_date": tomorrow.isoformat(),
                "tags": ["review", "project"],
                "status": "scheduled",
            },
            {
                "title": "Doctor Appointment",
                "event_type": "appointment",
                "event_date": next_week.isoformat(),
                "tags": ["personal", "health"],
                "status": "scheduled",
            },
            {
                "title": "Completed Task",
                "event_type": "task",
                "event_date": today.isoformat(),
                "tags": ["task"],
                "status": "completed",
            },
        ]

        created_events = []
        for event_data in events_data:
            event = _new_calendar_event(**event_data)
            created_ids.append(event.id)
            created_events.append(event)

            result = db.create_event(event)
            if result["success"] is not True:
                raise AssertionError

        # Test date range queries
        date_range_events = db.get_events_for_date_range(today, tomorrow)
        date_range_ids = [e.id for e in date_range_events]

        # Should include today and tomorrow events
        if created_events[0].id not in date_range_ids:
            raise AssertionError
        if created_events[1].id not in date_range_ids:
            raise AssertionError
        if created_events[3].id not in date_range_ids:
            raise AssertionError

        # Test search functionality
        search_results = db.search_events("standup")
        if len(search_results) < 1:
            raise AssertionError
        if not any(e.id == created_events[0].id for e in search_results):
            raise AssertionError

        search_results = db.search_events("project")
        if len(search_results) < 1:
            raise AssertionError
        if not any(e.id == created_events[1].id for e in search_results):
            raise AssertionError

        # Test status filtering
        scheduled_events = db.get_events_by_status("scheduled")
        scheduled_ids = [e.id for e in scheduled_events]
        if created_events[0].id not in scheduled_ids:
            raise AssertionError
        if created_events[1].id not in scheduled_ids:
            raise AssertionError
        if created_events[2].id not in scheduled_ids:
            raise AssertionError

        completed_events = db.get_events_by_status("completed")
        completed_ids = [e.id for e in completed_events]
        if created_events[3].id not in completed_ids:
            raise AssertionError

    finally:
        _cleanup_events(db, created_ids)


@pytest.mark.integration
def test_appointments_reminder_functionality(db_manager):
    """Test reminder creation and management."""
    db = AppointmentsDatabase(db_manager)
    created_ids = []

    try:
        # Create event with reminder
        future_date = (datetime.now() + timedelta(hours=2)).date()
        reminder_event = _new_calendar_event(
            title="Important Meeting",
            event_date=future_date.isoformat(),
            start_time="14:00:00",
            reminder_minutes_before=30,
        )
        created_ids.append(reminder_event.id)

        result = db.create_event(reminder_event)
        if result["success"] is not True:
            raise AssertionError

        # Test reminder retrieval
        upcoming_reminders = db.get_upcoming_reminders()

        # For integration testing, we can test the reminder creation mechanism

        # Create event with past reminder time to test immediate reminders
        past_reminder_time = datetime.now() - timedelta(minutes=5)
        past_event = _new_calendar_event(
            title="Past Reminder Event",
            event_date=past_reminder_time.date().isoformat(),
            start_time=past_reminder_time.time().strftime("%H:%M:%S"),
            reminder_minutes_before=30,
        )
        created_ids.append(past_event.id)

        result = db.create_event(past_event)
        if result["success"] is not True:
            raise AssertionError

        # Check for reminders
        upcoming_reminders = db.get_upcoming_reminders()

        # Test marking reminder as sent (if any exist)
        if upcoming_reminders:
            reminder_id = upcoming_reminders[0]["id"]
            mark_result = db.mark_reminder_sent(reminder_id)
            if mark_result is not True:
                raise AssertionError

            # Verify reminder was marked as sent
            updated_reminders = db.get_upcoming_reminders()
            # The sent reminder should no longer appear in upcoming
            updated_reminder_ids = [r["id"] for r in updated_reminders]
            if reminder_id in updated_reminder_ids:
                raise AssertionError

    finally:
        _cleanup_events(db, created_ids)


@pytest.mark.integration
def test_appointments_recurring_events(db_manager):
    """Test handling of recurring events."""
    db = AppointmentsDatabase(db_manager)
    created_ids = []

    try:
        # Create recurring event
        recurring_event = _new_calendar_event(
            title="Weekly Team Meeting",
            description="Recurring weekly meeting",
            event_type="meeting",
            tags=["recurring", "team", "weekly"],
        )
        recurring_event.recurrence_pattern = "weekly"
        recurring_event.recurrence_end_date = (
            (datetime.now() + timedelta(weeks=4)).date().isoformat()
        )
        created_ids.append(recurring_event.id)

        result = db.create_event(recurring_event)
        if result["success"] is not True:
            raise AssertionError

        # Verify recurring event was created
        retrieved_event = db.get_event(recurring_event.id)
        assert retrieved_event is not None
        if retrieved_event.recurrence_pattern != "weekly":
            raise AssertionError

        # Test search for recurring events
        recurring_search = db.search_events("weekly")
        if len(recurring_search) < 1:
            raise AssertionError
        if not any(e.id == recurring_event.id for e in recurring_search):
            raise AssertionError

        # Create monthly recurring event
        monthly_event = _new_calendar_event(title="Monthly Review", event_type="meeting")
        monthly_event.recurrence_pattern = "monthly"
        created_ids.append(monthly_event.id)

        result = db.create_event(monthly_event)
        if result["success"] is not True:
            raise AssertionError

    finally:
        _cleanup_events(db, created_ids)


@pytest.mark.integration
def test_appointments_validation_and_edge_cases(db_manager):
    """Test validation and edge case handling."""
    db = AppointmentsDatabase(db_manager)
    created_ids = []

    try:
        # Test create event with minimal data
        minimal_event = CalendarEvent(id=f"minimal-{uuid.uuid4().hex[:8]}", title="Minimal Event")
        created_ids.append(minimal_event.id)

        result = db.create_event(minimal_event)
        if result["success"] is not True:
            raise AssertionError

        # Test get non-existent event
        non_existent = db.get_event("non-existent-id")
        assert non_existent is None

        # Test update non-existent event
        update_result = db.update_event("non-existent-id", {"title": "New Title"})
        if update_result is not False:
            raise AssertionError

        # Test delete non-existent event
        delete_result = db.delete_event("non-existent-id")
        if delete_result is not False:
            raise AssertionError

        # Test create event with duplicate ID (should handle gracefully)
        duplicate_event = CalendarEvent(id=minimal_event.id, title="Duplicate Event")

        duplicate_result = db.create_event(duplicate_event)
        # Should either succeed with update or fail gracefully
        if "success" not in duplicate_result:
            raise AssertionError

        # Test all-day event
        all_day_event = _new_calendar_event(title="All Day Event", start_time=None, end_time=None)
        all_day_event.all_day = True
        created_ids.append(all_day_event.id)

        all_day_result = db.create_event(all_day_event)
        if all_day_result["success"] is not True:
            raise AssertionError

        retrieved_all_day = db.get_event(all_day_event.id)
        assert retrieved_all_day is not None
        if retrieved_all_day.all_day is not True:
            raise AssertionError

    finally:
        _cleanup_events(db, created_ids)


@pytest.mark.integration
def test_appointments_complex_data_handling(db_manager):
    """Test handling of complex data types (participants, tags, metadata)."""
    db = AppointmentsDatabase(db_manager)
    created_ids = []

    try:
        # Create event with complex data
        complex_event = _new_calendar_event(
            title="Quarterly Review Meeting",
            description="Comprehensive quarterly business review",
            participants=["alice@test.com", "bob@test.com", "charlie@test.com"],
            tags=["important", "quarterly", "review"],
        )
        complex_event.metadata = {
            "room": "Conference Room A",
            "catering": True,
            "attendee_count": 15,
            "budget": 500.00,
        }
        created_ids.append(complex_event.id)

        result = db.create_event(complex_event)
        if result["success"] is not True:
            raise AssertionError

        # Retrieve and verify complex data
        retrieved = db.get_event(complex_event.id)
        assert retrieved is not None

        # Verify participants handling
        assert len(retrieved.participants) == 3
        if "alice@test.com" not in retrieved.participants:
            raise AssertionError
        if "bob@test.com" not in retrieved.participants:
            raise AssertionError
        if "charlie@test.com" not in retrieved.participants:
            raise AssertionError

        assert len(retrieved.tags) == 3
        if "important" not in retrieved.tags:
            raise AssertionError
        if "quarterly" not in retrieved.tags:
            raise AssertionError
        if "review" not in retrieved.tags:
            raise AssertionError

        if retrieved.metadata:
            if retrieved.metadata.get("room") != "Conference Room A":
                raise AssertionError
            if retrieved.metadata.get("catering") is not True:
                raise AssertionError
            if retrieved.metadata.get("attendee_count") != 15:
                raise AssertionError

        # Test search by participants (use search functionality)
        quarterly_events = db.search_events("Quarterly")
        if len(quarterly_events) < 1:
            raise AssertionError
        if not any(e.id == complex_event.id for e in quarterly_events):
            raise AssertionError

    finally:
        _cleanup_events(db, created_ids)


@pytest.mark.integration
def test_appointments_performance_bulk_operations(db_manager):
    """Test bulk operations and performance with multiple events."""
    db = AppointmentsDatabase(db_manager)
    created_ids = []

    try:
        # Create multiple events for bulk testing
        events = []
        for i in range(10):
            event = _new_calendar_event(
                title=f"Bulk Test Event {i + 1}",
                description=f"Event {i + 1} for bulk testing",
                event_type="meeting" if i % 2 == 0 else "task",
                tags=["bulk", "test", f"batch-{i // 5}"],
            )
            events.append(event)
            created_ids.append(event.id)

        # Bulk create
        for event in events:
            result = db.create_event(event)
            if result["success"] is not True:
                raise AssertionError

        # Test bulk retrieval using date range
        today = date.today()
        future_date = today + timedelta(days=30)
        all_events = db.get_events_for_date_range(today, future_date)
        created_event_ids = [e.id for e in events]
        retrieved_ids = [e.id for e in all_events]

        # Verify all created events are in the retrieved list
        for event_id in created_event_ids:
            if event_id not in retrieved_ids:
                raise AssertionError

        # Test bulk update (update all to completed status)
        for event in events:
            update_result = db.update_event(event.id, {"status": "completed"})
            if update_result is not True:
                raise AssertionError

        # Verify bulk updates
        completed_events = db.get_events_by_status("completed")
        completed_ids = [e.id for e in completed_events]
        for event_id in created_event_ids:
            if event_id not in completed_ids:
                raise AssertionError

    finally:
        _cleanup_events(db, created_ids)
