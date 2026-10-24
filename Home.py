"""Home dashboard (Member 4). Run with:  streamlit run Home.py"""
import streamlit as st

import utils

st.set_page_config(page_title="ER Wait Dashboard", layout="wide")
utils.assumptions()

st.title("ER shift dashboard")
st.caption(f"Demo time: {utils.DEMO_NOW:%A %B %d, %H:%M}. Sample data, not real patients.")

# --- pull one number from each solution ---
staff = utils.staffing_table()
upcoming = staff[staff["hour"] >= utils.DEMO_NOW.hour]
peak = upcoming.loc[upcoming["expected_arrivals"].idxmax()]

waiting = utils.waiting_list()
now_row = staff[staff["hour"] == utils.DEMO_NOW.hour].iloc[0]

spaces = utils.spaces_table()
free_now = int((spaces["status"] == "free").sum())
free_soon = int((spaces["expected_free_in_min"] <= 120).sum())

# --- one alert banner ---
if peak["nurse_gap"] > 0 and free_now + free_soon < 4:
    st.error(f"Rush expected at {int(peak['hour'])}:00 and only {free_now + free_soon} spaces free in the next 2 hours. "
             f"Call in {int(peak['nurse_gap'])} nurse(s) and speed up discharges.")
elif peak["nurse_gap"] > 0:
    st.warning(f"Rush expected at {int(peak['hour'])}:00: short {int(peak['nurse_gap'])} nurse(s).")
else:
    st.success("Staffing looks enough for the rest of the shift.")

# --- three columns, one per solution ---
c1, c2, c3 = st.columns(3)
with c1:
    st.subheader("1. Forecast & staffing")
    st.metric("Busiest hour ahead", f"{int(peak['hour'])}:00", f"{int(peak['expected_arrivals'])} arrivals expected", delta_color="off")
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
