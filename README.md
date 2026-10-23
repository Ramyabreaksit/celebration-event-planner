# 🎉 Celebration & Event Planner

An intelligent, full-lifecycle celebration planning platform built with **Python**, **Streamlit**, and **Google Gemini** (`google-generativeai`).

Whether you are planning a vibrant Big Fat Indian Wedding, an intimate 1st Birthday party, a joyful Baby Shower (*Godh Bharai*), a lively College Farewell, or an Annual Corporate Gala, the **Celebration & Event Planner** takes you from early conceptual vision to flawless day-of execution.

---

## 📌 Problem Statement

Planning celebrations often involves juggling disjointed spreadsheets, fragmented vendor estimates, conflicting timelines, and unpredictable attendee turnouts. Hosts frequently struggle with:
- **Unrealistic Budgeting**: Misallocating funds across venue, catering, decor, and entertainment without visibility into true per-head expenditure.
- **Fragmented Timelines**: Disorganized day-of schedules leading to vendor bottlenecks and delays.
- **Dietary & RSVP Complexity**: Failing to track attendee plus-ones and dietary preferences (e.g., Vegetarian, Jain, Vegan, Halal).
- **Lack of Contingency Protocols**: No actionable backup plan when faced with bad weather, power cuts, or vendor cancellations.

**Celebration & Event Planner** solves this by providing a unified, AI-orchestrated workflow that synthesizes realistic budget allocations, curated menus, countdown checklists, and contingency protocols into an interactive, exportable blueprint.

---

## ✨ Features

### 1. Tailored Event Input Form
- **Occasion Variety**: Pre-configured options for Birthdays, Weddings, Baby Showers, Festivals (Diwali, Holi, Eid, Christmas), College Reunions, Anniversaries, Corporate Galas, and Custom events.
- **Input Validation & Sanitization**: Strict validation ensuring dates are not in the past, guest count is within 1 to 5,000, and budget is greater than ₹0.
- **Contextual Parameters**: Location/City, Venue Setting (Indoor, Outdoor Lawn, Hybrid, Beach), and Dietary profile (Jain, Pure Veg, Mixed, Vegan, Halal, Gluten-Free).

### 2. AI-Generated Structured Event Plan (Gemini)
- **Concept & Aesthetic Theme**: Creative title, tagline, narrative, color palette swatches, atmospheric vibe, and guest dress code.
- **Categorical Budget Breakdown**: Strategic budget allocation into Venue, Food & Beverages, Decor & Ambience, Entertainment & Media, and Miscellaneous Contingency, complete with interactive tables and an Altair donut chart.
- **Day-Of Timeline**: Hour-by-hour run-of-show with designated activity leads (Coordinator, Host, DJ, Caterer).
- **Countdown Task Checklist**: Actionable milestone checklist counting backwards from the event date (8 weeks, 4 weeks, 2 weeks, 1 day before, morning of) with completion progress tracking.
- **Curated Menu & Decor Ideas**: Multi-course culinary suggestions aligned with dietary requirements, plus entrance, stage, table, and photo booth styling blueprints.
- **Risk Management & Backup Plan**: Concrete contingency protocols for weather disruptions, vendor no-shows, guest count surges, and AV/power failures.

### 3. Guest List & RSVP Headcount Tracker
- Add guests with contact info, RSVP status (Confirmed, Declined, Pending), plus-ones, and dietary restrictions.
- Live comparison of **Planned Per-Head Budget** vs. **Actual Per-Head Spend** based on confirmed headcount.
- Visual alerts if confirmed attendees exceed initial venue/budget capacity.
- Instant CSV export of guest list.

### 4. Interactive "Ask the Planner" Chat Assistant
- Context-aware chatbot with the active event plan loaded in memory.
- Ask follow-up questions: cost-saving suggestions, music playlist ideas, seating arrangements, and vendor negotiation tips.

