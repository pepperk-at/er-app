# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Streamlit ER wait-time dashboard for a DTO 5389 (uOttawa) group project. The repo holds **two separate apps** that deploy from the same GitHub repo (`pepperk-at/er-app`) to Streamlit Community Cloud:

- **BEFORE app** (repo root: `Home.py`, `pages/`, `utils.py`, `data/`): the original starter with sample data. Leave it untouched so the team can compare before/after.
- **AFTER app** (`app_v2/`): the version built from teammates' real deliverables, as agreed by the team.
- **V3 app** (`app_v3/`): a copy of `app_v2` (Nov 18, 2026) for trying new ideas. Helpers are `utils_v3.py` and `city_v3.py` (5 Ottawa EDs, events, incident scenarios; `HOME_ED` is the ED the sample files describe, others are scaled by annual visits). The active scenario lives in `st.session_state["incident"]` and `utils_v3.staffing_table()` adds its arrivals, so every page reflects it. Data in `app_v3/data/`. New-idea work goes here, not in `app_v2`; log each idea in `app_v3/README.md`.

Pushing to `main` redeploys both apps. There are no tests, linter or build step.

## Commands

Run from the repo root (Windows, local `.venv`):

```powershell
.\.venv\Scripts\python.exe -m streamlit run app_v2/Home.py   # AFTER app
.\.venv\Scripts\python.exe -m streamlit run Home.py          # BEFORE app
```

Verify changes by running the app and clicking through every page; a page error usually means a data file's header or value doesn't match the file agreement.

Regenerate the 3-day forecast (needs `prophet pandas requests`, optional `truststore`, and `ottawa_er_training_data_2025.csv` copied from `data/Chengjin/` into `app_v2/tools/`):

```powershell
python app_v2/tools/forecast.py   # writes app_v2/data/forecast.csv
```

## Architecture

- Each app is a Streamlit multipage app: `Home.py` is the dashboard, `pages/N_*.py` are one page per solution (1 Forecast & Staffing, 2 Triage, 3 Treatment Spaces). Every page calls `utils.assumptions()` first, which draws the shared sidebar sliders.
- All file loading and shared calculations live in the helper module. The AFTER app's helper is deliberately named `utils_v2.py` and imported as `import utils_v2 as utils`, so the two apps never load each other's `utils.py`. Keep that naming.
- Each app reads only its own data folder (`DATA = Path(__file__).parent / "data"`). New teammate files go into `app_v2/data/` only; the root `data/` keeps the samples. `data/Chengjin/`, `data/Godwin/` and `data/Gulchaman/` hold raw handoffs (scripts, training data, specs), not app inputs. They are local only (in `.gitignore`) so they stay out of the public repo; never commit them.
- `DEMO_NOW` (2026-11-30 18:00) in the helper module is the app's "current time". The forecast must cover it plus the next 24 h, otherwise the app shows a range message.
- Key `utils_v2.py` pieces: `CTAS` (level colours: 1 red, 2 orange, 3 yellow, 4 green, 5 white, a team choice, not standard CTAS colours), `REASSESS_MIN` (CTAS reassessment intervals, confirmed in Godwin's brief, Member 2) and `DUE_SOON_SHARE` (80%, a team guess), `level_chart()` (shared by Home and Triage), `check_spaces()` (Gulchaman's treatment-space rules and file validation), `staffing_table()` / `next_hours()` (forecast vs schedule).
- V3 map (pydeck): plain-text layer settings must be quoted (`width_units="'pixels'"`), otherwise pydeck turns them into data expressions. Hover tips are plain text with `\n` (Streamlit escapes HTML), and `TOOLTIP_STYLE` has `top: 100%` to cancel a Streamlit 1.65 tooltip offset.
- AFTER-app charts use Altair (bundled with Streamlit) to meet Chengjin's layout requests. If any other library is added, add it to the matching `requirements.txt` (`app_v2/requirements.txt` for the AFTER app) or the cloud app crashes.

## Data file agreement

The app only cares that each file has the exact name and columns. Format rules from `README.md`:

| File | Columns |
|---|---|
| forecast.csv | date, hour, expected_arrivals |
| schedule.csv | hour, nurses_scheduled, doctors_scheduled (24 rows, reused for every forecast day) |
| triage_rules.xlsx | sheet `complaints`: complaint, start_level; sheet `vitals`: vital_sign, operator, cutoff, new_level |
| waiting_room.csv | patient_id, arrival_time (YYYY-MM-DD HH:MM), complaint, ctas_level |
| spaces.csv | space_id, status (free/occupied/cleaning), ctas_level, time_in_space_min |
| avg_stay.csv | ctas_level, avg_stay_min |

- Lowercase headers, `hour` 0-23, `ctas_level` integer 1-5, dates in YYYY-MM-DD.
- `status` lowercase; leave `ctas_level`/`time_in_space_min` blank for free and cleaning spaces.
- `vital_sign` ∈ heart_rate, oxygen_saturation, temperature, pain_score; `operator` ∈ `<`, `>`, `<=`, `>=`.

## Project status

`app_v2/README.md` is the running log: what differs from the BEFORE app, each teammate's rules, expected results with sample data, and a "Paused here" note with open to-dos. Read it first when resuming work and update it when behaviour changes. Only Katherine pushes to the repo; deployment steps are in `DEPLOYMENT.md`.
