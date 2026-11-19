"""Solution 3 page, laid out from Gulchaman's sketch (data/Gulchaman/member-3-handoff/Treatment-Space-Page-Sketch.svg).

Rules (Member 3 handoff, utils_v3.check_spaces):
- Free now / Occupied / Cleaning are counted straight from spaces.csv.
- For occupied spaces, raw remaining = assumed stay for the CTAS level - time already in the space.
- Only positive estimates count toward the 2 h and 4 h groups; the 4 h group includes the 2 h group.
- Zero or negative estimates stay occupied and are flagged "update needed".
- Cleaning spaces have no readiness time; no cleaning time is assumed.
"""
import streamlit as st

import city_v3 as city
import utils_v3 as utils  # own name so it never loads utils.py or utils_v2.py

st.set_page_config(page_title="Treatment spaces (v3)", layout="wide")
utils.assumptions()

st.title("ER treatment spaces")
city.incident_banner(utils.selected_hospital())
if utils.selected_hospital() != city.HOME_ED:
    st.info(f"Patient-level records exist only for {city.hospital_name(city.HOME_ED)} (sample data), "
            "so this page shows those.")

try:
    df = utils.spaces_table()
except utils.SpacesDataError as err:
    st.error("The treatment-space data is invalid, so no totals or estimates are shown. "
             "Fix spaces.csv / avg_stay.csv and reload.")
    for problem in err.problems:
        st.markdown(f"- {problem}")
    st.stop()

s = utils.spaces_summary(df)
st.caption(f"Fictional Ottawa ER · {utils.DEMO_NOW:%d %b %Y, %H:%M} {utils.TIMEZONE} · "
           f"{df['space_id'].iloc[0]}–{df['space_id'].iloc[-1]} ({len(df)} spaces)")

# --- status totals ---
a, b, c = st.columns(3)
with a, st.container(border=True):
    st.metric("Free now", s["free"])
    st.caption("Marked free in spaces.csv")
with b, st.container(border=True):
    st.metric("Occupied", s["occupied"])
    st.caption(f"Still occupied, including {s['exceeded']} flagged")
with c, st.container(border=True):
    st.metric("Cleaning", s["cleaning"])
    st.caption("Readiness time unknown")

# --- estimated occupancy endings ---
with st.container(border=True):
    st.markdown("**Additional occupied spaces estimated to finish occupancy**")
    w2, w4 = st.columns(2)
    w2.metric("Within 2 hours", s["within_2h"])
    w4.metric("Within 4 hours", s["within_4h"])
    st.caption("Positive remaining estimates only. Upper boundaries included. "
               "The 4-hour group includes the 2-hour group, so do not add them.")
    st.markdown("**Occupancy ending is not confirmed readiness for reuse; no cleaning time is assumed.**")

# --- reached / exceeded flag ---
if s["exceeded"]:
    st.warning(f"**{s['exceeded']} occupied spaces: estimate reached or exceeded — update needed.**  \n"
               "They stay occupied and are left out of the 2- and 4-hour counts.")

# --- space detail ---
st.subheader("Space detail")
order = {"Within 2 h and 4 h": 0, "Within 4 h only": 1, "Outside both windows": 2,
         "Estimate reached or exceeded: update needed, still occupied": 3,
         "Free now": 4, "Readiness time unknown": 5}
table = (df.assign(_order=df["interpretation"].map(order))
           .sort_values(["_order", "raw_remaining_min", "space_id"])
           [["space_id", "status", "ctas_level", "time_in_space_min", "avg_stay_min",
             "raw_remaining_min", "interpretation"]])
table["status"] = table["status"].str.capitalize()
st.dataframe(
    table, hide_index=True, width="stretch",
    column_config={
        "space_id": "Space",
        "status": "Status",
        "ctas_level": st.column_config.NumberColumn("CTAS", format="%d"),
        "time_in_space_min": st.column_config.NumberColumn("Elapsed (min)", format="%d"),
        "avg_stay_min": st.column_config.NumberColumn("Assumed stay (min)", format="%d"),
        "raw_remaining_min": st.column_config.NumberColumn("Raw remaining (min)", format="%d"),
        "interpretation": "Interpretation",
    },
)

st.info("**Synthetic data · unvalidated stay assumptions inherited from the starter app · planning demonstration only.**  \n"
        "Raw remaining = assumed stay − elapsed time in space. This snapshot makes no clinical promise. "
        "Rules and sources: Gulchaman's Member 3 handoff (Sources-and-Assumptions.md).")
