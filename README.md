# 📉 Signal Lab (Vibe Coding)

A premium **institutional-grade risk analytics dashboard** built as part of a **100-day vibe coding challenge**.

This project focuses on **financial engineering, vectorized backtesting, and B2B product design** — creating a tool that a Dubai Portfolio Manager would actually use.

---

## ✨ Features

- 📈 **Market Data:** Real-time OHLCV fetching via Yahoo Finance.
- ⚡ **Vectorized Engine:** Lightning-fast pandas-based backtester (no loops).
- 🛡️ **Risk Analytics:** Professional drawdown profiles (Underwater plots), Calmar Ratios, and Monthly Heatmaps.
- 🪄 **AI Narrative Layer:** Deterministic "AI Analyst" that generates text summaries based on hard math (hallucination-free).
- 🎛️ **Robustness Sweep:** Grid search engine to test strategy performance across different volatility thresholds.
- 🎨 **Pro UI:** Custom high-contrast dark mode with glassmorphism effects.

---

## 🗂️ Project Structure

```text
signal-lab/
├── market_app.py       # Main Streamlit Dashboard (UI)
├── data/
│   └── market_data.py  # Yahoo Finance wrappers
├── signals/
│   ├── backtest.py     # Vectorized equity curves & risk metrics
│   ├── indicators.py   # Technical indicators (MA, Deviation, Z-Score)
│   ├── sweep.py        # Parameter grid search engine
│   └── evaluation.py   # Signal quality metrics
├── logo.png            # Branding asset
└── README.md

```
🚀 How to Run
Requirements
Python 3.11+

uv installed (or pip)

Setup

# Install dependencies
uv sync

# Run the app
uv run streamlit run market_app.py

🧠 Design Philosophy
Data Density: Institutional users need curves and heatmaps, not fluff.

Deterministic AI: AI features must be grounded in math (RAG-lite) to prevent financial hallucinations.

Vectorized Speed: Loops are banned in the calculation layer to ensure instant feedback.

📅 Vibe Coding Log
Day 1-2: MVP setup, API integration, and dark UI foundations.

Day 3-5: Built the Signal Engine (Mean Reversion) and interactive dashboard controls.

Day 6-7: Added Backtesting and the "Robustness Sweep" grid search.

Day 8: Refactor: Migrated to a fully vectorized engine (removed all for-loops) for 100x speed gains.

Day 9: Risk Analytics: Added Institutional Metrics (Calmar, Max Drawdown), Underwater Plots, Monthly Heatmaps, and the "AI Risk Commentary" layer.

📌 Next Ideas
[ ] Deployment: Ship to Streamlit Community Cloud (Day 10).

[ ] Mobile Optimization: Ensure the dashboard is responsive for client demos.

[ ] PDF Reporting: Generate "One-Pager" investor reports.

[ ] Multi-Asset: Support Crypto/Forex pairs alongside Equities.