"""AI Event Planner module powered by Google Gemini (google-generativeai).

Handles structured prompt generation, JSON schema validation,
caching with st.cache_data, error recovery, and interactive Q&A.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from utils import calculate_budget_breakdown, format_inr, sanitize_text

# Default Gemini models and fallback sequence
AVAILABLE_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest"]
DEFAULT_MODEL = "gemini-2.5-flash"


def get_model_fallback_chain(primary_model: str) -> List[str]:
    """Build candidate model order starting from primary_model followed by other available models.

    Args:
        primary_model: The user's selected Gemini model identifier.

    Returns:
        List of unique model strings in retry order.
    """
    chain = [primary_model]
    for m in AVAILABLE_MODELS:
        if m not in chain:
            chain.append(m)
    return chain


def get_gemini_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """Retrieve the Gemini API key from explicit input, st.secrets, or environment variable.

    Priority:
    1. Explicit key provided in parameters / UI.
    2. Streamlit secrets (st.secrets["GEMINI_API_KEY"]).
    3. Environment variable (os.environ["GEMINI_API_KEY"]).

    Args:
        explicit_key: Optional key directly passed in.

    Returns:
        The resolved API key string, or None if not found.
    """
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()

    # Try Streamlit secrets
    try:
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            key = st.secrets["GEMINI_API_KEY"]
            if key and str(key).strip():
                return str(key).strip()
    except Exception:
        pass

    # Try Environment variable
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    return None


def clean_json_string(raw_text: str) -> str:
    """Strip markdown code block wrappers and leading/trailing whitespace from JSON strings.

    Args:
        raw_text: Raw string returned by LLM.

    Returns:
        Clean JSON string ready for json.loads.
    """
    text = raw_text.strip()
    # Remove markdown code block fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def validate_and_normalize_plan(raw_plan: Dict[str, Any], total_budget: float) -> Dict[str, Any]:
    """Ensure all required sections are present and normalize budget allocations to total budget.

    Required keys:
    - concept_and_theme (title, tagline, description, color_palette, vibe, dress_code)
    - day_of_timeline (list of time, activity, details, owner)
    - budget_split (list of category, amount, percentage, notes)
    - task_checklist (list of deadline, task, category, tip)
    - menu_suggestions (dict of courses and item lists)
    - decor_ideas (dict of areas and item lists)
    - backup_plan (list of risk, mitigation)

    Args:
        raw_plan: Parsed JSON dict.
        total_budget: User's total budget in INR.

    Returns:
        Validated and normalized plan dictionary.
    """
    plan: Dict[str, Any] = {}

    # 1. Concept and theme
    concept = raw_plan.get("concept_and_theme", {})
    if not isinstance(concept, dict):
        concept = {}
    plan["concept_and_theme"] = {
        "title": concept.get("title", "Celebration Extravaganza"),
        "tagline": concept.get("tagline", "Unforgettable Moments, Masterfully Curated"),
        "description": concept.get("description", "A vibrant and joyful celebration thoughtfully planned to perfection."),
        "color_palette": concept.get("color_palette", ["Royal Gold", "Ivory White", "Blush Pink", "Sage Green"]),
        "vibe": concept.get("vibe", "Warm, Elegant & Energetic"),
        "dress_code": concept.get("dress_code", "Festive Traditional / Smart Casual"),
    }

    # 2. Budget Split
    budget_raw = raw_plan.get("budget_split", [])
    if isinstance(budget_raw, list) and len(budget_raw) > 0:
        total_pct = sum([float(item.get("percentage", 0)) for item in budget_raw]) or 100.0
        normalized_splits = []
        for item in budget_raw:
            cat = item.get("category", "General")
            pct = round((float(item.get("percentage", 10)) / total_pct) * 100, 1)
            amt = round(total_budget * (pct / 100.0), 2)
            normalized_splits.append({
                "category": cat,
                "percentage": pct,
                "amount": amt,
                "formatted_amount": format_inr(amt),
                "notes": item.get("notes", "Strategic budget allocation for optimum guest experience."),
            })
        plan["budget_split"] = normalized_splits
    else:
        # Fallback to standard baseline calculations
        defaults = calculate_budget_breakdown(total_budget)
        for d in defaults:
            d["notes"] = "Balanced baseline allocation"
        plan["budget_split"] = defaults

    # 3. Day of Timeline
    timeline_raw = raw_plan.get("day_of_timeline", [])
    if isinstance(timeline_raw, list) and len(timeline_raw) > 0:
        plan["day_of_timeline"] = timeline_raw
    else:
        plan["day_of_timeline"] = [
            {"time": "10:00 AM", "activity": "Vendor Setup & Venue Inspection", "details": "Decor, AV equipment and seating setup verified.", "owner": "Event Coordinator"},
            {"time": "04:00 PM", "activity": "F&B Prep & Sound Check", "details": "Catering team arrives, sound test and ambient lighting lit.", "owner": "Catering Lead & DJ"},
            {"time": "06:30 PM", "activity": "Guest Arrival & Welcome Refreshments", "details": "Welcome drinks, registration, and photo booth active.", "owner": "Reception Team"},
            {"time": "07:30 PM", "activity": "Main Ceremony / Key Highlight", "details": "Focal celebration activity, speeches, or felicitation.", "owner": "Emcee / Host"},
            {"time": "08:30 PM", "activity": "Dinner Banquet & Live Entertainment", "details": "Buffet opens, music performance or dance floor open.", "owner": "Host & DJ"},
            {"time": "10:30 PM", "activity": "Cake Cutting / Farewell & Return Favors", "details": "Sweet finale, vote of thanks, and distribution of return gifts.", "owner": "Host Family"},
        ]

    # 4. Task Checklist
    checklist_raw = raw_plan.get("task_checklist", [])
    if isinstance(checklist_raw, list) and len(checklist_raw) > 0:
        plan["task_checklist"] = checklist_raw
    else:
        plan["task_checklist"] = [
            {"deadline": "8 Weeks Before", "task": "Lock in Venue and Caterer", "category": "Booking", "tip": "Pay advance deposit and confirm vendor cancellation policies."},
            {"deadline": "6 Weeks Before", "task": "Finalize Guest List & Send Save-the-Dates", "category": "Guests", "tip": "Create digital invitations with RSVP deadlines."},
            {"deadline": "4 Weeks Before", "task": "Hire Photographer, Decorator & DJ", "category": "Vendors", "tip": "Share a mood board and favorite song/shot list."},
            {"deadline": "2 Weeks Before", "task": "Review RSVP Headcount & Finalize Menu", "category": "Catering", "tip": "Confirm exact dietary splits (veg, non-veg, Jain, vegan)."},
            {"deadline": "1 Week Before", "task": "Prepare Day-of Schedule & Assign Leads", "category": "Logistics", "tip": "Designate a trusted point of contact for vendor queries."},
            {"deadline": "1 Day Before", "task": "Final Venue Walkthrough & Favor Packing", "category": "Preparation", "tip": "Double check audio mics, projector, and emergency cash."},
            {"deadline": "Event Morning", "task": "Early Inspection & Sound Check", "category": "Execution", "tip": "Stay relaxed and hydrated; trust your designated team!"},
        ]

    # 5. Menu Suggestions
    menu_raw = raw_plan.get("menu_suggestions", {})
    if isinstance(menu_raw, dict) and len(menu_raw) > 0:
        plan["menu_suggestions"] = menu_raw
    else:
        plan["menu_suggestions"] = {
            "welcome_drinks": ["Fresh Mint Lime Cooler", "Spiced Mango Virgin Mojito"],
            "starters": ["Crispy Paneer Tikka / Chicken Malai Kebab", "Spinach Cheese Corn Cigars"],
            "main_course": ["Dal Makhani / Butter Chicken", "Paneer Butter Masala", "Assorted Naans & Rotis", "Dum Biryani with Burani Raita"],
            "desserts": ["Warm Gulab Jamun with Rabdi", "Artisan Kulfi & Fresh Fruit Tart"],
            "late_night_bites": ["Chai & Filter Coffee Station with Cookies"],
        }

    # 6. Decor Ideas
    decor_raw = raw_plan.get("decor_ideas", {})
    if isinstance(decor_raw, dict) and len(decor_raw) > 0:
        plan["decor_ideas"] = decor_raw
    else:
        plan["decor_ideas"] = {
            "entrance": ["Floral arch with warm fairy lights and custom welcome signage"],
            "stage_focal_area": ["Draped geometric backdrop with illuminated monogram / celebration theme banner"],
            "tables_and_seating": ["Low floral centerpieces with brass tea-light votives"],
            "photo_booth": ["Interactive selfie corner with customized handheld quirky props and neon sign"],
            "ambient_lighting": ["Warm amber uplighting and fairy light canopy across seating area"],
        }

    # 7. Backup Plan
    backup_raw = raw_plan.get("backup_plan", [])
    if isinstance(backup_raw, list) and len(backup_raw) > 0:
        plan["backup_plan"] = backup_raw
    else:
        plan["backup_plan"] = [
            {"risk": "Inclement Weather / Rain (for outdoor spaces)", "mitigation": "Ensure venue has a waterproof tent canopy or reserve an indoor banquet backup hall on standby."},
            {"risk": "Vendor Delay or No-Show", "mitigation": "Maintain secondary vendor contact list and complete contract sign-offs with penalty clauses 2 weeks prior."},
            {"risk": "Unexpected Guest Count Surge (+20%)", "mitigation": "Arrange catering buffer policy with venue (+10% food margin) and extra folding banquet chairs."},
            {"risk": "Power Outage or Audio Malfunction", "mitigation": "Verify venue backup generator automatic switchover and have 1 battery-powered Bluetooth PA speaker."},
            {"risk": "Medical / First-Aid Emergencies", "mitigation": "Keep a fully stocked first-aid kit, ORS sachets, pain relievers, and local emergency hospital numbers at desk."},
        ]

    return plan


def parse_gemini_json_response(raw_text: str, total_budget: float) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Parse and validate JSON response from Gemini.

    Args:
        raw_text: Raw response string from Gemini model.
        total_budget: User's total budget in INR.

    Returns:
        Tuple of (success: bool, validated_plan_dict or None, error_message: str).
    """
    if not raw_text or not raw_text.strip():
        return False, None, "Gemini returned an empty response. Please try again."

    cleaned_text = clean_json_string(raw_text)

    try:
        data = json.loads(cleaned_text)
    except json.JSONDecodeError as err:
        # Attempt to recover by locating the outermost braces
        brace_start = cleaned_text.find("{")
        brace_end = cleaned_text.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            try:
                data = json.loads(cleaned_text[brace_start : brace_end + 1])
            except Exception:
                return (
                    False,
                    None,
                    f"Could not parse AI response as valid JSON (JSON error: {err}). Please check your prompt or retry.",
                )
        else:
            return (
                False,
                None,
                f"Response did not contain a valid JSON object (JSON error: {err}). Please try again.",
            )

    if not isinstance(data, dict):
        return False, None, "Expected a JSON object from Gemini, but received a different data type."

    try:
        normalized = validate_and_normalize_plan(data, total_budget)
        return True, normalized, ""
    except Exception as exc:
        return False, None, f"Error validating plan structure: {str(exc)}"


