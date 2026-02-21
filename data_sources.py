"""
Data sources for macro risk dashboard.
Fetches FRED series and yfinance tickers; uses Streamlit caching with TTL.
"""
import io
import os
import streamlit as st
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime, timedelta

FRED_SERIES = ["BAMLH0A0HYM2", "WALCL"]  # HY OAS, Fed balance sheet
YF_TICKERS = ["HYG", "JNK", "SPY", "XLF", "KRE", "UUP", "^VIX"]
CACHE_TTL_SECONDS = 900


def _get_fred_api_key():
    """FRED API key from env or Streamlit secrets (optional; free at fred.stlouisfed.org)."""
    # Streamlit Cloud: secrets are top-level in TOML, e.g. FRED_API_KEY = "your_key"
    try:
        if hasattr(st, "secrets"):
            key = st.secrets.get("FRED_API_KEY") or st.secrets.get("fred_api_key")
            if key and isinstance(key, str):
                return key.strip()
    except Exception:
        pass
    return os.environ.get("FRED_API_KEY", "").strip()


def is_fred_api_configured():
    """Return True if FRED API key is set (for dashboard display)."""
    return bool(_get_fred_api_key())


def _parse_fred_csv(text: str, series_id: str) -> pd.Series:
    """Parse FRED-style CSV (DATE + value column) into a Series."""
    df = pd.read_csv(io.StringIO(text))
    date_col = df.columns[0]
    value_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()
    # FRED uses "." for missing; coerce to numeric and dropna
    s = pd.to_numeric(df[value_col], errors="coerce").dropna()
    s.name = series_id
    return s


def _fetch_fred_via_api(series_id: str, api_key: str) -> pd.Series:
    """Fetch series via FRED API (reliable when API key is set)."""
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        obs = data.get("observations", [])
        if not obs:
            return pd.Series(dtype=float)
        dates = []
        values = []
        for o in obs:
            v = o.get("value", ".")
            if v == ".":
                continue
            try:
                values.append(float(v))
                dates.append(pd.to_datetime(o["date"]))
            except (ValueError, TypeError):
                continue
        if not dates:
            return pd.Series(dtype=float)
        s = pd.Series(values, index=pd.DatetimeIndex(dates)).sort_index()
        s.name = series_id
        return s
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_fred_series(series_id: str) -> pd.Series:
    """Fetch a single FRED series. Uses API if key set; else tries CSV and gateway."""
    api_key = _get_fred_api_key()
    if api_key:
        s = _fetch_fred_via_api(series_id, api_key)
        if len(s) > 0:
            return s
    headers = {"User-Agent": "MacroRiskDashboard/1.0 (Streamlit)"}
    try:
        r = requests.get(
            f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
            timeout=15,
            headers=headers,
        )
        r.raise_for_status()
        if r.text and "date" in r.text.lower().split("\n")[0]:
            s = _parse_fred_csv(r.text, series_id)
            if len(s) > 0:
                return s
    except Exception:
        pass
    try:
        r = requests.get(
            f"https://www.ivo-welch.info/cgi-bin/fredwrap?symbol={series_id}",
            timeout=15,
            headers=headers,
        )
        r.raise_for_status()
        if r.text and len(r.text.strip()) > 10 and "date" in r.text.lower()[:200]:
            s = _parse_fred_csv(r.text, series_id)
            if len(s) > 0:
                return s
    except Exception:
        pass
    return pd.Series(dtype=float)


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
