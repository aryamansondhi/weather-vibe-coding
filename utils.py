# utils.py
from __future__ import annotations

from typing import Optional, Dict


WEATHER_CODE = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm + hail",
    99: "Thunderstorm + hail",
}


def c_to_f(c: Optional[float]) -> Optional[float]:
    return None if c is None else (c * 9 / 5) + 32


def fmt_num(x: Optional[float], decimals: int = 1) -> str:
    if x is None:
        return "—"
    return f"{x:.{decimals}f}"


def weather_family(code: Optional[int]) -> str:
    if code is None:
        return "default"
    if code in (0, 1):
        return "clear"
    if code in (2, 3):
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75):
        return "snow"
    if code in (95, 96, 99):
        return "thunder"
    return "default"


def mood_icon(mood: str) -> str:
    return {
        "clear": "☀️",
        "cloudy": "☁️",
        "rain": "🌧️",
        "snow": "❄️",
        "thunder": "⛈️",
        "fog": "🌫️",
        "default": "🌙",
    }.get(mood, "🌙")


# Dark-first, weather-reactive accents
PALETTES: Dict[str, Dict[str, str]] = {
    "default": {
        "bg_top": "#0B0D12",
        "bg_bottom": "#07080C",
        "accent": "#E50914",
        "accent2": "#7C3AED",
        "muted": "#A7AFBE",
        "card": "rgba(255,255,255,0.06)",
        "border": "rgba(255,255,255,0.10)",
    },
    "clear": {
        "bg_top": "#090B10",
        "bg_bottom": "#07080C",
        "accent": "#FBBF24",
        "accent2": "#FB7185",
        "muted": "#B7BFCE",
        "card": "rgba(255,255,255,0.06)",
        "border": "rgba(255,255,255,0.10)",
    },
    "cloudy": {
        "bg_top": "#0A0C12",
        "bg_bottom": "#07080C",
        "accent": "#60A5FA",
        "accent2": "#A78BFA",
        "muted": "#B0B7C6",
        "card": "rgba(255,255,255,0.06)",
        "border": "rgba(255,255,255,0.10)",
    },
    "rain": {
        "bg_top": "#070A10",
        "bg_bottom": "#05060A",
        "accent": "#22D3EE",
        "accent2": "#3B82F6",
        "muted": "#A9B2C4",
        "card": "rgba(255,255,255,0.06)",
        "border": "rgba(255,255,255,0.10)",
    },
    "snow": {
        "bg_top": "#090B10",
        "bg_bottom": "#05060A",
        "accent": "#E0F2FE",
        "accent2": "#93C5FD",
        "muted": "#B7C0CF",
        "card": "rgba(255,255,255,0.06)",
        "border": "rgba(255,255,255,0.10)",
    },
    "thunder": {
        "bg_top": "#080911",
        "bg_bottom": "#04040A",
        "accent": "#A78BFA",
        "accent2": "#F59E0B",
        "muted": "#AAB3C6",
        "card": "rgba(255,255,255,0.06)",
        "border": "rgba(255,255,255,0.10)",
    },
    "fog": {
        "bg_top": "#080A10",
        "bg_bottom": "#05060A",
        "accent": "#94A3B8",
        "accent2": "#22C55E",
        "muted": "#ADB6C7",
        "card": "rgba(255,255,255,0.06)",
        "border": "rgba(255,255,255,0.10)",
    },
}


def comfort_score(temp_c: Optional[float], wind_kmh: Optional[float], code: Optional[int]) -> Optional[int]:
    """
    Simple heuristic: 0–100 comfort score.
    - prefers ~22°C
    - penalizes wind
    - penalizes rain/snow/thunder a bit
    """
    if temp_c is None:
        return None

    # temperature penalty
    temp_pen = min(60.0, abs(temp_c - 22.0) * 3.0)

    # wind penalty
    w = wind_kmh or 0.0
    wind_pen = min(25.0, w * 0.6)

    # condition penalty
    fam = weather_family(code)
    cond_pen = {
        "clear": 0.0,
        "cloudy": 4.0,
        "fog": 10.0,
        "rain": 18.0,
        "snow": 22.0,
        "thunder": 28.0,
        "default": 8.0,
    }.get(fam, 8.0)

    score = 100.0 - (temp_pen + wind_pen + cond_pen)
    score = max(0.0, min(100.0, score))
    return int(round(score))


def comfort_label(score: Optional[int]) -> str:
    if score is None:
        return "—"
    if score >= 80:
        return "Excellent"
    if score >= 65:
        return "Good"
    if score >= 50:
        return "Okay"
    if score >= 35:
        return "Meh"
    return "Rough"
