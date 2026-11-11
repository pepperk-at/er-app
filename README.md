# ER Wait Dashboard (DTO 5389 group project)

Starter Streamlit app: a home dashboard plus one page per solution.
All numbers in `data/` are SAMPLE values. Replace each file with the real one
(same file name, same columns) when a team member hands it over.

## Run on your computer
```
python -m venv .venv
.venv\Scripts\activate          (Windows)
pip install -r requirements.txt
streamlit run Home.py
```

## Files and owners (file agreement)
| File | Owner | Columns |
|---|---|---|
| data/forecast.csv | Member 1 | date, hour, expected_arrivals |
| data/schedule.csv | Member 1 | hour, nurses_scheduled, doctors_scheduled |
| data/triage_rules.xlsx | Member 2 | sheet `complaints`: complaint, start_level; sheet `vitals`: vital_sign, operator, cutoff, new_level |
| data/waiting_room.csv | Member 2 | patient_id, arrival_time (YYYY-MM-DD HH:MM), complaint, ctas_level |
| data/spaces.csv | Member 3 | space_id, status (free/occupied/cleaning), ctas_level, time_in_space_min |
| data/avg_stay.csv | Member 3 | ctas_level, avg_stay_min |

Each member can make their numbers any way they like. The app only cares that the file matches.
Start from the sample file in `data/` and replace the values. Keep the headers and the file name.

Format rules (most errors come from these):
- Headers spelled exactly as above: lowercase, no extra spaces.
- `hour` is 0 to 23, and all 24 hours are in both `forecast.csv` and `schedule.csv`.
- Dates are for the demo day, 2026-11-30, in the same format as the sample. Excel can change dates when it saves, so open the CSV in Notepad to check.
- `ctas_level` is a whole number from 1 to 5.
- `status` in `spaces.csv` is lowercase: `free`, `occupied` or `cleaning`. Leave `ctas_level` and `time_in_space_min` blank for free and cleaning spaces.
- In `triage_rules.xlsx`, `vital_sign` is one of `heart_rate`, `oxygen_saturation`, `temperature`, `pain_score`, and `operator` is one of `<`, `>`, `<=`, `>=`.
- Save CSVs as plain "CSV (Comma delimited)". Only the triage rules file is .xlsx.

Along with the file, each member sends their method and sources for the report.
Member 1 also sends three sourced numbers for the sidebar sliders in `utils.py`:
nursing minutes per patient, patients per doctor per hour, and minutes per doctor assessment.

## Member 4: putting it together
1. Copy the new files into `data/`, replacing the samples.
2. If the demo date changes, update `DEMO_NOW` in `utils.py`.
3. Set Member 1's numbers as the slider defaults in `utils.py` and remove the "Sample values" captions.
4. Run the app locally and click through every page. An error usually means a header or value is spelled differently.
5. Commit and push. Streamlit Cloud redeploys on its own (see DEPLOYMENT.md).
6. Ask each member to check their page on the live link.

## Code
- `Home.py`: dashboard (Member 4)
- `pages/`: one file per solution page
- `utils.py`: file loading and the calculations shared by all pages
