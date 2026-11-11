"""Shared helpers for the AFTER app (app_v2): every page imports from here.

Differences from the original app:
- forecast.csv is Chengjin's 48-hour Prophet forecast (made by tools/forecast.py).
- Each forecast row gets a full timestamp (date + hour), so the two days don't mix.
- The schedule is the same every day, so it is joined on hour.

All data files follow the team's file agreement. To swap sample data for real data,
replace the file in the data/ folder with the same name and the same columns.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "data"

# The demo pretends it is this moment. Change it if the sample data changes.
DEMO_NOW = pd.Timestamp("2026-11-30 18:00")

# CTAS reassessment intervals in minutes (Murray et al., 2004). Level 1 = continuous care.
REASSESS_MIN = {1: 0, 2: 15, 3: 30, 4: 60, 5: 120}


# @st.cache_data means: read the file once, then reuse it on every click (fast).


def _with_timestamp(df):
    # Accept 2026-11-30 or 2026/11/30, then build one timestamp per row.
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"].astype(str).str.replace("/", "-"))
    df["timestamp"] = df["date"] + pd.to_timedelta(df["hour"], unit="h")
    return df.sort_values("timestamp", ignore_index=True)


@st.cache_data
def load_forecast():
    return _with_timestamp(pd.read_csv(DATA / "forecast.csv"))



@st.cache_data
def load_schedule():
    return pd.read_csv(DATA / "schedule.csv")


@st.cache_data
def load_triage_rules():
    complaints = pd.read_excel(DATA / "triage_rules.xlsx", sheet_name="complaints")
    vitals = pd.read_excel(DATA / "triage_rules.xlsx", sheet_name="vitals")
    return complaints, vitals


@st.cache_data
def load_waiting_room():
    df = pd.read_csv(DATA / "waiting_room.csv", parse_dates=["arrival_time"])
    return df


@st.cache_data
def load_spaces():
    spaces = pd.read_csv(DATA / "spaces.csv", dtype={"ctas_level": "Int64", "time_in_space_min": "Int64"})
    avg = pd.read_csv(DATA / "avg_stay.csv")
    return spaces, avg


def assumptions():
    """Staffing assumptions shown as sliders in the sidebar on every page.

    st.session_state remembers values between clicks and between pages.
    The slider value is copied into a plain key (nurse_min etc.) so it survives page changes.
    """
    st.sidebar.header("Assumptions")
    sliders = [
        ("nurse_min", "Nursing minutes per patient", 10, 120, 45, 5),
        ("pts_per_doc", "Patients one doctor sees per hour", 1.0, 5.0, 2.5, 0.5),
        ("assess_min", "Average minutes per doctor assessment", 5, 60, 20, 5),
    ]
    for key, label, lo, hi, default, step in sliders:
        st.session_state.setdefault(key, default)
        st.session_state[key] = st.sidebar.slider(label, lo, hi, st.session_state[key], step)
    st.sidebar.caption("Sample values. Member 1 replaces them with sourced figures.")
    st.sidebar.info("AFTER version: Chengjin's 48-hour forecast. Other data is still the sample.")


def staffing_table():
    """Solution 1 calculation: forecast arrivals -> staff needed -> gap vs schedule (all 48 hours)."""
    fc = load_forecast().merge(load_schedule(), on="hour", how="left")
    fc["nurses_needed"] = (fc["expected_arrivals"] * st.session_state.nurse_min / 60).apply(lambda x: int(-(-x // 1)))
    fc["doctors_needed"] = (fc["expected_arrivals"] / st.session_state.pts_per_doc).apply(lambda x: int(-(-x // 1)))
    fc["nurse_gap"] = fc["nurses_needed"] - fc["nurses_scheduled"]
    fc["doctor_gap"] = fc["doctors_needed"] - fc["doctors_scheduled"]
    return fc.sort_values("timestamp", ignore_index=True)


def current_hour_row(staff):
    """The forecast row for the demo hour. Stops the page with a clear message if it is missing."""
    row = staff[staff["timestamp"] == DEMO_NOW.floor("h")]
    if row.empty:
        st.error(f"forecast.csv has no row for {DEMO_NOW:%Y-%m-%d %H}:00. "
                 f"It covers {staff['timestamp'].min():%Y-%m-%d %H:%M} to {staff['timestamp'].max():%Y-%m-%d %H:%M}. "
                 "Regenerate the forecast or change DEMO_NOW in utils.py.")
        st.stop()
    return row.iloc[0]


def next_hours(staff, hours=24):
    """Forecast rows from the demo hour forward, up to `hours` ahead (crosses midnight)."""
    start = DEMO_NOW.floor("h")
    return staff[(staff["timestamp"] >= start) & (staff["timestamp"] < start + pd.Timedelta(hours=hours))]


def waiting_list():
    """Waiting room = sample file + any patients entered on the triage page this session."""
    base = load_waiting_room()
    added = pd.DataFrame(st.session_state.get("added_patients", []))
    df = pd.concat([base, added], ignore_index=True) if len(added) else base.copy()
    df["waited_min"] = ((DEMO_NOW - pd.to_datetime(df["arrival_time"])).dt.total_seconds() // 60).astype(int)
    df["reassess_due"] = df["ctas_level"].map(REASSESS_MIN)
    df["overdue"] = df["waited_min"] > df["reassess_due"]
    return df


def wait_estimate(df, doctors_on_duty):
    """Solution 2: estimated wait for a NEW patient at each level.

    (patients ahead at the same or higher urgency x average assessment minutes) / doctors on duty
    """
    rows = []
    for level in range(1, 6):
        ahead = int((df["ctas_level"] <= level).sum())
        est = ahead * st.session_state.assess_min / max(doctors_on_duty, 1)
        rows.append({"ctas_level": level, "patients_ahead": ahead, "est_wait_min": round(est)})
    return pd.DataFrame(rows)


def spaces_table():
    """Solution 3: expected minutes until each occupied space frees up."""
    spaces, avg = load_spaces()
    df = spaces.merge(avg, on="ctas_level", how="left")
    remaining = (df["avg_stay_min"] - df["time_in_space_min"]).clip(lower=0)
    df["expected_free_in_min"] = remaining.where(df["status"] == "occupied")
    return df
