"""
Macro Risk Dashboard - Streamlit app.
"""
import pandas as pd
import streamlit as st
from data_sources import get_all_data, is_fred_api_configured, fetch_fred_series
from signals import build_metrics_table

# Tooltips for table metrics (keys match df["Metric"] exactly). Under 40 words each.
METRIC_TOOLTIPS = {
    "HY OAS (BAML)": (
        "ICE BofA US High Yield Option-Adjusted Spread (BAMLH0A0HYM2). "
        "Measures high-yield bond spread over Treasuries. Widening signals credit stress and rising default risk; key for systemic risk."
    ),
    "Fed Balance Sheet (WALCL)": (
        "Federal Reserve total assets (WALCL). Reflects QE/QT and liquidity provision. "
        "Shrinking can tighten financial conditions and amplify stress."
    ),
    "HYG": (
        "iShares iBoxx High Yield Corporate Bond ETF. Tracks high-yield bond performance. "
        "Weakness signals credit repricing and risk-off sentiment; credit risk indicator."
    ),
    "JNK": (
        "SPDR Bloomberg High Yield Bond ETF. Proxy for high-yield credit. "
        "Declines indicate credit stress and flight to quality; systemic risk signal."
    ),
    "SPY": (
        "SPDR S&P 500 ETF. Broad US equity market proxy. "
        "Used as growth and risk-on indicator; falls signal stress and regime shift."
    ),
    "XLF": (
        "Financial Select Sector SPDR. US financial sector equity proxy. "
        "Leading indicator of systemic and tail risk in banking and financial conditions."
    ),
    "KRE": (
        "SPDR S&P Regional Banking ETF. Regional bank equity proxy. "
        "Sensitive to funding and credit stress; tail risk and financial stability indicator."
    ),
    "UUP (Dollar)": (
        "Invesco DB US Dollar Index. US dollar strength versus major currencies. "
        "Strong dollar can tighten global financial conditions and amplify EM stress."
    ),
    "VIX": (
        "CBOE Volatility Index. Options-implied S&P 500 volatility. "
        "Elevation signals fear and stress; key gauge of market and macro risk."
    ),
}

st.set_page_config(page_title="Macro Risk Dashboard", layout="wide")
st.title("Macro Risk Dashboard")

# Sidebar: show if FRED API is configured (so Cloud users can verify secrets)
with st.sidebar:
    if is_fred_api_configured():
        st.success("FRED API: configured")
    else:
        st.warning(
            "FRED API: not set — HY OAS & WALCL may be blank. "
            "Add secret `FRED_API_KEY` in app Settings → Secrets, then redeploy."
        )

# Refresh button: clear cache and rerun
if st.button("Refresh data"):
    get_all_data.clear()
    fetch_fred_series.clear()
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

# Five sections with table (hover tooltips on Metric column only)
sections = ["Credit Risk", "Volatility", "Liquidity/Dollar", "Rates & Growth", "Tail Risk"]
display_cols = ["Metric", "Current", "4W Trend", "Flag", "Notes"]

for section in sections:
    st.subheader(section)
    section_df = table_df[table_df["Section"] == section][display_cols].reset_index(drop=True)
    # Tooltips DataFrame: same shape, only Metric column populated
    tooltips_df = pd.DataFrame("", index=section_df.index, columns=section_df.columns)
    for idx in section_df.index:
        metric_val = section_df.loc[idx, "Metric"]
        tooltips_df.loc[idx, "Metric"] = METRIC_TOOLTIPS.get(metric_val, "")
    styled_df = section_df.style.set_tooltips(tooltips_df)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    st.write("")
