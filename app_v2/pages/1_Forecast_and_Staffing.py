"""Solution 1 page, AFTER version (Chengjin's 3-day forecast.csv).

Charts use Altair (comes with Streamlit) so we can set them up the way Chengjin asked:
legend at the top left under the chart title, no "Time" axis name, dates shown as 2026/11/30.
"""
import altair as alt
import streamlit as st

import utils_v2 as utils  # own name so it never loads the original app's utils.py

st.set_page_config(page_title="Forecast & staffing (after)", layout="wide")
utils.assumptions()

st.title("Forecast & staffing")
df = utils.staffing_table()
days = df["date"].nunique()
st.write(f"Expected arrivals for {days} days ({df['timestamp'].min():%Y/%m/%d %H:%M} to "
         f"{df['timestamp'].max():%Y/%m/%d %H:%M}), and the staff needed to handle them. "
         "Forecast by Chengjin (Prophet model with Ottawa weather).")
st.caption("The model is trained on synthetic (dummy) hourly arrivals for 2025 plus real Ottawa weather from "
           "Open-Meteo. The data is illustrative and does not come from any specific hospital.")

# Time as text without a timezone, so the browser shows the hours exactly as in forecast.csv.
df["time"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
# A tick every 4 hours in 24-hour time (00:00, 04:00 ... 20:00). Midnight also shows the date
# (2026/11/30) on a second line, so you can still tell the days apart.
# The tick times are listed one by one; Streamlit's chart library breaks with tickCount={"interval": ...}.
TICKS = [{"year": t.year, "month": t.month, "date": t.day, "hours": t.hour}
         for t in df["timestamp"] if t.hour % 4 == 0]
X = alt.X("time:T", title=None, axis=alt.Axis(
    # labelOverlap=False keeps every 4-hour label; otherwise 3 days of labels get thinned to every 8 hours.
    # labelFlush=False keeps the first label centred on its tick so it doesn't run into 04:00.
    values=TICKS, labelAngle=0, grid=True, labelOverlap=False, labelFlush=False,
    labelExpr="hours(datum.value) == 0 ? [timeFormat(datum.value, '%H:%M'), timeFormat(datum.value, '%Y/%m/%d')]"
              " : timeFormat(datum.value, '%H:%M')"))
TIP_TIME = alt.Tooltip("time:T", title="Time", format="%Y/%m/%d %H:00")


def line_chart(columns, y_title):
    """One line per column. Legend sits at the top left, just under the subheader.
    Hovering picks the nearest hour and makes the dots at that hour bigger."""
    long = df.melt(id_vars="time", value_vars=list(columns), var_name="series", value_name="value")
    long["series"] = long["series"].map(columns)
    hover = alt.selection_point(on="pointerover", nearest=True, fields=["time"], empty=False, clear="pointerout")
    base = alt.Chart(long).encode(
        x=X,
        y=alt.Y("value:Q", title=y_title),
        # Blue = forecast need, orange = schedule, so the two lines are easy to tell apart.
        color=alt.Color("series:N", sort=list(columns.values()),
                        scale=alt.Scale(range=["#4C9BE8", "#F28E2B"]),
                        legend=alt.Legend(title=None, orient="top", direction="horizontal")),
    )
    lines = base.mark_line()
    dots = base.mark_point(filled=True).encode(
        size=alt.condition(hover, alt.value(120), alt.value(15)),
        tooltip=[TIP_TIME, alt.Tooltip("series:N", title="Line"), alt.Tooltip("value:Q", title=y_title)],
    ).add_params(hover)
    st.altair_chart((lines + dots).properties(height=320), width="stretch")


st.subheader("Expected arrivals per hour")
line_chart({"expected_arrivals": "Expected arrivals"}, "Arrivals")

st.subheader("Nurses needed vs scheduled")
line_chart({"nurses_needed": "Nurses needed", "nurses_scheduled": "Nurses scheduled"}, "Nurses")

st.subheader("Doctors needed vs scheduled")
line_chart({"doctors_needed": "Doctors needed", "doctors_scheduled": "Doctors scheduled"}, "Doctors")

st.subheader("Hours that are short-staffed")
short = df[(df["nurse_gap"] > 0) | (df["doctor_gap"] > 0)].copy()
short["date"] = short["date"].dt.strftime("%Y/%m/%d")
st.write(f"{len(short)} of {len(df)} hours are short of nurses or doctors.")
st.dataframe(short[["date", "hour", "expected_arrivals", "nurses_needed", "nurses_scheduled", "nurse_gap",
                    "doctors_needed", "doctors_scheduled", "doctor_gap"]], hide_index=True)

st.caption("Nurses needed = arrivals x nursing minutes per patient / 60. "
           "Doctors needed = arrivals / patients one doctor sees per hour. Change the assumptions in the sidebar. "
           "The schedule is the same every day, so every day uses schedule.csv.")
