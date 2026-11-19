"""V3 idea: the whole City of Ottawa. Map of the 5 EDs, the events on, and "what if" incident scenarios.

Pick an event and an incident (e.g. food poisoning at a 6 pm game). The app estimates how many people
go to an ED, which hospital they go to, and when, and adds them to every page's numbers.
The method is in city_v3.py and app_v3/README.md.
"""
import altair as alt
import pandas as pd
import streamlit as st

import city_v3 as city
import utils_v3 as utils  # own name so it never loads utils.py or utils_v2.py

st.set_page_config(page_title="City & events (v3)", layout="wide")
utils.assumptions()

st.title("City of Ottawa: hospitals and events")
st.caption(f"Demo time: {utils.DEMO_NOW:%A %B %d, %H:%M}. Hospital numbers other than the home ED "
           f"({city.hospital_name(city.HOME_ED)}) are estimates scaled from its sample data.")

events, status = city.load_events()
events["when"] = pd.to_datetime(events["date"] + " " + events["start_time"])
forecast_days = sorted(utils.load_forecast()["date"].dt.date.unique())

# ---------------------------------------------------------------- scenario controls
st.header("Incident scenario")
saved = st.session_state.get("incident") or {}
CUSTOM = "Custom event (pick a venue)"
labels = {r.event_id: f"{r.name} · {r.venue} · {r.when:%a %b %d %H:%M}" for r in events.itertuples()}
options = list(labels) + [CUSTOM]
default_id = saved.get("event_id", "E01")

with st.container(border=True):
    left, right = st.columns(2)
    with left:
        event_id = st.selectbox("Event", options, index=options.index(default_id) if default_id in options else 0,
                                format_func=lambda i: labels.get(i, i))
        if event_id == CUSTOM:
            venues = events.drop_duplicates("venue").set_index("venue")
            venue_name = st.selectbox("Venue", venues.index.tolist())
            ev = {"name": f"Custom event at {venue_name}", "venue": venue_name,
                  "lat": venues.loc[venue_name, "lat"], "lon": venues.loc[venue_name, "lon"],
                  "when": pd.Timestamp(f"{utils.DEMO_NOW:%Y-%m-%d} 18:00"), "expected_attendance": 5000,
                  "notes": "Custom event"}
        else:
            ev = events.set_index("event_id").loc[event_id].to_dict() | {"event_id": event_id}
        attendance = st.number_input("Attendance", 0, 100_000, int(saved.get("attendance", ev["expected_attendance"]))
                                     if saved.get("event_id") == event_id else int(ev["expected_attendance"]), 500)
        # The forecast only covers a few days, so the scenario runs on one of them.
        in_window = ev["when"].date() in forecast_days
        day = st.selectbox("Day (forecast days only)", forecast_days,
                           index=forecast_days.index(ev["when"].date()) if in_window else 0,
                           format_func=lambda d: f"{d:%a %Y/%m/%d}")
        start_time = st.time_input("Start time", ev["when"].time(), step=900)
        if not in_window:
            st.caption(f"The real event is on {ev['when']:%a %b %d}, outside the forecast. "
                       "The scenario plays it on the day picked above.")
        if ev.get("notes"):
            st.caption(f"Note: {ev['notes']}")
    with right:
        incident = st.selectbox("Incident", list(city.INCIDENTS),
                                index=list(city.INCIDENTS).index(saved.get("incident", list(city.INCIDENTS)[0])))
        d = city.INCIDENTS[incident]
        same = saved.get("incident") == incident  # keep the user's slider values for the same incident type

        def pct(label, key, lo, hi, step, help_text):
            value = saved[key] if same else d.get(key, 0.15)
            return st.slider(label, lo, hi, float(round(value * 100, 3)), step, format="%.1f%%", help=help_text) / 100

        exposed = pct("Share of attendees exposed", "exposed", 0.0, 100.0, 0.5, "E.g. ate at the affected food stand")
        attack = pct("Share of exposed who get sick or hurt (attack rate)", "attack", 0.0, 100.0, 0.1, None)
        to_ed = pct("Share of those who go to an ED", "to_ed", 0.0, 100.0, 0.1, "The rest stay home or see a clinic")
        value = saved["under18"] if saved else 0.15
        under18 = st.slider("Share under 18 (go to CHEO first)", 0.0, 100.0, value * 100, 1.0, format="%.0f%%") / 100
        st.caption(d["source"])

    params = {"event_id": event_id, "event": ev["name"], "venue": ev["venue"], "lat": float(ev["lat"]),
              "lon": float(ev["lon"]), "attendance": int(attendance),
              "start": f"{day:%Y-%m-%d} {start_time:%H:%M}", "incident": incident,
              "exposed": exposed, "attack": attack, "to_ed": to_ed, "under18": under18}
    n_est = round(attendance * exposed * attack * to_ed)
    b1, b2, b3 = st.columns([1, 1, 3])
    if b1.button("Apply to dashboard", type="primary"):
        st.session_state["incident"] = params
        st.rerun()
    if b2.button("Clear scenario", disabled=not saved):
        st.session_state["incident"] = None
        st.rerun()
    b3.markdown(f"**{attendance:,} attendees x {exposed:.1%} exposed x {attack:.1%} sick x {to_ed:.1%} to an ED "
                f"= about {n_est} ED patients**")

