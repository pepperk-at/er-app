"""Solution 1 page (built from Member 1's forecast.csv)."""
import streamlit as st

import utils

st.set_page_config(page_title="Forecast & staffing", layout="wide")
utils.assumptions()

st.title("Forecast & staffing")
st.write("Expected arrivals for the next 24 hours, and the staff needed to handle them.")

df = utils.staffing_table()

st.subheader("Expected arrivals per hour")
st.line_chart(df, x="hour", y="expected_arrivals")

st.subheader("Nurses needed vs scheduled")
st.line_chart(df, x="hour", y=["nurses_needed", "nurses_scheduled"])

st.subheader("Hours that are short-staffed")
short = df[(df["nurse_gap"] > 0) | (df["doctor_gap"] > 0)]
st.dataframe(short[["hour", "expected_arrivals", "nurses_needed", "nurses_scheduled", "nurse_gap",
                    "doctors_needed", "doctors_scheduled", "doctor_gap"]], hide_index=True)

st.caption("Nurses needed = arrivals x nursing minutes per patient / 60. "
           "Doctors needed = arrivals / patients one doctor sees per hour. Change the assumptions in the sidebar.")
