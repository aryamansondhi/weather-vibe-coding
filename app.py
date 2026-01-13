# app.py
from __future__ import annotations

import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Any, Dict, List, Optional

from services import geocode_city, get_weather
from utils import (
    WEATHER_CODE,
    PALETTES,
    c_to_f,
    fmt_num,
    weather_family,
    mood_icon,
    comfort_score,
    comfort_label,
)

st.set_page_config(page_title="Weather", page_icon="☁️", layout="centered")


def inject_css(p: Dict[str, str]) -> None:
    st.markdown(
        f"""
<style>
.stApp {{
  background: radial-gradient(1200px 700px at 15% 10%, rgba(229,9,20,0.18), transparent 55%),
              radial-gradient(900px 600px at 85% 20%, rgba(124,58,237,0.16), transparent 55%),
              linear-gradient(180deg, {p["bg_top"]} 0%, {p["bg_bottom"]} 100%);
  color: rgba(255,255,255,0.92);
}}
.block-container {{
  padding-top: 2.2rem;
  padding-bottom: 2.2rem;
  max-width: 920px;
}}
header, footer {{ visibility: hidden; }}

.small-muted {{
  color: {p["muted"]};
  font-size: 0.95rem;
}}
.stTextInput > div > div > input {{
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid {p["border"]} !important;
  border-radius: 14px !important;
  padding: 0.9rem 1rem !important;
  color: rgba(255,255,255,0.92) !important;
}}
.stTextInput label {{ color: {p["muted"]} !important; }}

.stButton > button {{
  width: 100%;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,0.10);
  background: linear-gradient(90deg, {p["accent"]}, {p["accent2"]});
  color: #0B0D12;
  font-weight: 800;
  padding: 0.85rem 1rem;
  transition: transform 0.12s ease, filter 0.12s ease;
}}
.stButton > button:hover {{ transform: translateY(-1px); filter: brightness(1.06); }}
.stButton > button:active {{ transform: translateY(0px); filter: brightness(0.98); }}

.card {{
  background: {p["card"]};
  border: 1px solid {p["border"]};
  border-radius: 18px;
  padding: 1.1rem 1.1rem;
  box-shadow: 0 14px 40px rgba(0,0,0,0.45);
}}
.cardGlow {{ position: relative; overflow: hidden; }}
.cardGlow:before {{
  content: "";
  position: absolute;
  inset: -2px;
  background: radial-gradient(600px 240px at 15% 0%,
      rgba(255,255,255,0.08),
      rgba(255,255,255,0.00) 55%);
  pointer-events: none;
}}
.accentLine {{
  height: 3px; width: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, {p["accent"]}, {p["accent2"]});
  margin-bottom: 0.8rem;
  opacity: 0.95;
}}
.kpi {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.8rem;
  margin-top: 0.8rem;
}}
.kpiItem {{
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 0.9rem 0.9rem;
}}
.kpiLabel {{ color: {p["muted"]}; font-size: 0.85rem; margin-bottom: 0.25rem; }}
.kpiValue {{ font-size: 1.25rem; font-weight: 900; letter-spacing: -0.02em; }}
.badge {{
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.10);
  color: rgba(255,255,255,0.88);
  font-size: 0.9rem;
}}
.hr {{ height: 1px; width: 100%; background: rgba(255,255,255,0.10); margin: 1.1rem 0; }}
@media (max-width: 740px) {{ .kpi {{ grid-template-columns: 1fr; }} }}
</style>
        """,
        unsafe_allow_html=True,
    )


# Default theme until we fetch weather
inject_css(PALETTES["default"])


# Session state (favorites)
if "favorites" not in st.session_state:
    st.session_state.favorites = ["Delhi", "New York", "London"]


# Sidebar: units + favorites
with st.sidebar:
    st.markdown("### Settings")
    use_fahrenheit = st.toggle("Show temperatures in °F", value=False)

    st.markdown("### Favorites")
    fav = st.selectbox("Quick pick", options=st.session_state.favorites, index=0)

    add_city = st.text_input("Add a favorite city", placeholder="e.g., Paris")
    if st.button("Add to favorites"):
        c = (add_city or "").strip()
        if c and c not in st.session_state.favorites:
            st.session_state.favorites.insert(0, c)
            st.success("Added.")
        elif c in st.session_state.favorites:
            st.info("Already in favorites.")
        else:
            st.warning("Type a city name first.")

    if st.button("Remove selected favorite"):
        if fav in st.session_state.favorites and len(st.session_state.favorites) > 1:
            st.session_state.favorites.remove(fav)
            st.success("Removed.")
        else:
            st.info("Keep at least one favorite.")


# Header
st.markdown("<div class='small-muted'>Day 2: cleaner architecture • one insight • same premium UI</div>", unsafe_allow_html=True)
st.markdown("<h1 style='margin-top:0.3rem;'>Weather</h1>", unsafe_allow_html=True)
st.markdown("<div class='small-muted'>Search a city, see current conditions + a 7-day outlook.</div>", unsafe_allow_html=True)
st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

