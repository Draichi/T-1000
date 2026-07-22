#!/usr/bin/env python
"""Validate the FeeEngine against real on-chain LP P&L.

Methodology (see plan doc): pick real positions with an unambiguous
owner+tick-range mapping -- prefer `owner != NFPM_ADDRESS` (a contract/bot
interacting with the pool directly, so the position maps 1:1 to a single
economic actor) whose tick range was never reused by that same owner (so
mint<->burn pairing is unambiguous). Replay the simulator once through the
full event log, and at each candidate's mint/burn checkpoints, compare the
simulator's implied fees (from feeGrowthInside deltas) against the actual
on-chain fees, computed as Collect.amount - Burn.amount per token (Burn only
marks principal as owed; Collect is what actually transfers principal+fees).

Usage:
    uv run python scripts/validate.py --processed-dir data/processed --owner 0x...
    uv run python scripts/validate.py --processed-dir data/processed  # auto-picks candidates
"""
import argparse
from pathlib import Path

import pandas as pd

from t1000 import constants
from t1000.fee_engine import FeeEngine

BIGINT_FIELDS = {"amount0", "amount1", "sqrt_price_x96", "liquidity", "amount"}


def load_events(processed_dir: Path) -> pd.DataFrame:
    df = pd.read_parquet(processed_dir / "raw_events.parquet")
    for col in BIGINT_FIELDS:
        if col in df.columns:
            df[col] = df[col].map(lambda v: int(v) if pd.notna(v) else None)
    return df.sort_values(["block_number", "log_index"]).reset_index(drop=True)


def find_candidate_owners(events_df: pd.DataFrame, top_n: int = 5) -> list[str]:
    """Owners (!= NFPM) all of whose mint tick-ranges are unique to them --
    i.e. unambiguous 1:1 mint<->burn pairing, no shared/reused ranges."""
    mints = events_df[events_df.event_type == "Mint"]
    non_nfpm = mints[mints.owner != constants.NFPM_ADDRESS]
    per_owner = non_nfpm.groupby("owner")
    candidates = []
    for owner, group in per_owner:
        range_counts = group.groupby(["tick_lower", "tick_upper"]).size()
        if (range_counts == 1).all() and len(group) >= 3:
            candidates.append((owner, len(group)))
    candidates.sort(key=lambda x: -x[1])
    return [owner for owner, _ in candidates[:top_n]]


def _apply_row(engine: FeeEngine, row) -> None:
    if row.event_type == "Mint":
        engine.apply_mint(int(row.tick_lower), int(row.tick_upper), int(row.amount))
    elif row.event_type == "Burn":
        engine.apply_burn(int(row.tick_lower), int(row.tick_upper), int(row.amount))
    elif row.event_type == "Swap":
        engine.apply_swap(int(row.amount0), int(row.amount1), int(row.sqrt_price_x96), int(row.tick), int(row.liquidity))


def _pct_diff(sim: float, actual: float):
    if actual == 0:
        return None
    return abs(sim - actual) / abs(actual) * 100


