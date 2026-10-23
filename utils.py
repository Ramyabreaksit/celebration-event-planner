"""Utility functions for Celebration & Event Planner.

Includes input validation, budget calculations, RSVP metrics,
and export generation (Markdown and PDF).
"""

from __future__ import annotations

import datetime
import html
import io
import re
from typing import Any, Dict, List, Optional, Tuple


def sanitize_text(text: Optional[str], max_len: int = 500) -> str:
    """Sanitize user text input by stripping whitespace and capping length.

    Args:
        text: Raw user string input.
        max_len: Maximum permitted characters.

    Returns:
        Sanitized text string.
    """
    if not text:
        return ""
    cleaned = text.strip()
    # Strip any potential null bytes or control characters
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)
    return cleaned[:max_len]


def validate_event_inputs(
    event_type: str,
    event_date: Any,
    city: str,
    guest_count: int,
    budget: float,
    current_date: Optional[datetime.date] = None,
) -> Tuple[bool, List[str]]:
    """Validate all event planning input parameters.

    Rules:
    - Event type cannot be empty.
    - Event date cannot be in the past.
    - City cannot be empty.
    - Guest count must be between 1 and 5000 inclusive.
    - Total budget must be strictly greater than 0 INR.

    Args:
        event_type: Type of event (e.g. Birthday, Wedding).
        event_date: Target date for the event.
        city: City where event takes place.
        guest_count: Expected number of attendees.
        budget: Total planned budget in INR.
        current_date: Reference current date (defaults to today).

    Returns:
        A tuple of (is_valid: bool, error_messages: list of strings).
    """
    errors: List[str] = []

    # 1. Event Type
    clean_type = sanitize_text(event_type, 100)
    if not clean_type:
        errors.append("Event type is required. Please select or enter an event type.")

    # 2. Date Validation
    if current_date is None:
        current_date = datetime.date.today()

    if not isinstance(event_date, (datetime.date, datetime.datetime)):
        errors.append("Invalid event date provided.")
    else:
        target_date = event_date.date() if isinstance(event_date, datetime.datetime) else event_date
        if target_date < current_date:
            errors.append(
                f"Event date ({target_date.strftime('%d-%b-%Y')}) cannot be in the past. "
                f"Please choose a date on or after today ({current_date.strftime('%d-%b-%Y')})."
            )

    # 3. City
    clean_city = sanitize_text(city, 100)
    if not clean_city:
        errors.append("City / location is required. Please specify where the celebration will take place.")

    # 4. Guest Count
    try:
        guest_int = int(guest_count)
        if guest_int < 1:
            errors.append("Guest count must be at least 1 guest.")
        elif guest_int > 5000:
            errors.append("Guest count cannot exceed 5,000 attendees.")
    except (ValueError, TypeError):
        errors.append("Guest count must be a valid integer between 1 and 5,000.")

    # 5. Budget Validation
    try:
        budget_float = float(budget)
        if budget_float <= 0:
            errors.append("Total budget must be strictly greater than ₹ 0.")
    except (ValueError, TypeError):
        errors.append("Total budget must be a valid positive number.")

    is_valid = len(errors) == 0
    return is_valid, errors


def format_inr(amount: float) -> str:
    """Format a monetary amount in Indian Rupee (INR) representation.

    Example:
        150000 -> "₹ 1,50,000"
        25500.5 -> "₹ 25,500.50"

    Args:
        amount: Numerical amount in INR.

    Returns:
        Formatted INR string.
    """
    try:
        val = float(amount)
    except (ValueError, TypeError):
        return "₹ 0"

    is_negative = val < 0
    val = abs(val)

    # Separate integer and decimal portions
    dec_part = f"{val:.2f}".split(".")[1]
    int_str = str(int(val))

    if len(int_str) <= 3:
        formatted_int = int_str
    else:
        last_three = int_str[-3:]
        remaining = int_str[:-3]
        # In Indian numbering system, comma separates every 2 digits after last 3
        groups = []
        while remaining:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        groups.reverse()
        formatted_int = ",".join(groups) + "," + last_three

    result = f"₹ {formatted_int}"
    if dec_part != "00":
        result += f".{dec_part}"

    return f"-{result}" if is_negative else result


