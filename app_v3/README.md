# ER Wait Dashboard: V3 version (new ideas)

A copy of the AFTER app (`app_v2/`) made on Nov 18, 2026, for trying new ideas.
`app_v2/` stays as the AFTER version the team agreed on; root stays as the BEFORE version.

> **Paused Nov 25, 2026. User guide added (`USER_GUIDE.md`). Pushed Nov 21: Idea 2 (CTAS alert names) and the map hover fix (Streamlit pinned to 1.65.0).
> All pages load on Streamlit Cloud and map hover works there. Open to-dos: see "Paused here" at the bottom.**

## Run on your computer
From the `er-app` folder:
```
.venv\Scripts\python.exe -m streamlit run app_v3/Home.py
```

## How it is kept separate
- Helper modules are `utils_v3.py` (imported as `utils`) and `city_v3.py` (imported as `city`), so it never
  loads `utils.py` or `utils_v2.py`.
- Reads only `app_v3/data/` (a copy of `app_v2/data/` on Nov 18, plus `hospitals.csv` and `events.csv`).
- `tools/forecast.py` writes to `app_v3/data/forecast.csv`.
- Everything in `app_v2/README.md` (forecast, triage alerts, treatment spaces) applies here as of Nov 18.

## New ideas
| Date | Idea | From | Status |
|---|---|---|---|
| Nov 18, 2026 | City of Ottawa scale: all 5 EDs, map, events, incident scenarios | Katherine | Built, pushed Nov 20 |
| Nov 21, 2026 | Wait alerts renamed to CTAS terms (Past / Near / Within target) | Godwin's question | Built, pushed Nov 21 |

## Idea 1: City of Ottawa, events and incidents
New page **City & Events** (`pages/0_City_and_Events.py`, logic in `city_v3.py`) and a **Hospital** picker
in the sidebar of every page.

