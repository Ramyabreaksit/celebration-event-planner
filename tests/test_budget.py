"""Unit tests for budget calculations, INR currency formatting, and RSVP metrics."""

import pytest

from utils import (
    calculate_budget_breakdown,
    calculate_per_head_metrics,
    calculate_rsvp_summary,
    format_inr,
)


def test_format_inr():
    """Verify standard Indian Rupee notation with comma placement."""
    assert format_inr(0) == "₹ 0"
    assert format_inr(500) == "₹ 500"
    assert format_inr(1500) == "₹ 1,500"
    assert format_inr(25000) == "₹ 25,000"
    assert format_inr(150000) == "₹ 1,50,000"
    assert format_inr(12500000) == "₹ 1,25,00,000"
    assert format_inr(100.5) == "₹ 100.50"
    assert format_inr(-500) == "-₹ 500"


def test_calculate_budget_breakdown_sum():
    """Budget category allocations must sum to the total budget and 100%."""
    total = 300000.0
    splits = calculate_budget_breakdown(total)

    total_allocated = sum(item["amount"] for item in splits)
    total_pct = sum(item["percentage"] for item in splits)

    assert round(total_pct, 1) == 100.0
    assert abs(total_allocated - total) < 1.0  # Within roundoff tolerance

    # Check key categories exist
    categories = [item["category"] for item in splits]
    assert "Venue & Logistics" in categories
    assert "Food & Beverages" in categories


def test_calculate_per_head_metrics():
    """Verify planned vs confirmed per head math."""
    total_budget = 100000.0
    planned_guests = 100
    confirmed_guests = 80

    metrics = calculate_per_head_metrics(total_budget, planned_guests, confirmed_guests)

    assert metrics["planned_per_head"] == 1000.0
    assert metrics["confirmed_per_head"] == 1250.0
    assert metrics["variance_per_head"] == 250.0
    assert "₹ 1,000" in metrics["formatted_planned_per_head"]
    assert "₹ 1,250" in metrics["formatted_confirmed_per_head"]


def test_calculate_per_head_metrics_zero_confirmed():
    """When zero guests have confirmed, confirmed per head should be zero without ZeroDivisionError."""
    total_budget = 50000.0
    planned_guests = 50
    confirmed_guests = 0

    metrics = calculate_per_head_metrics(total_budget, planned_guests, confirmed_guests)
    assert metrics["planned_per_head"] == 1000.0
    assert metrics["confirmed_per_head"] == 0.0
    assert metrics["variance_per_head"] == 0.0


def test_calculate_rsvp_summary():
    """Verify RSVP summary aggregator counts plus-ones and computes dietary stats."""
    sample_guests = [
        {"name": "Aarav Sharma", "status": "Confirmed", "plus_ones": 1, "dietary": "Vegetarian"},
        {"name": "Priya Patel", "status": "Confirmed", "plus_ones": 0, "dietary": "Vegetarian"},
        {"name": "Rohan Mehta", "status": "Confirmed", "plus_ones": 2, "dietary": "Non-Vegetarian"},
        {"name": "Neha Verma", "status": "Declined", "plus_ones": 1, "dietary": "Vegetarian"},
        {"name": "Karan Singh", "status": "Pending", "plus_ones": 0, "dietary": "Jain"},
    ]

    summary = calculate_rsvp_summary(sample_guests)

    assert summary["total_invited"] == 5
    assert summary["confirmed_count"] == 3
    assert summary["declined_count"] == 1
    assert summary["pending_count"] == 1

    # Total headcount: (1+1) + (1+0) + (1+2) = 6 attendees
    assert summary["total_headcount"] == 6

    # Confirmation rate: 3/5 = 60%
    assert summary["confirmation_rate"] == 60.0

    # Dietary breakdown
    diet_map = summary["dietary_breakdown"]
    assert diet_map["Vegetarian"] == 3  # Aarav + plus_one (2) + Priya (1) = 3
    assert diet_map["Non-Vegetarian"] == 3  # Rohan + 2 plus_ones = 3
