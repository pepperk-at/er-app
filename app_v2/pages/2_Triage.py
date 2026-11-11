"""Solution 2 page (built from Member 2's triage_rules.xlsx and waiting_room.csv)."""
import operator

import streamlit as st

import utils_v2 as utils  # own name so it never loads the original app's utils.py

st.set_page_config(page_title="Triage support (after)", layout="wide")
utils.assumptions()

st.title("Triage support")
st.caption("Suggests a level from the rules table. The nurse always makes the final decision. Sample rules, not clinical advice.")

complaints, vitals = utils.load_triage_rules()
OPS = {"<": operator.lt, ">": operator.gt, "<=": operator.le, ">=": operator.ge}

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
    st.success(f"Suggested level: {level}")
    st.write("Why: " + "; ".join(reasons))
    # remember the patient for this session so the waiting room updates
    st.session_state.setdefault("added_patients", []).append(
        {"patient_id": f"NEW{len(st.session_state['added_patients']) + 1}",
         "arrival_time": utils.DEMO_NOW, "complaint": complaint, "ctas_level": level})

# --- waiting room statistics ---
waiting = utils.waiting_list()
staff = utils.staffing_table()
doctors = int(utils.current_hour_row(staff)["doctors_scheduled"])

left, right = st.columns(2)
with left:
    st.subheader("Patients waiting by level")
    st.bar_chart(waiting["ctas_level"].value_counts().sort_index(), x_label="Triage level", y_label="Patients")
with right:
    st.subheader(f"Estimated wait for a new patient ({doctors} doctors on duty)")
    st.dataframe(utils.wait_estimate(waiting, doctors), hide_index=True)

st.subheader("Overdue for reassessment")
st.dataframe(waiting[waiting["overdue"]][["patient_id", "complaint", "ctas_level", "waited_min", "reassess_due"]],
             hide_index=True)
