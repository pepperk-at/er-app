# ER Wait Dashboard (DTO 5389 group project)

A Streamlit dashboard for an Ottawa emergency department: expected arrivals and staffing gaps, triage wait
alerts, and treatment space status. The app's clock is fixed at Mon Nov 30, 2026, 18:00, so the numbers stay the
same each time it is opened.

## Start here
- Live app (nothing to install): https://er-app-njjqu4r98jkzf5dru58spw.streamlit.app
- User guide: [app_v3/USER_GUIDE.md](app_v3/USER_GUIDE.md) walks through every page step by step, explains each
  control and label, and lists the app's limits and troubleshooting tips.

The rest of this README is for running and updating the app.

This repo holds three versions of the app. Each one has its own code and its own `data/` folder, and they never
load each other's files.

| Version | Folder | Main file | What it is |
|---|---|---|---|
| BEFORE | repo root | `Home.py` | The first starter app with sample data. Kept as it was so the team can show before and after. |
| AFTER | `app_v2/` | `app_v2/Home.py` | Built from the team's real deliverables. This is the version the team agreed on. |
| V3 | `app_v3/` | `app_v3/Home.py` | A copy of AFTER (Nov 18) for new ideas: all 5 Ottawa EDs, a city map, events, incident scenarios, and wait alerts named in CTAS terms. |

V3 live app: https://er-app-njjqu4r98jkzf5dru58spw.streamlit.app

Each version has its own notes:
- `app_v2/README.md`: what changed from the BEFORE app, each teammate's rules, and the results to expect with the sample data.
- `app_v3/README.md`: each new idea, the page-by-page review, and the current to-do list.
- `DEPLOYMENT.md`: how the apps are published on Streamlit Community Cloud.

## Pages
All three versions have the same core pages. V3 adds the City & Events page and a Hospital picker in the sidebar.

| Page | Shows | From |
|---|---|---|
| Home | Summary of patients waiting, wait alerts, free spaces and the staffing gap | Katherine |
| City & Events (V3 only) | Map of the 5 EDs, events, and where patients go in an incident | Katherine |
| Forecast & Staffing | Expected arrivals per hour against nurses and doctors scheduled | Chengjin |
| Triage | CTAS level for each patient and who is past their target time | Godwin |
| Treatment Spaces | Free, occupied and cleaning spaces, and which ones should free up soon | Gulchaman |

## Run on your computer
From the `er-app` folder (Windows):
```
python -m venv .venv
.venv\Scripts\activate
pip install -r app_v3/requirements.txt
```
Then run the version you want:
```
.venv\Scripts\python.exe -m streamlit run app_v3/Home.py     (V3)
.venv\Scripts\python.exe -m streamlit run app_v2/Home.py     (AFTER)
.venv\Scripts\python.exe -m streamlit run Home.py            (BEFORE)
```
Each version has its own `requirements.txt`. V3 pins `streamlit==1.65.0` so the map hover boxes show up next to
the mouse.

## Data files
Every version reads the same six files from its own `data/` folder. The app only cares that each file has the
exact name and columns below. The root `data/` keeps the original samples; real files go in `app_v2/data/` (and
`app_v3/data/` for V3).

| File | Owner | Columns |
|---|---|---|
| forecast.csv | Chengjin | date, hour, expected_arrivals |
| schedule.csv | Chengjin | hour, nurses_scheduled, doctors_scheduled |
| triage_rules.xlsx | Godwin | sheet `complaints`: complaint, start_level; sheet `vitals`: vital_sign, operator, cutoff, new_level |
| waiting_room.csv | Godwin | patient_id, arrival_time (YYYY-MM-DD HH:MM), complaint, ctas_level |
| spaces.csv | Gulchaman | space_id, status (free/occupied/cleaning), ctas_level, time_in_space_min |
| avg_stay.csv | Gulchaman | ctas_level, avg_stay_min |

V3 also reads `hospitals.csv`, `events.csv` and two Ottawa boundary files (`ottawa_city.geojson`,
`ottawa_da.geojson`). See `app_v3/README.md` for where those come from.

Format rules (most errors come from these):
- Headers spelled exactly as above: lowercase, no extra spaces.
- `hour` is 0 to 23, and all 24 hours are in `schedule.csv`. The forecast has to cover Nov 30 at 18:00 and the 24 hours after it.
- Dates are in YYYY-MM-DD format. Excel can change dates when it saves, so open the CSV in Notepad to check.
- `ctas_level` is a whole number from 1 to 5.
- `status` in `spaces.csv` is lowercase: `free`, `occupied` or `cleaning`. Leave `ctas_level` and `time_in_space_min` blank for free and cleaning spaces.
- In `triage_rules.xlsx`, `vital_sign` is one of `heart_rate`, `oxygen_saturation`, `temperature`, `pain_score`, and `operator` is one of `<`, `>`, `<=`, `>=`.
- Save CSVs as plain "CSV (Comma delimited)". Only the triage rules file is .xlsx.

## Updating the app
Only Katherine pushes to this repo. Teammates send their files to her.
1. Check the new file has the same name and columns as the one it replaces.
2. Copy it into `app_v2/data/` (and `app_v3/data/` if V3 should use it too). Leave the root `data/` alone.
3. Run the app locally and click through every page. An error usually means a header or value is spelled differently.
4. Commit and push to `main`. Streamlit Cloud redeploys every version on its own (see `DEPLOYMENT.md`).

To rebuild the forecast, run `app_v2/tools/forecast.py` (or `app_v3/tools/forecast.py`). The steps are in
`app_v2/README.md`.

## Code
Each version has the same layout:
- `Home.py`: the dashboard
- `pages/`: one file per page
- a helper module for file loading and shared calculations: `utils.py` (BEFORE), `utils_v2.py` (AFTER),
  `utils_v3.py` and `city_v3.py` (V3). The different names keep the versions from loading each other's helpers.
