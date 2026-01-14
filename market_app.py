# market_app.py
from __future__ import annotations

import streamlit as st
import matplotlib.pyplot as plt

from data.market_data import MarketQuery, fetch_ohlc
from signals.indicators import IndicatorConfig, compute_signals


st.set_page_config(page_title="Market Signals", layout="centered")
st.title("📈 Market Signal Dashboard")

st.caption("Baseline financial signals — trends, volatility, and deviations")

# Sidebar controls
with st.sidebar:
    st.header("Settings")

    ticker = st.text_input("Ticker", value="SPY")
    period = st.selectbox("Period", ["6mo", "1y", "2y"], index=0)

    cfg = IndicatorConfig(
        ma_short=st.slider("Short MA window", 5, 30, 10),
        ma_long=st.slider("Long MA window", 20, 100, 30),
        deviation_threshold=st.slider("Deviation threshold (%)", 1.0, 10.0, 3.0) / 100,
    )

# Fetch + compute
query = MarketQuery(ticker=ticker.upper(), period=period)
df = fetch_ohlc(query)

if df.empty:
    st.error("No data returned.")
    st.stop()

signals = compute_signals(df, cfg)

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

# --- Volatility ---
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