# market_app.py
from __future__ import annotations
from signals.backtest import compute_equity_curves, summarize_backtest
from signals.sweep import SweepConfig, run_sweep

import streamlit as st
import matplotlib.pyplot as plt
import yfinance as yf
import base64
import seaborn as sns

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

def render_disclaimer():
    st.sidebar.markdown("---")
    st.sidebar.caption("⚠️ **DISCLAIMER: EDUCATIONAL USE ONLY**")
    st.sidebar.caption(
        """
        This application is for **research and demonstration purposes only**. 
        It does not constitute financial advice, investment recommendations, 
        or a solicitation to buy or sell any assets.
        
        * **No Liability:** The creator assumes no responsibility for any financial losses.
        * **Data:** Market data is sourced from free third-party APIs (Yahoo Finance) 
            and may be delayed or inaccurate.
        * **Hypothetical:** Backtest results are based on historical data and 
            do not guarantee future performance.
            
        **Trade at your own risk.**
        """
    )

def plot_monthly_heatmap(bt_df):
    # Calculate monthly compounding returns
    monthly_rets = bt_df["strat_rets"].resample('ME').apply(lambda x: (1 + x).prod() - 1)
    
    # Reshape for the grid
    df_h = monthly_rets.to_frame()
    df_h['Year'] = df_h.index.year
    df_h['Month'] = df_h.index.month_name().str[:3]
    pivot = df_h.pivot(index='Year', columns='Month', values='strat_rets')
    
    # Order months correctly
    m_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    pivot = pivot.reindex(columns=[m for m in m_order if m in pivot.columns])

    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor(BG_MAIN)
    
    # Institutional 'RdYlGn' color scheme (Red for loss, Green for gain)
    sns.heatmap(pivot * 100, annot=True, fmt=".1f", cmap="RdYlGn", center=0, 
                cbar=False, ax=ax, annot_kws={"size": 9, "weight": "bold"})
    
    ax.set_title("Tactical Performance Attribution (%)", color=TEXT_PRIMARY, pad=15)
    ax.tick_params(colors=TEXT_MUTED)
    return fig

def generate_risk_commentary(ticker, metrics_df, latest_data):
    # Ensure numeric extraction
    strat = metrics_df[metrics_df["Portfolio"] == "Tactical Risk-Off"].iloc[0]
    bh = metrics_df[metrics_df["Portfolio"] == "Buy & Hold"].iloc[0]
    
    # Calculate differences
    sharpe_diff = float(strat["Sharpe"]) - float(bh["Sharpe"])
    bh_dd_abs = abs(float(bh["Max Drawdown"]))
    strat_dd_abs = abs(float(strat["Max Drawdown"]))
    dd_reduction = (bh_dd_abs - strat_dd_abs) * 100
    
    # Logic for status
    status = "DEFENSIVE (Cash)" if latest_data["is_cooldown"] == 1 else "ACTIVE (Invested)"
    
    # Return raw bullet points (no extra HTML here)
    return (
        f"<li><b>Risk Regime</b>: {status}</li>"
        f"<li><b>Alpha Generation</b>: +{sharpe_diff:.2f} Sharpe points vs Benchmark</li>"
        f"<li><b>Risk Mitigation</b>: Max Drawdown reduced by {dd_reduction:.2f}%</li>"
        f"<li><b>Current Deviation</b>: {latest_data['deviation']*100:.2f}%</li>"
    )

def format_metrics_table(metrics):
    m = metrics.copy()
    
    # 1. Format numbers as percentages for the B2B dashboard
    pct_cols = ["Total Return", "Ann. Return", "Ann. Vol", "Max Drawdown"]
    for col in pct_cols:
        m[col] = (m[col] * 100).round(2).astype(str) + "%"
    
    # 2. Round the ratio columns
    m["Sharpe"] = m["Sharpe"].round(2)
    m["Calmar"] = m["Calmar"].round(2)
    
    return m

