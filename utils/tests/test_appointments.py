"""Comprehensive tests for utils.appointments module."""

from datetime import datetime

import pytest

from utils.appointments import (
    Appointment,
    create_appointment,
    is_valid_date_string,
    normalize_event_title,
)


class TestAppointment:
    """Tests for Appointment dataclass."""

    def test_appointment_creation(self):
        """Test basic appointment creation."""
        start_time = datetime(2024, 1, 15, 10, 30)
        end_time = datetime(2024, 1, 15, 11, 30)

        appointment = Appointment(
            title="Meeting with Client",
            start_time=start_time,
            end_time=end_time,
            description="Quarterly review meeting",
        )

        assert appointment.title == "Meeting with Client"
        assert appointment.start_time == start_time
        assert appointment.end_time == end_time
        assert appointment.description == "Quarterly review meeting"

    def test_appointment_default_description(self):
        """Test appointment with default empty description."""
        start_time = datetime(2024, 1, 15, 10, 30)
        end_time = datetime(2024, 1, 15, 11, 30)

        appointment = Appointment(title="Quick Call", start_time=start_time, end_time=end_time)

        assert appointment.description == ""

    def test_appointment_equality(self):
        """Test appointment equality comparison."""
        start_time = datetime(2024, 1, 15, 10, 30)
        end_time = datetime(2024, 1, 15, 11, 30)

        appointment1 = Appointment("Meeting", start_time, end_time, "Description")
        appointment2 = Appointment("Meeting", start_time, end_time, "Description")
        appointment3 = Appointment("Different Meeting", start_time, end_time, "Description")

        assert appointment1 == appointment2
        assert appointment1 != appointment3

    def test_appointment_repr(self):
        """Test appointment string representation."""
        start_time = datetime(2024, 1, 15, 10, 30)
        end_time = datetime(2024, 1, 15, 11, 30)

        appointment = Appointment("Test Meeting", start_time, end_time, "Test")

        repr_str = repr(appointment)
        assert "Test Meeting" in repr_str
        assert "2024-01-15" in repr_str


class TestCreateAppointment:
    """Tests for create_appointment function."""

    def test_create_appointment_basic(self):
        """Test basic appointment creation via function."""
        appointment = create_appointment(
            title="team standup",
            start_time="2024-01-15T09:00:00",
            end_time="2024-01-15T09:30:00",
            description="Daily team standup meeting",
        )

        assert appointment.title == "Team Standup"  # Should be normalized
        assert appointment.start_time == datetime(2024, 1, 15, 9, 0, 0)
        assert appointment.end_time == datetime(2024, 1, 15, 9, 30, 0)
        assert appointment.description == "Daily team standup meeting"

    def test_create_appointment_no_description(self):
        """Test appointment creation without description."""
        appointment = create_appointment(
            title="lunch break", start_time="2024-01-15T12:00:00", end_time="2024-01-15T13:00:00"
        )

        assert appointment.title == "Lunch Break"
        assert appointment.description == ""

    def test_create_appointment_with_timezone(self):
        """Test appointment creation with timezone-aware timestamps."""
        appointment = create_appointment(
            title="remote meeting",
            start_time="2024-01-15T09:00:00+00:00",
            end_time="2024-01-15T10:00:00+00:00",
            description="International team call",
        )

        assert appointment.title == "Remote Meeting"
        assert appointment.start_time.year == 2024
        assert appointment.start_time.month == 1
        assert appointment.start_time.day == 15

    def test_create_appointment_invalid_datetime(self):
        """Test appointment creation with invalid datetime strings."""
        with pytest.raises(ValueError):
            create_appointment(
                title="Invalid Meeting",
                start_time="invalid-datetime",
                end_time="2024-01-15T10:00:00",
                description="This should fail",
            )

        with pytest.raises(ValueError):
            create_appointment(
                title="Invalid Meeting",
                start_time="2024-01-15T09:00:00",
                end_time="not-a-datetime",
                description="This should also fail",
            )

    def test_create_appointment_microseconds(self):
        """Test appointment creation with microsecond precision."""
        appointment = create_appointment(
            title="precise meeting",
            start_time="2024-01-15T09:00:00.123456",
            end_time="2024-01-15T09:30:00.654321",
            description="High precision timing",
        )

        assert appointment.start_time.microsecond == 123456
        assert appointment.end_time.microsecond == 654321


