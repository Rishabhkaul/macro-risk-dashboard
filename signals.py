"""
Signal generation for macro risk dashboard.
Thresholds, scoring (Green=0, Yellow=1, Red=2), regime labels, 4W trend and flags.
"""
from typing import Optional, Tuple

import pandas as pd
import numpy as np

# ~20 trading days for 4-week lookback
TRADING_DAYS_4W = 20

# Regime by total score
REGIMES = [
    (0, 4, "Expansion"),
    (5, 8, "Late Cycle"),
    (9, 14, "Stress Building"),
    (15, 999, "Crisis"),
]


def _pct_change_4w(series: pd.Series, last_n: int = TRADING_DAYS_4W) -> Optional[float]:
    """4-week percent change using last_n points (for daily series)."""
    if series is None or len(series) < 2 or last_n >= len(series):
        return None
    recent = series.iloc[-last_n:]
    old = recent.iloc[0]
    new = recent.iloc[-1]
    if old == 0 or np.isnan(old):
        return None
    return float((new - old) / old * 100)


def trend_arrow(pct: Optional[float]) -> str:
    """↑ if >+2%, ↓ if <-2%, → otherwise."""
    if pct is None or np.isnan(pct):
        return "—"
    if pct > 2:
        return "↑"
    if pct < -2:
        return "↓"
    return "→"


def flag_hy_oas(value: Optional[float]) -> int:
    """HY OAS: <4 green=0, 4–6 yellow=1, >6 red=2."""
    if value is None or np.isnan(value):
        return 1
    if value < 4:
        return 0
    if value <= 6:
        return 1
    return 2


def flag_vix(value: Optional[float]) -> int:
    """VIX: <20 green=0, 20–30 yellow=1, >30 red=2."""
    if value is None or np.isnan(value):
        return 1
    if value < 20:
        return 0
    if value <= 30:
        return 1
    return 2


def flag_etf_4w(pct: Optional[float]) -> int:
    """ETFs / 4W-based: green >=-2%, yellow -2% to -6%, red <=-6%."""
    if pct is None or np.isnan(pct):
        return 1
    if pct >= -2:
        return 0
    if pct >= -6:
        return 1
    return 2


def flag_label(flag: int) -> str:
    if flag == 0:
        return "Green"
    if flag == 1:
        return "Yellow"
    return "Red"


# Metric config: (section, display_name, series_id_or_ticker, flag_type, optional note key)
METRIC_CONFIG = [
    ("Credit Risk", "HY OAS (BAML)", "BAMLH0A0HYM2", "hy_oas", None),
    ("Credit Risk", "HYG", "HYG", "etf_4w", None),
    ("Credit Risk", "JNK", "JNK", "etf_4w", None),
    ("Volatility", "VIX", "^VIX", "vix", None),
    ("Liquidity/Dollar", "Fed Balance Sheet (WALCL)", "WALCL", "etf_4w", "4W % chg"),
    ("Liquidity/Dollar", "UUP (Dollar)", "UUP", "etf_4w", None),
    ("Rates & Growth", "SPY", "SPY", "etf_4w", None),
    ("Tail Risk", "XLF", "XLF", "etf_4w", None),
    ("Tail Risk", "KRE", "KRE", "etf_4w", None),
]


def build_metrics_table(data: dict) -> Tuple[pd.DataFrame, int, str]:
    """
    Build table-ready dataframe with Metric, Current, 4W Trend, Flag, Notes.
    Also returns total_risk_score and regime_label.
    """
    rows = []
    total_score = 0

    for section, display_name, key, flag_type, note_hint in METRIC_CONFIG:
        series = data.get(key)
        if series is None or not isinstance(series, pd.Series):
            current = None
            pct_4w = None
        else:
            current = float(series.iloc[-1]) if len(series) > 0 else None
            pct_4w = _pct_change_4w(series, TRADING_DAYS_4W)

        if flag_type == "hy_oas":
            flag = flag_hy_oas(current)
        elif flag_type == "vix":
            flag = flag_vix(current)
        else:
            flag = flag_etf_4w(pct_4w)

        total_score += flag
        arrow = trend_arrow(pct_4w)
        notes = note_hint or ""
        if current is not None and not np.isnan(current):
            current_str = f"{current:.2f}" if key != "WALCL" else f"{current:,.0f}"
        else:
            current_str = "—"
        rows.append({
            "Section": section,
            "Metric": display_name,
            "Current": current_str,
            "4W Trend": arrow,
            "Flag": flag_label(flag),
            "Notes": notes,
        })

    df = pd.DataFrame(rows)

    regime_label = "Unknown"
    for lo, hi, label in REGIMES:
        if lo <= total_score <= hi:
            regime_label = label
            break

    return df, total_score, regime_label