# Main input defaults to selected favorite
city = st.text_input("City", value=fav, placeholder="e.g., Delhi, New York, London")

colA, colB = st.columns([1, 1])
with colA:
    go = st.button("Get weather")
with colB:
    st.caption("Tip: add country/state if ambiguous (e.g., Springfield, IL)")


if not go:
    st.markdown(
        """
<div class="card cardGlow">
  <div class="accentLine"></div>
  <div style="font-size:1.1rem; font-weight:900;">Ready.</div>
  <div class="small-muted" style="margin-top:0.35rem;">
    Pick a favorite or type a city. Then hit <b>Get weather</b>.
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# Fetch + render
try:
    geo = geocode_city(city.strip())
    if not geo:
        st.error("City not found. Try adding a country/state (e.g., 'Springfield, IL').")
        st.stop()

    lat, lon = geo["latitude"], geo["longitude"]
    place = f'{geo.get("name")}, {geo.get("admin1","")}, {geo.get("country","")}'.replace(" ,", ",").strip()

    wx = get_weather(lat, lon)
    current: Dict[str, Any] = (wx.get("current") or {})
    daily: Dict[str, Any] = (wx.get("daily") or {})

    temp_c = current.get("temperature_2m")
    feels_c = current.get("apparent_temperature")
    wind = current.get("wind_speed_10m")
    code = current.get("weather_code")

    condition = WEATHER_CODE.get(code, f"Weather code {code}")
    mood = weather_family(code)
    palette = PALETTES.get(mood, PALETTES["default"])
    inject_css(palette)

    # units
    temp = c_to_f(temp_c) if use_fahrenheit else temp_c
    feels = c_to_f(feels_c) if use_fahrenheit else feels_c
    unit = "°F" if use_fahrenheit else "°C"

    # Day 2 Insight: comfort score (computed using Celsius baseline)
    score = comfort_score(temp_c, wind, code)
    score_text = f"{score}/100 • {comfort_label(score)}" if score is not None else "—"
    go_outside = "Yes" if (score is not None and score >= 65) else "Maybe later"

    st.markdown(
        f"""
<div class="card cardGlow">
  <div class="accentLine"></div>
  <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:1rem;">
    <div>
      <div class="small-muted">Location</div>
      <div style="font-size:1.35rem; font-weight:900; letter-spacing:-0.02em;">{place}</div>
      <div class="small-muted" style="margin-top:0.25rem;">Updated: {datetime.now().strftime("%b %d, %Y • %I:%M %p")}</div>
    </div>
    <div class="badge">{mood_icon(mood)} {condition}</div>
  </div>

  <div class="kpi">
    <div class="kpiItem">
      <div class="kpiLabel">Temperature</div>
      <div class="kpiValue">{fmt_num(temp)}{unit}</div>
    </div>
    <div class="kpiItem">
      <div class="kpiLabel">Feels like</div>
      <div class="kpiValue">{fmt_num(feels)}{unit}</div>
    </div>
    <div class="kpiItem">
      <div class="kpiLabel">Wind</div>
      <div class="kpiValue">{fmt_num(wind, 0)} km/h</div>
    </div>
    <div class="kpiItem">
      <div class="kpiLabel">Comfort</div>
      <div class="kpiValue">{score_text}</div>
    </div>
  </div>

  <div class="hr"></div>
  <div class="small-muted">Go for a walk? <b>{go_outside}</b> • Theme: <b>{mood}</b></div>
</div>
        """,
        unsafe_allow_html=True,
    )

    # 7-day forecast
    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
    st.subheader("7-day forecast")

    dates: List[str] = daily.get("time") or []
    tmax: List[Optional[float]] = daily.get("temperature_2m_max") or []
    tmin: List[Optional[float]] = daily.get("temperature_2m_min") or []
    prcp: List[Optional[float]] = daily.get("precipitation_sum") or []
    wcode: List[Optional[int]] = daily.get("weather_code") or []

    if use_fahrenheit:
        tmax = [c_to_f(x) for x in tmax]
        tmin = [c_to_f(x) for x in tmin]

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(dates, tmax, label="Max")
    ax.plot(dates, tmin, label="Min")
    ax.set_ylabel(f"Temperature ({unit})")
    ax.set_xlabel("Date")
    ax.tick_params(axis="x", rotation=25)
    ax.legend()
    st.pyplot(fig)

    rows = []
    for i in range(min(len(dates), 7)):
        rows.append(
            {
                "Date": dates[i],
                "Condition": WEATHER_CODE.get(wcode[i], f"Code {wcode[i]}"),
                f"Max ({unit})": None if tmax[i] is None else round(tmax[i], 1),
                f"Min ({unit})": None if tmin[i] is None else round(tmin[i], 1),
                "Precip (mm)": None if prcp[i] is None else round(prcp[i], 1),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

except requests.RequestException as e:
    st.error(f"Network/API error: {e}")
except Exception as e:
    st.error(f"Unexpected error: {e}")
