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

## Code
- `Home.py`: dashboard (Member 4)
- `pages/`: one file per solution page
- `utils.py`: file loading and the calculations shared by all pages
