"""Celebration & Event Planner — Streamlit Web Application.

A comprehensive AI-powered celebration management platform built with Python,
Streamlit, and Google Gemini.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List

import altair as alt
import pandas as pd
import streamlit as st

from planner import (
    cached_generate_event_plan,
    chat_with_planner,
    generate_plan_gemini,
    get_gemini_api_key,
    validate_and_normalize_plan,
)
from utils import (
    calculate_budget_breakdown,
    calculate_per_head_metrics,
    calculate_rsvp_summary,
    format_inr,
    generate_plan_markdown,
    generate_plan_pdf,
    sanitize_text,
    validate_event_inputs,
)

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Celebration & Event Planner",
    page_icon="🎉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-Contrast, Accessible CSS
st.markdown(
    """
    <style>
    /* High-contrast accessible styling */
    .main-header {
        background: linear-gradient(135deg, #1E1B4B 0%, #312E81 50%, #4338CA 100%);
        padding: 24px 32px;
        border-radius: 12px;
        color: #FFFFFF !important;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: #FFFFFF !important;
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 6px;
    }
    .main-header p {
        color: #E0E7FF !important;
        font-size: 1.05rem;
        margin-bottom: 0;
    }
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-left: 5px solid #4F46E5;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-card-alert {
        background-color: #FEF2F2;
        border: 1px solid #FECACA;
        border-left: 5px solid #DC2626;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 14px;
    }
    .metric-title {
        color: #475569;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        color: #0F172A;
        font-size: 1.6rem;
        font-weight: 700;
        margin: 4px 0;
    }
    .metric-sub {
        color: #64748B;
        font-size: 0.85rem;
    }
    .color-chip {
        display: inline-block;
        padding: 4px 12px;
        margin: 4px 6px 4px 0;
        border-radius: 16px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid #CBD5E1;
        background-color: #F1F5F9;
        color: #0F172A;
    }
    .timeline-badge {
        background-color: #EEF2FF;
        color: #3730A3;
        font-weight: 700;
        padding: 4px 8px;
        border-radius: 6px;
        border: 1px solid #C7D2FE;
    }
    .badge-confirmed {
        background-color: #DCFCE7;
        color: #166534;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 12px;
    }
    .badge-declined {
        background-color: #FEE2E2;
        color: #991B1B;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 12px;
    }
    .badge-pending {
        background-color: #FEF3C7;
        color: #92400E;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 12px;
    }
    /* Ensure inputs have high contrast focus borders */
    input:focus, select:focus, textarea:focus {
        border-color: #4F46E5 !important;
        box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_session_state() -> None:
    """Initialize session state variables."""
    if "event_plan" not in st.session_state:
        st.session_state.event_plan = None
    if "event_inputs" not in st.session_state:
        st.session_state.event_inputs = {}
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "guests" not in st.session_state:
        # Initial sample guests for demonstration
        st.session_state.guests = [
            {"name": "Ananya Sharma", "contact": "ananya@example.com", "status": "Confirmed", "plus_ones": 1, "dietary": "Vegetarian"},
            {"name": "Vikram Malhotra", "contact": "+91 98765 43210", "status": "Confirmed", "plus_ones": 0, "dietary": "Non-Vegetarian"},
            {"name": "Rohan & Riya Desai", "contact": "rohan.d@example.com", "status": "Confirmed", "plus_ones": 2, "dietary": "Jain"},
            {"name": "Sunita Rao", "contact": "sunita@example.com", "status": "Declined", "plus_ones": 0, "dietary": "Vegetarian"},
            {"name": "Karan Singhania", "contact": "+91 91234 56789", "status": "Pending", "plus_ones": 1, "dietary": "Standard / Mixed"},
        ]
    if "task_status" not in st.session_state:
        st.session_state.task_status = {}


init_session_state()

# ---------------------------------------------------------
# SIDEBAR: Configuration & API Key Setup
# ---------------------------------------------------------
with st.sidebar:
    st.image(
        "https://images.unsplash.com/photo-1511795409834-ef04bbd61622?auto=format&fit=crop&w=400&q=80",
        caption="Curate Unforgettable Celebrations",
        use_column_width=True,
    )
    st.markdown("### 🔑 API Configuration")

    detected_key = get_gemini_api_key()
    api_key_input = st.text_input(
        "Gemini API Key",
        value=detected_key or "",
        type="password",
        help="Reads automatically from st.secrets or GEMINI_API_KEY env var. You can also paste it here directly.",
        placeholder="AIzaSy...",
    )

    if detected_key:
        st.success("✅ Gemini API Key detected and active", icon="🔐")
    else:
        st.info("💡 Enter your key above, or set `GEMINI_API_KEY` in `.env` or `.streamlit/secrets.toml`.", icon="ℹ️")

    model_option = st.selectbox(
        "Gemini Model",
        options=["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest"],
        index=0,
        help="Fast and reliable generation tailored for structured event planning (with auto-fallback).",
    )

    st.markdown("---")
    st.markdown("### ♿ Accessibility & Tips")
    st.markdown(
        """
        - **WCAG High Contrast**: Optimized color palette for readability.
        - **Multi-sensory cues**: Text labels alongside status icons.
        - **Currency**: All figures presented in Indian Rupees (₹).
        """
    )
    st.markdown("---")
    if st.button("🔄 Reset Event Data & Form", help="Clears current plan and inputs", use_container_width=True):
        st.session_state.event_plan = None
        st.session_state.event_inputs = {}
        st.session_state.chat_messages = []
        st.session_state.task_status = {}
        st.rerun()

# ---------------------------------------------------------
# MAIN BANNER
# ---------------------------------------------------------
st.markdown(
    """
    <div class="main-header">
        <h1>🎉 Celebration & Event Planner</h1>
        <p>End-to-End Intelligent Event Architect — From Inspiring Idea to Seamless Execution</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# FEATURE 1: EVENT INPUT FORM
# ---------------------------------------------------------
st.subheader("1. Tell Us About Your Celebration", divider="violet")

with st.form("event_input_form", clear_on_submit=False):
    col1, col2, col3 = st.columns([1.2, 1, 1])

    with col1:
        event_types = [
            "Birthday Party",
            "Wedding Ceremony & Reception",
            "Baby Shower (Godh Bharai)",
            "Festival Celebration (Diwali, Holi, Eid, Christmas)",
            "College Farewell / Reunion",
            "Corporate Gala / Annual Party",
            "Anniversary Celebration",
            "Housewarming (Griha Pravesh)",
            "Other Celebration",
        ]
        selected_type = st.selectbox(
            "Event Type *",
            options=event_types,
            index=0,
            help="Select the occasion you are celebrating.",
        )
        custom_type = ""
        if selected_type == "Other Celebration":
            custom_type = st.text_input(
                "Specify Event Type *",
                placeholder="e.g. Graduation Dinner, Startup Launch",
                help="Enter custom event category",
            )

        city_options = [
            "Mumbai",
            "Bengaluru",
            "Delhi NCR",
            "Hyderabad",
            "Chennai",
            "Kolkata",
            "Pune",
            "Jaipur",
            "Goa",
            "Ahmedabad",
            "Chandigarh",
            "Other City",
        ]
        selected_city = st.selectbox(
            "Host City / Location *",
            options=city_options,
            index=1,
            help="Select or enter the city where the celebration will take place.",
        )
        custom_city = ""
        if selected_city == "Other City":
            custom_city = st.text_input("Enter City Name *", placeholder="e.g. Udaipur, Kochi, Lucknow")

    with col2:
        today_date = datetime.date.today()
        default_event_date = today_date + datetime.timedelta(days=30)
        event_date = st.date_input(
            "Event Date *",
            value=default_event_date,
            min_value=today_date,
            help="Select celebration date. Dates in the past are not allowed.",
        )

        guest_count = st.number_input(
            "Expected Guest Count (1 - 5,000) *",
            min_value=1,
            max_value=5000,
            value=80,
            step=5,
            help="Total anticipated attendees including family and friends.",
        )

        venue_type = st.selectbox(
            "Venue Setting *",
            options=["Indoor Banquet / Hall", "Outdoor Lawn / Terrace", "Hybrid (Indoor & Outdoor)", "Beach / Resort", "Home / Private Space"],
            index=0,
            help="Physical layout of your venue.",
        )

    with col3:
        budget = st.number_input(
            "Total Budget (INR ₹) *",
            min_value=1000.0,
            max_value=500000000.0,
            value=250000.0,
            step=5000.0,
            format="%.2f",
            help="Comprehensive planned expenditure in Indian Rupees (₹).",
        )

        dietary_needs = st.selectbox(
            "Primary Dietary Requirements *",
            options=[
                "Vegetarian & Non-Vegetarian (Mixed)",
                "Pure Vegetarian",
                "Jain Vegetarian (No root vegetables)",
                "Vegan / Plant-based Friendly",
                "Halal Friendly",
                "Gluten-Free & Allergy Conscious",
            ],
            index=0,
            help="Dietary profile for menu planning.",
        )

        budget_per_head_preview = budget / max(1, guest_count)
        st.markdown(
            f"""
            <div style="background-color: #EEF2FF; border: 1px solid #C7D2FE; padding: 10px; border-radius: 6px; margin-top: 8px;">
                <span style="color: #3730A3; font-size: 0.82rem; font-weight: 600;">PLANNED PER-HEAD BUDGET</span><br>
                <b style="color: #1E1B4B; font-size: 1.2rem;">{format_inr(budget_per_head_preview)}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

    theme_preferences = st.text_area(
        "Theme, Aesthetic & Special Preferences",
        value="Royal floral elegance with pastel peach and ivory tones, live acoustic music, memorable photo booth, and vibrant return gifts.",
        help="Describe special traditions, color palettes, musical preferences, or key moments.",
        height=75,
    )

    form_col1, form_col2 = st.columns([1, 1])
    with form_col1:
        submit_plan = st.form_submit_button("✨ Generate AI Event Plan", type="primary", use_container_width=True)
    with form_col2:
        load_demo_plan = st.form_submit_button("💡 Explore Sample Celebration Plan", use_container_width=True)


# Determine Effective Inputs
final_event_type = custom_type if selected_type == "Other Celebration" and custom_type else selected_type
final_city = custom_city if selected_city == "Other City" and custom_city else selected_city

# Handle Form Submissions
if submit_plan or load_demo_plan:
    is_valid, validation_errors = validate_event_inputs(
        event_type=final_event_type,
        event_date=event_date,
        city=final_city,
        guest_count=guest_count,
        budget=budget,
    )

    if not is_valid:
        for err in validation_errors:
            st.error(f"⚠️ {err}", icon="🚨")
    else:
        st.session_state.event_inputs = {
            "event_type": sanitize_text(final_event_type),
            "date": event_date.strftime("%Y-%m-%d"),
            "city": sanitize_text(final_city),
            "guests": int(guest_count),
            "budget": float(budget),
            "theme": sanitize_text(theme_preferences),
            "dietary": dietary_needs,
            "venue_type": venue_type,
        }

        if load_demo_plan:
            with st.spinner("Generating curated demonstration plan..."):
                demo_data = {
                    "concept_and_theme": {
                        "title": f"The Grand {final_event_type} Soirée",
                        "tagline": "A Symphony of Elegance, Warmth, and Joyful Memories",
                        "description": (
                            f"An enchanting {final_event_type.lower()} celebration curated for {guest_count} cherished guests in {final_city}. "
                            "Balancing opulent Indian hospitality with contemporary aesthetic flair, the evening transitions from warm welcoming ceremonies "
                            "to vibrant feast and dancing under ambient canopy lighting."
                        ),
                        "color_palette": ["Royal Ivory", "Champagne Gold", "Pastel Peach", "Emerald Foliage"],
                        "vibe": "Warm, Sophisticated, and High-Energy",
                        "dress_code": "Festive Indian Glam / Smart Cocktail Attire",
                    },
                    "day_of_timeline": [
                        {"time": "02:00 PM", "activity": "Vendor Setup & Floral Styling", "details": "Stage backdrop, lighting rigging, and table centerpieces prepared.", "owner": "Decor Team Lead"},
                        {"time": "04:30 PM", "activity": "Sound Check & Technical Run", "details": "Microphones tested, DJ playlist pre-loaded, ambient lighting warmed up.", "owner": "AV & DJ Team"},
                        {"time": "06:30 PM", "activity": "Welcome Reception & Live Mocktails", "details": "Guests arrive, welcomed with rose petal shower and signature coolers.", "owner": "Host Reception Team"},
                        {"time": "07:30 PM", "activity": "Focal Celebration & Speeches", "details": "Key ceremonial moments, cake cutting or felicitation, photo highlights.", "owner": "Emcee & Host Family"},
                        {"time": "08:30 PM", "activity": "Grand Banquet Feast & DJ Floor", "details": "Multi-course dinner buffet opens, dance floor opens with curated playlist.", "owner": "Catering Lead & DJ"},
                        {"time": "11:00 PM", "activity": "Vote of Thanks & Return Favors", "details": "Warm parting words, distribution of artisan return favors, farewell.", "owner": "Hosts"},
                    ],
                    "budget_split": [
                        {"category": "Venue & Infrastructure", "percentage": 35.0, "amount": round(budget * 0.35, 2), "notes": f"Banquet hall rental, air conditioning, and premium guest parking in {final_city}."},
                        {"category": "Food & Beverages", "percentage": 30.0, "amount": round(budget * 0.30, 2), "notes": f"Full course buffet with welcome drinks and desserts ({dietary_needs})."},
                        {"category": "Decor & Ambience", "percentage": 15.0, "amount": round(budget * 0.15, 2), "notes": "Focal stage, entrance arch, table floral arrangements, and mood lighting."},
                        {"category": "Entertainment & Photography", "percentage": 12.0, "amount": round(budget * 0.12, 2), "notes": "Candid photographer, traditional videographer, sound system and DJ."},
                        {"category": "Miscellaneous & Contingency", "percentage": 8.0, "amount": round(budget * 0.08, 2), "notes": "Staff gratuities, permits, emergency fund, and return favors."},
                    ],
                    "task_checklist": [
                        {"deadline": "8 Weeks Before", "task": f"Finalize & book venue in {final_city}", "category": "Booking", "tip": "Verify power backup and catering exclusivity rules."},
                        {"deadline": "6 Weeks Before", "task": "Design & distribute digital invitations with RSVP link", "category": "Guests", "tip": "Request dietary preferences on the invitation form."},
                        {"deadline": "4 Weeks Before", "task": "Lock in Caterer, Photographer, and DJ", "category": "Vendors", "tip": "Conduct a food tasting session before finalizing menu."},
                        {"deadline": "2 Weeks Before", "task": "Audit RSVP responses and confirm final plate count", "category": "Catering", "tip": "Include a +5% buffer with caterer to avoid shortages."},
                        {"deadline": "1 Week Before", "task": "Share day-of timeline with all vendor leads", "category": "Logistics", "tip": "Create a vendor coordination WhatsApp group."},
                        {"deadline": "1 Day Before", "task": "Pack return gifts and review audio equipment", "category": "Preparation", "tip": "Keep emergency contact numbers handy."},
                        {"deadline": "Event Morning", "task": "Inspect venue setup and test microphones", "category": "Execution", "tip": "Take a moment to relax and celebrate!"},
                    ],
                    "menu_suggestions": {
                        "welcome_drinks": ["Saffron Kesar Badam Milk", "Chilled Mint Lychee Mojito", "Fresh Coconut Water"],
                        "appetizers": ["Paneer Tikka with Mint Chutney", "Crispy Lotus Stem in Sweet Chilli", "Tandoori Chicken / Galouti Kebab"],
                        "main_course": ["Dal Makhani Slow-cooked 24 hrs", "Paneer Lababdar", "Hyderabadi Dum Biryani with Mirchi ka Salan", "Assorted Butter Naans & Laccha Parathas"],
                        "desserts": ["Hot Gulab Jamun with Malai Rabdi", "Pistachio Kulfi", "Fresh Seasonal Fruit Fondue"],
                        "late_night_station": ["Kullhad Chai & Masala Filter Coffee with Khari"],
                    },
                    "decor_ideas": {
                        "entrance": ["Grand floral tunnel with brass urlis and floating marigolds & tea lights"],
                        "stage_and_focal_area": ["Backlit geometric arch adorned with peach garden roses and fairy fairy canopies"],
                        "table_settings": ["Mirror centerpieces with brass candle votives and linen napkins"],
                        "photo_booth": ["Quirky customized neon sign with floral frame and vintage props"],
                        "ambient_lighting": ["Warm amber spot lamps and golden fairy light ceilings"],
                    },
                    "backup_plan": [
                        {"risk": "Sudden Rain or Stormy Weather", "mitigation": "Venue has an indoor banquet hall ready on standby, and waterproof tenting covered for reception area."},
                        {"risk": "Vendor Delay or Emergency Absence", "mitigation": "Retain secondary vendor contact list with 1-hour dispatch SLA; contracts have strict delivery milestones."},
                        {"risk": "Unexpected Guest Count Surge (+15%)", "mitigation": "Caterer agreed on 10% instant buffet replenishment buffer; venue has 25 extra folding chairs in reserve."},
                        {"risk": "Power Outage or Audio Feedback Failure", "mitigation": "Dual generator switchgear tested; portable high-output battery speaker on standby behind stage."},
                    ],
                }
                st.session_state.event_plan = validate_and_normalize_plan(demo_data, budget)
                st.success("🎉 Curated sample event plan loaded successfully! Explore the tabs below.", icon="✅")
        else:
            active_key = api_key_input.strip() if api_key_input else detected_key
            if not active_key:
                st.warning(
                    "🔑 Please enter your Gemini API Key in the sidebar to generate an AI plan, "
                    "or click 'Explore Sample Celebration Plan' for an instant demonstration.",
                    icon="🔐",
                )
            else:
                with st.spinner("🤖 Gemini AI is architecting your custom celebration plan..."):
                    success, plan_res, error_msg = cached_generate_event_plan(
                        event_type=st.session_state.event_inputs["event_type"],
                        date_str=st.session_state.event_inputs["date"],
                        city=st.session_state.event_inputs["city"],
                        guests=st.session_state.event_inputs["guests"],
                        budget=st.session_state.event_inputs["budget"],
                        theme=st.session_state.event_inputs["theme"],
                        dietary=st.session_state.event_inputs["dietary"],
                        venue_type=st.session_state.event_inputs["venue_type"],
                        api_key=active_key,
                        model_name=model_option,
                    )
                    if success and plan_res:
                        st.session_state.event_plan = plan_res
                        st.success("🎉 AI Celebration Plan generated successfully!", icon="✅")
                    else:
                        st.error(error_msg, icon="❌")

# ---------------------------------------------------------
# PRESENTATION OF PLAN & TRACKER TABS
# ---------------------------------------------------------
plan = st.session_state.event_plan
inputs = st.session_state.event_inputs

if plan is not None:
    st.markdown("<br>", unsafe_allow_html=True)

    tab_overview, tab_budget, tab_timeline, tab_menu_decor, tab_tasks, tab_rsvp, tab_chat, tab_download = st.tabs([
        "🎨 Concept & Overview",
        "💰 Budget & Charts",
        "⏰ Day-of Timeline",
        "🍽️ Menu & Decor",
        "✅ Task Checklist",
        "👥 RSVP & Headcount Tracker",
        "💬 Ask the Planner",
        "📥 Download Plan",
    ])

    # -----------------------------------------------------
    # TAB 1: CONCEPT & OVERVIEW
    # -----------------------------------------------------
    with tab_overview:
        concept = plan.get("concept_and_theme", {})
        st.subheader(concept.get("title", "Celebration Concept"), divider="violet")
        st.caption(f"✨ *{concept.get('tagline', '')}*")

        st.markdown(f"**Concept Overview:**\n\n{concept.get('description', '')}")

        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            st.markdown("#### 🎨 Color Palette")
            colors = concept.get("color_palette", [])
            for c in colors:
                st.markdown(f"<span class='color-chip'>● {c}</span>", unsafe_allow_html=True)
        with col_c2:
            st.markdown("#### 🌟 Atmosphere & Vibe")
            st.info(concept.get("vibe", "Joyous & Elegant"), icon="✨")
        with col_c3:
            st.markdown("#### 👗 Recommended Dress Code")
            st.success(concept.get("dress_code", "Festive"), icon="👔")

        st.markdown("---")
        st.markdown("#### 🛡️ Contingency & Risk Management Plan")
        backup_items = plan.get("backup_plan", [])
        if backup_items:
            for b in backup_items:
                if isinstance(b, dict):
                    with st.expander(f"⚠️ Risk: {b.get('risk', 'Contingency')}", expanded=True):
                        st.markdown(f"**Action Protocol:** {b.get('mitigation', 'N/A')}")
                else:
                    st.write(f"- {b}")

    # -----------------------------------------------------
    # TAB 2: BUDGET SPLIT & CHARTS
    # -----------------------------------------------------
    with tab_budget:
        st.subheader("💰 Categorical Budget Allocation", divider="violet")

        total_b = inputs.get("budget", 250000.0)
        guests_cnt = inputs.get("guests", 80)
        planned_head_cost = total_b / max(1, guests_cnt)

        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">TOTAL BUDGET</div>
                    <div class="metric-value">{format_inr(total_b)}</div>
                    <div class="metric-sub">Allocated across all celebration verticals</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m_col2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">PLANNED GUESTS</div>
                    <div class="metric-value">{guests_cnt}</div>
                    <div class="metric-sub">Target attendance headcount</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m_col3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">BUDGET PER HEAD</div>
                    <div class="metric-value">{format_inr(planned_head_cost)}</div>
                    <div class="metric-sub">Target investment per attendee</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        budget_splits = plan.get("budget_split", [])
        df_budget = pd.DataFrame(budget_splits)

        if not df_budget.empty:
            b_chart_col, b_table_col = st.columns([1.1, 1.3])

            with b_chart_col:
                st.markdown("#### Budget Distribution Chart")
                # Altair Donut Chart
                chart = (
                    alt.Chart(df_budget)
                    .mark_arc(innerRadius=60, stroke="#FFFFFF", strokeWidth=2)
                    .encode(
                        theta=alt.Theta(field="amount", type="quantitative"),
                        color=alt.Color(
                            field="category",
                            type="nominal",
                            scale=alt.Scale(
                                range=["#4F46E5", "#0D9488", "#E11D48", "#F59E0B", "#8B5CF6", "#0284C7"]
                            ),
                            legend=alt.Legend(title="Category", orient="bottom", columns=2),
                        ),
                        tooltip=[
                            alt.Tooltip("category", title="Category"),
                            alt.Tooltip("percentage", title="Percentage (%)"),
                            alt.Tooltip("amount", title="Amount (INR)", format=",.2f"),
                        ],
                    )
                    .properties(height=320)
                )
                st.altair_chart(chart, use_container_width=True)

            with b_table_col:
                st.markdown("#### Category Breakdown Table")
                display_df = df_budget[["category", "percentage", "formatted_amount", "notes"]].copy()
                display_df.columns = ["Category", "Share (%)", "Amount (INR)", "Strategic Notes"]
                st.dataframe(display_df, use_container_width=True, hide_index=True)

    # -----------------------------------------------------
    # TAB 3: DAY-OF TIMELINE
    # -----------------------------------------------------
    with tab_timeline:
        st.subheader("⏰ Day-of Timeline & Run of Show", divider="violet")
        st.markdown("Keep vendors, hosts, and coordinators perfectly aligned on the big day.")

        timeline_items = plan.get("day_of_timeline", [])
        if timeline_items:
            for item in timeline_items:
                col_t1, col_t2 = st.columns([1, 4])
                with col_t1:
                    st.markdown(f"<span class='timeline-badge'>⏰ {item.get('time', '-')}</span>", unsafe_allow_html=True)
                    st.caption(f"**Owner:** {item.get('owner', 'Coordinator')}")
                with col_t2:
                    st.markdown(f"**{item.get('activity', 'Activity')}**")
                    st.markdown(f"{item.get('details', '')}")
                st.divider()

    # -----------------------------------------------------
    # TAB 4: MENU & DECOR
    # -----------------------------------------------------
    with tab_menu_decor:
        col_m, col_d = st.columns(2)

        with col_m:
            st.subheader("🍽️ Curated Menu", divider="violet")
            menu = plan.get("menu_suggestions", {})
            if isinstance(menu, dict):
                for course, dishes in menu.items():
                    course_name = course.replace("_", " ").title()
                    st.markdown(f"#### {course_name}")
                    if isinstance(dishes, list):
                        for dish in dishes:
                            st.markdown(f"- {dish}")
                    else:
                        st.markdown(f"- {dishes}")
                    st.markdown("<br>", unsafe_allow_html=True)

        with col_d:
            st.subheader("✨ Decor & Aesthetic Blueprint", divider="violet")
            decor = plan.get("decor_ideas", {})
            if isinstance(decor, dict):
                for area, ideas in decor.items():
                    area_name = area.replace("_", " ").title()
                    st.markdown(f"#### {area_name}")
                    if isinstance(ideas, list):
                        for idea in ideas:
                            st.markdown(f"- {idea}")
                    else:
                        st.markdown(f"- {ideas}")
                    st.markdown("<br>", unsafe_allow_html=True)

    # -----------------------------------------------------
    # TAB 5: TASK CHECKLIST
    # -----------------------------------------------------
    with tab_tasks:
        st.subheader("✅ Preparation Milestones & Countdown", divider="violet")
        st.markdown("Track countdown tasks leading up to the celebration.")

        tasks = plan.get("task_checklist", [])
        if tasks:
            completed_count = sum(
                1 for i in range(len(tasks)) if st.session_state.task_status.get(f"task_{i}", False)
            )
            progress_val = completed_count / len(tasks)
            st.progress(progress_val, text=f"Progress: {completed_count} of {len(tasks)} milestones completed ({int(progress_val * 100)}%)")
            st.markdown("<br>", unsafe_allow_html=True)

            for i, task_item in enumerate(tasks):
                t_key = f"task_{i}"
                is_checked = st.session_state.task_status.get(t_key, False)

                t_col1, t_col2 = st.columns([0.8, 5])
                with t_col1:
                    checked = st.checkbox(
                        label=task_item.get("deadline", f"Step {i+1}"),
                        value=is_checked,
                        key=t_key,
                        help="Mark milestone as completed",
                    )
                    st.session_state.task_status[t_key] = checked
                with t_col2:
                    strike = "~~" if checked else ""
                    st.markdown(f"{strike}**{task_item.get('task', '')}**{strike}")
                    st.caption(f"🏷️ Category: {task_item.get('category', 'General')} | 💡 Pro-Tip: {task_item.get('tip', '-')}")
                st.divider()

    # -----------------------------------------------------
    # TAB 6: GUEST LIST & RSVP TRACKER
    # -----------------------------------------------------
    with tab_rsvp:
        st.subheader("👥 Guest List & RSVP Headcount Tracker", divider="violet")
        st.markdown("Track responses, plus-ones, and monitor real-time headcount against your budget per head.")

        # Compute RSVP summary
        rsvp_summary = calculate_rsvp_summary(st.session_state.guests)
        total_invited = rsvp_summary["total_invited"]
        confirmed_headcount = rsvp_summary["total_headcount"]

        # Calculate live per-head metrics
        per_head = calculate_per_head_metrics(
            total_budget=inputs.get("budget", 250000.0),
            planned_guests=inputs.get("guests", 80),
            confirmed_guests=confirmed_headcount,
        )

        r_col1, r_col2, r_col3, r_col4 = st.columns(4)
        with r_col1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">TOTAL INVITED</div>
                    <div class="metric-value">{total_invited}</div>
                    <div class="metric-sub">Primary invitees</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with r_col2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">CONFIRMED HEADCOUNT</div>
                    <div class="metric-value">{confirmed_headcount}</div>
                    <div class="metric-sub">Attendees (incl. plus-ones)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with r_col3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">PLANNED PER HEAD</div>
                    <div class="metric-value">{per_head['formatted_planned_per_head']}</div>
                    <div class="metric-sub">Based on {inputs.get('guests', 80)} target guests</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with r_col4:
            # Check if confirmed headcount exceeds planned guests
            is_over_capacity = confirmed_headcount > inputs.get("guests", 80)
            card_class = "metric-card-alert" if is_over_capacity else "metric-card"
            st.markdown(
                f"""
                <div class="{card_class}">
                    <div class="metric-title">ACTUAL BUDGET / HEAD</div>
                    <div class="metric-value">{per_head['formatted_confirmed_per_head']}</div>
                    <div class="metric-sub">{'⚠️ Exceeds planned capacity!' if is_over_capacity else 'Active confirmed expenditure'}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if is_over_capacity:
            st.warning(
                f"⚠️ **Headcount Alert**: Confirmed attendees ({confirmed_headcount}) exceed your planned guest limit ({inputs.get('guests', 80)}). "
                "Consider increasing catering buffer or reviewing seating layout in the Backup Plan.",
                icon="⚠️",
            )

        # Dietary distribution chips
        diet_breakdown = rsvp_summary.get("dietary_breakdown", {})
        if diet_breakdown:
            st.markdown("##### 🥗 Confirmed Dietary Preferences Breakdown:")
            diet_pills = " &nbsp;|&nbsp; ".join([f"**{k}:** {v} guests" for k, v in diet_breakdown.items()])
            st.info(f"📋 {diet_pills}")

        st.markdown("---")

        # Add New Guest Form
        with st.expander("➕ Add New Guest", expanded=False):
            with st.form("add_guest_form", clear_on_submit=True):
                g_col1, g_col2, g_col3 = st.columns(3)
                with g_col1:
                    new_name = st.text_input("Guest Name *", placeholder="e.g. Ramesh Gupta", help="Full name of primary invitee")
                    new_contact = st.text_input("Contact Email / Phone", placeholder="+91 ... or email", help="Optional contact details")
                with g_col2:
                    new_status = st.selectbox("RSVP Status *", ["Confirmed", "Pending", "Declined"], index=0, help="Current response status")
                    new_plus_ones = st.number_input("Plus-Ones / Family Members", min_value=0, max_value=20, value=0, help="Additional attendees joining this guest")
                with g_col3:
                    new_diet = st.selectbox("Dietary Preference", ["Vegetarian", "Non-Vegetarian", "Jain", "Vegan", "Standard / Mixed", "Gluten-Free"], index=0)
                    st.markdown("<br>", unsafe_allow_html=True)
                    submit_guest = st.form_submit_button("Add to Guest List", type="primary", use_container_width=True)

                if submit_guest:
                    if not new_name.strip():
                        st.error("Please enter a valid guest name.")
                    else:
                        st.session_state.guests.append({
                            "name": sanitize_text(new_name),
                            "contact": sanitize_text(new_contact),
                            "status": new_status,
                            "plus_ones": int(new_plus_ones),
                            "dietary": new_diet,
                        })
                        st.success(f"Added {new_name} to the guest list!")
                        st.rerun()

        # Display Guest Table
        if st.session_state.guests:
            guest_rows = []
            for idx, g in enumerate(st.session_state.guests):
                stat = g.get("status", "Pending")
                icon_stat = "✅ Confirmed" if stat == "Confirmed" else ("❌ Declined" if stat == "Declined" else "⏳ Pending")
                guest_rows.append({
                    "Index": idx + 1,
                    "Name": g.get("name"),
                    "Contact": g.get("contact", "-"),
                    "Status": icon_stat,
                    "Plus-Ones": g.get("plus_ones", 0),
                    "Total Group": 1 + g.get("plus_ones", 0) if stat == "Confirmed" else 0,
                    "Dietary": g.get("dietary", "Standard"),
                })

            df_guests = pd.DataFrame(guest_rows)
            st.dataframe(df_guests, use_container_width=True, hide_index=True)

            # Export Guests CSV
            csv_data = df_guests.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Guest List (CSV)",
                data=csv_data,
                file_name="celebration_guests.csv",
                mime="text/csv",
                help="Export current guest list and RSVP status as CSV file.",
            )

    # -----------------------------------------------------
    # TAB 7: ASK THE PLANNER (CHAT)
    # -----------------------------------------------------
    with tab_chat:
        st.subheader("💬 Ask the Planner", divider="violet")
        st.markdown(
            "Have follow-up questions? Ask about vendor negotiations, menu tweaks, song recommendations, or budget optimization."
        )

        # Quick question prompt buttons
        st.markdown("**Quick Inquiries:**")
        q_cols = st.columns(4)
        quick_questions = [
            "How can I cut 15% from decor costs without losing elegance?",
            "Suggest 5 trending entrance songs for our celebration.",
            "What return favors under ₹300 per head fit this theme?",
            "How should we organize seating for our confirmed guests?",
        ]
        user_query_override = None
        for i, q_text in enumerate(quick_questions):
            with q_cols[i]:
                if st.button(f"💡 {q_text[:32]}...", key=f"quick_q_{i}", help=q_text, use_container_width=True):
                    user_query_override = q_text

        # Display conversation history
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat Input
        chat_prompt = st.chat_input("Ask a question about your celebration plan...") or user_query_override

        if chat_prompt:
            st.session_state.chat_messages.append({"role": "user", "content": chat_prompt})
            with st.chat_message("user"):
                st.markdown(chat_prompt)

            active_key = api_key_input.strip() if api_key_input else detected_key
            with st.chat_message("assistant"):
                with st.spinner("Event planner is preparing tailored advice..."):
                    if not active_key:
                        reply = (
                            "🔑 Please provide your Gemini API key in the sidebar to chat live with the planner. "
                            "In the meantime, you can explore the generated tabs above!"
                        )
                    else:
                        reply = chat_with_planner(
                            messages=st.session_state.chat_messages,
                            user_query=chat_prompt,
                            plan_context=plan,
                            event_inputs=inputs,
                            api_key=active_key,
                            model_name=model_option,
                        )
                    st.markdown(reply)
                    st.session_state.chat_messages.append({"role": "assistant", "content": reply})

    # -----------------------------------------------------
    # TAB 8: DOWNLOAD FINAL PLAN
    # -----------------------------------------------------
    with tab_download:
        st.subheader("📥 Export & Download Your Event Blueprint", divider="violet")
        st.markdown("Download your comprehensive plan to share with vendors, co-hosts, and family members.")

        rsvp_sum = calculate_rsvp_summary(st.session_state.guests)
        md_content = generate_plan_markdown(plan, inputs, rsvp_summary=rsvp_sum)
        pdf_bytes = generate_plan_pdf(plan, inputs, rsvp_summary=rsvp_sum)

        col_d1, col_d2 = st.columns(2)

        with col_d1:
            st.markdown("#### 📄 Document Plan (.PDF)")
            st.markdown(
                "A beautifully formatted, high-contrast PDF document complete with overview cards, budget breakdown tables, day-of timeline, menu, and risk protocols."
            )
            st.download_button(
                label="📥 Download Event Plan (PDF)",
                data=pdf_bytes,
                file_name=f"{inputs.get('event_type', 'Celebration').replace(' ', '_')}_Plan.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                help="Download full plan as a printable PDF",
            )

        with col_d2:
            st.markdown("#### 📝 Markdown / Text Plan (.TXT)")
            st.markdown(
                "Plain structured markdown document ready to paste into Google Docs, Notion, or send via email to family and team members."
            )
            st.download_button(
                label="📥 Download Plan (Markdown / Text)",
                data=md_content,
                file_name=f"{inputs.get('event_type', 'Celebration').replace(' ', '_')}_Plan.md",
                mime="text/markdown",
                use_container_width=True,
                help="Download full plan as formatted markdown",
            )

        st.markdown("---")
        with st.expander("👀 Live Document Preview (Markdown Format)", expanded=False):
            st.markdown(md_content)

else:
    # Empty State Guidance
    st.info(
        "👈 Fill out the event specifications above and click **'Generate AI Event Plan'** or **'Explore Sample Celebration Plan'** to begin!",
        icon="🎈",
    )
    st.markdown(
        """
        ### What this planner generates:
        - 🎨 **Creative Concept & Theme**: Authentic storytelling, color palette, dress code, and atmospheric vibe.
        - 💰 **Strategic Budget Breakdown**: Dynamic table & Altair donut chart allocating every rupee realistically.
        - ⏰ **Day-Of Timeline**: Run-of-show schedule with designated owners from setup to farewell.
        - 🍽️ **Curated Menu & Decor Ideas**: Multi-course culinary suggestions matching dietary needs and styling ideas.
        - ✅ **Countdown Task Checklist**: Actionable milestone checklist counting backwards from event date.
        - 🛡️ **Risk Contingency Protocol**: Practical backup strategies for weather, vendor delays, and guest surges.
        - 👥 **Guest List & RSVP Tracker**: Headcount analytics against planned budget per head.
        - 💬 **Interactive Chat Assistant**: Grounded advice for cost-cutting, vendor negotiations, and music playlists.
        """
    )
