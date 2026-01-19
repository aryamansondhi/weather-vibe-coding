# signals/backtest.py
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    cooldown_days: int = 5


def build_position_from_signal(signal: pd.Series, cooldown_days: int) -> pd.Series:
    """
    Long-only position (1=in market, 0=in cash).
    VECTORIZED VERSION: No for-loops. Uses rolling windows for speed.
    """
    if cooldown_days <= 0:
        raise ValueError("cooldown_days must be > 0")

    # 1. Convert signal to boolean
    sig = signal.fillna(False).astype(bool)

    # 2. Create the "Risk Off" mask using a rolling window
    # logic: if a signal happened in the last 'cooldown_days', we are out.
    # .rolling().max() checks if ANY True value exists in the window.
    # .shift(1) because the cooldown starts the NEXT day.
    is_risk_off = (
        sig.rolling(window=cooldown_days, min_periods=1)
        .max()
        .shift(1)
        .fillna(0)
        .astype(bool)
    )

    # 3. Position is inverse of Risk Off (1.0 = Invested, 0.0 = Cash)
    pos = (~is_risk_off).astype(float)
    
    return pos


def compute_equity_curves(
    df: pd.DataFrame,
    price_col: str = "Adj Close",
    signal_col: str = "signal",
    cooldown_days: int = 5,
) -> pd.DataFrame:
    """
    Returns equity curves and daily returns.
    """
    if price_col not in df.columns:
        raise ValueError(f"Expected '{price_col}' column")
    if signal_col not in df.columns:
        raise ValueError(f"Expected '{signal_col}' column")

    price = df[price_col]
    
    # Ensure price is a Series
    if isinstance(price, pd.DataFrame):
        price = price.iloc[:, 0]

    daily_ret = price.pct_change().fillna(0.0)

    # Uses the new vectorized function
    position = build_position_from_signal(df[signal_col], cooldown_days=cooldown_days)

    strat_ret = daily_ret * position

    bh_equity = (1.0 + daily_ret).cumprod()
    strat_equity = (1.0 + strat_ret).cumprod()

    out = pd.DataFrame(
        {
            "daily_ret": daily_ret,
            "position": position,
            "strat_ret": strat_ret,
            "bh_equity": bh_equity,
            "strat_equity": strat_equity,
        },
        index=df.index,
    )
    return out


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def annualized_return(equity: pd.Series, periods_per_year: int = 252) -> float:
    if len(equity) < 2:
        return 0.0
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    years = (len(equity) - 1) / periods_per_year
    if years <= 0:
        return total_return
    return (1.0 + total_return) ** (1.0 / years) - 1.0


def annualized_volatility(daily_returns: pd.Series, periods_per_year: int = 252) -> float:
    return float(daily_returns.std(ddof=0) * np.sqrt(periods_per_year))


def sharpe_ratio(
    daily_returns: pd.Series,
    risk_free_rate_annual: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    rf_daily = (1.0 + risk_free_rate_annual) ** (1.0 / periods_per_year) - 1.0
    excess = daily_returns - rf_daily
    vol = excess.std(ddof=0)
    if vol == 0 or np.isnan(vol):
        return 0.0
    return float((excess.mean() / vol) * np.sqrt(periods_per_year))


def summarize_backtest(bt: pd.DataFrame) -> pd.DataFrame:
    bh_eq = bt["bh_equity"]
    st_eq = bt["strat_equity"]

    bh_ret = bt["daily_ret"]
    st_ret = bt["strat_ret"]

    out = pd.DataFrame(
        {
            "portfolio": ["buy_hold", "strategy"],
            "total_return": [float(bh_eq.iloc[-1] - 1.0), float(st_eq.iloc[-1] - 1.0)],
            "ann_return": [annualized_return(bh_eq), annualized_return(st_eq)],
            "ann_vol": [annualized_volatility(bh_ret), annualized_volatility(st_ret)],
            "max_drawdown": [max_drawdown(bh_eq), max_drawdown(st_eq)],
            "sharpe": [sharpe_ratio(bh_ret), sharpe_ratio(st_ret)],
        }
    )
    return out