# BRFSS Data Validation Dashboard

A web-based application for validating Behavioral Risk Factor Surveillance System (BRFSS) data submissions against CDC standards. Built using conversational AI-assisted development with Claude Code.

---

## Overview

The BRFSS Validation Dashboard helps public health agencies validate their survey data before submission to the CDC. It automatically detects whether uploaded data contains raw survey responses or aggregated prevalence statistics, then applies comprehensive validation rules to identify errors and data quality issues.

### What is BRFSS?

The Behavioral Risk Factor Surveillance System is the nation's premier system of health-related telephone surveys. Administered by state health departments, BRFSS collects data about U.S. residents regarding their health-related risk behaviors, chronic health conditions, and use of preventive services. The CDC has collected BRFSS data annually since 1984.

---

## Key Features

### 1. CSV File Upload with Drag-and-Drop
- Intuitive drag-and-drop interface for file submission
- Click-to-browse file selection
- Supports CSV files up to 16MB
- Real-time file size display
- Format documentation with example data

### 2. Automatic Data Format Detection
The system intelligently detects two BRFSS data formats:

| Format | Description | Use Case |
|--------|-------------|----------|
| **Raw Survey Data** | Individual respondent records with BRFSS variable codes | State health departments submitting survey responses |
| **Aggregated Data** | Prevalence statistics by state, topic, and demographic | Researchers analyzing published BRFSS indicators |

### 3. Comprehensive Validation Against BRFSS Standards

