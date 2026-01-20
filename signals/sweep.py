# signals/sweep.py
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

from signals.indicators import IndicatorConfig, compute_signals
from signals.backtest import compute_equity_curves, summarize_backtest


@dataclass(frozen=True)
class SweepConfig:
    ma_short: int = 10
    ma_long: int = 30
    # Range of deviation thresholds (percentages)
    dev_pcts: tuple[float, ...] = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
    # Range of cooldown periods (days)
    cooldown_days: tuple[int, ...] = (1, 3, 5, 7, 10, 15)


def run_sweep(df: pd.DataFrame, cfg: SweepConfig) -> pd.DataFrame:
    results = []  # Fixed: Initialize the list we actually use

    for dev in cfg.dev_pcts:
        # Create config for this specific loop iteration
        ind_cfg = IndicatorConfig(
            ma_short=cfg.ma_short,
            ma_long=cfg.ma_long,
            deviation_threshold=dev / 100.0,
        )

        # 1. Compute Signals
        sig_df = compute_signals(df, ind_cfg)
        sig_count = int(sig_df["signal"].sum())

        for cd in cfg.cooldown_days:
            # 2. Run Backtest for this combination
            bt = compute_equity_curves(sig_df, cooldown_days=cd)
            metrics = summarize_backtest(bt)

            # 3. Extract Metrics safely using B2B column names (Title Case)
            strat = metrics[metrics["Portfolio"] == "Tactical Risk-Off"].iloc[0]
            bh = metrics[metrics["Portfolio"] == "Buy & Hold"].iloc[0]

            # 4. Append to results
            results.append({
                "dev_pct": dev,            # Fixed: 'dev', not 'd'
                "cooldown_days": cd,       # Fixed: 'cd', not 'c'
                "signal_count": sig_count, 
                
                # Performance Metrics (Raw Floats)
                "strategy_total_return": float(strat["Total Return"]),
                "strategy_sharpe": float(strat["Sharpe"]),
                "strategy_max_dd": float(strat["Max Drawdown"]),
                
                "buyhold_total_return": float(bh["Total Return"]),
                "buyhold_sharpe": float(bh["Sharpe"]),
                
                # Deltas (Strategy - Benchmark)
                "delta_total_return": float(strat["Total Return"]) - float(bh["Total Return"]),
                "delta_sharpe": float(strat["Sharpe"]) - float(bh["Sharpe"])
            })

    return pd.DataFrame(results)