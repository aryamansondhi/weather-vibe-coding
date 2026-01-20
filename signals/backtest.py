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


def compute_equity_curves(df, cooldown_days=5):
    """
    Calculates equity curves and drawdown for B&H vs Strategy.
    """
    out = df.copy()
    
    # 1. Daily Returns
    out["bh_rets"] = out["Adj Close"].pct_change().fillna(0)
    
    # 2. Strategy Logic (Stay in cash for X days after a signal)
    out["is_cooldown"] = out["signal"].rolling(window=cooldown_days, min_periods=1).max().fillna(0)
    out["strat_pos"] = 1 - out["is_cooldown"]
    out["strat_rets"] = out["bh_rets"] * out["strat_pos"].shift(1).fillna(0)
    
    # 3. Equity Curves (Compounding)
    out["bh_equity"] = (1 + out["bh_rets"]).cumprod()
    out["strat_equity"] = (1 + out["strat_rets"]).cumprod()
    
    # 4. DRAWDOWN CALCULATION (The B2B Metric)
    # High-water mark
    out["bh_hwm"] = out["bh_equity"].cummax()
    out["strat_hwm"] = out["strat_equity"].cummax()
    
    # Drawdown %
    out["bh_dd"] = (out["bh_equity"] / out["bh_hwm"]) - 1
    out["strat_dd"] = (out["strat_equity"] / out["strat_hwm"]) - 1
    
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


def summarize_backtest(bt_df):
    """
    Summarizes performance with a focus on Risk-Adjusted Metrics.
    """
    metrics = []
    for col, name in [("bh", "Buy & Hold"), ("strat", "Tactical Risk-Off")]:
        equity = bt_df[f"{col}_equity"]
        rets = bt_df[f"{col}_rets"]
        dd = bt_df[f"{col}_dd"]
        
        total_ret = equity.iloc[-1] - 1
        ann_ret = (1 + total_ret) ** (252 / len(bt_df)) - 1
        ann_vol = rets.std() * np.sqrt(252)
        sharpe = ann_ret / ann_vol if ann_vol != 0 else 0
        
        # Risk Metrics
        max_dd = dd.min()
        # Calmar Ratio: Reward-to-Pain ratio
        calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0
        
        metrics.append({
            "Portfolio": name,
            "Total Return": total_ret,
            "Ann. Return": ann_ret,
            "Ann. Vol": ann_vol,
            "Sharpe": sharpe,
            "Max Drawdown": max_dd,
            "Calmar": calmar
        })
        
    return pd.DataFrame(metrics)