"""Shared helpers for the AFTER app (app_v2): every page imports from here.

Differences from the original app:
- forecast.csv is Chengjin's 3-day Prophet forecast (made by tools/forecast.py).
- Each forecast row gets a full timestamp (date + hour), so the days don't mix.
- The schedule is the same every day, so it is joined on hour.

All data files follow the team's file agreement. To swap sample data for real data,
replace the file in the data/ folder with the same name and the same columns.
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "data"

# The demo pretends it is this moment. Change it if the sample data changes.
# All times in the data files are Ottawa local time (America/Toronto). The timestamp has no
# timezone attached so it can be compared directly with the forecast and arrival times.
DEMO_NOW = pd.Timestamp("2026-11-30 18:00")
TIMEZONE = "America/Toronto"

# CTAS reassessment intervals in minutes, confirmed by Godwin (Member 2) in
# data/Godwin/triage_group_brief.docx (CTAS, Murray et al., 2004). Level 1 = continuous care.
REASSESS_MIN = {1: 0, 2: 15, 3: 30, 4: 60, 5: 120}

# CTAS level names and colours (team choice: red, orange, yellow, green, white).
# "text" is the font colour that stays readable on that background.
CTAS = {
    1: {"name": "Resuscitation", "color": "#D62728", "text": "white"},
    2: {"name": "Emergent", "color": "#F28E2B", "text": "black"},
    3: {"name": "Urgent", "color": "#F2C200", "text": "black"},
    4: {"name": "Less urgent", "color": "#2CA02C", "text": "white"},
    5: {"name": "Non-urgent", "color": "#F4F4F4", "text": "black"},
}

# Wait alerts. Thresholds = REASSESS_MIN (Godwin). DUE_SOON_SHARE is a team guess, not in his brief:
# "Overdue" = waited longer than the reassessment interval for the level.
# "Due soon" = waited at least DUE_SOON_SHARE of that interval (80% = 12 of 15 min for level 2).
DUE_SOON_SHARE = 0.8
ALERT_COLORS = {"Overdue": "#D62728", "Due soon": "#F28E2B", "On time": "#2CA02C"}


def ctas_label(level):
    """3 -> '3 Urgent'"""
    return f"{level} {CTAS[int(level)]['name']}"


def level_chart(waiting, height=300, numbers_only=False):
    """Bar chart of waiting patients per triage level, each bar in its CTAS colour.
    Used on the Home and Triage pages so both look the same.
    numbers_only=True labels the bars 1-5 (for narrow columns); hovering still shows the name."""
    axis = alt.Axis(labelAngle=0, labelExpr="split(datum.value, ' ')[0]") if numbers_only else alt.Axis(labelAngle=0)
    counts = waiting["ctas_level"].value_counts().reindex(list(CTAS), fill_value=0).rename_axis("level")
    counts = counts.reset_index(name="patients")
    counts["label"] = counts["level"].map(ctas_label)
    bars = alt.Chart(counts).mark_bar(stroke="#999").encode(
        x=alt.X("label:N", title="Triage level", sort=None, axis=axis),
        y=alt.Y("patients:Q", title="Patients", axis=alt.Axis(tickMinStep=1)),
        color=alt.Color("label:N", legend=None, scale=alt.Scale(
            domain=[ctas_label(lvl) for lvl in CTAS], range=[c["color"] for c in CTAS.values()])),
        tooltip=[alt.Tooltip("label:N", title="Level"), alt.Tooltip("patients:Q", title="Patients")],
    )
    return bars.properties(height=height)


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
    st.sidebar.info("AFTER version: Chengjin's 72-hour forecast and Gulchaman's treatment-space update. "
                    "Other data is still the sample.")


def staffing_table():
    """Solution 1 calculation: forecast arrivals -> staff needed -> gap vs schedule (every forecast hour)."""
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
    df["minutes_left"] = df["reassess_due"] - df["waited_min"]  # negative = minutes overdue
    due_soon = df["waited_min"] >= df["reassess_due"] * DUE_SOON_SHARE
    df["alert"] = "On time"
    df.loc[due_soon, "alert"] = "Due soon"
    df.loc[df["overdue"], "alert"] = "Overdue"
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


SPACES_COLUMNS = ["space_id", "status", "ctas_level", "time_in_space_min"]
AVG_STAY_COLUMNS = ["ctas_level", "avg_stay_min"]


class SpacesDataError(ValueError):
    """spaces.csv or avg_stay.csv breaks the file rules. .problems lists every problem found."""

    def __init__(self, problems):
        self.problems = problems
        super().__init__("; ".join(problems))


def _whole_number(value):
    """'0', '45' -> int. Anything else (blank, -1, 1.5, NaN) -> None."""
    ok = value.isascii() and value.isdigit() and value == str(int(value))
    return int(value) if ok else None


def check_spaces(spaces, avg):
    """Solution 3 calculation (Gulchaman's rules, Member 3 handoff).

    `spaces` and `avg` are read as text, so nothing is guessed or filled in.
    Raises SpacesDataError if either file breaks the rules; no totals are made from bad data.

    For occupied rows: raw_remaining_min = avg_stay_min - time_in_space_min (not clipped at 0).
    - 0 < raw <= 120  -> estimated to finish occupancy within 2 h (also counts in 4 h)
    - 0 < raw <= 240  -> within 4 h (includes the 2 h group, so never add them)
    - raw <= 0        -> estimate reached or exceeded: still occupied, flagged "update needed"
    Cleaning rows have no estimate: readiness time unknown.
    """
    problems = []

    # avg_stay.csv: exact columns, one positive whole number for each CTAS 1-5.
    avg_min = {}
    if list(avg.columns) != AVG_STAY_COLUMNS:
        problems.append(f"avg_stay.csv columns must be {', '.join(AVG_STAY_COLUMNS)}")
    elif avg.isna().any().any():
        problems.append("avg_stay.csv has a row with missing fields")
    else:
        for level, minutes in zip(avg["ctas_level"], avg["avg_stay_min"]):
            n = _whole_number(minutes)
            if level not in {"1", "2", "3", "4", "5"}:
                problems.append(f"avg_stay.csv: CTAS level '{level}' is not 1-5")
            elif level in avg_min:
                problems.append(f"avg_stay.csv: CTAS {level} is listed twice")
            elif not n:
                problems.append(f"avg_stay.csv: CTAS {level} needs a whole number of minutes above 0")
            else:
                avg_min[level] = n
        missing = sorted({"1", "2", "3", "4", "5"} - set(avg["ctas_level"]))
        if missing:
            problems.append(f"avg_stay.csv: no average for CTAS {', '.join(missing)}")

    # spaces.csv: exact columns, unique IDs, known statuses, patient fields only on occupied rows.
    if list(spaces.columns) != SPACES_COLUMNS:
        problems.append(f"spaces.csv columns must be {', '.join(SPACES_COLUMNS)}")
        raise SpacesDataError(problems)
    if spaces.empty:
        problems.append("spaces.csv has no rows")
    if spaces.isna().any().any():
        problems.append("spaces.csv has a row with missing fields")
        raise SpacesDataError(problems)

    seen = set()
    for row in spaces.itertuples(index=False):
        sid = row.space_id
        if not sid or sid.strip() != sid:
            problems.append(f"spaces.csv: invalid space_id '{sid}'")
        elif sid in seen:
            problems.append(f"duplicate space_id: {sid}")
        seen.add(sid)
        if row.status not in {"free", "occupied", "cleaning"}:
            problems.append(f"{sid}: status must be free, occupied or cleaning (got '{row.status}')")
        elif row.status == "occupied":
            if row.ctas_level not in {"1", "2", "3", "4", "5"}:
                problems.append(f"{sid}: ctas_level must be 1-5")
            if row.time_in_space_min == "":
                problems.append(f"{sid}: missing time_in_space_min")
            elif _whole_number(row.time_in_space_min) is None:
                problems.append(f"{sid}: time_in_space_min must be a whole number of minutes, 0 or more")
        elif row.ctas_level != "" or row.time_in_space_min != "":
            problems.append(f"{sid}: {row.status} spaces must have blank ctas_level and time_in_space_min")

    if problems:
        raise SpacesDataError(problems)

    # Every row is valid: now calculate.
    df = spaces.copy()
    occupied = df["status"] == "occupied"
    df["ctas_level"] = pd.to_numeric(df["ctas_level"]).astype("Int64")
    df["time_in_space_min"] = pd.to_numeric(df["time_in_space_min"]).astype("Int64")
    df["avg_stay_min"] = df["ctas_level"].map({int(k): v for k, v in avg_min.items()}).astype("Int64")
    df["raw_remaining_min"] = (df["avg_stay_min"] - df["time_in_space_min"]).where(occupied)
    raw = df["raw_remaining_min"]
    df["within_2h"] = occupied & (raw > 0) & (raw <= 120)
    df["within_4h"] = occupied & (raw > 0) & (raw <= 240)
    df["estimate_exceeded"] = occupied & (raw <= 0)

    def interpret(r):
        if r.status == "free":
            return "Free now"
        if r.status == "cleaning":
            return "Readiness time unknown"
        if r.estimate_exceeded:
            return "Estimate reached or exceeded: update needed, still occupied"
        if r.within_2h:
            return "Within 2 h and 4 h"
        if r.within_4h:
            return "Within 4 h only"
        return "Outside both windows"

    df["interpretation"] = df.apply(interpret, axis=1)
    return df


def spaces_summary(df):
    """The six totals shown on the page, from check_spaces() output."""
    return {
        "free": int((df["status"] == "free").sum()),
        "occupied": int((df["status"] == "occupied").sum()),
        "cleaning": int((df["status"] == "cleaning").sum()),
        "within_2h": int(df["within_2h"].sum()),
        "within_4h": int(df["within_4h"].sum()),
        "exceeded": int(df["estimate_exceeded"].sum()),
    }


def spaces_table():
    """Solution 3 for the app: read the two data files as text and run check_spaces().

    Raises SpacesDataError if a file is invalid; pages show the error instead of totals.
    """
    spaces = pd.read_csv(DATA / "spaces.csv", dtype=str, keep_default_na=False)
    avg = pd.read_csv(DATA / "avg_stay.csv", dtype=str, keep_default_na=False)
    return check_spaces(spaces, avg)