def validate_owner(events_df: pd.DataFrame, owner: str) -> list[dict]:
    mints = events_df[(events_df.event_type == "Mint") & (events_df.owner == owner)]
    burns = events_df[(events_df.event_type == "Burn") & (events_df.owner == owner)]
    collects = events_df[(events_df.event_type == "Collect") & (events_df.owner == owner)]

    positions = []  # (mint_idx, burn_idx, collect_idx, tick_lower, tick_upper, liquidity)
    for mint_idx, mint_row in mints.iterrows():
        tl, tu = mint_row.tick_lower, mint_row.tick_upper
        matching_burns = burns[
            (burns.tick_lower == tl) & (burns.tick_upper == tu) & (burns.index > mint_idx)
        ]
        if matching_burns.empty:
            continue  # still open at end of window
        burn_idx = matching_burns.index[0]
        burn_row = matching_burns.iloc[0]
        matching_collects = collects[
            (collects.tick_lower == tl) & (collects.tick_upper == tu)
            & (collects.index >= burn_idx) & (collects.block_number == burn_row.block_number)
        ]
        if matching_collects.empty:
            continue
        collect_idx = matching_collects.index[0]
        positions.append((mint_idx, burn_idx, collect_idx, tl, tu))

    if not positions:
        return []

    checkpoints = {}  # event index -> list of (kind, position_index)
    for pos_i, (mint_idx, burn_idx, collect_idx, tl, tu) in enumerate(positions):
        checkpoints.setdefault(mint_idx, []).append(("mint", pos_i))
        checkpoints.setdefault(burn_idx, []).append(("burn", pos_i))

    last_idx = max(burn_idx for _, burn_idx, _, _, _ in positions)
    fee_inside_at_mint = {}
    results = []

    engine = FeeEngine()
    for row in events_df.iloc[: last_idx + 1].itertuples():
        idx = row.Index
        kinds = checkpoints.get(idx)

        if kinds is None:
            if row.event_type in ("Mint", "Burn", "Swap"):
                _apply_row(engine, row)
            continue

        is_mint_checkpoint = any(k == "mint" for k, _ in kinds)
        if is_mint_checkpoint:
            _apply_row(engine, row)  # apply the mint's own effect first
            for _, pos_i in kinds:
                tl, tu = positions[pos_i][3], positions[pos_i][4]
                fee_inside_at_mint[pos_i] = engine.fee_growth_inside(tl, tu)
        else:  # burn checkpoint(s) -- read fee growth BEFORE applying the burn
            for _, pos_i in kinds:
                mint_idx, burn_idx, collect_idx, tl, tu = positions[pos_i]
                fee_inside_end = engine.fee_growth_inside(tl, tu)
                liquidity = int(events_df.loc[mint_idx, "amount"])
                start0, start1 = fee_inside_at_mint[pos_i]
                end0, end1 = fee_inside_end
                delta0 = (end0 - start0) % constants.Q256
                delta1 = (end1 - start1) % constants.Q256
                sim_fees0 = liquidity * delta0 / constants.Q128
                sim_fees1 = liquidity * delta1 / constants.Q128
                burn_row = events_df.loc[burn_idx]
                collect_row = events_df.loc[collect_idx]
                actual_fees0 = collect_row.amount0 - burn_row.amount0
                actual_fees1 = collect_row.amount1 - burn_row.amount1
                results.append(
                    {
                        "owner": owner,
                        "tick_lower": tl,
                        "tick_upper": tu,
                        "mint_block": int(events_df.loc[mint_idx, "block_number"]),
                        "burn_block": int(burn_row.block_number),
                        "sim_fees0": sim_fees0,
                        "actual_fees0": actual_fees0,
                        "pct_diff0": _pct_diff(sim_fees0, actual_fees0),
                        "sim_fees1": sim_fees1,
                        "actual_fees1": actual_fees1,
                        "pct_diff1": _pct_diff(sim_fees1, actual_fees1),
                    }
                )
            _apply_row(engine, row)  # now apply the burn's own effect

    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--owner", default=None, help="specific owner address to validate; default: auto-pick")
    parser.add_argument(
        "--max-duration-blocks",
        type=int,
        default=500,
        help=(
            "positions open longer than this (in blocks) are reported separately: their tick "
            "boundaries are more likely to have been touched by liquidity minted before the "
            "fetch window started (the documented bootstrap-window limitation), which biases "
            "their fee accounting -- short-duration positions are unaffected since their entire "
            "relevant history is guaranteed to be inside the fetched window."
        ),
    )
    args = parser.parse_args()

    events_df = load_events(Path(args.processed_dir))
    print(f"Loaded {len(events_df):,} events")

    if args.owner:
        owners = [args.owner.lower()]
    else:
        owners = find_candidate_owners(events_df)
        print(f"Auto-picked candidate owners: {owners}")

    all_results = []
    for owner in owners:
        results = validate_owner(events_df, owner)
        all_results.extend(results)

    if not all_results:
        print("No valid mint->burn->collect triplets found for candidate owners.")
        return

    df = pd.DataFrame(all_results)
    df["duration_blocks"] = df["burn_block"] - df["mint_block"]
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    print(df)

    def summarize(label: str, subset: pd.DataFrame) -> None:
        valid0 = subset["pct_diff0"].dropna()
        valid1 = subset["pct_diff1"].dropna()
        print(f"\n--- Summary: {label} (n={len(subset)}) ---")
        if len(valid0):
            print(f"token0 (USDC) pct diff: mean={valid0.mean():.6f}%  max={valid0.max():.6f}%  n={len(valid0)}")
        if len(valid1):
            print(f"token1 (WETH) pct diff: mean={valid1.mean():.6f}%  max={valid1.max():.6f}%  n={len(valid1)}")

    short = df[df["duration_blocks"] <= args.max_duration_blocks]
    long = df[df["duration_blocks"] > args.max_duration_blocks]

    summarize(f"short-duration positions (<= {args.max_duration_blocks} blocks, full history guaranteed in-window)", short)
    if len(long):
        summarize(
            f"long-duration positions (> {args.max_duration_blocks} blocks -- "
            "boundaries may depend on pre-fetch-window liquidity history, see plan doc's "
            "documented bootstrap-window limitation; NOT part of the <0.5% validation claim)",
            long,
        )


if __name__ == "__main__":
    main()