class TestNormalizeEventTitle:
    """Tests for normalize_event_title function."""

    def test_normalize_basic_title(self):
        """Test basic title normalization."""
        assert normalize_event_title("meeting with client") == "Meeting With Client"
        assert normalize_event_title("TEAM STANDUP") == "Team Standup"
        assert normalize_event_title("lunch break") == "Lunch Break"

    def test_normalize_extra_whitespace(self):
        """Test normalization with extra whitespace."""
        assert normalize_event_title("  meeting   with    client  ") == "Meeting With Client"
        assert normalize_event_title("\t\nteam\n\tstandup\t\n") == "Team Standup"
        assert normalize_event_title("   ") == ""

    def test_normalize_mixed_case(self):
        """Test normalization with mixed case."""
        assert normalize_event_title("MeEtInG wItH cLiEnT") == "Meeting With Client"
        assert normalize_event_title("tEaM sTaNdUp") == "Team Standup"

    def test_normalize_special_characters(self):
        """Test normalization preserves special characters."""
        assert normalize_event_title("client meeting - q4 review") == "Client Meeting - Q4 Review"
        assert normalize_event_title("team-building @ park") == "Team-Building @ Park"
        assert normalize_event_title("meeting (urgent)") == "Meeting (Urgent)"

    def test_normalize_numbers(self):
        """Test normalization with numbers."""
        assert normalize_event_title("sprint 2024 planning") == "Sprint 2024 Planning"
        assert normalize_event_title("q1 review meeting") == "Q1 Review Meeting"

    def test_normalize_empty_and_none(self):
        """Test normalization with empty and None values."""
        assert normalize_event_title("") == ""
        assert normalize_event_title("   \t\n   ") == ""

    def test_normalize_single_word(self):
        """Test normalization with single words."""
        assert normalize_event_title("meeting") == "Meeting"
        assert normalize_event_title("LUNCH") == "Lunch"
        assert normalize_event_title("break") == "Break"

    def test_normalize_apostrophes(self):
        """Test normalization with apostrophes."""
        assert normalize_event_title("client's quarterly review") == "Client'S Quarterly Review"
        assert normalize_event_title("team's standup meeting") == "Team'S Standup Meeting"


class TestIsValidDateString:
    """Tests for is_valid_date_string function."""

    def test_valid_date_strings(self):
        """Test valid date string formats."""
        valid_dates = [
            "2024-01-15",
            "2024-12-31",
            "2023-02-28",
            "2024-02-29",  # Leap year
            "2000-01-01",
            "1999-12-31",
        ]

        for date_str in valid_dates:
            assert is_valid_date_string(date_str), f"Should be valid: {date_str}"

    def test_invalid_date_strings(self):
        """Test invalid date string formats."""
        invalid_dates = [
            "2024-13-01",  # Invalid month
            "2024-01-32",  # Invalid day
            "2023-02-29",  # Not a leap year
            "24-01-15",  # Wrong year format
            "2024-1-15",  # Non-zero-padded month
            "2024-01-5",  # Non-zero-padded day
            "2024/01/15",  # Wrong separator
            "01-15-2024",  # Wrong order
            "2024-01-15 ",  # Trailing space
            " 2024-01-15",  # Leading space
            "2024-01-15T00:00:00",  # With time
            "",  # Empty string
            "invalid",  # Not a date
            "2024-01",  # Incomplete
            "2024-01-15-extra",  # Extra characters
        ]

        for date_str in invalid_dates:
            assert not is_valid_date_string(date_str), f"Should be invalid: {date_str}"

    def test_edge_case_dates(self):
        """Test edge case dates."""
        # Test year boundaries
        assert is_valid_date_string("0001-01-01")  # Minimum year for datetime
        assert is_valid_date_string("9999-12-31")  # Maximum year for datetime

        # Test month boundaries
        assert is_valid_date_string("2024-01-01")  # January
        assert is_valid_date_string("2024-12-31")  # December

        # Test day boundaries
        assert is_valid_date_string("2024-01-01")  # First day of month
        assert is_valid_date_string("2024-01-31")  # Last day of January
        assert is_valid_date_string("2024-02-29")  # Leap day

    def test_non_string_inputs(self):
        """Test non-string inputs."""
        non_string_inputs = [
            None,
            123,
            datetime(2024, 1, 15),
            ["2024-01-15"],
            {"date": "2024-01-15"},
        ]

        for input_val in non_string_inputs:
            assert not is_valid_date_string(input_val), f"Should be invalid: {input_val}"

    def test_leap_year_validation(self):
        """Test leap year date validation."""
        # Leap years
        assert is_valid_date_string("2000-02-29")  # Divisible by 400
        assert is_valid_date_string("2004-02-29")  # Divisible by 4
        assert is_valid_date_string("2024-02-29")  # Recent leap year

        # Non-leap years
        assert not is_valid_date_string("1900-02-29")  # Divisible by 100 but not 400
        assert not is_valid_date_string("2001-02-29")  # Not divisible by 4
        assert not is_valid_date_string("2023-02-29")  # Recent non-leap year

    def test_month_day_validation(self):
        """Test month and day boundary validation."""
        # Valid days for different months
        assert is_valid_date_string("2024-01-31")  # January has 31 days
        assert is_valid_date_string("2024-02-28")  # February has 28 days (non-leap)
        assert is_valid_date_string("2024-04-30")  # April has 30 days

        # Invalid days for different months
        assert not is_valid_date_string("2024-02-30")  # February doesn't have 30 days
        assert not is_valid_date_string("2024-04-31")  # April doesn't have 31 days
        assert not is_valid_date_string("2024-06-31")  # June doesn't have 31 days


