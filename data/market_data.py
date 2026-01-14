# data/market_data.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import pandas as pd
import streamlit as st
import yfinance as yf


@dataclass(frozen=True)
class MarketQuery:
    ticker: str = "SPY"
    period: str = "1y"       # e.g., "6mo", "1y", "5y"
    interval: str = "1d"     # e.g., "1d", "1h"


@st.cache_data(ttl=900)
def fetch_ohlc(q: MarketQuery) -> pd.DataFrame:
    """
    Fetch OHLCV data from Yahoo Finance.
    Returns a dataframe indexed by datetime with columns:
    Open, High, Low, Close, Adj Close, Volume (depending on availability).
    """
    df = yf.download(q.ticker, period=q.period, interval=q.interval, auto_adjust=False, progress=False)

    if df is None or df.empty:
        return pd.DataFrame()

    # Normalize column names (yfinance returns capitalized columns already)
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)

    # If yfinance returns MultiIndex columns (e.g., level includes ticker),
    # flatten it to single-level columns.
    if isinstance(df.columns, pd.MultiIndex):
        # Usually: (PriceField, Ticker) or (Ticker, PriceField)
        # We want the price field names only.
        if "Adj Close" in df.columns.get_level_values(0):
            # columns like ("Adj Close", "SPY")
            df.columns = df.columns.get_level_values(0)
        else:
            # columns like ("SPY", "Adj Close")
            df.columns = df.columns.get_level_values(-1)

    # Sometimes Adj Close can be missing for some intervals
    return df
