# The Fashion Agents: AI Fashion Trend Analysis

Capstone project for fashion trend forecasting using editorial, social, computer-vision, and color-lexicon data.

## Project contents

- Python pipeline scripts for ingestion, computer vision, NLP, modeling, and reporting.
- database/color_lexicon/ for color-lexicon schema and seed assets.
- docs/reference/ for technical design and data-source documentation.
- docs/CLEANUP_RECOVERY_RUNBOOK.md for the project cleanup and recovery history.

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

~~~bash
python -m pip install -r requirements.txt
~~~

3. For browser-based scraping, install the Playwright browser separately:

~~~bash
python -m playwright install
~~~

4. Copy .env.example to .env and fill in local values.

Never commit .env or place real credentials in .env.example.

## Configuration

Database, cloud-storage, and API settings are read from environment variables. The required variable names are listed in .env.example.

## Running

Review the relevant script before running it because ingestion, database writes, scraping, and model generation can have external side effects.

Examples:

~~~bash
python main.py
streamlit run landing_page.py
~~~

Do not run production ingestion or destructive database operations without confirming the target environment.

## Validation

Basic syntax validation:

~~~bash
python -m compileall .
git diff --check
~~~

The project currently has script-level checks rather than a single unified test suite. Run database and network-dependent checks only with valid local configuration and explicit approval.
