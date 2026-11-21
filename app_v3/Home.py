"""Home dashboard, V3 version (Chengjin's 3-day forecast). Run with:  streamlit run app_v3/Home.py"""
import pandas as pd
import streamlit as st

import city_v3 as city
import utils_v3 as utils  # own name so it never loads utils.py or utils_v2.py

st.set_page_config(page_title="ER Wait Dashboard (v3)", layout="wide")

# Plain-language meaning of each CTAS level, shown in the triage table at the bottom.
MEANING = {
    1: "Life-threatening; needs immediate care (e.g. cardiac arrest, major trauma).",
    2: "Potential threat to life, limb or function; needs rapid care.",
    3: "Serious problem that could get worse without care.",
    4: "Less urgent; could get worse or cause distress if not treated within a few hours.",
    5: "Non-urgent; often a minor or long-standing problem.",
}
utils.assumptions()

hospital = utils.selected_hospital()
st.title(f"ER shift dashboard: {city.hospital_name(hospital)}")
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

# --- incident scenario (City & Events page), then one alert banner ---
city.incident_banner(hospital)
sample_note = "" if hospital == city.HOME_ED else f" Patient records are the {city.hospital_name(city.HOME_ED)} sample."
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
    st.metric("Patients waiting", len(waiting),
              help="Patients in the waiting room who have been triaged but are not yet in a treatment space. "
                   "Includes any patient added on the Triage page.")
    st.metric("Past CTAS target", int((waiting["alert"] == "Past target").sum()),
              help="Patients who have waited longer than the CTAS target time to physician assessment for their "
                   "level (see the triage table below, e.g. 15 min for level 2), counted from arrival.")
    st.altair_chart(utils.level_chart(waiting, height=250, numbers_only=True), width="stretch")
with c3:
    st.subheader("3. Treatment spaces")
    if spaces:
        st.metric("Free now", free_now,
                  help="Treatment spaces marked free in the spaces file: empty, clean and ready for a patient now.")
        st.metric("Estimated to finish occupancy within 2 h", ending_2h,
                  help="Occupied spaces whose patient is expected to leave within 2 hours: the average stay for "
                       "the patient's CTAS level minus the time already spent in the space. This is an estimate, "
                       "and cleaning time is not included, so the space is not guaranteed to be ready.")
        st.caption(f"{spaces['exceeded']} occupied spaces past their estimate (update needed). "
                   f"{spaces['cleaning']} being cleaned, readiness unknown.")
    else:
        st.error("Treatment-space data is invalid. See the Treatment Spaces page.")

# --- triage level key (CTAS) ---
st.subheader("Triage levels (CTAS)")
levels = pd.DataFrame([
    {"Level": lvl, "Name": c["name"], "What it means": MEANING[lvl],
     "See a physician within": "Immediately" if utils.TARGET_MIN[lvl] == 0 else f"{utils.TARGET_MIN[lvl]} min",
     "Reassess while waiting": "Continuous care" if utils.REASSESS_MIN[lvl] == 0 else f"Every {utils.REASSESS_MIN[lvl]} min"}
    for lvl, c in utils.CTAS.items()])
st.dataframe(levels.style.map(lambda lvl: f"background-color:{utils.CTAS[lvl]['color']};color:{utils.CTAS[lvl]['text']}",
                              subset=["Level"]), hide_index=True, width="stretch")
st.caption("Canadian Triage and Acuity Scale (CTAS): 1 is the most urgent. Target times to physician assessment and "
           "reassessment intervals from Godwin's brief (Murray et al., 2004). Colours are a team choice.")

st.caption("Use the pages in the sidebar for details." + sample_note)
