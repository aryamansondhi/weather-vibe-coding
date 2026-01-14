# signals/indicators.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass(frozen=True)
class IndicatorConfig:
    return_window: int = 1        # daily returns
    vol_window: int = 20          # ~1 trading month
    ma_short: int = 10
    ma_long: int = 30
    deviation_threshold: float = 0.03  # 3% deviation


def compute_returns(df: pd.DataFrame) -> pd.Series:
    """
    Compute simple returns from adjusted close prices.
    """
    if "Adj Close" not in df.columns:
        raise ValueError("Expected 'Adj Close' column")

    return df["Adj Close"].pct_change()


def compute_volatility(returns: pd.Series, window: int) -> pd.Series:
    """
    Rolling volatility (std of returns).
    """
    return returns.rolling(window=window).std()


def compute_moving_average(series: pd.Series, window: int) -> pd.Series:
    """
    Simple moving average.
    """
    return series.rolling(window=window).mean()


def compute_signals(
    df: pd.DataFrame,
    cfg: IndicatorConfig = IndicatorConfig()
) -> pd.DataFrame:
    """
    Given OHLC dataframe, compute indicators and signal flags.
    Returns a new dataframe with indicators added.
    """
    out = df.copy()
    adj_close = out["Adj Close"]
    if isinstance(adj_close, pd.DataFrame):
        adj_close = adj_close.iloc[:, 0]

    # Returns
    out["returns"] = compute_returns(out)

    # Volatility
    out["volatility"] = compute_volatility(out["returns"], cfg.vol_window)

    # Moving averages
    out["ma_short"] = compute_moving_average(out["Adj Close"], cfg.ma_short)
    out["ma_long"] = compute_moving_average(out["Adj Close"], cfg.ma_long)

    # Deviation from long MA
    out["deviation"] = (out["Adj Close"] - out["ma_long"]) / out["ma_long"]

    # Signal flag: price deviates significantly from baseline
    out["signal"] = out["deviation"].abs() > cfg.deviation_threshold

    return out
