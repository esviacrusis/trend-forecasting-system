# Operational Readiness and Next Development Plan

The cleanup and conservative adoption phases are complete. This plan covers the next stage: safely configuring, testing, and developing the permanent working copy.

Permanent working copy:

~~~text
/Users/eric/Documents/CSUEB Subjects/2026 Spring/BAN 693 Capstone/Codes/trend-forecasting-system-final
~~~

Project directory:

~~~text
/Users/eric/Documents/CSUEB Subjects/2026 Spring/BAN 693 Capstone/Codes/trend-forecasting-system-final/trend-forecasting-system
~~~

## Safety rules

- Keep the original project and backup files unchanged.
- Use non-production credentials and data first.
- Never commit .env or real secrets.
- Run one external operation at a time.
- Confirm whether each operation is read-only or writes data.
- Do not run full ingestion, scraping, or model generation until a small controlled test passes.
- Record failures and configuration changes.

## Phase 1: Prepare the development environment

From the permanent repository:

~~~bash
cd "/Users/eric/Documents/CSUEB Subjects/2026 Spring/BAN 693 Capstone/Codes/trend-forecasting-system-final"
git status
git branch --show-current
git log --oneline -4
~~~

Confirm the branch is cleanup/project-structure-resumed and the working tree is clean.

Use an isolated virtual environment:

~~~bash
python3 -m venv /private/tmp/trend-forecasting-system-final-venv
source /private/tmp/trend-forecasting-system-final-venv/bin/activate
python -m pip install -r trend-forecasting-system/requirements.txt
python -m pip check
~~~

## Phase 2: Configure non-production services

Edit only the local file:

~~~text
trend-forecasting-system/.env
~~~

Use approved non-production values for database, cloud storage, and API services. Do not copy credentials from the original project without reviewing and rotating them if necessary.

Verify that .env remains ignored:

~~~bash
git check-ignore -v trend-forecasting-system/.env
git status --short
~~~

## Phase 3: Run a read-only database smoke test

Before running the test, confirm:

- the database host is non-production or explicitly approved;
- the test performs only a connection and read-only query;
- no tables, rows, schemas, or files will be changed.

Use a small read-only connection test appropriate for the configured environment. Do not run ingestion or insert/update scripts at this stage.

Record:

- date and environment;
- connection result;
- read-only query result;
- any error without exposing credentials.

## Phase 4: Verify the application interface

Start the Streamlit application from the project directory:

~~~bash
cd trend-forecasting-system
streamlit run landing_page.py
~~~

Verify the HOME page first. Do not select database-backed pages until the read-only database smoke test has passed.

Check:

- application starts;
- navigation renders;
- no secrets appear in the interface or logs;
- database-backed pages fail safely if the service is unavailable.

## Phase 5: Run controlled pipeline tests

Run one small operation at a time:

1. database read-only access;
2. one sample ingestion;
3. computer-vision processing on a small approved sample;
4. feature generation;
5. model training on a test dataset;
6. prediction and report generation.

After each step:

~~~bash
git status --short
~~~

Check generated outputs and confirm they are ignored or stored in an approved location.

Do not run the full pipeline until every small test is understood and documented.

## Phase 6: Improve maintainability

After the pipeline is confirmed:

- add focused automated tests;
- separate source, tests, data, and generated outputs more clearly if needed;
- pin dependency versions after confirming compatibility;
- document database schema and pipeline order;
- add logging that excludes secret values;
- remove obsolete scripts only with review;
- update the README with verified commands.

## Phase 7: Release readiness review

Review:

- Git status and commit history;
- dependency installation;
- configuration and secret handling;
- database permissions;
- UI startup;
- pipeline results;
- generated output locations;
- backup availability;
- documented limitations.

Create a release or milestone commit only after the review.

## Finish-line checklist

- [ ] Non-production configuration reviewed.
- [ ] .env remains ignored.
- [ ] Read-only database smoke test passes.
- [ ] Streamlit HOME page starts.
- [ ] Database-backed pages tested safely.
- [ ] Small pipeline test passes.
- [ ] Generated outputs are controlled.
- [ ] No secrets appear in tracked files or logs.
- [ ] Dependencies are reproducible.
- [ ] README reflects verified commands.
- [ ] Limitations and external dependencies are documented.
- [ ] Original project and backups remain preserved.

The next development milestone is complete when the system can be configured and exercised safely without exposing credentials or changing production data unexpectedly.
