"""
Macro Risk Dashboard - Streamlit app.
"""
import streamlit as st
from data_sources import get_all_data
from signals import build_metrics_table

st.set_page_config(page_title="Macro Risk Dashboard", layout="wide")
st.title("Macro Risk Dashboard")

# Refresh button: clear cache and rerun
if st.button("Refresh data"):
    get_all_data.clear()
    st.rerun()

# Load data and compute signals
data = get_all_data()
table_df, total_score, regime_label = build_metrics_table(data)

# Top metrics
col1, col2 = st.columns(2)
with col1:
    st.metric("Total Risk Score", total_score)
with col2:
    st.metric("Regime Label", regime_label)

st.divider()

# Five sections with table
sections = ["Credit Risk", "Volatility", "Liquidity/Dollar", "Rates & Growth", "Tail Risk"]
display_cols = ["Metric", "Current", "4W Trend", "Flag", "Notes"]

for section in sections:
    st.subheader(section)
    section_df = table_df[table_df["Section"] == section][display_cols]
    st.dataframe(section_df, width="stretch", hide_index=True)
    st.write("")