def build_event_prompt(inputs: Dict[str, Any]) -> str:
    """Construct a comprehensive prompt for Gemini to generate the structured event plan.

    Args:
        inputs: Validated event input dictionary.

    Returns:
        Structured prompt string.
    """
    event_type = inputs.get("event_type", "Celebration")
    event_date = inputs.get("date", "Upcoming")
    city = inputs.get("city", "India")
    guests = inputs.get("guests", 100)
    budget = inputs.get("budget", 100000)
    theme = inputs.get("theme", "Celebratory and elegant")
    dietary = inputs.get("dietary", "Standard / Mixed")
    venue_type = inputs.get("venue_type", "Indoor / Outdoor")

    prompt = f"""You are an elite, highly experienced professional Celebration & Event Planner in India.
Create an exhaustive, highly practical, and culturally authentic end-to-end plan for the following event:

EVENT SPECIFICATIONS:
- Event Type: {event_type}
- Event Date: {event_date}
- Location / City: {city}
- Expected Guest Count: {guests}
- Total Budget: INR {budget:,.2f} (₹{budget})
- Theme & Aesthetic Preferences: {theme}
- Dietary Requirements: {dietary}
- Venue Setting: {venue_type}

REQUIREMENTS:
Return ONLY a valid JSON object (no markdown surrounding, or within ```json ```) with EXACTLY this structure:
{{
  "concept_and_theme": {{
    "title": "Creative and catchy title for the celebration",
    "tagline": "Inspiring one-line tagline",
    "description": "Comprehensive 2-3 paragraph explanation of the creative concept, flow, and unique touches",
    "color_palette": ["Color 1", "Color 2", "Color 3", "Color 4"],
    "vibe": "Mood and energy description (e.g., Royal, intimate, high-energy)",
    "dress_code": "Recommended attire for guests"
  }},
  "day_of_timeline": [
    {{
      "time": "e.g., 04:00 PM",
      "activity": "Activity name",
      "details": "Specific actions, vendor readiness, and guest flow",
      "owner": "Who is responsible (e.g., Host, Event Coordinator, DJ, Caterer)"
    }}
  ],
  "budget_split": [
    {{
      "category": "Venue & Infrastructure",
      "percentage": 35.0,
      "amount": {round(budget * 0.35, 2)},
      "notes": "Cost rationale and realistic vendors in {city}"
    }},
    {{
      "category": "Food & Beverages",
      "percentage": 30.0,
      "amount": {round(budget * 0.30, 2)},
      "notes": "Catering per plate breakdown for {guests} guests based on {dietary}"
    }},
    {{
      "category": "Decor & Ambience",
      "percentage": 15.0,
      "amount": {round(budget * 0.15, 2)},
      "notes": "Floral, lighting, stage and signage specifics matching theme '{theme}'"
    }},
    {{
      "category": "Entertainment & Photography",
      "percentage": 12.0,
      "amount": {round(budget * 0.12, 2)},
      "notes": "DJ, Emcee, candid photographer, and video highlights"
    }},
    {{
      "category": "Miscellaneous & Contingency",
      "percentage": 8.0,
      "amount": {round(budget * 0.08, 2)},
      "notes": "Permits, emergency cash, staff tips, and transportation"
    }}
  ],
  "task_checklist": [
    {{
      "deadline": "e.g., 8 Weeks Before",
      "task": "Task description",
      "category": "Venue / Vendor / Guests / Logistics",
      "tip": "Practical insider pro tip to save money or avoid delays"
    }}
  ],
  "menu_suggestions": {{
    "welcome_drinks": ["Drink 1", "Drink 2"],
    "starters": ["Starter 1", "Starter 2", "Starter 3"],
    "main_course": ["Dish 1", "Dish 2", "Dish 3", "Bread/Rice item"],
    "desserts": ["Dessert 1", "Dessert 2"],
    "special_dietary_options": ["Option tailored for {dietary}"]
  }},
  "decor_ideas": {{
    "entrance": ["Entrance idea 1", "Entrance idea 2"],
    "stage_or_focal_area": ["Focal element 1", "Focal element 2"],
    "table_settings": ["Table styling 1", "Table styling 2"],
    "lighting_and_ambience": ["Lighting feature 1", "Lighting feature 2"],
    "photo_booth_and_extras": ["Photo spot idea 1", "Interactive element 2"]
  }},
  "backup_plan": [
    {{
      "risk": "Risk scenario (e.g., Rain/weather, Vendor no-show, Guest count surge)",
      "mitigation": "Actionable, concrete contingency protocol"
    }}
  ]
}}

Ensure realistic numbers tailored for {city}, {guests} guests, and total INR {budget}. Provide at least 5 timeline steps, at least 6 checklist milestones counting backwards from {event_date}, and at least 4 backup risk contingency plans.
"""
    return prompt


