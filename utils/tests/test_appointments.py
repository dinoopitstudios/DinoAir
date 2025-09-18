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

        if appointment.title != "Meeting with Client":
            raise AssertionError
        if appointment.start_time != start_time:
            raise AssertionError
        if appointment.end_time != end_time:
            raise AssertionError
        if appointment.description != "Quarterly review meeting":
            raise AssertionError

    def test_appointment_default_description(self):
        """Test appointment with default empty description."""
        start_time = datetime(2024, 1, 15, 10, 30)
        end_time = datetime(2024, 1, 15, 11, 30)

        appointment = Appointment(title="Quick Call", start_time=start_time, end_time=end_time)

        if appointment.description != "":
            raise AssertionError

    def test_appointment_equality(self):
        """Test appointment equality comparison."""
        start_time = datetime(2024, 1, 15, 10, 30)
        end_time = datetime(2024, 1, 15, 11, 30)

        appointment1 = Appointment("Meeting", start_time, end_time, "Description")
        appointment2 = Appointment("Meeting", start_time, end_time, "Description")
        appointment3 = Appointment("Different Meeting", start_time, end_time, "Description")

        if appointment1 != appointment2:
            raise AssertionError
        if appointment1 == appointment3:
            raise AssertionError

    def test_appointment_repr(self):
        """Test appointment string representation."""
        start_time = datetime(2024, 1, 15, 10, 30)
        end_time = datetime(2024, 1, 15, 11, 30)

        appointment = Appointment("Test Meeting", start_time, end_time, "Test")

        repr_str = repr(appointment)
        if "Test Meeting" not in repr_str:
            raise AssertionError
        if "2024-01-15" not in repr_str:
            raise AssertionError


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

        if appointment.title != "Team Standup":
            raise AssertionError
        if appointment.start_time != datetime(2024, 1, 15, 9, 0, 0):
            raise AssertionError
        if appointment.end_time != datetime(2024, 1, 15, 9, 30, 0):
            raise AssertionError
        if appointment.description != "Daily team standup meeting":
            raise AssertionError

    def test_create_appointment_no_description(self):
        """Test appointment creation without description."""
        appointment = create_appointment(
            title="lunch break", start_time="2024-01-15T12:00:00", end_time="2024-01-15T13:00:00"
        )

        if appointment.title != "Lunch Break":
            raise AssertionError
        if appointment.description != "":
            raise AssertionError

    def test_create_appointment_with_timezone(self):
        """Test appointment creation with timezone-aware timestamps."""
        appointment = create_appointment(
            title="remote meeting",
            start_time="2024-01-15T09:00:00+00:00",
            end_time="2024-01-15T10:00:00+00:00",
            description="International team call",
        )

        if appointment.title != "Remote Meeting":
            raise AssertionError
        if appointment.start_time.year != 2024:
            raise AssertionError
        if appointment.start_time.month != 1:
            raise AssertionError
        if appointment.start_time.day != 15:
            raise AssertionError

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

        if appointment.start_time.microsecond != 123456:
            raise AssertionError
        if appointment.end_time.microsecond != 654321:
            raise AssertionError


