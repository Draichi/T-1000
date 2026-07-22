"""Shared helpers for loading the processed parquet dataset + snapshot index
(used by scripts/train.py, scripts/backtest.py, and tests)."""
from pathlib import Path

import pandas as pd

from .snapshot import load_snapshot_index_from_dir

# uint160/uint256 values (sqrt_price_x96 especially, ~1e28-1e29) were stored
# as decimal strings in parquet to avoid overflowing PyArrow's int64
# inference -- see scripts/build_dataset.py for why, must parse back here.
BIGINT_FIELDS = {"amount0", "amount1", "sqrt_price_x96", "liquidity", "amount"}


def load_processed_dataset(processed_dir):
    processed_dir = Path(processed_dir)
    events_df = pd.read_parquet(processed_dir / "raw_events.parquet")
    for col in BIGINT_FIELDS:
        if col in events_df.columns:
            events_df[col] = events_df[col].map(lambda v: int(v) if pd.notna(v) else None)
    events_df = events_df.sort_values(["block_number", "log_index"]).reset_index(drop=True)

    gas_df = pd.read_parquet(processed_dir / "gas.parquet")
    swaps_df = events_df[events_df.event_type == "Swap"].reset_index(drop=True)
    snapshot_index = load_snapshot_index_from_dir(processed_dir / "snapshots")

    return events_df, gas_df, swaps_df, snapshot_index
