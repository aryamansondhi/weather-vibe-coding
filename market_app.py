# market_app.py
from __future__ import annotations

import streamlit as st
import matplotlib.pyplot as plt
import yfinance as yf

from data.market_data import MarketQuery, fetch_ohlc
from signals.indicators import IndicatorConfig, compute_signals
from signals.evaluation import summarize_signal_performance

def _get_qp() -> dict:
    # Streamlit provides st.query_params in newer versions
    try:
        return dict(st.query_params)
    except Exception:
        return {}

def _get_str(qp: dict, key: str, default: str) -> str:
    v = qp.get(key, default)
    if isinstance(v, list):
        return v[0] if v else default
    return v

def _get_int(qp: dict, key: str, default: int) -> int:
    try:
        return int(_get_str(qp, key, str(default)))
    except Exception:
        return default

def _get_float(qp: dict, key: str, default: float) -> float:
    try:
        return float(_get_str(qp, key, str(default)))
    except Exception:
        return default

def _set_qp(params: dict) -> None:
    # Write query params (works on Streamlit versions with st.query_params)
    try:
        st.query_params.clear()
        for k, v in params.items():
            st.query_params[k] = str(v)
    except Exception:
        # Older Streamlit fallback
        try:
            st.experimental_set_query_params(**{k: str(v) for k, v in params.items()})
        except Exception:
            pass

st.set_page_config(page_title="Market Signals", layout="centered")

qp = _get_qp()

default_ticker = _get_str(qp, "ticker", "SPY").upper()
default_period = _get_str(qp, "period", "6mo")

default_ma_short = _get_int(qp, "ma_short", 10)
default_ma_long = _get_int(qp, "ma_long", 30)
default_dev_pct = _get_float(qp, "dev", 3.0)  # stored as percent, e.g. 3.0
default_horizon = _get_int(qp, "h", 5)

# Sidebar controls
with st.sidebar:
    st.header("Settings")

    ticker = st.text_input("Ticker", value=default_ticker)

    period_options = ["6mo", "1y", "2y"]
    period = st.selectbox(
        "Period",
        period_options,
        index=period_options.index(default_period) if default_period in period_options else 0,
    )

    ma_short = st.slider("Short MA window", 5, 30, default_ma_short)
    ma_long = st.slider("Long MA window", 20, 100, default_ma_long)
    dev_pct = st.slider("Deviation threshold (%)", 1.0, 10.0, default_dev_pct)
    horizon_days = st.slider("Forward return horizon (trading days)", 1, 20, default_horizon)

    cfg = IndicatorConfig(
        ma_short=ma_short,
        ma_long=ma_long,
        deviation_threshold=dev_pct / 100,
    )

_set_qp({
    "ticker": ticker.upper(),
    "period": period,
    "ma_short": ma_short,
    "ma_long": ma_long,
    "dev": dev_pct,   # percent
    "h": horizon_days
})

# Fetch + compute
query = MarketQuery(ticker=ticker.upper(), period=period)
df = fetch_ohlc(query)

if df.empty:
    st.error("No data returned.")
    st.stop()

signals = compute_signals(df, cfg)

# Fetch instrument metadata (lightweight)
try:
    info = yf.Ticker(ticker.upper()).info
    long_name = info.get("longName") or info.get("shortName") or ""
except Exception:
    long_name = ""

# Title (now ticker + name are defined)
title_line = f"📈 {ticker.upper()}"
if long_name:
    title_line += f" — {long_name}"

st.title(title_line)
st.caption("Baseline financial signals — trends, volatility, and deviations")


# --- Price + MAs ---
st.subheader("Price & Trend")

fig, ax = plt.subplots()
ax.plot(signals.index, signals["Adj Close"], label="Adj Close")
ax.plot(signals.index, signals["ma_short"], label="Short MA")
ax.plot(signals.index, signals["ma_long"], label="Long MA")

# Mark signal points
signal_points = signals[signals["signal"]]
ax.scatter(
    signal_points.index,
    signal_points["Adj Close"],
    color="red",
    label="Signal",
    zorder=5,
)

ax.legend()
ax.set_ylabel("Price")
st.pyplot(fig)


# --- Volatility --
st.subheader("Rolling Volatility")

fig2, ax2 = plt.subplots()
ax2.plot(signals.index, signals["volatility"])
ax2.set_ylabel("Volatility (Std of Returns)")
st.pyplot(fig2)


# --- Latest signal summary ---
latest = signals.iloc[-1]

st.subheader("Latest Snapshot")

col1, col2, col3 = st.columns(3)
col1.metric("Price", f"{latest['Adj Close']:.2f}")
col2.metric("Deviation", f"{latest['deviation']*100:.2f}%")
col3.metric("Signal Active", "Yes" if latest["signal"] else "No")


# --- Evaluation ---
st.subheader("Evaluation (Baseline Check)")

summary = summarize_signal_performance(signals, horizon_days=horizon_days)

# Make it readable as percentages
summary_display = summary.copy()
summary_display["mean_fwd_return"] = (summary_display["mean_fwd_return"] * 100).round(3)
summary_display["median_fwd_return"] = (summary_display["median_fwd_return"] * 100).round(3)

st.dataframe(summary_display, use_container_width=True, hide_index=True)

st.caption("🔗 Tip: Bookmark or share this URL to save the current view.")

signal_count = int(summary.loc[summary["group"] == "signal_days", "count"].iloc[0])
st.caption(
    f"Note: signal days are often rare. You have **{signal_count}** signal day(s) in this sample for the current settings."
)