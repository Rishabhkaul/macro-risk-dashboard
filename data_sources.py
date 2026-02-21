"""
Data sources for macro risk dashboard.
Fetches FRED series and yfinance tickers; uses Streamlit caching with TTL.
"""
import io
import streamlit as st
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime, timedelta

FRED_SERIES = ["BAMLH0A0HYM2", "WALCL"]  # HY OAS, Fed balance sheet
YF_TICKERS = ["HYG", "JNK", "SPY", "XLF", "KRE", "UUP", "^VIX"]
CACHE_TTL_SECONDS = 900


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_fred_series(series_id: str) -> pd.Series:
    """Fetch a single FRED series as CSV (no API key required)."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df["DATE"] = pd.to_datetime(df["DATE"])
        df = df.set_index("DATE").sort_index()
        s = df.iloc[:, 0]
        s.name = series_id
        return s
    except Exception as e:
        return pd.Series(dtype=float)  # empty on error


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_yfinance_tickers(tickers: list[str]) -> dict[str, pd.Series]:
    """Fetch yfinance history for given tickers; returns dict of close price Series."""
    end = datetime.now()
    start = end - timedelta(days=90)
    out = {}
    for t in tickers:
        try:
            obj = yf.Ticker(t)
            hist = obj.history(start=start, end=end, auto_adjust=True)
            if hist is not None and not hist.empty and "Close" in hist.columns:
                s = hist["Close"].sort_index()
                s.name = t
                out[t] = s
            else:
                out[t] = pd.Series(dtype=float)
        except Exception:
            out[t] = pd.Series(dtype=float)
    return out


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_all_data() -> dict:
    """
    Fetch all macro data: FRED series + yfinance.
    Returns dict mapping symbol -> pandas Series (with datetime index).
    """
    data = {}
    for sid in FRED_SERIES:
        data[sid] = fetch_fred_series(sid)
    yf_data = fetch_yfinance_tickers(YF_TICKERS)
    data.update(yf_data)
    return data
