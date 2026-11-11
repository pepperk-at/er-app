"""Solution 1 page, AFTER version (Chengjin's 48-hour forecast.csv)."""
import streamlit as st

import utils_v2 as utils  # own name so it never loads the original app's utils.py

st.set_page_config(page_title="Forecast & staffing (after)", layout="wide")
utils.assumptions()

st.title("Forecast & staffing")
df = utils.staffing_table()
st.write(f"Expected arrivals for the next 48 hours ({df['timestamp'].min():%b %d %H:%M} to "
         f"{df['timestamp'].max():%b %d %H:%M}), and the staff needed to handle them. "
         "Forecast by Chengjin (Prophet model with Ottawa weather).")

chart = df.set_index("timestamp")

st.subheader("Expected arrivals per hour")
st.line_chart(chart, y="expected_arrivals", x_label="Time", y_label="Arrivals")

st.subheader("Nurses needed vs scheduled")
st.line_chart(chart, y=["nurses_needed", "nurses_scheduled"], x_label="Time", y_label="Nurses")

st.subheader("Doctors needed vs scheduled")
st.line_chart(chart, y=["doctors_needed", "doctors_scheduled"], x_label="Time", y_label="Doctors")

st.subheader("Hours that are short-staffed")
short = df[(df["nurse_gap"] > 0) | (df["doctor_gap"] > 0)].copy()
short["date"] = short["date"].dt.strftime("%Y-%m-%d")
st.write(f"{len(short)} of {len(df)} hours are short of nurses or doctors.")
st.dataframe(short[["date", "hour", "expected_arrivals", "nurses_needed", "nurses_scheduled", "nurse_gap",
                    "doctors_needed", "doctors_scheduled", "doctor_gap"]], hide_index=True)

st.caption("Nurses needed = arrivals x nursing minutes per patient / 60. "
           "Doctors needed = arrivals / patients one doctor sees per hour. Change the assumptions in the sidebar. "
           "The schedule is the same every day, so both days use schedule.csv.")
