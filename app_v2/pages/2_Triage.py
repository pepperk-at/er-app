"""Solution 2 page, AFTER version (built from Member 2's triage_rules.xlsx and waiting_room.csv).

Member 2's suggestions: colour code each triage level, and alert when a patient's waited minutes
pass the threshold for their level. The thresholds are placeholders (see utils_v2.py) until
Member 2 sends the real ones; the data files are still the samples.
"""
import operator

import streamlit as st

import utils_v2 as utils  # own name so it never loads the original app's utils.py

st.set_page_config(page_title="Triage support (after)", layout="wide")
utils.assumptions()

st.title("Triage support")
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
    due = utils.REASSESS_MIN[level]
    st.caption("Reassess continuously." if due == 0 else f"Reassess within {due} minutes.")
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
overdue = waiting[waiting["alert"] == "Overdue"]
soon = waiting[waiting["alert"] == "Due soon"]
if len(overdue):
    worst = overdue.sort_values(["ctas_level", "minutes_left"]).iloc[0]
    st.error(f"{len(overdue)} of {len(waiting)} patients are overdue for reassessment. "
             f"Most urgent: {worst['patient_id']} (level {worst['ctas_level']}), "
             f"{-worst['minutes_left']} min past the {worst['reassess_due']} min threshold.")
if len(soon):
    st.warning(f"{len(soon)} patients are due for reassessment soon: " + ", ".join(soon["patient_id"]))
if not len(overdue) and not len(soon):
    st.success("Every waiting patient is within their reassessment time.")

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


# Every waiting patient, most urgent problem first: overdue, then due soon, then by level.
st.subheader("Waiting patients and reassessment alerts")
order = {"Overdue": 0, "Due soon": 1, "On time": 2}
table = waiting.assign(_o=waiting["alert"].map(order)).sort_values(["_o", "ctas_level", "minutes_left"])
table = table[["patient_id", "complaint", "ctas_level", "waited_min", "reassess_due", "minutes_left", "alert"]]
table = table.rename(columns={"reassess_due": "threshold_min"})


def color_level(lvl):
    c = utils.CTAS[lvl]
    return f"background-color:{c['color']};color:{c['text']}"


def color_alert(alert):
    return f"background-color:{utils.ALERT_COLORS[alert]};color:white;font-weight:bold"


st.dataframe(table.style.map(color_level, subset=["ctas_level"]).map(color_alert, subset=["alert"]),
             hide_index=True, height=(len(table) + 1) * 35 + 3,  # tall enough to show every patient
             column_config={
                 "minutes_left": st.column_config.NumberColumn("minutes_left", help="Negative = minutes overdue"),
                 "threshold_min": st.column_config.NumberColumn("threshold_min",
                                                                help="CTAS reassessment interval for the level"),
             })
st.caption(f"Overdue = waited longer than the threshold for the level. Due soon = waited at least "
           f"{utils.DUE_SOON_SHARE:.0%} of it. Thresholds are the CTAS reassessment intervals "
           "(level 1 continuous, 2: 15, 3: 30, 4: 60, 5: 120 min); placeholder until Member 2 confirms them.")
