"""Home dashboard, AFTER version (Chengjin's 48-hour forecast). Run with:  streamlit run app_v2/Home.py"""
import streamlit as st

import utils_v2 as utils  # own name so it never loads the original app's utils.py

st.set_page_config(page_title="ER Wait Dashboard (after)", layout="wide")
utils.assumptions()

st.title("ER shift dashboard: after")
st.caption(f"Demo time: {utils.DEMO_NOW:%A %B %d, %H:%M}. Forecast from Chengjin's model; other data is still sample, not real patients.")

# --- pull one number from each solution ---
staff = utils.staffing_table()
upcoming = utils.next_hours(staff, 24)  # next 24 hours, can run past midnight
peak = upcoming.loc[upcoming["expected_arrivals"].idxmax()]
peak_label = f"{peak['timestamp']:%a %H}:00"

waiting = utils.waiting_list()
now_row = utils.current_hour_row(staff)

spaces = utils.spaces_table()
free_now = int((spaces["status"] == "free").sum())
free_soon = int((spaces["expected_free_in_min"] <= 120).sum())

# --- one alert banner ---
if peak["nurse_gap"] > 0 and free_now + free_soon < 4:
    st.error(f"Rush expected at {peak_label} and only {free_now + free_soon} spaces free in the next 2 hours. "
             f"Call in {int(peak['nurse_gap'])} nurse(s) and speed up discharges.")
elif peak["nurse_gap"] > 0:
    st.warning(f"Rush expected at {peak_label}: short {int(peak['nurse_gap'])} nurse(s).")
else:
    st.success("Staffing looks enough for the next 24 hours.")

# --- three columns, one per solution ---
c1, c2, c3 = st.columns(3)
with c1:
    st.subheader("1. Forecast & staffing")
    st.metric("Busiest hour, next 24 h", f"{peak_label}", f"{int(peak['expected_arrivals'])} arrivals expected", delta_color="off")
    st.metric("Nurse gap at peak", int(peak["nurse_gap"]))
with c2:
    st.subheader("2. Waiting room")
    st.metric("Patients waiting", len(waiting))
    st.metric("Overdue for reassessment", int(waiting["overdue"].sum()))
    st.bar_chart(waiting["ctas_level"].value_counts().sort_index(), x_label="Triage level", y_label="Patients")
with c3:
    st.subheader("3. Treatment spaces")
    st.metric("Free now", free_now)
    st.metric("Likely free within 2 hours", free_soon)

st.caption("Use the pages in the sidebar for details.")
