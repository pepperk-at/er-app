"""Solution 3 page (built from Member 3's spaces.csv and avg_stay.csv)."""
import streamlit as st

import utils

st.set_page_config(page_title="Treatment spaces", layout="wide")
utils.assumptions()

st.title("ER treatment spaces")

df = utils.spaces_table()
window = st.slider("Look ahead (hours)", 1, 4, 2)

a, b, c = st.columns(3)
a.metric("Free now", int((df["status"] == "free").sum()))
b.metric(f"Likely free within {window} h", int((df["expected_free_in_min"] <= window * 60).sum()))
c.metric("Being cleaned", int((df["status"] == "cleaning").sum()))

st.dataframe(df[["space_id", "status", "ctas_level", "time_in_space_min", "avg_stay_min", "expected_free_in_min"]]
             .sort_values("expected_free_in_min"), hide_index=True)
st.caption("Expected free in = average stay for the patient's level minus time already in the space.")
