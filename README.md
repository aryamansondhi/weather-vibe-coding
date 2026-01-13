# 🌦️ Weather App (Vibe Coding)

A premium dark-mode weather application built as part of a **100-day vibe coding challenge**.

This project focuses on **product thinking, data reasoning, and clean engineering** — not just shipping features.

---

## ✨ Features

- 🌍 City search with geocoding  
- 🌡️ Celsius ↔ Fahrenheit toggle  
- 🎨 Dark UI with **weather-reactive theming**  
- ⭐ Favorites (quick access cities)  
- 📊 7-day forecast (chart + table)  
- 🧠 Comfort Score (simple heuristic insight)  
- ⚡ Cached API calls for fast reloads  

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

📌 Next Ideas

Hourly forecast strip

Location auto-detect

Deploy to Streamlit Cloud

Historical comparisons

Built with intention, not tutorials.

---