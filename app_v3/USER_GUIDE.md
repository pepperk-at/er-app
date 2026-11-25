# ER App v3 User Guide

Nov 25, 2026 · Katherine Hall

## Overview

ER App v3 is a shift dashboard for an Ottawa emergency department. In one place it shows the arrival forecast and staffing gaps, who is in the waiting room and how long they've waited against CTAS targets, and which treatment spaces are free or about to free up. Version 3 adds a city view: all five Ottawa EDs on a map, upcoming events, and an incident scenario that sends extra patients to each hospital.

It's built for the charge nurse or shift lead who has to decide, before a rush, whether to call in staff or speed up discharges.

The forecast comes from Chengjin's model. Patient records, treatment spaces and the staff schedule are sample data, not real patients. The demo clock is fixed (Monday, November 30 at 18:00), so the numbers stay the same every time you open the app.

## Getting started

The easiest way in is the online version: [er-app-njjqu4r98jkzf5dru58spw.streamlit.app](https://er-app-njjqu4r98jkzf5dru58spw.streamlit.app). Nothing to install. If it has been idle for a while, Streamlit Cloud may ask you to wake it up first, which takes about a minute.

To run it on your own computer, open a terminal in the `ER-App` folder and run:

```
.venv\Scripts\python.exe -m streamlit run app_v3/Home.py
```

The app opens in your browser on the Home page. Every page has the same sidebar:

1. Page list at the top: Home, City and Events, Forecast and Staffing, Triage, Treatment Spaces.
2. Hospital picker. Choose which of the five Ottawa EDs the pages show. The default is the Ottawa Hospital Civic Campus, the only ED with its own data files.
3. Assumptions sliders: nursing minutes per patient (default 45), patients one doctor sees per hour (2.5) and average minutes per doctor assessment (20). Changing them updates every page.
4. Project team, showing who built each part.

Your hospital choice, slider values and any incident scenario stay in place as you move between pages. They reset when you reload the page or close the browser tab.

## Using the app

Start on Home for the summary, then open the page that matches the problem you see. The City and Events page is where you set up a "what if" incident.

### Home: the shift at a glance

The banner at the top gives the one thing to act on. Red means a rush is coming, you're short of nurses and fewer than 4 treatment spaces are free or freeing up. Orange means a rush with a nurse shortfall. Green means staffing looks fine for the next 24 hours.

Under it, three columns pull one number from each part of the app:

- Forecast and staffing: the busiest hour in the next 24 hours and the nurse gap at that hour.
- Waiting room: how many patients are waiting, how many are past their CTAS target, and a bar chart by level.
- Treatment spaces: spaces free now and spaces expected to free up within 2 hours.

Hover the small info icons for what each number counts. The CTAS table at the bottom lists each triage level, what it means, the target time to see a physician and how often to reassess.

### Forecast and Staffing: plan the next three days

1. Read the arrivals chart. It shows expected patients per hour for the 3 forecast days. If an incident is applied, a second line shows arrivals with the incident added.
2. Compare the nurse and doctor charts. Blue is the number needed, orange is the number scheduled. Where blue sits above orange, you're short.
3. Check the short-staffed table at the bottom. It lists every hour with a nurse or doctor gap, so you know which shifts to fill.
4. Try the sidebar sliders to test a different assumption, for example 60 nursing minutes per patient instead of 45.

Hover a line to see the exact value for that hour.

### Triage: suggest a level and watch the waiting room

1. Pick the presenting complaint.
2. Enter heart rate, oxygen saturation, temperature and pain score.
3. Click **Suggest level**. The app shows a coloured level badge, the reasons behind it, and the CTAS target time.
4. The patient joins the waiting room as NEW1, NEW2 and so on, and the counts on Home update too.

The suggestion comes from a sample rules table: the complaint sets a starting level, and any vital sign past its cutoff can move it to a more urgent level. The nurse always makes the final call.

The waiting room section below shows alerts first (most urgent patient past target), then a chart by level, an estimated wait for a new patient at each level based on the doctors on duty, and a full table sorted with the most overdue patients at the top.

### Treatment Spaces: know what's free

The top boxes count spaces that are free now, occupied and being cleaned. The next box estimates how many occupied spaces will free up within 2 and 4 hours. The 4-hour number already includes the 2-hour number, so don't add them.

An orange warning lists spaces whose patient has stayed longer than the average for their level. Those need someone to update their status. The detail table shows every space with its time used, assumed stay and estimated time left.

### City and Events: run an incident scenario

1. Pick an event from the list, or pick "Custom event" and choose a venue. The default is a what-if sold-out game at Canadian Tire Centre at 18:00 on November 30.
2. Check the attendance, day and start time. Only the three forecast days can be picked.
3. Pick the incident type: food poisoning, normal event or crowd injury. The sliders fill in with default rates.
4. Adjust the sliders if you want: share exposed, share who get sick or hurt, share who go to an ED, and share under 18.
5. Read the estimate line (attendees x exposed x sick x to an ED) and the Where patients go table, which updates as you move the sliders.
6. Click **Apply to dashboard**.

After you apply, the map draws a line from the venue to each ED receiving patients, labelled with patient count and drive time. An Impact section shows each ED's surge capacity, how far over it goes and the nurse and doctor gaps with and without the incident. A banner appears on every other page, and the Home and Forecast numbers for the hospital in the sidebar now include the extra patients.

Click **Clear scenario** to go back to normal numbers.

## Features and terms

A quick lookup for the controls and labels you'll see.

| Feature or term | Where | What it does or means |
| --- | --- | --- |
| Hospital picker | Sidebar | Switches every page to one of 5 EDs: Civic, General, Queensway Carleton (QCH), Montfort or CHEO. Only Civic has its own data; the others are scaled by annual ED visits. |
| Assumptions sliders | Sidebar | Set nursing minutes per patient and doctor throughput. Nurses needed = arrivals x nursing minutes / 60. Doctors needed = arrivals / patients per doctor per hour. |
| Nurse gap, doctor gap | Home, Forecast | Staff needed minus staff scheduled for that hour. Above 0 means short. |
| Past target | Triage, Home | Patient has waited longer than the CTAS target time to see a physician, counted from arrival. Shown in red. |
| Near target | Triage | Patient has used at least 80% of their target time. Shown in orange. The 80% is a team guess. |
| Within target | Triage | Patient still has more than 20% of their target time left. |
| CTAS targets | Home, Triage | Level 1 immediately, level 2 within 15 min, level 3 within 30 min, level 4 within 60 min, level 5 within 120 min. |
| Suggest level | Triage | Suggests a CTAS level from complaint and vitals, then adds the patient to the waiting room for this session. |
| Estimated wait for a new patient | Triage | Expected wait at each level, given who is already waiting and the doctors on duty now. |
| Free now | Home, Treatment Spaces | Spaces marked empty, clean and ready. |
| Estimated to finish within 2 h / 4 h | Home, Treatment Spaces | Occupied spaces whose patient should leave soon, based on average stay for their level. Cleaning time not included. |
| Update needed | Treatment Spaces | Patient has been in the space at least as long as the average stay. Status needs checking. |
| Apply to dashboard / Clear scenario | City and Events | Adds the incident's patients to the forecast on every page, or removes them. |
| Where patients go | City and Events | Every ED nearest first, with drive time, patient count and why it gets patients or not. |
| Surge capacity | City and Events | Spaces free now plus spaces expected to free up within 4 hours, per ED. |
| Map toggles | City and Events | Show or hide the 10 km circle and 5, 10 and 15 minute drive rings around the picked hospital, and Ottawa's census areas. |
| Map hover | City and Events | Hover an ED for status and patients, a star for its events, or a line for patients and drive time. |
| Live events (Ticketmaster) | City and Events | Paste a free Ticketmaster key to add live Ottawa events. Without a key the app uses its built-in list of 27 events. |

Where incident patients go follows three rules. Under-18s go to CHEO first, up to its surge capacity. Everyone else goes to the nearest adult ED until it's full, then the next nearest. Once every ED is full, the rest are split among the adult EDs by size, not distance.

## Limits and troubleshooting

The app is a planning demo, not a clinical tool. Keep these limits in mind when you present or read the numbers.

- The forecast is trained on synthetic hourly arrivals plus real Ottawa weather, so volumes are illustrative. Doctor gaps in particular come out high.
- Patient, space and schedule data are samples for the Civic. On the Triage and Treatment Spaces pages, every hospital shows the Civic's records.
- Drive times are straight-line distance x 1.4 at 40 km/h, not real roads. Everyone is assumed to drive; paramedic dispatch and code orange coordination aren't modelled.
- Crowd injury rates are placeholders with no source yet. The 25% who go to an ED for food poisoning is a team assumption.
- Some event start times and attendance numbers in the built-in list are estimates. Check the notes column before demo day.
- Reassessment isn't tracked, because the waiting room file has no last-reassessed time. Alerts measure time to physician assessment only.

| Problem | What to do |
| --- | --- |
| Map and other pages didn't change after I moved the sliders | Click **Apply to dashboard**. A blue note appears when your settings differ from the applied scenario. |
| Warning that patients arrive after the forecast ends | The incident is too late in the 3-day window. Pick an earlier day or start time. |
| My triaged patients and scenario disappeared | They only last for the browser session. Reloading the page clears them. |
| Treatment Spaces shows a red "data is invalid" box | A row in spaces.csv or avg_stay.csv is broken. The box lists each problem to fix. |
| Online app shows a sleep or wake-up screen | Click the wake-up button and wait about a minute. |
| Map hover box appears in the wrong place | Make sure requirements.txt still pins Streamlit 1.65.0. Newer versions move the box. |