**Hospitals** (`data/hospitals.csv`): Civic, General, Queensway Carleton, Montfort, CHEO (18 and under).
- Only one ED has data files. `HOME_ED = "civic"` in `city_v3.py` (change it if the team's ED is a different one).
- The other EDs use the same forecast and schedule, scaled by annual ED visits. Sources are in the file:
  The Ottawa Hospital over 170,000 a year across 2 EDs (split evenly, an assumption), QCH about 78,000,
  Montfort over 50,000, CHEO 71,273 (Apr 2024 to Mar 2025). Map locations are approximate.
- Triage and Treatment Spaces pages always show the home ED's patient records (there are none for the others).

**Events** (`data/events.csv`): a hand-made list, rebuilt Nov 20 (27 events, Nov 20 to Dec 10). Each row has its
source. Senators home games come from the NHL's public schedule (`api-web.nhle.com`, no key, unofficial); this fixed
the New Jersey game to Dec 3 (was Dec 4) and the Charge opener to 14:00. Attendance for most non-hockey rows is a guess
(see `notes`). Events in Gatineau are left out, since patients there would go to Quebec hospitals.
- No official City of Ottawa events feed was found. The free source is the Ticketmaster Discovery API.
  To switch on live events, get a free key at developer.ticketmaster.com and save it as
  `TICKETMASTER_API_KEY = "..."` in `.streamlit/secrets.toml` (locally, already in `.gitignore`) or in the
  Streamlit Cloud app's **Settings > Secrets**. Without a key, or if the call fails, the app uses events.csv only.
- To try live events without a secrets file, paste the key in **Live events (Ticketmaster)** on the City & Events
  page (kept for that browser session only). **Refresh live events** skips the 3-hour cache.
- Map: a legend above it; hover an ED (status, patients, capacity, drive), a venue (its events), or a line
  (patients, % of the incident, drive time). Teal venues come only from live events. Light Carto basemap
  (free, no key), ED names on white tags (`MAP_LABELS` in `city_v3.py`), and a table below the map explaining
  each label.
- Lines (Nov 18, replaced the 3D arcs): flat 2D map (tilt locked off); a straight line (PathLayer) from the
  venue to each ED that gets patients. Thickness = patients relative to the busiest ED (3 to 16 px); colour =
  the ED's status (red over capacity, orange receiving).
- pydeck gotcha (Nov 18): plain-text layer settings must be quoted, e.g. `width_units="'pixels'"`. Unquoted,
  pydeck turns the text into a data expression, deck.gl gets no unit, and the lines draw as huge stripes across
  the map. Tested in headless Chrome.
- Hover fix (Nov 18): Streamlit 1.65 drew the hover box one map-height above the mouse (off the map), and it
  escapes HTML in hover text. `TOOLTIP_STYLE` adds `top: 100%` to cancel the offset, and tips are plain text.
  Tested in headless Chrome. If Streamlit is upgraded and the box lands below the map, remove `top`.
  Because of this, `requirements.txt` pins `streamlit==1.65.0` (Nov 21): unpinned, Streamlit Cloud installed a
  newer release and the hover box opened one map-height below the mouse.
- Map restyle (Nov 19): dark Carto basemap (light grey road and place names), ED dots all the same size
  (no longer scaled by visits), events as stars (IconLayer, SVG star), incident venue as a big gold star,
  a buffer per ED (one colour per ED), and Ottawa's 2021 dissemination areas plus the
  City of Ottawa boundary (Statistics Canada, `data/ottawa_da.geojson`, `data/ottawa_city.geojson`, made by
  `tools/ottawa_boundaries.py`). Both new layers have on/off toggles above the map.
- Buffers (Nov 19, changed from 50 km at 50%): the 5 EDs are within about 15 km of each other, so 50 km circles
  covered the whole city and stacked into a solid colour. Now 10 km (`BUFFER_KM`) with a light fill (~12%,
  `BUFFER_ALPHA`) and a solid edge, plus thin drive-time rings at 5, 10 and 15 min (`DRIVE_ZONES_MIN`). The rings
  use the routing rule (straight line x 1.4 at 40 km/h), so 10 km is about 21 min. Circles, not real road times.
- Buffer per hospital (Nov 19): only the ED picked in the sidebar **Hospital** dropdown gets the buffer and rings
  (`focus` in `city_map`). Change the dropdown to see another ED's zone.
- Where patients go (Nov 19): a **Where patients go** table under the scenario settings (`route_table` in
  `city_v3.py`) lists every ED nearest first, with drive time, patients and why (nearest adult ED, children first,
  not needed, full and sharing overflow). It updates before **Apply**. After Apply, each line has a label
  ("3 pt · 8 min") and the map zooms to the venue and the EDs that get patients.
  Example: NAC (300 people, food poisoning defaults) gives 3 patients, all to the Civic (8 min); General is 9 min.
- Loop test (Nov 19): every event x incident type, a custom event at each venue, 11 edge cases (0 and 100,000
  attendees, all sliders at 0 or 100%, late starts) and every page x every hospital. No errors. Fixed 3 edge cases:
  with 0 patients the table said "Not needed: nearer EDs had space" and the page said "stays within capacity"
  (now "No patients expected"); CHEO now says when it is full and extra children go to adult EDs; a warning shows
  when patients arrive after the forecast ends (e.g. a late start on the last day), since they can't be in the
  staffing numbers.
- Nov 20: Ticketmaster key could not be obtained, so the app uses events.csv only. The live-events code stays in
  case a key turns up. Alternatives looked at: NHL public schedule (no key, used to build events.csv), SeatGeek
  (needs a developer signup), City of Ottawa open data (no events dataset).
- Live events have no attendance, so the app uses the venue capacity (`VENUE_CAPACITY` in `city_v3.py`), or 500.
- On demo day (Mon Nov 30) there is **no big game in Ottawa**: the Senators play in Nashville. Real events that
  night are small (NAC concerts, a Hard Rock Casino show). So row E01 is a **what-if** sold-out game at
  Canadian Tire Centre at 18:00, the default scenario. Real Senators and Charge games on other days are listed too.

**Incident scenario**: pick an event (or a custom event at a venue), a day and start time, and an incident type.
- ED patients = attendance x share exposed x attack rate x share who go to an ED (sliders).
- Food poisoning defaults: 5% exposed, 75% attack rate (77.7% in a catering outbreak, India),
  25% go to an ED (assumption), onset median 2.5 h (CDC MMWR: 30 min to 8 h).
- Normal event: 1 per 1,000 treated on site, 0.027 per 1,000 taken to hospital (pooled mass gathering studies).
- Crowd injury: placeholder values, no source yet.
- Arrival time = onset after the start + drive time (straight line x 1.4 at 40 km/h).
- Which hospital (`incident_plan` in `city_v3.py`), in this order:
  1. Under-18s go to CHEO up to its surge capacity; any children left over join the adults.
  2. Everyone else goes to the nearest adult ED by drive time until its surge capacity is used, then the next nearest.
  3. Once every ED is full, the rest are shared among the adult EDs by ED size (annual visits), not by distance.
     CHEO gets none of this overflow.
- Limits: everyone is treated as driving to hospital; no paramedic dispatch, code orange coordination, or patients
  choosing their own ED. Drive times are straight line x 1.4 at 40 km/h, not real roads.
- Surge capacity = spaces free now + estimated to finish within 4 h (Gulchaman's rules, scaled per ED).
- **Apply to dashboard** adds the incident patients to the expected arrivals, so the Home and Forecast pages
  (and the nurse/doctor gaps) change for the hospital picked in the sidebar. A banner on every page says so.

With the default scenario (17,000 at Canadian Tire Centre, 18:00, food poisoning): about 159 ED patients;
QCH is nearest (22 min). All 5 EDs together have a surge capacity of 35, so every ED goes over and the page
says a code orange (mass casualty) response would be needed.

| ED | Drive | Surge capacity | Patients | Over by | Line |
|---|---|---|---|---|---|
| QCH | 22 min | 7 | 40 | 33 | 15 px |
| Civic | 40 min | 8 | 43 | 35 | 16 px |
| CHEO | 51 min | 7 | 7 (children) | 0 | 5 px |
| General | 52 min | 8 | 43 | 35 | 16 px |
| Montfort | 59 min | 5 | 26 | 21 | 11 px |

Steps 1 and 2 place only 35 patients; the other 124 are shared by size, so Civic and General get more than QCH
even though QCH is nearest. If the team prefers, the overflow could be shared by distance instead.

Still to check: the visit numbers per campus, whether Civic is the right home ED, and the share who go to an ED.

## Idea 2: wait alerts in CTAS terms (Nov 21, 2026)
Godwin asked what Overdue / Due soon / On time mean and wanted them to match real ED terms.

CTAS (Murray et al., 2004) uses the same times (1 immediate, 2: 15, 3: 30, 4: 60, 5: 120 min) for two clocks:
time to physician initial assessment, counted from arrival, and the nurse reassessment interval, which restarts
after each reassessment. The app counts from arrival and `waiting_room.csv` has no last-reassessed time, so it
was really measuring the physician-assessment target while calling it reassessment. The team chose to rename
(option A) rather than add a `last_reassessed` column (option B).

- Labels: Overdue → **Past target**, Due soon → **Near target**, On time → **Within target**. Same rule and colours.
- Home: "Overdue for reassessment" → "Past CTAS target". The CTAS table gets a "See a physician within" column
  next to "Reassess while waiting".
- Triage: banners, table heading, `threshold_min` → `target_min`, and the caption say "CTAS target time to physician
  assessment". The new-patient result shows both the physician target and the reassessment interval.
- `utils_v3.py`: new `TARGET_MIN` drives the alerts; `REASSESS_MIN` is kept for display. `DUE_SOON_SHARE` →
  `NEAR_TARGET_SHARE` (still 80%, still a team guess).
- Sample data result unchanged: 14 of 18 past target, 2 near target (P1012, P1005), 2 within target.
- `app_v2` still uses the old labels.

## Page-by-page review (Nov 19, 2026)
**Home** (done):
- Sidebar **Hospital** dropdown: picks which Ottawa ED every page shows (only the home ED has data files; the
  others are scaled by annual visits). Fixed: it needed two clicks to switch. The widget now has its own key
  (`_hospital`) instead of `index=`; the sidebar sliders got the same fix.
- Info icons (tooltips) on Patients waiting, Overdue for reassessment (renamed Past CTAS target on Nov 21), Free now, and Estimated to finish occupancy
  within 2 h.
- New **Triage levels (CTAS)** table at the bottom: level, name, plain meaning, reassessment interval.

**City & Events** (done): dark map, ED stars and buffers, DA layer, Where patients go table (Road km to 2 decimals),
loop test and 3 edge-case fixes. Details in Idea 1 above.

**Forecast & Staffing, Triage, Treatment Spaces** (done, Nov 20).

## Paused here (Nov 25, 2026)
Done on Nov 25:
- User guide written: `app_v3/USER_GUIDE.md`, pushed to `main` (`ddb2486`). It was drafted from the code and this
  README, not by clicking through the app, so check the steps against the live app. An editable copy is in Claude
  Docs (https://claude.ai/artifact/G9zTG9EwshEpdDErE8dSEK); the two are not synced, so edit one and copy it over.
- The guide's byline names Katherine Hall in the public repo; change it to the group name if preferred.
- This README note is committed locally; push it with the next change.

Done on Nov 21:
- Idea 2 (CTAS alert names) pushed to `main` (`b6203b4`), with the Nov 20 README updates. `app_v2` keeps the old
  labels on purpose, so the team can see the before and after.
- Error check of all 5 V3 pages, run locally with Streamlit's test runner, with no scenario and with the default
  food poisoning scenario applied. No crashes or Python errors. The red and orange boxes are the app's own alerts.
- Reply drafted for Godwin explaining Past / Near / Within target (not sent yet).
- Before/after scenario for the presentation (Triage wait estimate at 18:00, sample data): calling in 2 doctors
  (4 to 6) cuts the level 3 estimate from 35 to 23 min and level 5 from 90 to 60 min, about a third less. Only
  doctors change the estimate; nurses do not. The full staffing gap (14 doctors) is not used because Chengjin's
  synthetic volume is too high.
- MAE for the forecast is Chengjin's part; the dashboard does not report it.
- Deployed V3 app checked: https://er-app-njjqu4r98jkzf5dru58spw.streamlit.app. All 5 pages load with no errors
  and match the local numbers (headless Chrome screenshots; clicks not tested).
- Map hover fixed on Streamlit Cloud (`0ade4f7`): the box opened about 570 px below the mouse, under the map.
  Cause: the cloud ran a newer Streamlit than 1.65, so the `top: 100%` fix pushed the box down. Pinned
  `streamlit==1.65.0` in `requirements.txt`. Retested with a mouse sweep in headless Chrome: all 14 hover boxes
  (5 EDs, 9 venues) open next to the mouse, locally and on the cloud.
- Seen on Treatment Spaces, left for Gulchaman to decide: the heading says "Fictional Ottawa ER" (other pages
  name the Civic Campus), and the Interpretation column is cut off at the right edge.

Done on Nov 20: page-by-page review of all pages; `events.csv` rebuilt for Nov 20 to Dec 10; app code pushed
(`8e62825`). Team emailed with 4 questions (see below), and asked on Teams to check it.

Pushed to `main` on Nov 21: the Streamlit pin (`0ade4f7`). This README update is committed; push it with the next
change (it only changes notes, not the app).

Local only, not on GitHub:
- `reference/evidence.md`: personal notes (sources and assumptions, testing, contribution log, GenAI use).
- Git branch `backup-before-handoff-removal`: backup from removing the handoff folders. Delete it with
  `git branch -D backup-before-handoff-removal` once the three `data/` handoff folders look right.

V3 on Streamlit Cloud (main file `app_v3/Home.py`): https://er-app-njjqu4r98jkzf5dru58spw.streamlit.app

Teammates' raw handoffs (`data/Chengjin/`, `data/Godwin/`, `data/Gulchaman/`) are kept local only and are in
`.gitignore`, so they are not in the public repo. Three old Chengjin files (`forecast.csv`, `forecast.zip`,
`forecast/forecast.py`) were pushed before Nov 20 and are still in the GitHub history.

To do next:
- Send the reply to Godwin.
- In the deployed V3 app, try the clicks: Apply a scenario, change the Hospital picker (pages load and map hover works, Nov 21).
- Treatment Spaces heading and cut-off column: wait for Gulchaman's call.
- Confirm with the team: Civic is the right `HOME_ED`, the visit numbers per campus, and the 25% who go to an ED.
- Decide: share the overflow by ED size (now) or by distance.
- Check hovering over the scenario lines in a real browser (dots and stars checked with a mouse sweep, Nov 21).
- Check the unconfirmed start times and attendance guesses in `events.csv` (see its `notes` column) before demo day.
- Class pitch Part 2 and the slide still say triage estimates wait times per level (see `app_v2/README.md`).
  They should use the new alert names (Past / Near / Within CTAS target), now that Idea 2 is pushed.
- The team was emailed on Nov 20 about the questions above; record their answers here.
- Write out full citations for the incident sources (CDC MMWR, India outbreak, mass gathering studies).