class TestAppointmentsIntegration:
    """Integration tests for appointments module."""

    @pytest.mark.integration
    def test_complete_appointment_workflow(self):
        """Test complete workflow of creating and working with appointments."""
        # Create appointment with raw input
        raw_title = "  important    CLIENT meeting  "
        start_time = "2024-01-15T14:30:00"
        end_time = "2024-01-15T15:30:00"
        description = "Quarterly business review with key client"

        appointment = create_appointment(raw_title, start_time, end_time, description)

        # Verify normalization and parsing
        assert appointment.title == "Important Client Meeting"
        assert appointment.start_time == datetime(2024, 1, 15, 14, 30, 0)
        assert appointment.end_time == datetime(2024, 1, 15, 15, 30, 0)
        assert appointment.description == description

        # Verify appointment duration
        duration = appointment.end_time - appointment.start_time
        assert duration.total_seconds() == 3600  # 1 hour

    @pytest.mark.integration
    def test_appointment_list_operations(self):
        """Test operations on lists of appointments."""
        appointments = [
            create_appointment("Meeting 1", "2024-01-15T09:00:00", "2024-01-15T10:00:00"),
            create_appointment("Meeting 2", "2024-01-15T11:00:00", "2024-01-15T12:00:00"),
            create_appointment("Meeting 3", "2024-01-15T14:00:00", "2024-01-15T15:00:00"),
        ]

        # Test sorting by start time
        sorted_appointments = sorted(appointments, key=lambda a: a.start_time)
        assert sorted_appointments[0].title == "Meeting 1"
        assert sorted_appointments[1].title == "Meeting 2"
        assert sorted_appointments[2].title == "Meeting 3"

        # Test filtering by time
        afternoon_appointments = [a for a in appointments if a.start_time.hour >= 12]
        assert len(afternoon_appointments) == 1
        assert afternoon_appointments[0].title == "Meeting 3"

    @pytest.mark.boundary
    def test_extreme_datetime_values(self):
        """Test appointments with extreme datetime values."""
        # Very early date
        early_appointment = create_appointment(
            "Early Meeting", "0001-01-01T00:00:00", "0001-01-01T01:00:00"
        )
        assert early_appointment.start_time.year == 1

        # Very late date
        late_appointment = create_appointment(
            "Future Meeting", "9999-12-31T23:00:00", "9999-12-31T23:59:59"
        )
        assert late_appointment.start_time.year == 9999

        # Identical start and end times (zero-duration appointment)
        zero_duration_appointment = create_appointment(
            "Instant Meeting", "2024-06-01T12:00:00", "2024-06-01T12:00:00"
        )
        assert zero_duration_appointment.start_time == zero_duration_appointment.end_time
        assert zero_duration_appointment.title == "Instant Meeting"

    @pytest.mark.boundary
    def test_date_validation_edge_cases(self):
        """Test date validation with various edge cases."""
        # Test all months
        for month in range(1, 13):
            date_str = f"2024-{month:02d}-01"
            assert is_valid_date_string(date_str)

        # Test various days
        for day in range(1, 29):  # Safe range for all months
            date_str = f"2024-01-{day:02d}"
            assert is_valid_date_string(date_str)

        # Test year range
        for year in [1, 100, 1000, 2000, 9999]:
            date_str = f"{year:04d}-01-01"
            assert is_valid_date_string(date_str)