def calculate_budget_breakdown(
    total_budget: float,
    custom_splits: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """Compute standard categorical budget allocations in INR.

    Default baseline:
    - Venue: 35%
    - Food & Beverage: 30%
    - Decor & Styling: 15%
    - Entertainment & Photography: 12%
    - Miscellaneous & Contingency: 8%

    Args:
        total_budget: Total budget in INR.
        custom_splits: Optional dictionary mapping category to percentage (0-100).

    Returns:
        List of category dictionaries with name, percentage, allocated INR, and formatted text.
    """
    if custom_splits is None:
        custom_splits = {
            "Venue & Logistics": 35.0,
            "Food & Beverages": 30.0,
            "Decor & Ambience": 15.0,
            "Entertainment & Media": 12.0,
            "Miscellaneous & Contingency": 8.0,
        }

    # Normalize percentages to 100%
    total_pct = sum(custom_splits.values()) or 100.0
    breakdown = []

    for category, pct in custom_splits.items():
        normalized_pct = round((pct / total_pct) * 100, 1)
        allocated_amount = round(total_budget * (normalized_pct / 100.0), 2)
        breakdown.append({
            "category": category,
            "percentage": normalized_pct,
            "amount": allocated_amount,
            "formatted_amount": format_inr(allocated_amount),
        })

    return breakdown


def calculate_per_head_metrics(
    total_budget: float,
    planned_guests: int,
    confirmed_guests: int,
) -> Dict[str, Any]:
    """Calculate per-head expenditure and variance comparing planned vs confirmed.

    Args:
        total_budget: Total planned budget.
        planned_guests: Expected guest count from initial inputs.
        confirmed_guests: Actual confirmed attendee count from RSVP tracker.

    Returns:
        Dictionary with planned per head, confirmed per head, variance, and formatted strings.
    """
    safe_planned = max(1, planned_guests)
    safe_confirmed = max(0, confirmed_guests)

    planned_per_head = round(total_budget / safe_planned, 2)
    confirmed_per_head = round(total_budget / safe_confirmed, 2) if safe_confirmed > 0 else 0.0
    variance_per_head = round(confirmed_per_head - planned_per_head, 2) if safe_confirmed > 0 else 0.0

    return {
        "planned_guests": safe_planned,
        "confirmed_guests": safe_confirmed,
        "planned_per_head": planned_per_head,
        "confirmed_per_head": confirmed_per_head,
        "variance_per_head": variance_per_head,
        "formatted_planned_per_head": format_inr(planned_per_head),
        "formatted_confirmed_per_head": format_inr(confirmed_per_head),
        "formatted_variance_per_head": format_inr(variance_per_head),
    }


def calculate_rsvp_summary(guests: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate summary statistics from the guest list.

    Args:
        guests: List of guest dicts with 'status', 'plus_ones', 'dietary', etc.

    Returns:
        Summary dict containing counts of invited, confirmed, declined, pending,
        total confirmed headcount (primary + plus-ones), and dietary breakdown.
    """
    total_invited = len(guests)
    confirmed_count = 0
    declined_count = 0
    pending_count = 0
    total_headcount = 0  # Confirmed guests + their confirmed plus-ones
    dietary_counts: Dict[str, int] = {}

    for g in guests:
        status = str(g.get("status", "Pending")).capitalize()
        plus_ones = int(g.get("plus_ones", 0) or 0)
        diet = str(g.get("dietary", "Standard / Mixed")).strip()

        if status == "Confirmed":
            confirmed_count += 1
            attending_group = 1 + max(0, plus_ones)
            total_headcount += attending_group
            dietary_counts[diet] = dietary_counts.get(diet, 0) + attending_group
        elif status == "Declined":
            declined_count += 1
        else:
            pending_count += 1

    confirmation_rate = round((confirmed_count / total_invited * 100), 1) if total_invited > 0 else 0.0

    return {
        "total_invited": total_invited,
        "confirmed_count": confirmed_count,
        "declined_count": declined_count,
        "pending_count": pending_count,
        "total_headcount": total_headcount,
        "confirmation_rate": confirmation_rate,
        "dietary_breakdown": dietary_counts,
    }


def generate_plan_markdown(
    plan: Dict[str, Any],
    event_inputs: Dict[str, Any],
    rsvp_summary: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a clean, structured Markdown document of the full event plan.

    Args:
        plan: Validated event plan dictionary from Gemini.
        event_inputs: Original input parameters.
        rsvp_summary: Optional RSVP and guest metrics.

    Returns:
        Formatted markdown string.
    """
    concept = plan.get("concept_and_theme", {})
    title = concept.get("title", f"{event_inputs.get('event_type', 'Celebration')} Plan")
    tagline = concept.get("tagline", "")
    budget = event_inputs.get("budget", 0)
    city = event_inputs.get("city", "N/A")
    date_str = str(event_inputs.get("date", "N/A"))
    guests = event_inputs.get("guests", 0)

    md = []
    md.append(f"# 🎉 {title}")
    if tagline:
        md.append(f"*{tagline}*\n")
    md.append(f"**Generated on:** {datetime.date.today().strftime('%B %d, %Y')}\n")

    md.append("## 📌 Event Overview")
    md.append(f"- **Event Type:** {event_inputs.get('event_type')}")
    md.append(f"- **Event Date:** {date_str}")
    md.append(f"- **Location / City:** {city}")
    md.append(f"- **Expected Guests:** {guests}")
    md.append(f"- **Total Budget:** {format_inr(budget)}")
    md.append(f"- **Budget Per Head (Planned):** {format_inr(budget / max(1, guests))}")
    md.append(f"- **Venue Setting:** {event_inputs.get('venue_type', 'Indoor/Outdoor')}")
    md.append(f"- **Dietary Preferences:** {event_inputs.get('dietary', 'All')}")
    md.append("")

    # Theme & Concept
    md.append("## 🎨 Concept & Theme")
    md.append(concept.get("description", "A custom tailored celebration experience."))
    md.append("")
    if concept.get("color_palette"):
        colors = ", ".join(concept.get("color_palette", []))
        md.append(f"- **Color Palette:** {colors}")
    if concept.get("dress_code"):
        md.append(f"- **Dress Code:** {concept.get('dress_code')}")
    if concept.get("vibe"):
        md.append(f"- **Vibe & Atmosphere:** {concept.get('vibe')}")
    md.append("")

    # Budget Split
    md.append("## 💰 Budget Breakdown")
    budget_items = plan.get("budget_split", [])
    if budget_items:
        md.append("| Category | Amount (INR) | Share (%) | Allocation Strategy & Notes |")
        md.append("|---|---|---|---|")
        for item in budget_items:
            cat = item.get("category", "General")
            amt = format_inr(item.get("amount", 0))
            pct = item.get("percentage", 0)
            notes = item.get("notes", "-")
            md.append(f"| {cat} | {amt} | {pct}% | {notes} |")
    md.append("")

    # Day-of Timeline
    md.append("## ⏰ Day-of Timeline")
    timeline = plan.get("day_of_timeline", [])
    if timeline:
        md.append("| Time | Activity | Description | Person In Charge |")
        md.append("|---|---|---|---|")
        for t in timeline:
            time_val = t.get("time", "-")
            activity = t.get("activity", "-")
            details = t.get("details", "-")
            owner = t.get("owner", "Host / Planner")
            md.append(f"| {time_val} | {activity} | {details} | {owner} |")
    md.append("")

    # Task Checklist
    md.append("## ✅ Task Checklist (Countdown)")
    tasks = plan.get("task_checklist", [])
    if tasks:
        md.append("| Timeframe / Deadline | Task | Category | Key Tip / Advice |")
        md.append("|---|---|---|---|")
        for task in tasks:
            deadline = task.get("deadline", "-")
            name = task.get("task", "-")
            cat = task.get("category", "General")
            tip = task.get("tip", "-")
            md.append(f"| {deadline} | {name} | {cat} | {tip} |")
    md.append("")

    # Menu Suggestions
    md.append("## 🍽️ Curated Menu Suggestions")
    menu = plan.get("menu_suggestions", {})
    if isinstance(menu, dict):
        for course, items in menu.items():
            course_title = course.replace("_", " ").title()
            md.append(f"### {course_title}")
            if isinstance(items, list):
                for item in items:
                    md.append(f"- {item}")
            else:
                md.append(f"- {items}")
            md.append("")
    md.append("")

    # Decor Ideas
    md.append("## ✨ Decor & Styling Ideas")
    decor = plan.get("decor_ideas", {})
    if isinstance(decor, dict):
        for area, details in decor.items():
            area_title = area.replace("_", " ").title()
            md.append(f"### {area_title}")
            if isinstance(details, list):
                for item in details:
                    md.append(f"- {item}")
            else:
                md.append(f"- {details}")
            md.append("")
    md.append("")

    # Backup Plan / Contingency
    md.append("## 🛡️ Risk Management & Backup Plan")
    backup = plan.get("backup_plan", [])
    if backup:
        for risk_item in backup:
            if isinstance(risk_item, dict):
                risk = risk_item.get("risk", "Contingency")
                mitigation = risk_item.get("mitigation", "N/A")
                md.append(f"### ⚠️ Risk: {risk}")
                md.append(f"**Mitigation Plan:** {mitigation}\n")
            else:
                md.append(f"- {risk_item}")
    md.append("")

    # RSVP Tracker Summary if available
    if rsvp_summary:
        md.append("## 👥 Guest List & RSVP Summary")
        md.append(f"- **Total Invited:** {rsvp_summary.get('total_invited', 0)}")
        md.append(f"- **Confirmed Headcount:** {rsvp_summary.get('total_headcount', 0)}")
        md.append(f"- **Confirmation Rate:** {rsvp_summary.get('confirmation_rate', 0)}%")
        diet_breakdown = rsvp_summary.get("dietary_breakdown", {})
        if diet_breakdown:
            md.append(f"- **Dietary Needs Breakdown:** {', '.join([f'{k}: {v}' for k, v in diet_breakdown.items()])}")
        md.append("")

    md.append("---\n*Celebration & Event Planner — Designed with Google Gemini*")
    return "\n".join(md)


def generate_plan_pdf(
    plan: Dict[str, Any],
    event_inputs: Dict[str, Any],
    rsvp_summary: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Generate a clean, high-contrast, professional PDF of the event plan.

    Uses ReportLab with high-contrast text and tables.
    Returns bytes suitable for Streamlit `st.download_button`.

    Args:
        plan: Validated event plan dictionary.
        event_inputs: Original input parameters.
        rsvp_summary: Optional guest list summary.

    Returns:
        PDF binary content.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom high-contrast styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#1E1B4B"),
        alignment=0,
        spaceAfter=6,
    )

    tagline_style = ParagraphStyle(
        "Tagline",
        parent=styles["Italic"],
        fontName="Helvetica-Oblique",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#4338CA"),
        spaceAfter=12,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1E1B4B"),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#312E81"),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.white,
    )

    table_body_style = ParagraphStyle(
        "TableBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#0F172A"),
    )

    story = []

    concept = plan.get("concept_and_theme", {})
    title = concept.get("title", f"{event_inputs.get('event_type', 'Celebration')} Plan")
    tagline = concept.get("tagline", "Curated AI Event Architecture")

    # Document Header
    story.append(Paragraph(html.escape(title), title_style))
    if tagline:
        story.append(Paragraph(html.escape(tagline), tagline_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#4F46E5"), spaceAfter=12))

    # Event Overview Card
    story.append(Paragraph("Event Overview", h1_style))
    budget_val = event_inputs.get("budget", 0)
    guests_val = event_inputs.get("guests", 1)
    planned_per_head = budget_val / max(1, guests_val)

    overview_data = [
        [
            Paragraph("<b>Event Type:</b> " + html.escape(str(event_inputs.get("event_type", ""))), body_style),
            Paragraph("<b>Date:</b> " + html.escape(str(event_inputs.get("date", ""))), body_style),
        ],
        [
            Paragraph("<b>City / Venue:</b> " + html.escape(str(event_inputs.get("city", ""))), body_style),
            Paragraph("<b>Setting:</b> " + html.escape(str(event_inputs.get("venue_type", ""))), body_style),
        ],
        [
            Paragraph("<b>Guest Count:</b> " + str(guests_val), body_style),
            Paragraph("<b>Total Budget:</b> " + html.escape(format_inr(budget_val)), body_style),
        ],
        [
            Paragraph("<b>Budget / Head:</b> " + html.escape(format_inr(planned_per_head)), body_style),
            Paragraph("<b>Dietary Focus:</b> " + html.escape(str(event_inputs.get("dietary", ""))), body_style),
        ],
    ]
    overview_table = Table(overview_data, colWidths=[260, 260])
    overview_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(overview_table)
    story.append(Spacer(1, 10))

    # Concept & Theme Section
    story.append(Paragraph("Concept & Aesthetic Theme", h1_style))
    desc = concept.get("description", "")
    if desc:
        story.append(Paragraph(html.escape(desc), body_style))

    palette = ", ".join(concept.get("color_palette", []))
    if palette:
        story.append(Paragraph(f"<b>Color Palette:</b> {html.escape(palette)}", body_style))
    if concept.get("vibe"):
        story.append(Paragraph(f"<b>Vibe:</b> {html.escape(str(concept.get('vibe')))}", body_style))
    if concept.get("dress_code"):
        story.append(Paragraph(f"<b>Dress Code:</b> {html.escape(str(concept.get('dress_code')))}", body_style))
    story.append(Spacer(1, 10))

    # Budget Split Section
    budget_items = plan.get("budget_split", [])
    if budget_items:
        story.append(Paragraph("Budget Allocation & Category Split", h1_style))
        b_rows = [[
            Paragraph("Category", table_header_style),
            Paragraph("Share (%)", table_header_style),
            Paragraph("Amount (INR)", table_header_style),
            Paragraph("Strategic Notes", table_header_style),
        ]]
        for item in budget_items:
            b_rows.append([
                Paragraph(html.escape(str(item.get("category", ""))), table_body_style),
                Paragraph(f"{item.get('percentage', 0)}%", table_body_style),
                Paragraph(html.escape(format_inr(item.get("amount", 0))), table_body_style),
                Paragraph(html.escape(str(item.get("notes", ""))), table_body_style),
            ])
        b_table = Table(b_rows, colWidths=[120, 55, 95, 250])
        b_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(b_table)
        story.append(Spacer(1, 10))

    # Timeline Section
    timeline = plan.get("day_of_timeline", [])
    if timeline:
        story.append(Paragraph("Day-Of Timeline", h1_style))
        t_rows = [[
            Paragraph("Time", table_header_style),
            Paragraph("Activity", table_header_style),
            Paragraph("Details", table_header_style),
            Paragraph("Lead", table_header_style),
        ]]
        for item in timeline:
            t_rows.append([
                Paragraph(html.escape(str(item.get("time", ""))), table_body_style),
                Paragraph(html.escape(str(item.get("activity", ""))), table_body_style),
                Paragraph(html.escape(str(item.get("details", ""))), table_body_style),
                Paragraph(html.escape(str(item.get("owner", "Host"))), table_body_style),
            ])
        t_table = Table(t_rows, colWidths=[70, 120, 230, 100])
        t_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#312E81")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(t_table)
        story.append(Spacer(1, 10))

    # Task Checklist
    tasks = plan.get("task_checklist", [])
    if tasks:
        story.append(Paragraph("Countdown Task Checklist", h1_style))
        tk_rows = [[
            Paragraph("Milestone", table_header_style),
            Paragraph("Task", table_header_style),
            Paragraph("Category", table_header_style),
            Paragraph("Planner Tip", table_header_style),
        ]]
        for t in tasks:
            tk_rows.append([
                Paragraph(html.escape(str(t.get("deadline", ""))), table_body_style),
                Paragraph(html.escape(str(t.get("task", ""))), table_body_style),
                Paragraph(html.escape(str(t.get("category", ""))), table_body_style),
                Paragraph(html.escape(str(t.get("tip", ""))), table_body_style),
            ])
        tk_table = Table(tk_rows, colWidths=[90, 150, 90, 190])
        tk_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0D9488")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0FDFA")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(tk_table)
        story.append(Spacer(1, 10))

    # Curated Menu Section
    menu = plan.get("menu_suggestions", {})
    if isinstance(menu, dict) and menu:
        story.append(Paragraph("Curated Menu Suggestions", h1_style))
        for course, items in menu.items():
            course_name = course.replace("_", " ").title()
            story.append(Paragraph(course_name, h2_style))
            if isinstance(items, list):
                bullet_text = " • ".join([str(x) for x in items])
                story.append(Paragraph(html.escape(bullet_text), body_style))
            else:
                story.append(Paragraph(html.escape(str(items)), body_style))
        story.append(Spacer(1, 8))

    # Decor Ideas Section
    decor = plan.get("decor_ideas", {})
    if isinstance(decor, dict) and decor:
        story.append(Paragraph("Decor & Styling Architecture", h1_style))
        for area, details in decor.items():
            area_name = area.replace("_", " ").title()
            story.append(Paragraph(area_name, h2_style))
            if isinstance(details, list):
                bullet_text = " • ".join([str(x) for x in details])
                story.append(Paragraph(html.escape(bullet_text), body_style))
            else:
                story.append(Paragraph(html.escape(str(details)), body_style))
        story.append(Spacer(1, 8))

    # Contingency & Backup Plan Section
    backup = plan.get("backup_plan", [])
    if backup:
        story.append(Paragraph("Risk Contingency & Backup Plan", h1_style))
        for risk_item in backup:
            if isinstance(risk_item, dict):
                r_title = risk_item.get("risk", "Contingency")
                r_plan = risk_item.get("mitigation", "")
                story.append(Paragraph(f"<b>⚠️ Risk: {html.escape(r_title)}</b>", h2_style))
                story.append(Paragraph(f"<b>Action:</b> {html.escape(r_plan)}", body_style))
            else:
                story.append(Paragraph(f"• {html.escape(str(risk_item))}", body_style))
        story.append(Spacer(1, 8))

    # RSVP Tracker summary if present
    if rsvp_summary:
        story.append(Paragraph("Guest List & RSVP Status", h1_style))
        rsvp_text = (
            f"<b>Invited:</b> {rsvp_summary.get('total_invited', 0)} | "
            f"<b>Confirmed Headcount:</b> {rsvp_summary.get('total_headcount', 0)} | "
            f"<b>Confirmation Rate:</b> {rsvp_summary.get('confirmation_rate', 0)}%"
        )
        story.append(Paragraph(rsvp_text, body_style))

    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#94A3B8"), spaceAfter=8))
    footer_text = "Celebration & Event Planner — Automated Plan Report • High Contrast & Accessible"
    story.append(Paragraph(footer_text, ParagraphStyle("Footer", parent=body_style, fontSize=8, textColor=colors.gray)))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