class TestNormalizeEventTitle:
    """Tests for normalize_event_title function."""

    def test_normalize_basic_title(self):
        """Test basic title normalization."""
        if normalize_event_title("meeting with client") != "Meeting With Client":
            raise AssertionError
        if normalize_event_title("TEAM STANDUP") != "Team Standup":
            raise AssertionError
        if normalize_event_title("lunch break") != "Lunch Break":
            raise AssertionError

    def test_normalize_extra_whitespace(self):
        """Test normalization with extra whitespace."""
        if normalize_event_title("  meeting   with    client  ") != "Meeting With Client":
            raise AssertionError
        if normalize_event_title("\t\nteam\n\tstandup\t\n") != "Team Standup":
            raise AssertionError
        if normalize_event_title("   ") != "":
            raise AssertionError

    def test_normalize_mixed_case(self):
        """Test normalization with mixed case."""
        if normalize_event_title("MeEtInG wItH cLiEnT") != "Meeting With Client":
            raise AssertionError
        if normalize_event_title("tEaM sTaNdUp") != "Team Standup":
            raise AssertionError

    def test_normalize_special_characters(self):
        """Test normalization preserves special characters."""
        if normalize_event_title("client meeting - q4 review") != "Client Meeting - Q4 Review":
            raise AssertionError
        if normalize_event_title("team-building @ park") != "Team-Building @ Park":
            raise AssertionError
        if normalize_event_title("meeting (urgent)") != "Meeting (Urgent)":
            raise AssertionError

    def test_normalize_numbers(self):
        """Test normalization with numbers."""
        if normalize_event_title("sprint 2024 planning") != "Sprint 2024 Planning":
            raise AssertionError
        if normalize_event_title("q1 review meeting") != "Q1 Review Meeting":
            raise AssertionError

    def test_normalize_empty_and_none(self):
        """Test normalization with empty and None values."""
        if normalize_event_title("") != "":
            raise AssertionError
        if normalize_event_title("   \t\n   ") != "":
            raise AssertionError

    def test_normalize_single_word(self):
        """Test normalization with single words."""
        if normalize_event_title("meeting") != "Meeting":
            raise AssertionError
        if normalize_event_title("LUNCH") != "Lunch":
            raise AssertionError
        if normalize_event_title("break") != "Break":
            raise AssertionError

    def test_normalize_apostrophes(self):
        """Test normalization with apostrophes."""
        if normalize_event_title("client's quarterly review") != "Client'S Quarterly Review":
            raise AssertionError
        if normalize_event_title("team's standup meeting") != "Team'S Standup Meeting":
            raise AssertionError


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
            if not is_valid_date_string(date_str):
                raise AssertionError(f"Should be valid: {date_str}")

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
            if is_valid_date_string(date_str):
                raise AssertionError(f"Should be invalid: {date_str}")

    def test_edge_case_dates(self):
        """Test edge case dates."""
        # Test year boundaries
        if not is_valid_date_string("0001-01-01"):
            raise AssertionError
        if not is_valid_date_string("9999-12-31"):
            raise AssertionError

        # Test month boundaries
        if not is_valid_date_string("2024-01-01"):
            raise AssertionError
        if not is_valid_date_string("2024-12-31"):
            raise AssertionError

        # Test day boundaries
        if not is_valid_date_string("2024-01-01"):
            raise AssertionError
        if not is_valid_date_string("2024-01-31"):
            raise AssertionError
        if not is_valid_date_string("2024-02-29"):
            raise AssertionError

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
            if is_valid_date_string(input_val):
                raise AssertionError(f"Should be invalid: {input_val}")

    def test_leap_year_validation(self):
        """Test leap year date validation."""
        # Leap years
        if not is_valid_date_string("2000-02-29"):
            raise AssertionError
        if not is_valid_date_string("2004-02-29"):
            raise AssertionError
        if not is_valid_date_string("2024-02-29"):
            raise AssertionError

        # Non-leap years
        if is_valid_date_string("1900-02-29"):
            raise AssertionError
        if is_valid_date_string("2001-02-29"):
            raise AssertionError
        if is_valid_date_string("2023-02-29"):
            raise AssertionError

    def test_month_day_validation(self):
        """Test month and day boundary validation."""
        # Valid days for different months
        if not is_valid_date_string("2024-01-31"):
            raise AssertionError
        if not is_valid_date_string("2024-02-28"):
            raise AssertionError
        if not is_valid_date_string("2024-04-30"):
            raise AssertionError

        # Invalid days for different months
        if is_valid_date_string("2024-02-30"):
            raise AssertionError
        if is_valid_date_string("2024-04-31"):
            raise AssertionError
        if is_valid_date_string("2024-06-31"):
            raise AssertionError


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
        if appointment.title != "Important Client Meeting":
            raise AssertionError
        if appointment.start_time != datetime(2024, 1, 15, 14, 30, 0):
            raise AssertionError
        if appointment.end_time != datetime(2024, 1, 15, 15, 30, 0):
            raise AssertionError
        if appointment.description != description:
            raise AssertionError

        # Verify appointment duration
        duration = appointment.end_time - appointment.start_time
        if duration.total_seconds() != 3600:
            raise AssertionError

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
        if sorted_appointments[0].title != "Meeting 1":
            raise AssertionError
        if sorted_appointments[1].title != "Meeting 2":
            raise AssertionError
        if sorted_appointments[2].title != "Meeting 3":
            raise AssertionError

        # Test filtering by time
        afternoon_appointments = [a for a in appointments if a.start_time.hour >= 12]
        assert len(afternoon_appointments) == 1
        if afternoon_appointments[0].title != "Meeting 3":
            raise AssertionError

    @pytest.mark.boundary
    def test_extreme_datetime_values(self):
        """Test appointments with extreme datetime values."""
        # Very early date
        early_appointment = create_appointment(
            "Early Meeting", "0001-01-01T00:00:00", "0001-01-01T01:00:00"
        )
        if early_appointment.start_time.year != 1:
            raise AssertionError

        # Very late date
        late_appointment = create_appointment(
            "Future Meeting", "9999-12-31T23:00:00", "9999-12-31T23:59:59"
        )
        if late_appointment.start_time.year != 9999:
            raise AssertionError

        # Identical start and end times (zero-duration appointment)
        zero_duration_appointment = create_appointment(
            "Instant Meeting", "2024-06-01T12:00:00", "2024-06-01T12:00:00"
        )
        if zero_duration_appointment.start_time != zero_duration_appointment.end_time:
            raise AssertionError
        if zero_duration_appointment.title != "Instant Meeting":
            raise AssertionError

    @pytest.mark.boundary
    def test_date_validation_edge_cases(self):
        """Test date validation with various edge cases."""
        # Test all months
        for month in range(1, 13):
            date_str = f"2024-{month:02d}-01"
            if not is_valid_date_string(date_str):
                raise AssertionError

        # Test various days
        for day in range(1, 29):  # Safe range for all months
            date_str = f"2024-01-{day:02d}"
            if not is_valid_date_string(date_str):
                raise AssertionError

        # Test year range
        for year in [1, 100, 1000, 2000, 9999]:
            date_str = f"{year:04d}-01-01"
            if not is_valid_date_string(date_str):
                raise AssertionError
