# services.py
from __future__ import annotations

from typing import Optional, Dict, Any
import requests
import streamlit as st


@st.cache_data(ttl=600)
def geocode_city(name: str) -> Optional[Dict[str, Any]]:
    """
    Returns best geocoding match for a city name via Open-Meteo geocoder.
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    r = requests.get(
        url,
        params={"name": name, "count": 1, "language": "en", "format": "json"},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    results = data.get("results") or []
    return results[0] if results else None


@st.cache_data(ttl=600)
def get_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Returns current + 7-day forecast via Open-Meteo.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "apparent_temperature", "wind_speed_10m", "weather_code"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "weather_code"],
        "forecast_days": 7,
        "timezone": "auto",
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()
