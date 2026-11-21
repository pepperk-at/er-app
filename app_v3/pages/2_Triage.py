"""Solution 2 page, V3 version (Godwin, Member 2; triage_rules.xlsx and waiting_room.csv are still the samples).

Godwin's suggestions: colour code each triage level, and alert when a patient's waited minutes
pass the target for their level. The targets are the CTAS times to physician assessment from his
brief (data/Godwin/triage_group_brief.docx); the 80% "near target" share is a team guess.
"""
import operator

import streamlit as st

import city_v3 as city
import utils_v3 as utils  # own name so it never loads utils.py or utils_v2.py

st.set_page_config(page_title="Triage support (v3)", layout="wide")
utils.assumptions()

st.title("Triage support")
city.incident_banner(utils.selected_hospital())
if utils.selected_hospital() != city.HOME_ED:
    st.info(f"Patient-level records exist only for {city.hospital_name(city.HOME_ED)} (sample data), "
            "so this page shows those.")
st.caption("Suggests a level from the rules table. The nurse always makes the final decision. Sample rules, not clinical advice.")

complaints, vitals = utils.load_triage_rules()
OPS = {"<": operator.lt, ">": operator.gt, "<=": operator.le, ">=": operator.ge}


def level_badge(level, big=False):
    """A coloured box with the level number and name, in the CTAS colour."""
    c = utils.CTAS[level]
    size = "1.6rem" if big else "1rem"
    return (f"<span style='background:{c['color']};color:{c['text']};padding:0.25em 0.7em;"
            f"border-radius:0.4em;border:1px solid #999;font-weight:600;font-size:{size}'>"
            f"Level {utils.ctas_label(level)}</span>")


# --- colour key, so everyone reads the colours the same way ---
st.markdown("**Colour key:** " + " ".join(level_badge(lvl) for lvl in utils.CTAS), unsafe_allow_html=True)

# --- entry form: nothing runs until the button is pressed ---
with st.form("triage"):
    complaint = st.selectbox("Presenting complaint", complaints["complaint"])
    a, b, c, d = st.columns(4)
    entered = {
        "heart_rate": a.number_input("Heart rate", 20, 250, 85),
        "oxygen_saturation": b.number_input("Oxygen saturation %", 50, 100, 97),
        "temperature": c.number_input("Temperature °C", 30.0, 43.0, 37.0, 0.1),
        "pain_score": d.number_input("Pain (0-10)", 0, 10, 3),
    }
    submitted = st.form_submit_button("Suggest level")

if submitted:
    level = int(complaints.loc[complaints["complaint"] == complaint, "start_level"].iloc[0])
    reasons = [f"{complaint} starts at level {level}"]
    for _, rule in vitals.iterrows():
        value = entered[rule["vital_sign"]]
        if OPS[rule["operator"]](value, rule["cutoff"]) and rule["new_level"] < level:
            level = int(rule["new_level"])  # most urgent rule wins (lower number = more urgent)
            reasons.append(f"{rule['vital_sign']} {rule['operator']} {rule['cutoff']} -> level {level}")
    st.markdown("Suggested: " + level_badge(level, big=True), unsafe_allow_html=True)
    st.write("Why: " + "; ".join(reasons))
    target, every = utils.TARGET_MIN[level], utils.REASSESS_MIN[level]
    st.caption("CTAS target: see a physician immediately, continuous care." if target == 0 else
               f"CTAS target: see a physician within {target} min; reassess every {every} min while waiting.")
    # remember the patient for this session so the waiting room updates
    st.session_state.setdefault("added_patients", []).append(
        {"patient_id": f"NEW{len(st.session_state['added_patients']) + 1}",
         "arrival_time": utils.DEMO_NOW, "complaint": complaint, "ctas_level": level})

# --- waiting room ---
waiting = utils.waiting_list()
staff = utils.staffing_table()
doctors = int(utils.current_hour_row(staff)["doctors_scheduled"])

# Alerts at the top of the waiting room, most serious first.
st.header("Waiting room")
past = waiting[waiting["alert"] == "Past target"]
near = waiting[waiting["alert"] == "Near target"]
if len(past):
    worst = past.sort_values(["ctas_level", "minutes_left"]).iloc[0]
    st.error(f"{len(past)} of {len(waiting)} patients have waited past the CTAS target time to physician assessment. "
             f"Most urgent: {worst['patient_id']} (level {worst['ctas_level']}), "
             f"{-worst['minutes_left']} min past the {worst['target_min']} min target.")
if len(near):
    st.warning(f"{len(near)} patients are near their CTAS target: " + ", ".join(near["patient_id"]))
if not len(past) and not len(near):
    st.success("Every waiting patient is within their CTAS target time.")

left, right = st.columns(2)
with left:
    st.subheader("Patients waiting by level")
    st.altair_chart(utils.level_chart(waiting), width="stretch")
with right:
    st.subheader(f"Estimated wait for a new patient ({doctors} doctors on duty)")
    est = utils.wait_estimate(waiting, doctors)
    st.dataframe(est.style.map(lambda lvl: f"background-color:{utils.CTAS[lvl]['color']};"
                                           f"color:{utils.CTAS[lvl]['text']}", subset=["ctas_level"]),
                 hide_index=True)


# Every waiting patient, most urgent problem first: past target, then near target, then by level.
st.subheader("Waiting patients and CTAS target alerts")
order = {"Past target": 0, "Near target": 1, "Within target": 2}
table = waiting.assign(_o=waiting["alert"].map(order)).sort_values(["_o", "ctas_level", "minutes_left"])
table = table[["patient_id", "complaint", "ctas_level", "waited_min", "target_min", "minutes_left", "alert"]]


def color_level(lvl):
    c = utils.CTAS[lvl]
    return f"background-color:{c['color']};color:{c['text']}"


def color_alert(alert):
    return f"background-color:{utils.ALERT_COLORS[alert]};color:white;font-weight:bold"


st.dataframe(table.style.map(color_level, subset=["ctas_level"]).map(color_alert, subset=["alert"]),
             hide_index=True, height=(len(table) + 1) * 35 + 3,  # tall enough to show every patient
             column_config={
                 "minutes_left": st.column_config.NumberColumn("minutes_left", help="Negative = minutes past target"),
                 "target_min": st.column_config.NumberColumn("target_min",
                                                             help="CTAS target time to physician assessment for the level"),
             })
st.caption(f"Past target = waited longer than the CTAS target time to physician assessment for the level, counted "
           f"from arrival. Near target = waited at least {utils.NEAR_TARGET_SHARE:.0%} of it. Targets: level 1 immediately, "
           "2: 15, 3: 30, 4: 60, 5: 120 min, from Godwin's triage brief (Murray et al., 2004). The near-target share is a "
           "team assumption. Reassessment is not tracked because the waiting room file has no last-reassessed time.")