def generate_plan_gemini(
    event_inputs: Dict[str, Any],
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_MODEL,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Invoke Gemini API using google-generativeai to produce the validated event plan.

    If the requested model returns 404 (e.g. retired or unavailable), it automatically
    retries with the next model in the fallback sequence.

    Args:
        event_inputs: Validated event input parameters.
        api_key: Optional Gemini API key.
        model_name: Model identifier (default: gemini-2.5-flash).

    Returns:
        Tuple of (success: bool, plan_dict or None, user_friendly_message: str).
    """
    resolved_key = get_gemini_api_key(api_key)
    if not resolved_key:
        return (
            False,
            None,
            "🔑 Gemini API Key is missing. Please provide your key in the sidebar, or set GEMINI_API_KEY in .streamlit/secrets.toml or your .env file.",
        )

    if genai is None:
        return (
            False,
            None,
            "The 'google-generativeai' package is not installed. Please install it with `pip install google-generativeai`.",
        )

    genai.configure(api_key=resolved_key)
    candidate_models = get_model_fallback_chain(model_name)
    last_error_msg = ""

    for idx, current_model in enumerate(candidate_models):
        try:
            model = genai.GenerativeModel(
                model_name=current_model,
                generation_config={"response_mime_type": "application/json", "temperature": 0.4},
            )
            prompt = build_event_prompt(event_inputs)
            response = model.generate_content(prompt)

            if not response or not hasattr(response, "text") or not response.text:
                return (
                    False,
                    None,
                    "Gemini did not return any content. The request may have been blocked or interrupted by safety filters.",
                )

            success, parsed_plan, error_msg = parse_gemini_json_response(
                response.text, total_budget=float(event_inputs.get("budget", 0))
            )
            return success, parsed_plan, error_msg

        except Exception as exc:
            err_str = str(exc)
            err_lower = err_str.lower()
            is_404 = (
                "404" in err_str
                or "not found" in err_lower
                or "notfound" in err_lower
                or "modelnotfounderror" in err_lower
            )

            # If 404 occurred and we have fallback models left, automatically retry
            if is_404 and (idx + 1 < len(candidate_models)):
                continue

            if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
                last_error_msg = "❌ The provided Gemini API Key is invalid. Please double-check your key in Google AI Studio."
            elif "ResourceExhausted" in err_str or "429" in err_str or "quota" in err_lower:
                last_error_msg = "⏳ Gemini API quota reached or rate-limited. Please wait a minute before requesting another plan."
            elif is_404:
                last_error_msg = (
                    f"⚠️ Model '{current_model}' returned 404 (not found). "
                    f"Tried fallback models: {', '.join(candidate_models)}. Please check model availability in your region."
                )
            else:
                last_error_msg = f"⚠️ Gemini API connection issue: {err_str}"

    return False, None, last_error_msg


@st.cache_data(show_spinner=False)
def cached_generate_event_plan(
    event_type: str,
    date_str: str,
    city: str,
    guests: int,
    budget: float,
    theme: str,
    dietary: str,
    venue_type: str,
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_MODEL,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Cached wrapper around generate_plan_gemini.

    Caches repeated API calls with st.cache_data so users do not burn API quotas
    when reviewing identical celebration setups.
    """
    inputs = {
        "event_type": event_type,
        "date": date_str,
        "city": city,
        "guests": guests,
        "budget": budget,
        "theme": theme,
        "dietary": dietary,
        "venue_type": venue_type,
    }
    return generate_plan_gemini(inputs, api_key=api_key, model_name=model_name)


def chat_with_planner(
    messages: List[Dict[str, str]],
    user_query: str,
    plan_context: Dict[str, Any],
    event_inputs: Dict[str, Any],
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_MODEL,
) -> str:
    """Respond to follow-up questions from the user in 'Ask the Planner' chat.

    Maintains conversational context and grounds all answers in the generated event plan.
    Automatically retries with fallback models if a 404 is encountered.

    Args:
        messages: Conversation history list of {'role': 'user'|'assistant', 'content': '...'}.
        user_query: The latest user question.
        plan_context: The active event plan dictionary.
        event_inputs: Original event parameters.
        api_key: Optional Gemini API key.
        model_name: Model identifier.

    Returns:
        The planner's response string.
    """
    resolved_key = get_gemini_api_key(api_key)
    if not resolved_key:
        return "🔑 Gemini API key is required to chat with the planner. Please enter your API key in the sidebar."

    if genai is None:
        return "The google-generativeai library is required for the chat assistant."

    genai.configure(api_key=resolved_key)

    system_instruction = f"""You are the head event planner for a {event_inputs.get('event_type', 'Celebration')} in {event_inputs.get('city', 'India')}.
Key Plan Parameters:
- Total Budget: INR {event_inputs.get('budget', 0):,.2f}
- Guest Count: {event_inputs.get('guests', 0)}
- Date: {event_inputs.get('date', 'Upcoming')}
- Theme: {event_inputs.get('theme', 'Celebration')}
- Dietary: {event_inputs.get('dietary', 'Mixed')}
- Venue Setting: {event_inputs.get('venue_type', 'Indoor/Outdoor')}

Plan Details in Memory:
- Concept: {plan_context.get('concept_and_theme', {}).get('title', '')} - {plan_context.get('concept_and_theme', {}).get('tagline', '')}
- Budget Breakdown: {json.dumps(plan_context.get('budget_split', []))}
- Timeline Highlights: {json.dumps(plan_context.get('day_of_timeline', [])[:3])}
- Menu Highlights: {json.dumps(plan_context.get('menu_suggestions', {}))}

Instructions:
- Provide specific, culturally resonant, budget-conscious, practical advice.
- When suggesting cost savings, recommend specific trade-offs (e.g. seasonal flowers, local snacks, digital invites).
- Keep answers concise, warm, highly structured with bullet points where helpful.
"""

    # Construct conversation prompt
    prompt_parts = [system_instruction, "\nConversation History:"]
    for m in messages[-6:]:  # Keep recent context
        role = "User" if m["role"] == "user" else "Planner"
        prompt_parts.append(f"{role}: {m['content']}")

    prompt_parts.append(f"User: {user_query}")
    prompt_parts.append("Planner:")
    full_prompt = "\n".join(prompt_parts)

    candidate_models = get_model_fallback_chain(model_name)
    last_exc = None

    for idx, current_model in enumerate(candidate_models):
        try:
            model = genai.GenerativeModel(model_name=current_model)
            response = model.generate_content(full_prompt)
            return response.text if response and response.text else "I could not generate an answer at this moment. Please ask again."
        except Exception as exc:
            err_str = str(exc)
            err_lower = err_str.lower()
            is_404 = (
                "404" in err_str
                or "not found" in err_lower
                or "notfound" in err_lower
                or "modelnotfounderror" in err_lower
            )
            if is_404 and (idx + 1 < len(candidate_models)):
                continue
            last_exc = exc
            break

    return f"⚠️ Chat assistant encountered an error: {str(last_exc)}"

