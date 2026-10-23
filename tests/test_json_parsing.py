"""Unit tests for Gemini structured JSON response parsing, schema validation, and normalization."""

import json
import pytest

from planner import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    clean_json_string,
    get_model_fallback_chain,
    parse_gemini_json_response,
    validate_and_normalize_plan,
)


def test_clean_json_string():
    """Verify markdown code fence stripping."""
    raw_markdown = """```json
    {
      "key": "value"
    }
    ```"""
    cleaned = clean_json_string(raw_markdown)
    assert cleaned.startswith("{")
    assert cleaned.endswith("}")

    # No fence
    raw_plain = '{"hello": "world"}'
    assert clean_json_string(raw_plain) == '{"hello": "world"}'


def test_parse_gemini_json_response_success():
    """Test standard valid JSON parsing and structure normalization."""
    valid_payload = {
        "concept_and_theme": {
            "title": "Starlight Sangeet",
            "tagline": "An evening of rhythm and romance",
            "description": "Magical outdoor evening celebration with fairy lights.",
            "color_palette": ["Midnight Blue", "Champagne Gold"],
            "vibe": "Joyful, musical",
            "dress_code": "Indo-Western Glitz",
        },
        "day_of_timeline": [
            {"time": "05:00 PM", "activity": "Welcome Reception", "details": "Guests arrive", "owner": "Host"},
            {"time": "07:00 PM", "activity": "Sangeet Dance Performances", "details": "Choreographed routines", "owner": "DJ & Emcee"},
        ],
        "budget_split": [
            {"category": "Venue", "percentage": 40.0, "amount": 80000, "notes": "Lawn rent"},
            {"category": "Food & Beverage", "percentage": 60.0, "amount": 120000, "notes": "Catering"},
        ],
        "task_checklist": [
            {"deadline": "4 Weeks Before", "task": "Book DJ", "category": "Music", "tip": "Verify sound limits"},
        ],
        "menu_suggestions": {
            "starters": ["Dahi Kebab", "Paneer Tikka"],
            "main_course": ["Paneer Pasanda", "Dal Makhani", "Naan"],
        },
        "decor_ideas": {
            "entrance": ["Fairy light tunnel"],
        },
        "backup_plan": [
            {"risk": "Rain", "mitigation": "Banquet hall standby"},
        ],
    }

    raw_text = f"```json\n{json.dumps(valid_payload)}\n```"
    success, plan, error = parse_gemini_json_response(raw_text, total_budget=200000.0)

    assert success is True
    assert error == ""
    assert plan is not None
    assert plan["concept_and_theme"]["title"] == "Starlight Sangeet"
    assert len(plan["budget_split"]) == 2
    # Verify budget was normalized properly
    assert sum(item["amount"] for item in plan["budget_split"]) == 200000.0


def test_parse_gemini_json_response_malformed():
    """Malformed JSON should gracefully fail with a helpful error message."""
    broken_text = "{ this is not valid json at all ... "
    success, plan, error = parse_gemini_json_response(broken_text, total_budget=100000.0)

    assert success is False
    assert plan is None
    assert "JSON error" in error or "valid JSON" in error


def test_parse_gemini_json_response_empty():
    """Empty or whitespace response should be rejected."""
    success, plan, error = parse_gemini_json_response("   ", total_budget=50000.0)
    assert success is False
    assert "empty" in error.lower()


def test_validate_and_normalize_plan_fallback():
    """When optional sections are missing from raw JSON, defaults should be populated."""
    incomplete_json = {
        "concept_and_theme": {
            "title": "Minimalist Anniversary",
        }
    }
    normalized = validate_and_normalize_plan(incomplete_json, total_budget=150000.0)

    assert normalized["concept_and_theme"]["title"] == "Minimalist Anniversary"
    # Fallback sections should exist
    assert "budget_split" in normalized
    assert len(normalized["budget_split"]) > 0
    assert "day_of_timeline" in normalized
    assert len(normalized["day_of_timeline"]) > 0
    assert "task_checklist" in normalized
    assert "menu_suggestions" in normalized
    assert "decor_ideas" in normalized
    assert "backup_plan" in normalized

    # Sum of budget split amounts must equal total budget
    total_split_amount = sum(item["amount"] for item in normalized["budget_split"])
    assert abs(total_split_amount - 150000.0) < 1.0


def test_model_constants_and_fallback_chain():
    """Verify that default model is gemini-2.5-flash and fallback chain is ordered properly."""
    assert DEFAULT_MODEL == "gemini-2.5-flash"
    assert "gemini-2.5-flash" in AVAILABLE_MODELS
    assert "gemini-2.5-flash-lite" in AVAILABLE_MODELS
    assert "gemini-flash-latest" in AVAILABLE_MODELS

    # Primary model first, remaining models follow
    chain = get_model_fallback_chain("gemini-2.5-flash")
    assert chain[0] == "gemini-2.5-flash"
    assert "gemini-2.5-flash-lite" in chain
    assert "gemini-flash-latest" in chain

    # If user selected gemini-2.5-flash-lite, it should be attempted first
    chain_lite = get_model_fallback_chain("gemini-2.5-flash-lite")
    assert chain_lite[0] == "gemini-2.5-flash-lite"
    assert len(chain_lite) == len(AVAILABLE_MODELS)