def plot_drawdown_chart(bt_df):
    fig, ax = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor(BG_MAIN)
    style_dark_ax(ax)

    # We plot the 'Underwater' area
    ax.fill_between(bt_df.index, bt_df["bh_dd"] * 100, 0, 
                   color=RED, alpha=0.3, label="B&H Drawdown")
    ax.plot(bt_df.index, bt_df["strat_dd"] * 100, 
            color=GREEN, label="Tactical Risk-Off Drawdown", linewidth=1.5)

    ax.set_ylabel("Drawdown (%)")
    ax.set_title("Underwater Analysis (Peak-to-Trough Decline)", color=TEXT_PRIMARY, pad=20)
    
    # Ensure the Y-axis makes sense (0% at top, negative below)
    ax.set_ylim(top=0) 
    
    leg = ax.legend(frameon=False, loc="lower left")
    for t in leg.get_texts():
        t.set_color(TEXT_PRIMARY)
        
    return fig

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
    render_disclaimer()

    # ... inside st.sidebar, after render_disclaimer() ...
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        <div style="text-align: center;">
            <p style="font-size: 14px; color: #A0A0A8; margin-bottom: 5px;">
                Engineered by <b>Aryaman Sondhi</b>
            </p>
            <a href="https://www.linkedin.com/in/aryaman-sondhi/" target="_blank">LinkedIn</a> • 
            <a href="https://github.com/aryamansondhi" target="_blank">GitHub</a>
        </div>
        """, 
        unsafe_allow_html=True
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
    latest = bt.iloc[-1]
    analysis = generate_risk_commentary(ticker.upper(), metrics, latest)

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
        st.subheader("Tactical Risk Analytics")
        
        # 1. Prepare Data
        strat_row = metrics[metrics["Portfolio"] == "Tactical Risk-Off"].iloc[0]
        bh_row = metrics[metrics["Portfolio"] == "Buy & Hold"].iloc[0]
        
        sharpe_diff = float(strat_row["Sharpe"]) - float(bh_row["Sharpe"])
        # Calculate Drawdown reduction
        dd_red = (abs(float(bh_row["Max Drawdown"])) - abs(float(strat_row["Max Drawdown"]))) * 100
        
        # Check if we are currently in cash
        is_cash = latest["is_cooldown"] == 1
        status_text = "DEFENSIVE (Cash)" if is_cash else "ACTIVE (Invested)"
        status_color = "#FFDD55" if is_cash else "#00E050" # Yellow vs Green

        # 2. Render the "Institutional Risk Summary" Card
        # Use a standard HTML block to prevent tag leakage
        st.markdown(f"""
        <div style="background-color: #16161A; border: 1px solid {GREEN}; border-radius: 12px; padding: 20px; margin-bottom: 25px;">
            <h4 style="color: {GREEN}; margin-top: 0; margin-bottom: 10px;">
                🪄 Institutional Risk Summary
            </h4>
            <div style="color: {TEXT_PRIMARY}; line-height: 1.6; font-size: 16px;">
                <ul style="margin-bottom: 0; padding-left: 20px;">
                    <li><b>Risk Regime:</b> <span style="color:{status_color}; font-weight:bold;">{status_text}</span></li>
                    <li><b>Alpha Generation:</b> {sharpe_diff:+.2f} Sharpe points vs Benchmark.</li>
                    <li><b>Risk Mitigation:</b> Max Drawdown reduced by {dd_red:.2f}%.</li>
                    <li><b>Current Deviation:</b> {latest['deviation']*100:.2f}%</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 3. Metrics Table
        st.dataframe(format_metrics_table(metrics), use_container_width=True, hide_index=True)
        
        st.divider()
        
        # 4. Visuals (Heatmap & Drawdown)
        st.markdown("##### Monthly Performance Attribution (%)")
        st.pyplot(plot_monthly_heatmap(bt), use_container_width=True)
        
        st.markdown("##### Drawdown Profile (Underwater Analysis)")
        st.pyplot(plot_drawdown_chart(bt), use_container_width=True)

        # --- NEW: Data Export for Institutional Analysis ---
        st.divider()
        st.caption("📥 **Institutional Data Export**")
        
        # Convert to CSV
        csv = bt.to_csv().encode('utf-8')
        
        st.download_button(
            label="⬇️ Download Backtest Data (CSV)",
            data=csv,
            file_name=f"{ticker}_backtest_results.csv",
            mime="text/csv",
            help="Export daily returns, signals, and equity curves for external analysis."
        )

    with tab_research:
        st.subheader("Research (Parameter Sweep)")
        st.caption("Runs a grid over deviation threshold and cooldown to check robustness.")

        # --- 1. RUN LOGIC ---
        if run_research:
            sweep_cfg = SweepConfig(
                ma_short=cfg.ma_short,
                ma_long=cfg.ma_long,
                dev_pcts=(1.0, 2.0, 3.0, 4.0, 5.0, 6.0),
                cooldown_days=(1, 3, 5, 7, 10, 15),
            )
            with st.spinner("Running sweep..."):
                # Save results to session state
                st.session_state["sweep_results"] = cached_sweep(df, sweep_cfg)

        # --- 2. DISPLAY LOGIC (Direct Mode) ---
        if "sweep_results" in st.session_state:
            res = st.session_state["sweep_results"]

            if min_signals < 5:
                st.warning("Low min signal threshold can produce misleading 'best' configs. Try 5+.")

            # Filter weak sample sizes
            filtered = res[res["signal_count"] >= min_signals].copy()
            
            if filtered.empty:
                st.error("No strategies met the minimum signal count. Try lowering the filter.")
            else:
                # Prepare Display DataFrame
                disp = filtered.copy()
                for col in ["strategy_total_return", "buyhold_total_return", "delta_total_return"]:
                    disp[col] = (disp[col] * 100).round(2)
                
                disp["strategy_max_dd"] = (disp["strategy_max_dd"] * 100).round(2)
                
                for col in ["strategy_sharpe", "buyhold_sharpe", "delta_sharpe"]:
                    disp[col] = disp[col].round(2)

                # Sort by Sharpe Improvement
                disp = disp.sort_values("delta_sharpe", ascending=False)

                # Rename Columns
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

                # --- 3. INSTANT FEEDBACK ---
                best_run = disp.iloc[0]
                sharpe_diff = best_run["Sharpe Diff"]
                
                if sharpe_diff > 0.5:
                     st.success(f"🚀 ALPHA DETECTED! Strategy beats Buy & Hold by {sharpe_diff} Sharpe points.")
                elif sharpe_diff > 0:
                    st.info(f"✅ Strategy beats Buy & Hold by {sharpe_diff} Sharpe points.")
                else:
                    st.warning("Strategy underperforms the market.")

                st.markdown("##### Sweep results")
                st.dataframe(disp, use_container_width=True, hide_index=True)

        else:
            st.info("Click **Run sweep** to generate the robustness table.")

st.caption("🔗 Tip: Bookmark or share this URL to save the current view.")

st.caption("Built in public. Educational signals, not financial advice.")