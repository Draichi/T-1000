#!/usr/bin/env python
"""Decode raw BigQuery log rows into typed event tables, build the gas-cost
history, and precompute FeeEngine snapshots for fast env.reset().

Gas calibration here is intentionally coarse: rather than decode NFPM
multicall/function-selector routing (a real rabbit hole -- many LP UIs bundle
mint+refund or decreaseLiquidity+collect+... into a single `multicall` call,
so gas isn't cleanly attributable per action from the tx-level receipt
alone), we take the median gas used across ALL NFPM-interacting transactions
in the window as one blended sanity-check figure, and keep
gas_model.DEFAULT_GAS_UNITS as the actual per-action estimates used by the
simulator. Precise per-action calibration (decode input[:4] selectors,
excluding multicall) is a documented follow-up, not required for the PoC's
core correctness claims.

Usage:
    uv run --active scripts/build_dataset.py --raw-dir data/raw --out-dir data/processed
"""
import argparse
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from t1000.abi_decode import decode_log_row
from t1000.fee_engine import FeeEngine
from t1000.snapshot import precompute_snapshots

EVENT_TYPE_TO_FILENAME = {
    "Swap": "swaps",
    "Mint": "mints",
    "Burn": "burns",
    "Collect": "collects",
    "CollectProtocol": "collect_protocol",
}

NON_FIELD_COLUMNS = {"event_type", "block_number", "log_index", "tx_hash", "timestamp"}

# uint160/uint256 values (sqrt_price_x96 in particular, ~1e28-1e29) routinely
# exceed int64 and overflow PyArrow's default integer inference, so these
# columns are stored as decimal strings in parquet and must be parsed back to
# Python int by any downstream reader (see events_as_records below).
BIGINT_FIELDS = {"amount0", "amount1", "sqrt_price_x96", "liquidity", "amount"}


def decode_logs(logs_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    skipped = 0
    for row in logs_df.itertuples(index=False):
        row_dict = row._asdict()
        try:
            event = decode_log_row(row_dict)
        except ValueError:
            skipped += 1
            continue
        rec = {
            "event_type": event.event_type,
            "block_number": event.block_number,
            "log_index": event.log_index,
            "tx_hash": event.tx_hash,
            "timestamp": event.timestamp,
        }
        rec.update(event.fields)
        records.append(rec)
    if skipped:
        print(f"  skipped {skipped} rows with unrecognized topic0")
    df = pd.DataFrame.from_records(records)
    df = df.sort_values(["block_number", "log_index"]).reset_index(drop=True)
    for col in BIGINT_FIELDS:
        if col in df.columns:
            df[col] = df[col].map(lambda v: str(v) if pd.notna(v) else v)
    return df


def split_by_type(events_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {t: events_df[events_df.event_type == t].reset_index(drop=True) for t in events_df.event_type.unique()}


def build_gas_table(blocks_df: pd.DataFrame, nfpm_tx_df: pd.DataFrame) -> pd.DataFrame:
    gas_df = blocks_df.sort_values("block_number").reset_index(drop=True)
    if not nfpm_tx_df.empty:
        blended_median = float(nfpm_tx_df["receipt_gas_used"].median())
        print(f"  blended median NFPM tx gas used (sanity check only): {blended_median:,.0f}")
    return gas_df


def events_as_records(events_df: pd.DataFrame) -> list:
    field_cols = [c for c in events_df.columns if c not in NON_FIELD_COLUMNS]
    records = []
    for row in events_df.itertuples(index=False):
        d = row._asdict()
        fields = {}
        for k in field_cols:
            v = d[k]
            if pd.isna(v):
                continue
            fields[k] = int(v) if k in BIGINT_FIELDS else v
        records.append(SimpleNamespace(event_type=d["event_type"], fields=fields, timestamp=d["timestamp"]))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--out-dir", default="data/processed")
    parser.add_argument("--snapshot-cadence-hours", type=float, default=24.0)
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Decoding logs...")
    logs_df = pd.read_parquet(raw_dir / "logs.parquet")
    events_df = decode_logs(logs_df)
    print(f"  decoded {len(events_df):,} events: {events_df.event_type.value_counts().to_dict()}")

    events_df.to_parquet(out_dir / "raw_events.parquet", index=False)
    for event_type, df in split_by_type(events_df).items():
        name = EVENT_TYPE_TO_FILENAME[event_type]
        df.to_parquet(out_dir / f"{name}.parquet", index=False)
        print(f"  wrote {len(df):,} rows -> {name}.parquet")

    print("Building gas table...")
    blocks_df = pd.read_parquet(raw_dir / "blocks.parquet")
    nfpm_tx_path = raw_dir / "nfpm_transactions.parquet"
    nfpm_tx_df = pd.read_parquet(nfpm_tx_path) if nfpm_tx_path.exists() else pd.DataFrame()
    gas_df = build_gas_table(blocks_df, nfpm_tx_df)
    gas_df.to_parquet(out_dir / "gas.parquet", index=False)
    print(f"  wrote {len(gas_df):,} rows -> gas.parquet")

    print("Precomputing tick-map snapshots (this replays every Mint/Burn/Swap once)...")
    records = events_as_records(events_df)
    engine = FeeEngine()
    snapshot_dir = out_dir / "snapshots"
    index = precompute_snapshots(
        records, snapshot_dir, cadence_seconds=args.snapshot_cadence_hours * 3600, engine=engine
    )
    n_swaps = sum(1 for r in records if r.event_type == "Swap")
    n_mismatches = len(engine.liquidity_mismatches)
    print(f"  wrote {len(index.entries)} snapshots -> {snapshot_dir}")
    print(
        f"  liquidity self-check: {n_mismatches}/{n_swaps} swaps mismatched "
        "(expected to be higher near the start of the fetch window, where pre-existing "
        "liquidity from before the bootstrap start isn't yet captured, and to decay "
        "toward zero as the tick map converges)"
    )


if __name__ == "__main__":
    main()
