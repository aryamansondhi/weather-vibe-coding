# market_app.py
from __future__ import annotations
from signals.backtest import compute_equity_curves, summarize_backtest
from signals.sweep import SweepConfig, run_sweep

import streamlit as st
import matplotlib.pyplot as plt
import yfinance as yf
import base64

from data.market_data import MarketQuery, fetch_ohlc
from signals.indicators import IndicatorConfig, compute_signals
from signals.evaluation import summarize_signal_performance

# --- UI Palette (High Contrast Dark Mode) ---
BG_MAIN = "#0B0B0E"        # Deep black app background
BG_PANEL = "#16161A"       # Lighter panel (was #111114)
BORDER_SUBTLE = "#2A2A30"  # Much more visible border (was #1C1C22)

TEXT_PRIMARY = "#F2F2F5"   # Brighter white
TEXT_MUTED = "#A0A0A8"     # Lighter grey for better readability

GREEN = "#00E050"          # Vivid green
RED = "#FF5555"            # Vivid red
NEUTRAL = "#A1A1AA"        # Secondary lines

def style_dark_ax(ax):
    ax.set_facecolor(BG_MAIN)
    ax.grid(alpha=0.12)
    ax.tick_params(colors=TEXT_MUTED)

    ax.yaxis.label.set_color(TEXT_MUTED)
    ax.xaxis.label.set_color(TEXT_MUTED)

    for spine in ax.spines.values():
        spine.set_color(BORDER_SUBTLE)

def format_metrics_table(metrics):
    m = metrics.copy()
    
    # 1. Rename the row values to English
    m["portfolio"] = m["portfolio"].replace({
        "buy_hold": "Buy & Hold",
        "strategy": "Active Strategy"
    })

    # 2. Format numbers as percentages
    for col in ["total_return", "ann_return", "ann_vol", "max_drawdown"]:
        m[col] = (m[col] * 100).round(2)
    m["sharpe"] = m["sharpe"].round(2)
    
    # 3. Rename columns
    return m.rename(columns={
        "portfolio": "Portfolio",
        "total_return": "Total Return (%)",
        "ann_return": "Ann Return (%)",
        "ann_vol": "Ann Vol (%)",
        "max_drawdown": "Max DD (%)",
        "sharpe": "Sharpe",
    })

def _get_qp() -> dict:
    # Streamlit provides st.query_params in newer versions
    try:
        return dict(st.query_params)
    except Exception:
        return {}

@st.cache_data(show_spinner=False)
def cached_sweep(df, sweep_cfg):
    return run_sweep(df, sweep_cfg)

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

