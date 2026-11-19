# ER Wait Dashboard: V3 version (new ideas)

A copy of the AFTER app (`app_v2/`) made on Nov 18, 2026, for trying new ideas.
`app_v2/` stays as the AFTER version the team agreed on; root stays as the BEFORE version.

> **Not committed or pushed yet (Nov 18, 2026).**

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
| Nov 18, 2026 | City of Ottawa scale: all 5 EDs, map, events, incident scenarios | Katherine | Built, not pushed |

## Idea 1: City of Ottawa, events and incidents
New page **City & Events** (`pages/0_City_and_Events.py`, logic in `city_v3.py`) and a **Hospital** picker
in the sidebar of every page.

**Hospitals** (`data/hospitals.csv`): Civic, General, Queensway Carleton, Montfort, CHEO (18 and under).
- Only one ED has data files. `HOME_ED = "civic"` in `city_v3.py` (change it if the team's ED is a different one).
- The other EDs use the same forecast and schedule, scaled by annual ED visits. Sources are in the file:
  The Ottawa Hospital over 170,000 a year across 2 EDs (split evenly, an assumption), QCH about 78,000,
  Montfort over 50,000, CHEO 71,273 (Apr 2024 to Mar 2025). Map locations are approximate.
- Triage and Treatment Spaces pages always show the home ED's patient records (there are none for the others).

**Events** (`data/events.csv`): a hand-made list, researched Nov 18. Each row has its source.
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
- Nov 18: Ticketmaster developer account pending approval, so the app uses events.csv only for now.
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

## Paused here (Nov 18, 2026)
Done today: app_v3 folder, City & Events page (5 EDs, events, incident scenarios), light map with legend,
hover tips, label table, straight lines (thickness = patients), routing rules written up above.

Not committed or pushed. Katherine said "not yet"; wait for her go-ahead.

To do next:
- Ticketmaster: add `TICKETMASTER_API_KEY` to `.streamlit/secrets.toml` (and Streamlit Cloud secrets) once the
  developer account is approved, then test live events.
- Confirm with the team: Civic is the right `HOME_ED`, the visit numbers per campus, and the 25% who go to an ED.
- Decide: share the overflow by ED size (now) or by distance.
- Check hovering over the new lines in a real browser (only checked with a screenshot so far).
- Before pushing: click through every page (pydeck comes with Streamlit, so requirements.txt needs no change).
