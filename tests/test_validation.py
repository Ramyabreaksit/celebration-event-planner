"""Unit tests for user input validation and sanitization."""

import datetime
import pytest

from utils import sanitize_text, validate_event_inputs


def test_sanitize_text():
    """Verify that text sanitization strips whitespace and control characters."""
    assert sanitize_text("  Royal Palace  ") == "Royal Palace"
    assert sanitize_text(None) == ""
    assert sanitize_text("Hello\x00World") == "HelloWorld"
    long_str = "a" * 600
    assert len(sanitize_text(long_str, max_len=100)) == 100


def test_validate_event_inputs_valid():
    """Test standard valid inputs succeed without errors."""
    today = datetime.date(2026, 11, 15)
    future_date = datetime.date(2026, 12, 25)

    is_valid, errors = validate_event_inputs(
        event_type="Wedding",
        event_date=future_date,
        city="Bengaluru",
        guest_count=250,
        budget=500000.0,
        current_date=today,
    )
    assert is_valid is True
    assert len(errors) == 0


def test_validate_event_inputs_today_date():
    """Events planned for today should be valid."""
    today = datetime.date(2026, 11, 15)
    is_valid, errors = validate_event_inputs(
        event_type="Birthday Party",
        event_date=today,
        city="Mumbai",
        guest_count=50,
        budget=50000.0,
        current_date=today,
    )
    assert is_valid is True
    assert len(errors) == 0


def test_validate_event_inputs_past_date():
    """Events planned in the past must fail validation."""
    today = datetime.date(2026, 11, 15)
    past_date = datetime.date(2026, 10, 10)

    is_valid, errors = validate_event_inputs(
        event_type="Corporate Gala",
        event_date=past_date,
        city="Delhi",
        guest_count=100,
        budget=200000.0,
        current_date=today,
    )
    assert is_valid is False
    assert any("past" in err.lower() for err in errors)


def test_validate_event_inputs_zero_or_negative_budget():
    """Budget must be strictly greater than 0."""
    today = datetime.date(2026, 11, 15)

    # Zero budget
    is_valid, errors = validate_event_inputs(
        event_type="Baby Shower",
        event_date=today,
        city="Pune",
        guest_count=40,
        budget=0.0,
        current_date=today,
    )
    assert is_valid is False
    assert any("budget" in err.lower() for err in errors)

    # Negative budget
    is_valid_neg, errors_neg = validate_event_inputs(
        event_type="Baby Shower",
        event_date=today,
        city="Pune",
        guest_count=40,
        budget=-5000.0,
        current_date=today,
    )
    assert is_valid_neg is False
    assert any("budget" in err.lower() for err in errors_neg)


def test_validate_event_inputs_guest_count_bounds():
    """Guest count must be between 1 and 5000."""
    today = datetime.date(2026, 11, 15)

    # Zero guests
    is_valid, errors = validate_event_inputs(
        event_type="Dinner",
        event_date=today,
        city="Hyderabad",
        guest_count=0,
        budget=10000.0,
        current_date=today,
    )
    assert is_valid is False
    assert any("guest" in err.lower() for err in errors)

    # Over 5000 guests
    is_valid_high, errors_high = validate_event_inputs(
        event_type="Festival",
        event_date=today,
        city="Chennai",
        guest_count=5001,
        budget=5000000.0,
        current_date=today,
    )
    assert is_valid_high is False
    assert any("5,000" in err or "5000" in err for err in errors_high)

    # Upper boundary: exactly 5000 guests
    is_valid_5000, errors_5000 = validate_event_inputs(
        event_type="Mega Festival",
        event_date=today,
        city="Jaipur",
        guest_count=5000,
        budget=10000000.0,
        current_date=today,
    )
    assert is_valid_5000 is True


def test_validate_event_inputs_empty_strings():
    """Empty event type or city should trigger validation errors."""
    today = datetime.date(2026, 11, 15)

    is_valid, errors = validate_event_inputs(
        event_type="   ",
        event_date=today,
        city="",
        guest_count=50,
        budget=50000.0,
        current_date=today,
    )
    assert is_valid is False
    assert any("type is required" in err.lower() for err in errors)
    assert any("city" in err.lower() for err in errors)