**For Raw Survey Data:**
- Validates 100+ BRFSS variable codes (GENHLTH, DIABETE4, SMOKE100, etc.)
- Checks state FIPS codes (1-56)
- Validates response codes against allowed ranges
- Handles special codes (7=Don't Know, 9=Refused, 88=None)

**For Aggregated Data:**
- Validates required fields (year, location, topic, question, data_value)
- Checks state abbreviations and names for consistency
- Validates prevalence percentages (0-100% range)
- Verifies confidence intervals (low <= value <= high)
- Checks sample sizes (minimum 10 for statistical validity)
- Validates 40+ recognized health topics

### 4. Error Detection and Reporting
- **Errors**: Critical issues that indicate invalid data (negative values, invalid codes)
- **Warnings**: Data quality concerns that don't prevent acceptance (small sample sizes, wide confidence intervals)
- Row-by-row error details with field identification
- First 100 errors displayed in scrollable table

### 5. Interactive Dashboard with Metrics
- Total submissions tracking
- Pass/fail/warning statistics
- Error breakdown by field type
- Pass rate percentage calculation
- Auto-refresh every 30 seconds

### 6. Interactive US State Map
- D3.js-powered visualization
- Color-coded states by validation status:
  - Green: Passed
  - Orange: Passed with Errors
  - Red: Failed
  - Gray: No submission
- Hover tooltips with state details
- Filter buttons for status categories

---

## Technical Architecture

```
brfss-dashboard/
├── app.py                    # Flask backend (1,161 lines)
├── requirements.txt          # Python dependencies
├── templates/                # Jinja2 HTML templates
│   ├── submit.html          # File upload interface
│   ├── validation_dashboard.html
│   ├── validation_detail.html
│   ├── map.html             # D3.js state map
│   └── error.html
├── mock_data/               # Sample test files
│   └── state_submissions/   # 50 state example files
└── uploads/                 # Temporary file storage
```

### Backend: Flask + Pandas

**Core Components:**
- **Flask 3.0.0**: Web framework handling routes and API endpoints
- **Pandas 2.1.3**: Data processing and validation logic
- **In-memory storage**: Fast, no database setup required

**API Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/submit` | GET/POST | File upload interface |
| `/validation` | GET | Dashboard summary |
| `/validation/<id>` | GET | Detailed results |
| `/map` | GET | Interactive state map |
| `/api/submissions` | GET | JSON submission list |
| `/api/state-status` | GET | State validation status |
| `/api/clear` | POST | Clear all data |

### Frontend: HTML/CSS + JavaScript

**Technologies:**
- HTML5 semantic markup
- CSS3 with responsive grid layouts
- Vanilla JavaScript for interactivity
- D3.js v7 for map visualization
- TopoJSON v3 for geographic data

**Design Features:**
- Dark blue navbar (#1e3a5f) for professional appearance
- Status badges with color coding
- Responsive two-column layouts
- Sticky table headers for large datasets
- Modal dialogs for confirmations

---

## Validation Workflow

```
         ┌─────────────────┐
         │   File Upload   │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │ Format Detection│
         │ (raw/aggregated)│
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │ Column Mapping  │
         │ & Normalization │
         └────────┬────────┘
                  │
    ┌─────────────┴─────────────┐
    │                           │
┌───▼───┐                 ┌─────▼─────┐
│  Raw  │                 │ Aggregated│
│Survey │                 │   Data    │
└───┬───┘                 └─────┬─────┘
    │                           │
    │ • FIPS codes              │ • Required fields
    │ • Variable codes          │ • State validation
    │ • Response ranges         │ • Data value ranges
    │                           │ • Confidence intervals
    │                           │ • Sample sizes
    └─────────────┬─────────────┘
                  │
         ┌────────▼────────┐
         │ Generate Stats  │
         │ & Summary       │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │ Determine Status│
         │ passed/failed/  │
         │ passed_with_err │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │ Display Results │
         └─────────────────┘
```

---

## Sample Data Included

The `mock_data/` directory contains test files for development and demonstration:

| File | Description |
|------|-------------|
| `brfss_valid_sample.csv` | Clean aggregated data (CA, TX) |
| `brfss_with_errors.csv` | Aggregated data with validation errors |
| `brfss_raw_survey_sample.csv` | Raw survey responses (Georgia) |
| `brfss_raw_with_errors.csv` | Raw data with errors |
| `continental_us_brfss_2023.csv` | Large dataset (100+ rows, all states) |
| `state_submissions/*.csv` | 50 individual state submission files |

---

## Installation & Setup

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Quick Start

```bash
# Clone or download the project
cd brfss-dashboard

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py

# Open in browser
# http://localhost:5000
```

### Dependencies

```
Flask==3.0.0
pandas==2.1.3
```

---

## How This Project Demonstrates AI-Assisted Development

This BRFSS Validation Dashboard was built entirely through conversational development with **Claude Code**, Anthropic's AI coding assistant. The development process showcases several key aspects of AI-assisted software engineering:

### 1. Rapid Prototyping
Through natural language conversation, the entire application was designed and implemented iteratively. Complex requirements like "validate BRFSS data against CDC standards" were translated into working code through dialogue.

### 2. Domain Knowledge Integration
Claude Code helped incorporate public health domain knowledge:
- BRFSS variable codes and their valid response ranges
- State FIPS codes and abbreviations
- CDC data format conventions
- Statistical validation rules (sample sizes, confidence intervals)

### 3. Full-Stack Development
The AI assistant handled all layers of the application:
- Backend validation logic with comprehensive error handling
- Frontend UI with modern CSS and JavaScript
- Interactive D3.js visualizations
- RESTful API design

### 4. Code Quality
The resulting codebase demonstrates:
- Clean separation of concerns
- Comprehensive input validation
- Graceful error handling
- Responsive design patterns
- Well-structured HTML templates

### 5. Iterative Refinement
Features were added and refined through conversation:
- "Add drag-and-drop upload" → Implemented with visual feedback
- "Show validation errors in a table" → Scrollable, sortable error display
- "Create a map showing state status" → Interactive D3.js visualization
- "Support both raw and aggregated formats" → Auto-detection logic

### 6. Documentation Generation
This README itself was generated by Claude Code after analyzing the complete codebase, demonstrating AI's ability to understand and document existing code.

---

## Future Enhancements

Potential improvements for production deployment:

- **Database Integration**: Replace in-memory storage with PostgreSQL or MongoDB
- **User Authentication**: Add login system for state health departments
- **Email Notifications**: Alert users when validation completes
- **Export Reports**: Generate PDF validation reports
- **Historical Tracking**: Track submission history over time
- **Batch Processing**: Support multiple file uploads
- **Custom Rules**: Allow agencies to configure validation thresholds

---

## Project Statistics

| Metric | Value |
|--------|-------|
| Lines of Python code | ~1,161 |
| HTML templates | 5 |
| BRFSS variables supported | 100+ |
| Health topics recognized | 40+ |
| State abbreviations | 56 (50 states + territories) |
| Mock data files | 60+ |

---

## License

This project was created for demonstration and educational purposes.

---

## Acknowledgments

- **CDC BRFSS Program**: For defining the data standards and formats
- **Anthropic Claude Code**: AI-assisted development platform
- **D3.js Community**: For the visualization library

---

*Built with Claude Code - demonstrating the future of AI-assisted software development*
