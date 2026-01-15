# signals/evaluation.py
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class EvalConfig:
    horizon_days: int = 5  # forward return horizon in trading days


def compute_forward_returns(adj_close: pd.Series, horizon_days: int) -> pd.Series:
    """
    Computes forward N-day returns:
        fwd_ret[t] = (price[t+N] / price[t]) - 1

    Returns a series aligned to the original index, with NaN for the last N rows.
    """
    if horizon_days <= 0:
        raise ValueError("horizon_days must be > 0")

    future_price = adj_close.shift(-horizon_days)
    fwd = (future_price / adj_close) - 1.0
    return fwd


def summarize_signal_performance(
    df: pd.DataFrame,
    signal_col: str = "signal",
    price_col: str = "Adj Close",
    horizon_days: int = 5,
) -> pd.DataFrame:
    """
    Creates a small summary table comparing forward returns:
    - on signal days
    - on non-signal days
    - overall baseline

    Expects df to already contain:
    - price_col (Adj Close)
    - signal_col (boolean)
    """
    if price_col not in df.columns:
        raise ValueError(f"Expected '{price_col}' column")
    if signal_col not in df.columns:
        raise ValueError(f"Expected '{signal_col}' column")

    adj = df[price_col]
    if isinstance(adj, pd.DataFrame):
        adj = adj.iloc[:, 0]

    fwd = compute_forward_returns(adj, horizon_days=horizon_days)

    tmp = df.copy()
    tmp[f"fwd_ret_{horizon_days}d"] = fwd

    # Drop NaNs introduced by shift at the tail
    tmp = tmp.dropna(subset=[f"fwd_ret_{horizon_days}d"])

    sig = tmp[tmp[signal_col] == True][f"fwd_ret_{horizon_days}d"]
    nonsig = tmp[tmp[signal_col] == False][f"fwd_ret_{horizon_days}d"]
    overall = tmp[f"fwd_ret_{horizon_days}d"]

    summary = pd.DataFrame(
        {
            "group": ["signal_days", "non_signal_days", "overall"],
            "count": [len(sig), len(nonsig), len(overall)],
            "mean_fwd_return": [sig.mean(), nonsig.mean(), overall.mean()],
            "median_fwd_return": [sig.median(), nonsig.median(), overall.median()],
        }
    )

    return summary