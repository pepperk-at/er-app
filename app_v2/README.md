# ER Wait Dashboard: AFTER version

The same app as the one in the repo root (the BEFORE version), but it uses Chengjin's
3-day forecast. The root app is left untouched so the team can compare the two.

> **Reminder (Nov 17, 2026): these changes have NOT been committed and pushed to GitHub yet.**
> Not yet on GitHub: Chengjin's 3-day forecast, Gulchaman's treatment spaces, the triage colours
> and wait alerts, and this README. Commit and push in VS Code, check the deployed app, then delete
> this note.
>
> **Paused here (Nov 17, 2026). Where things stand:**
> - Class pitch Part 4 (my part, the dashboard) is rewritten to match this app, in
>   `reference/Class Pitch - ER Wait Times.docx`. The old version is in
>   `reference/Class Pitch - ER Wait Times (before Nov 17 update).docx`.
> - Still to do: Part 2 of the pitch and the pitch slide still say the triage page estimates how
>   long each level will wait. The app now shows overdue / due soon / on time alerts instead.
>   Update those lines or check with Godwin.
> - Still to do: Part 4 is about 160 words. If the pitch runs long, cut the sentence that starts
>   "Below it, one box per teammate…".

## Run on your computer
From the `er-app` folder:
```
.venv\Scripts\python.exe -m streamlit run app_v2/Home.py
```

## What is different from the before app
| | Before (root) | After (app_v2) |
|---|---|---|
| Forecast | 24 h sample | 3 days (today + 2), Chengjin's Prophet model with Ottawa weather |
| Busiest hour | rest of today | next 24 h from demo time, can cross midnight |
| Forecast page | arrivals, nurses | every forecast hour, adds a doctors chart; Chengjin's chart layout (below) |
| Treatment spaces | one "likely free" count; overdue patients counted as "free soon" | Gulchaman's rules and page sketch (below) |
| Triage | plain level numbers, one overdue count | colour per level and Overdue / Due soon / On time alerts (below) |
| Helper module | `utils.py` | `utils_v2.py` (own name, so the two apps never mix) |

`schedule.csv` has 24 rows and is reused for every day.

## Forecast (Chengjin, Member 1)
- The forecast covers fixed calendar days from midnight, not a rolling window. Chengjin changed it from
  2 days to 3 (`data/Chengjin/forecast 3 days/forecast.py`), so it can be made on Nov 29 or Nov 30 and
  still cover the demo hour plus the next 24 hours. `app_v2/tools/forecast.py` now makes 3 days too.
- Her chart requests on the Forecast & Staffing page: legend at the top left under the chart title,
  no "Time" axis name, and dates shown as 2026/11/30. The charts are built with Altair to allow this.
- Later changes: x-axis tick every 4 hours in 24-hour time (00:00, 04:00 ... 20:00), with the date
  under each midnight tick. Hovering makes the dots at the nearest hour bigger and shows the values.
  "Needed" lines are blue and "scheduled" lines are orange.
- Training data: `ottawa_er_training_data_2025.csv`, every hour of 2025 (8,760 rows, no gaps or blanks).
  The model trains on Jan 1 to Oct 31.

## Treatment spaces (Gulchaman, Member 3)
Built from her handoff in `data/Gulchaman/member-3-handoff/` (rules in `Sources-and-Assumptions.md`,
layout from `Treatment-Space-Page-Sketch.svg`). The calculation is `check_spaces()` in `utils_v2.py`.
- Shows Free now, Occupied and Cleaning totals. Cleaning spaces show "Readiness time unknown".
- Raw remaining = assumed stay for the CTAS level minus time in the space. It is not clipped at 0.
- Only positive estimates count. Within 2 h means 0 < raw ≤ 120 and within 4 h means 0 < raw ≤ 240.
  The 4 h group includes the 2 h group.
- Raw ≤ 0 means the space stays occupied and is flagged "estimate reached or exceeded, update needed".
- If either file breaks the rules (wrong columns, duplicate ID, missing time and so on), the page lists
  the problems and shows no totals.
- The Home page says "estimated to finish occupancy" instead of "free" and notes that cleaning time is unknown.

With the sample data the results are 2 free, 16 occupied, 2 cleaning, 4 within 2 h, 6 within 4 h
and 8 flagged. Her 8 test cases and 10 bad-file checks all give her expected results.
The stay times (360/300/270/180/150) are still unvalidated sample values.

## Triage (Member 2)
No new data yet. Built from Member 2's two suggestions:
- **Colour code by level:** 1 red, 2 orange, 3 yellow, 4 green, 5 white (the team chose red and orange
  for levels 1 and 2 instead of the standard CTAS blue and red). A colour key sits at the top of the Triage page.
  The suggested level, the bar chart and the level columns in the tables use these colours.
- **Home page:** the "Waiting room" bar chart uses the same colours. It is the same chart as on the Triage page
  (`level_chart()` in `utils_v2.py`), labelled 1 to 5 because the column is narrow; hovering shows the level name.
  "Overdue for reassessment" uses the same Overdue rule as the Triage page.
- **Wait alerts:** each waiting patient's waited minutes are compared with a threshold for their level.
  Overdue = waited longer than the threshold (red banner and red label). Due soon = waited at least 80% of it
  (orange). Otherwise On time (green). The patient table lists the overdue patients first.
- The thresholds are the CTAS reassessment intervals (1 continuous, 2: 15, 3: 30, 4: 60, 5: 120 min), and
  the 80% "due soon" share is a guess. Both are placeholders in `utils_v2.py` (`REASSESS_MIN`, `DUE_SOON_SHARE`)
  until Member 2 confirms them.

With the sample data: 14 of 18 patients overdue, 2 due soon (P1012, P1005), 2 on time.

## Data
`app_v2/data/` has its own copy of every file. Teammates send their files to Katherine,
who puts them here, so the before app keeps the original samples.

| File | Status |
|---|---|
| forecast.csv | Chengjin's 3-day script run on Nov 17 (saved as `data/Chengjin/3daysforecast_2026-11-17.csv`), dates moved 13 days to Nov 30 to Dec 2 (72 hours). The arrivals use the Nov 17 to 19 weather. Replace it with a run on Nov 29 or 30 (see below). |
| schedule.csv, triage_rules.xlsx, waiting_room.csv, spaces.csv, avg_stay.csv | Still the samples |

## Making an updated forecast
Either Chengjin sends a new `forecast.csv` (copy it into `app_v2/data/`), or Katherine runs the script:
1. Put `ottawa_er_training_data_2025.csv` in `app_v2/tools/` (copy it from `data/Chengjin/`).
2. `pip install prophet pandas requests` (plus `truststore` if you get a certificate error).
3. `python app_v2/tools/forecast.py`. It writes `app_v2/data/forecast.csv` for today and the next 2 days (72 hours).
4. Run the app, check it, commit and push.

If the forecast does not include the demo hour (`DEMO_NOW` in `utils_v2.py`), the app shows
a message telling you what range it does have.