### 5. Document & Plan Export
- **Printable PDF**: High-contrast, beautifully styled document report generated via ReportLab with summary cards and tables.
- **Markdown / Plain Text**: Structured document ready to copy into Notion, Google Docs, or email.

---

## 🛠️ Tech Stack & Architecture

- **Frontend & UI**: [Streamlit](https://streamlit.io/) (Accessible high-contrast theme, responsive layout, Altair charts)
- **AI Engine**: [Google Generative AI](https://github.com/google-gemini/deprecated-generative-ai-python) (`google-generativeai` with `gemini-2.5-flash`, `gemini-2.5-flash-lite`, and `gemini-flash-latest`, with automatic 404 fallback)
- **Data & Visualizations**: [Pandas](https://pandas.pydata.org/), [Altair](https://altair-viz.github.io/)
- **Document Generation**: [ReportLab](https://www.reportlab.com/) (PDF engine), [FPDF2](https://py-pdf.github.io/fpdf2/)
- **Testing**: [Pytest](https://pytest.org/) (Comprehensive unit test coverage)
- **Environment Management**: Python 3.10+ / `python-dotenv`

### Code Architecture
```text
event-planner/
├── .env.example              # Example environment variable template
├── .gitignore                # Git ignore rules for secrets and caches
├── .streamlit/
│   └── config.toml           # Accessible high-contrast theme configuration
├── app.py                    # Main Streamlit web application & UI tabs
├── planner.py                # Gemini LLM integration, schema validation, caching & chat
├── utils.py                  # Input validation, budget math, RSVP metrics & PDF export
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
└── tests/
    ├── __init__.py
    ├── test_validation.py    # Tests for input sanitization and boundary rules
    ├── test_budget.py        # Tests for budget calculations and RSVP summaries
    └── test_json_parsing.py  # Tests for Gemini JSON parsing and error recovery
```

---

## 🚀 Setup & Installation

### 1. Clone or Navigate to Repository
```bash
git clone <repo-url>
cd event-planner
```

### 2. Set Up a Virtual Environment (Recommended)
```bash
python -m venv venv

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Gemini API Key
Obtain a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

You can supply your key in any of the following three ways:
1. **Via `.env` file**:
   ```bash
   cp .env.example .env
   # Edit .env and set GEMINI_API_KEY=your_key_here
   ```
2. **Via Streamlit Secrets** (`.streamlit/secrets.toml`):
   ```toml
   GEMINI_API_KEY = "your_actual_key_here"
   ```
3. **Directly in the Web UI**: Paste your key in the sidebar password field when running the app.

---

## 💻 Running the Application

Launch the Streamlit app:
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

*Tip*: If you want to preview the full interface without entering an API key immediately, click **"💡 Explore Sample Celebration Plan"** on the main form.

---

## 🧪 Running Unit Tests

Run the complete test suite with Pytest:
```bash
python -m pytest -v
```
All 17 tests validate:
- ✅ Input boundary rules (budgets $\le 0$, guests $< 1$ or $> 5000$, past dates)
- ✅ Rupee currency formatting and decimal calculations
- ✅ Budget splits and per-head headcount mathematics
- ✅ RSVP aggregations and dietary distributions
- ✅ Markdown code-fence stripping, schema validation, and fallback handling

---

## ♿ Accessibility Compliance

The application adheres to accessibility best practices:
- **WCAG High Contrast**: Indigo/slate text on clean backgrounds ($> 4.5:1$ contrast ratio).
- **No Color-Only Information**: Every indicator pairs colors with text and recognizable icons (e.g., `✅ Confirmed`, `❌ Declined`, `⏳ Pending`).
- **Form Usability**: Descriptive labels, inline placeholder text, and explicit `help` popovers on all interactive elements.
- **Keyboard Friendly**: Standard tab navigation supported across all form fields and data tables.

---

## 📄 License
MIT License. Created for celebratory joy and seamless event execution.
