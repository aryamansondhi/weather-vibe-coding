# signals/backtest.py
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    cooldown_days: int = 5  # number of trading days to stay in cash after a signal


def build_position_from_signal(signal: pd.Series, cooldown_days: int) -> pd.Series:
    """
    Long-only position (1=in market, 0=in cash).
    If signal[t] is True, then position is set to 0 for the NEXT cooldown_days.
    """
    if cooldown_days <= 0:
        raise ValueError("cooldown_days must be > 0")

    sig = signal.fillna(False).astype(bool)

    # position defaults to 1 (in market)
    pos = pd.Series(1.0, index=sig.index)

    # iterate through signal points and set future windows to 0
    # This is simple and explicit (fine for our dataset sizes).
    idx = sig.index.to_list()

    for i, is_sig in enumerate(sig.to_list()):
        if not is_sig:
            continue

        # cash starts next day
        start = i + 1
        end = min(i + 1 + cooldown_days, len(idx))
        if start < len(idx):
            pos.loc[idx[start:end]] = 0.0

    return pos


def compute_equity_curves(
    df: pd.DataFrame,
    price_col: str = "Adj Close",
    signal_col: str = "signal",
    cooldown_days: int = 5,
) -> pd.DataFrame:
    """
    Returns a DataFrame with:
      - bh_equity: buy & hold equity curve (starting at 1.0)
      - strat_equity: strategy equity curve (starting at 1.0)
      - position: 1 or 0 exposure used by strategy
      - daily_ret: daily returns from price
      - strat_ret: daily returns * position
    """
    if price_col not in df.columns:
        raise ValueError(f"Expected '{price_col}' column")
    if signal_col not in df.columns:
        raise ValueError(f"Expected '{signal_col}' column")

    price = df[price_col]
    if isinstance(price, pd.DataFrame):
        price = price.iloc[:, 0]

    daily_ret = price.pct_change().fillna(0.0)

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
    """
    Max drawdown as a negative number (e.g., -0.12 for -12%).
    """
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def annualized_return(equity: pd.Series, periods_per_year: int = 252) -> float:
    """
    Approx CAGR from equity curve assuming daily periods.
    """
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
    """
    Simple Sharpe using daily returns and constant annual risk-free rate.
    """
    rf_daily = (1.0 + risk_free_rate_annual) ** (1.0 / periods_per_year) - 1.0
    excess = daily_returns - rf_daily
    vol = excess.std(ddof=0)
    if vol == 0 or np.isnan(vol):
        return 0.0
    return float((excess.mean() / vol) * np.sqrt(periods_per_year))


def summarize_backtest(bt: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a small metrics table comparing Buy & Hold vs Strategy.
    Expects columns: daily_ret, strat_ret, bh_equity, strat_equity
    """
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