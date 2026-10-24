"""Chronological train/validation/test splitting helpers.

Time-series problems require splits that respect temporal ordering — random
splits leak future information. These helpers sort by a time column and slice
contiguous train/val/test segments using the configured fractions.
"""

from __future__ import annotations

import logging

import pandas as pd

from src.config import Config, get_config

logger = logging.getLogger(__name__)


def timestamp_group_split(
    df: pd.DataFrame,
    time_col: str,
    *,
    train_frac: float = 0.8,
    val_frac: float = 0.1,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split distinct timestamps, keeping every row at a timestamp together.

    Fractions apply to unique timestamps, not row counts. All three periods
    must be nonempty. For hourly demand, pass the hour-aligned pickup_hour.
    This opt-in helper does not change the legacy pipeline's row slicing.
    """
    if not (0 < train_frac < 1 and 0 < val_frac < 1
            and train_frac + val_frac < 1):
        raise ValueError("Fractions must be positive and leave a test period")
    if df[time_col].isna().any():
        raise ValueError("Split timestamps must not be missing")
    ordered = df.sort_values(time_col, kind="stable").reset_index(drop=True)
    times = ordered[time_col].drop_duplicates().sort_values().reset_index(drop=True)
    train_end = int(len(times) * train_frac)
    val_end = int(len(times) * (train_frac + val_frac))
    if not (0 < train_end < val_end < len(times)):
        raise ValueError("Not enough distinct timestamps for three nonempty periods")
    val_start, test_start = times.iloc[train_end], times.iloc[val_end]
    return (
        ordered.loc[ordered[time_col] < val_start].reset_index(drop=True),
        ordered.loc[(ordered[time_col] >= val_start)
                    & (ordered[time_col] < test_start)].reset_index(drop=True),
        ordered.loc[ordered[time_col] >= test_start].reset_index(drop=True),
    )


def time_based_split(
    df: pd.DataFrame,
    time_col: str,
    config: Config | None = None,
    *,
    train_frac: float | None = None,
    val_frac: float | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split ``df`` chronologically into (train, val, test).

    Rows are sorted by ``time_col`` and divided into contiguous segments. The
    test fraction is implied by ``1 - train_frac - val_frac``.
    """
    config = config or get_config()
    split_cfg = config.split
    train_frac = train_frac if train_frac is not None else split_cfg["train_frac"]
    val_frac = val_frac if val_frac is not None else split_cfg["val_frac"]

    if train_frac + val_frac > 1.0:
        raise ValueError("train_frac + val_frac must be <= 1.0")

    ordered = df.sort_values(time_col).reset_index(drop=True)
    n = len(ordered)
    train_end = int(n * train_frac)
    val_end = int(n * (train_frac + val_frac))

    train = ordered.iloc[:train_end].reset_index(drop=True)
    val = ordered.iloc[train_end:val_end].reset_index(drop=True)
    test = ordered.iloc[val_end:].reset_index(drop=True)

    logger.info(
        "Split on '%s': train=%d val=%d test=%d", time_col, len(train), len(val), len(test)
    )
    return train, val, test