active = st.session_state.get("incident")
if active and active != params:
    st.info("You changed the settings. Click **Apply to dashboard** to update the map and every page.")

# ---------------------------------------------------------------- map and impact
plan = city.incident_plan(active) if active else None
venue = {"lat": active["lat"], "lon": active["lon"], "tip": f"<b>{active['venue']}</b><br/>{active['event']}"} if active else None

st.header("Map")
st.markdown(city.map_legend(plan), unsafe_allow_html=True)
st.pydeck_chart(city.city_map(events, plan, venue), height=520)
st.caption(("" if plan else "Apply a scenario to see where patients go. ") + "Locations are approximate.")
st.markdown("**What the labels on the map mean** (all 5 EDs are open 24/7)")
st.dataframe(pd.DataFrame([
    ["Ottawa Hospital - Civic", "Civic", "The Ottawa Hospital, Civic Campus (Carling Ave)",
     "The ED the sample data describes"],
    ["Ottawa Hospital - General", "General", "The Ottawa Hospital, General Campus (Smyth Rd)",
     "Same hospital network as the Civic, second campus"],
    ["Queensway Carleton", "QCH", "Queensway Carleton Hospital (Nepean, west end)",
     "Nearest ED to Canadian Tire Centre"],
    ["Montfort", "Montfort", "Hôpital Montfort (east end)", "Francophone hospital"],
    ["CHEO (children)", "CHEO", "Children's Hospital of Eastern Ontario",
     "Only patients 18 and under; next to the General"],
], columns=["Map label", "Short name in tables", "Hospital", "Notes"]), hide_index=True, width="stretch")

if plan:
    start = pd.Timestamp(active["start"])
    st.header(f"Impact: {plan['patients']} ED patients from {active['event']}")
    h = plan["hospitals"]
    total_cap = int(h["capacity"].sum())
    if plan["patients"] > total_cap:
        st.error(f"More patients ({plan['patients']}) than the surge capacity of all 5 EDs together ({total_cap}). "
                 "The city would need a code orange (mass casualty) response.")
    elif h["over_capacity"].any():
        st.warning("At least one ED goes over its surge capacity.")
    else:
        st.success("Every receiving ED stays within its surge capacity.")

    # Peak nurse gap during the scenario window, without and with the incident, per ED.
    window = lambda df: df[(df["timestamp"] >= start.floor("h")) &
                           (df["timestamp"] <= start.floor("h") + pd.Timedelta(hours=city.SCENARIO_HOURS))]
    rows = []
    for r in h.itertuples():
        before = window(utils.staffing_table(r.hospital_id, with_incident=False))
        after = window(utils.staffing_table(r.hospital_id, with_incident=True))
        rows.append({"Hospital": r.short_name, "Drive (min)": r.drive_min, "Incident patients": r.patients,
                     "Surge capacity": r.capacity, "Over capacity": r.over_capacity,
                     "Peak nurse gap, no incident": int(before["nurse_gap"].max()),
                     "Peak nurse gap, with incident": int(after["nurse_gap"].max()),
                     "Peak doctor gap, with incident": int(after["doctor_gap"].max()),
                     **{f"CTAS {lvl}": getattr(r, f"ctas_{lvl}") for lvl in utils.CTAS}})
    table = pd.DataFrame(rows)

    def red_if_over(v):
        return "background-color:#D62728;color:white;font-weight:bold" if v > 0 else ""

    st.dataframe(table.style.map(red_if_over, subset=["Over capacity"]), hide_index=True)
    st.caption(f"Ordered by distance from {active['venue']}. Nurse/doctor gap = needed minus scheduled, highest hour "
               f"from {start:%H:%M} to {city.SCENARIO_HOURS} h later (forecast hours only). Surge capacity = treatment "
               "spaces free now + estimated to finish within 4 h. CTAS columns are expected patients per level.")

    st.subheader("Incident arrivals per hour, by hospital")
    hourly = plan["hourly"]
    if hourly["extra_arrivals"].sum() > 0:
        hourly = hourly.assign(time=hourly["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S"))
        chart = alt.Chart(hourly).mark_bar().encode(
            x=alt.X("time:T", title=None, axis=alt.Axis(format="%a %H:%M", labelAngle=0)),
            y=alt.Y("sum(extra_arrivals):Q", title="Extra arrivals"),
            color=alt.Color("short_name:N", title=None, legend=alt.Legend(orient="top")),
            tooltip=[alt.Tooltip("time:T", title="Hour", format="%a %H:00"),
                     alt.Tooltip("short_name:N", title="Hospital"),
                     alt.Tooltip("extra_arrivals:Q", title="Extra arrivals")])
        st.altair_chart(chart.properties(height=300), width="stretch")
    else:
        st.write("No ED patients expected from this scenario.")

