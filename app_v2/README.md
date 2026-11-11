# ER Wait Dashboard: AFTER version

The same app as the one in the repo root (the BEFORE version), but it uses Chengjin's
48-hour forecast. The root app is left untouched so the team can compare the two.

## Run on your computer
From the `er-app` folder:
```
.venv\Scripts\python.exe -m streamlit run app_v2/Home.py
```

## What is different from the before app
| | Before (root) | After (app_v2) |
|---|---|---|
| Forecast | 24 h sample | 48 h, Chengjin's Prophet model with Ottawa weather |
| Busiest hour | rest of today | next 24 h from demo time, can cross midnight |
| Forecast page | arrivals, nurses | 48 hours, adds a doctors chart |
| Helper module | `utils.py` | `utils_v2.py` (own name, so the two apps never mix) |

`schedule.csv` has 24 rows and is reused for both days.

## Data
`app_v2/data/` has its own copy of every file. New files from teammates go here,
so the before app keeps the original samples.

| File | Status |
|---|---|
| forecast.csv | Chengjin: Nov 9-10 run, relabelled to Nov 30 and Dec 1. Regenerate on Nov 30 (see below). |
| schedule.csv, triage_rules.xlsx, waiting_room.csv, spaces.csv, avg_stay.csv | Still the samples |

## Regenerating the forecast on Nov 30
`tools/forecast.py` is Chengjin's script with fixes (listed at the top of the file).
1. Put `ottawa_er_training_data_2025.csv` in `app_v2/tools/`.
2. `pip install prophet pandas requests` (plus `truststore` if you get a certificate error).
3. `python app_v2/tools/forecast.py`. It writes `app_v2/data/forecast.csv` for today and tomorrow.
4. Run the app, check it, commit and push.

If the forecast does not include the demo hour (`DEMO_NOW` in `utils_v2.py`), the app shows
a message telling you what range it does have.
