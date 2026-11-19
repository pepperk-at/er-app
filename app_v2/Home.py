"""Home dashboard, AFTER version (Chengjin's 3-day forecast). Run with:  streamlit run app_v2/Home.py"""
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

# Treatment spaces (Gulchaman's rules): free now is confirmed; "ending" is only an estimate of when
# an occupied space's patient may leave. It is not a promise the space is clean and ready.
try:
    spaces = utils.spaces_summary(utils.spaces_table())
except utils.SpacesDataError:
    spaces = None
if spaces:
    free_now, ending_2h = spaces["free"], spaces["within_2h"]
    spaces_text = (f"{free_now} space(s) free now and {ending_2h} more estimated to finish occupancy "
                   f"within 2 hours (cleaning time unknown)")

# --- one alert banner ---
if peak["nurse_gap"] > 0 and spaces and free_now + ending_2h < 4:
    st.error(f"Rush expected at {peak_label}: only {spaces_text}. "
             f"Call in {int(peak['nurse_gap'])} nurse(s) and speed up discharges.")
elif peak["nurse_gap"] > 0:
    st.warning(f"Rush expected at {peak_label}: short {int(peak['nurse_gap'])} nurse(s)."
               + (f" Treatment spaces: {spaces_text}." if spaces else ""))
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
    st.metric("Overdue for reassessment", int((waiting["alert"] == "Overdue").sum()))
    st.altair_chart(utils.level_chart(waiting, height=250, numbers_only=True), width="stretch")
with c3:
    st.subheader("3. Treatment spaces")
    if spaces:
        st.metric("Free now", free_now)
        st.metric("Estimated to finish occupancy within 2 h", ending_2h)
        st.caption(f"{spaces['exceeded']} occupied spaces past their estimate (update needed). "
                   f"{spaces['cleaning']} being cleaned, readiness unknown.")
    else:
        st.error("Treatment-space data is invalid. See the Treatment Spaces page.")

st.caption("Use the pages in the sidebar for details.")