# ---------------------------------------------------------------- events list
st.header("Events")
st.caption(status)
with st.expander("Live events (Ticketmaster)", expanded=False):
    st.markdown(
        "Events come from `data/events.csv` (hand-made) plus, when a key is set, live Ottawa events from the free "
        "**Ticketmaster Discovery API** (next 14 days, refreshed every 3 hours). Get a free key at "
        "[developer.ticketmaster.com](https://developer.ticketmaster.com/) (sign up, then *My Apps*: the "
        "*Consumer Key*). For the team app, save it once as `TICKETMASTER_API_KEY` in Streamlit Cloud "
        "**Settings > Secrets**. To try it now, paste it here (kept for this browser session only, never saved).")
    k1, k2 = st.columns([3, 1])
    pasted = k1.text_input("Ticketmaster key", type="password", value=st.session_state.get("tm_key", ""))
    if pasted != st.session_state.get("tm_key", ""):
        st.session_state["tm_key"] = pasted
        st.rerun()
    if k2.button("Refresh live events", disabled=not city.ticketmaster_key()):
        city.live_events.clear()
        st.rerun()
show = events.sort_values("when")[["when", "name", "venue", "category", "expected_attendance", "source", "source_url"]]
st.dataframe(show, hide_index=True, column_config={
    "when": st.column_config.DatetimeColumn("Start", format="ddd MMM D, HH:mm"),
    "expected_attendance": st.column_config.NumberColumn("Attendance (est.)", format="%d"),
    "source_url": st.column_config.LinkColumn("Link", display_text="open"),
})

with st.expander("How the estimates are made, and sources"):
    st.markdown(f"""
- **Hospitals:** 5 Ottawa EDs open 24/7. Only {city.hospital_name(city.HOME_ED)} has data files (sample). The others
  use the same hourly forecast and schedule, scaled by annual ED visits (`data/hospitals.csv` lists the source for each).
- **Events:** `data/events.csv` is a hand-made list, researched Nov 18, 2026. If a Ticketmaster API key is set
  (`TICKETMASTER_API_KEY` in Streamlit secrets), live Ottawa events are added. Their attendance is the venue capacity.
- **Patients:** attendance x share exposed x attack rate x share who go to an ED (sliders above).
- **Arrival time:** symptom onset after the event start (lognormal curve per incident type), plus drive time
  (straight-line distance x {city.ROAD_FACTOR}, at {city.DRIVE_KMH} km/h).
- **Which hospital:** the nearest ED until its surge capacity is used, then the next nearest. Under-18s go to CHEO first.
  If every ED is full, the rest are shared by ED size. In real life paramedics and the hospitals coordinate this.
- **Impact:** the incident patients are added to the expected arrivals, so nurses and doctors needed go up on the
  Home and Forecast pages for the hospital picked in the sidebar.
""")
