# 🌦️ Signal Lab (Vibe Coding)

A premium dark-mode weather application built as part of a **100-day vibe coding challenge**.

This project focuses on **product thinking, data reasoning, and clean engineering** — not just shipping features.

---

## ✨ Features

- 📈 **Market Data:** Real-time OHLCV fetching via Yahoo Finance.
- ⚡ **Signal Engine:** Deviation-based mean reversion signals with customizable Moving Averages.
- 🧪 **Backtest Lab:** Compare "Risk-Off" cooldown strategies against Buy & Hold equity curves.
- 🎛️ **Robustness Sweep:** Grid search engine to test strategy performance across different volatility thresholds.
- 🎨 **Pro UI:** Custom high-contrast dark mode with "SignalLab" branding.

---

## 🗂️ Project Structure

weather-app/
├── app.py # UI + orchestration
├── services.py # API + data access
├── utils.py # Pure logic, theming, heuristics
├── README.md

---

## 🚀 How to Run

### Requirements
- Python 3.11+
- `uv` installed

### Setup
```bash
uv sync

Run the app
uv run streamlit run app.py

'''

🧠 Design Philosophy

Thin UI layer

Pure logic separated from I/O

Product-oriented insights over raw data

📅 Vibe Coding Log

Day 1: MVP weather app, API integration, dark UI

Day 2: Refactor, modularization, comfort score insight, favorites, polish

Day 3: Built a market signals dashboard (SPY by default): OHLC fetch, returns/volatility, moving averages, deviation-based signal flags, Streamlit visualization.

Day 4: Added signal evaluation using forward N-day returns (baseline check: signal vs non-signal vs overall) + interactive horizon control in the dashboard.

Day 5: URL-synced state for shareable, reproducible views

Day 6: Backtest layer (risk-off cooldown strategy), equity curves, and core risk metrics (Sharpe, drawdown, vol).

Day 7: Robustness & Branding
- **Backend:** Added parameter sweep (grid search) to test strategy robustness across various settings.
- **Frontend:** Overhauled UI with a custom high-contrast dark theme, centered layout, and HTML-injected logo.

📌 Next Ideas

📌 Next Ideas
- [ ] Vectorize backtest engine (Performance upgrade)
- [ ] Rolling risk metrics (Regime detection)
- [ ] Interactive charts (Plotly integration)
- [ ] Real-time data feed connection

---