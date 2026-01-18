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
    dev_pcts: tuple[float, ...] = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)  # percent
    cooldown_days: tuple[int, ...] = (1, 3, 5, 7, 10, 15)


def run_sweep(df: pd.DataFrame, cfg: SweepConfig) -> pd.DataFrame:
    rows: list[dict] = []

    for dev in cfg.dev_pcts:
        ind_cfg = IndicatorConfig(
            ma_short=cfg.ma_short,
            ma_long=cfg.ma_long,
            deviation_threshold=dev / 100.0,
        )

        sig_df = compute_signals(df, ind_cfg)

        # signal count for sanity
        sig_count = int(sig_df["signal"].sum())

        for cd in cfg.cooldown_days:
            bt = compute_equity_curves(sig_df, cooldown_days=cd)
            metrics = summarize_backtest(bt)

            # grab strategy row
            strat = metrics[metrics["portfolio"] == "strategy"].iloc[0]
            bh = metrics[metrics["portfolio"] == "buy_hold"].iloc[0]

            rows.append(
                {
                    "dev_pct": dev,
                    "cooldown_days": cd,
                    "signal_count": sig_count,
                    "strategy_total_return": float(strat["total_return"]),
                    "strategy_sharpe": float(strat["sharpe"]),
                    "strategy_max_dd": float(strat["max_drawdown"]),
                    "buyhold_total_return": float(bh["total_return"]),
                    "buyhold_sharpe": float(bh["sharpe"]),
                    "delta_total_return": float(strat["total_return"] - bh["total_return"]),
                    "delta_sharpe": float(strat["sharpe"] - bh["sharpe"]),
                }
            )

    out = pd.DataFrame(rows)
    return out