st.set_page_config(
    page_title="SignalLab",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Logo ---
# --- LOGO (HTML INJECTION) ---
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# This HTML block guarantees centering
logo_b64 = get_base64_image("logo.png")
st.markdown(
    f"""
    <div style="display: flex; justify-content: center; margin-bottom: -10px;">
        <img src="data:image/png;base64,{logo_b64}" width="400">
    </div>
    """,
    unsafe_allow_html=True
)

# --- Tabs ---
tab_overview, tab_strategy, tab_research = st.tabs(["Overview", "Strategy", "Research"])

st.markdown(
    f"""
    <style>
    /* App background */
    .stApp {{
        background: {BG_MAIN};
        color: {TEXT_PRIMARY};
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: {BG_PANEL};
        border-right: 1px solid {BORDER_SUBTLE};
    }}

    /* --- TABS CONFIGURATION --- */
    div[data-baseweb="tab-list"] {{
        justify-content: center;
        width: 100%;
        margin-top: 0;        /* Removes default space above tabs */
        gap: 2rem;            /* Adds nice breathing room between tabs */
        border-bottom: none !important;
    }}
    
    /* HIDE NATIVE STREAMLIT TAB HIGHLIGHT (Fixes the glitch) */
    div[data-baseweb="tab-highlight"] {{
        display: none !important;
    }}
    
    /* Tab Styling (Inactive) */
    button[data-baseweb="tab"] {{
        font-size: 16px !important;
        font-weight: 600 !important;
        background-color: transparent !important;
        border: none !important;
        color: {TEXT_MUTED};
        padding: 0.5rem 1rem !important; 
    }}
    
    /* Tab Styling (Active Only) */
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {TEXT_PRIMARY} !important;
        border-bottom: 2px solid {GREEN} !important;
    }}

    /* Headers */
    h1, h2, h3 {{
        font-weight: 650;
        letter-spacing: -0.02em;
        color: {TEXT_PRIMARY};
    }}

    /* Captions */
    .stCaption, [data-testid="stCaptionContainer"] {{
        color: {TEXT_MUTED} !important;
    }}

    /* Metrics */
    [data-testid="stMetricValue"] {{
        font-size: 28px;
        font-weight: 650;
        color: {TEXT_PRIMARY};
    }}
    [data-testid="stMetricLabel"] {{
        color: {TEXT_MUTED};
    }}

    /* Dataframes */
    [data-testid="stDataFrame"] {{
        background: {BG_PANEL};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 14px;
        padding: 6px;
    }}

    /* Buttons */
    .stButton>button {{
        background: #222228 !important; 
        color: {TEXT_PRIMARY} !important;
        border: 1px solid {BORDER_SUBTLE} !important;
        border-radius: 10px !important;
        padding: 0.6rem 0.9rem !important;
        font-weight: 600 !important;
    }}
    .stButton>button:hover {{
        border-color: {TEXT_MUTED} !important;
        color: {GREEN} !important;
    }}

    /* Clean up header */
    header {{
        background: transparent !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

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
    cooldown_days = st.slider("Risk-off cooldown (days)", 1, 20, 5)

    st.divider()
    st.header("Research")

    run_research = st.button("Run sweep")
    min_signals = st.slider("Min signal count (filter)", 0, 50, 5)

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
bt = compute_equity_curves(signals, cooldown_days=cooldown_days)
metrics = summarize_backtest(bt)

# Fetch instrument metadata (lightweight)
try:
    info = yf.Ticker(ticker.upper()).info
    long_name = info.get("longName") or info.get("shortName") or ""
except Exception:
    long_name = ""

with tab_overview:

    # Title (now ticker + name are defined)
    # --- Header ---
    st.markdown(f"## {ticker.upper()}")

    if long_name:
        st.caption(long_name)

    st.caption("Signals, backtest, and robustness in one place.")

    # --- At-a-glance metrics ---
    latest = signals.iloc[-1]

    c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1])
    c1.metric("Price", f"{latest['Adj Close']:.2f}")
    c2.metric("Deviation", f"{latest['deviation']*100:.2f}%")
    c3.metric("Volatility", f"{latest['volatility']*100:.2f}%")
    c4.metric("Signal", "ON" if latest["signal"] else "OFF")

    # --- Price + MAs ---
    fig, ax = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor(BG_MAIN)
    style_dark_ax(ax)

    ax.plot(signals.index, signals["Adj Close"], label="Price", color=TEXT_PRIMARY)
    ax.plot(signals.index, signals["ma_short"], label="Short MA", color=NEUTRAL)
    ax.plot(signals.index, signals["ma_long"], label="Long MA", color=GREEN)

    signal_points = signals[signals["signal"]]
    if not signal_points.empty:
        ax.scatter(signal_points.index, signal_points["Adj Close"], color=RED, label="Signal", zorder=5)

    ax.set_ylabel("Price")

    leg = ax.legend(frameon=False)
    for t in leg.get_texts():
        t.set_color(TEXT_PRIMARY)

    st.pyplot(fig, use_container_width=True)

    # --- Volatility --
    st.subheader("Rolling Volatility")

    fig2, ax2 = plt.subplots(figsize=(12, 4))
    fig2.patch.set_facecolor(BG_MAIN)
    style_dark_ax(ax2)

    ax2.plot(signals.index, signals["volatility"], color=NEUTRAL)
    ax2.set_ylabel("Volatility (Std of Returns)")

    st.pyplot(fig2, use_container_width=True)

    with tab_strategy:
        # --- Evaluation ---
        st.markdown("##### Evaluation (baseline check)")

        summary = summarize_signal_performance(signals, horizon_days=horizon_days)

        # Make it readable as percentages
        summary_display = summary.copy()
        summary_display["mean_fwd_return"] = (summary_display["mean_fwd_return"] * 100).round(3)
        summary_display["median_fwd_return"] = (summary_display["median_fwd_return"] * 100).round(3)

        # --- Rename Columns & Rows for Display ---
        summary_display = summary_display.rename(columns={
            "group": "Market State",
            "count": "Count (Days)",
            "mean_fwd_return": "Average Return (%)",
            "median_fwd_return": "Median Return (%)"
        })
        
        summary_display["Market State"] = summary_display["Market State"].replace({
            "signal_days": "Signal Active",
            "non_signal_days": "No Signal",
            "overall": "Baseline (All Days)"
        })

        st.caption("Forward returns grouped by signal vs non-signal days.")

        # Display the renamed table
        st.dataframe(summary_display, use_container_width=True, hide_index=True)

        signal_count = int(summary.loc[summary["group"] == "signal_days", "count"].iloc[0])
        st.caption(
            f"Note: signal days are often rare. You have **{signal_count}** signal day(s) in this sample for the current settings."
        )

        st.subheader("Backtest (Signal → Strategy)")

        # Equity curve chart
        fig3, ax3 = plt.subplots(figsize=(12, 4))
        fig3.patch.set_facecolor(BG_MAIN)
        style_dark_ax(ax3)

        ax3.plot(bt.index, bt["bh_equity"], label="Buy & Hold", color=NEUTRAL)
        ax3.plot(bt.index, bt["strat_equity"], label="Signal Strategy", color=GREEN)
        ax3.set_ylabel("Equity (start = 1.0)")

        leg = ax3.legend(frameon=False)
        for t in leg.get_texts():
            t.set_color(TEXT_PRIMARY)

        st.pyplot(fig3, use_container_width=True)

        # Metrics table
        metrics_display = metrics.copy()
        for col in ["total_return", "ann_return", "ann_vol", "max_drawdown"]:
            metrics_display[col] = (metrics_display[col] * 100).round(2)

        metrics_display["sharpe"] = metrics_display["sharpe"].round(2)

        st.markdown("##### Strategy metrics")

        st.dataframe(format_metrics_table(metrics), use_container_width=True, hide_index=True)

        st.caption(
            "Strategy rule: if a signal triggers today, the strategy goes to cash starting next trading day for the cooldown window."
        )

    with tab_research:
        st.subheader("Research (Parameter Sweep)")

        st.caption("Runs a grid over deviation threshold and cooldown to check robustness. Filter out tiny sample sizes.")

        if run_research:
            sweep_cfg = SweepConfig(
                ma_short=cfg.ma_short,
                ma_long=cfg.ma_long,
                dev_pcts=(1.0, 2.0, 3.0, 4.0, 5.0, 6.0),
                cooldown_days=(1, 3, 5, 7, 10, 15),
            )

            with st.spinner("Running sweep…"):
                res = cached_sweep(df, sweep_cfg)

            if min_signals < 5:
                st.warning("Low min signal threshold can produce misleading 'best' configs. Try 5+.")

            # 1. Filter weak sample sizes
            res = res[res["signal_count"] >= min_signals].copy()

            # 2. Prepare Display DataFrame (Rounding)
            disp = res.copy()
            for col in ["strategy_total_return", "buyhold_total_return", "delta_total_return"]:
                disp[col] = (disp[col] * 100).round(2)
            
            disp["strategy_max_dd"] = (disp["strategy_max_dd"] * 100).round(2)
            
            for col in ["strategy_sharpe", "buyhold_sharpe", "delta_sharpe"]:
                disp[col] = disp[col].round(2)

            # 3. Sort by Sharpe Improvement
            disp = disp.sort_values("delta_sharpe", ascending=False)

            # 4. Rename Columns for English Display
            disp = disp.rename(columns={
                "dev_pct": "Threshold (%)",
                "cooldown_days": "Cooldown (Days)",
                "signal_count": "Signals (Count)",
                "strategy_total_return": "Strat Return (%)",
                "strategy_sharpe": "Strat Sharpe",
                "strategy_max_dd": "Strat Max DD (%)",
                "buyhold_total_return": "B&H Return (%)",
                "buyhold_sharpe": "B&H Sharpe",
                "delta_total_return": "Return Diff (%)",
                "delta_sharpe": "Sharpe Diff"
            })

            st.markdown("##### Sweep results")
            
            # Display the CLEAN dataframe (disp), not the old variable
            st.dataframe(disp, use_container_width=True, hide_index=True)

            st.caption("Tip: if signal_count is tiny (like 0–2), ignore the results. It’s not evidence.")
        else:
            st.info("Click **Run sweep** to generate the robustness table.")

st.caption("🔗 Tip: Bookmark or share this URL to save the current view.")

st.caption("Built in public. Educational signals, not financial advice.")