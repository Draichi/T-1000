#!/usr/bin/env python
"""Zero-training sanity check: sweep a grid of rule-based LP policies over the
same fixed holdout windows every PPO variant was scored on.

Motivation (TODO.md, "Status check 2026-08-02"): no PPO variant across 12+
configurations has beaten the reference baseline with statistical
significance. But that reference -- FullRangeBaselinePolicy -- is itself just
one arbitrary point in the rule-based family (WIDE band, rebalance the instant
price leaves the range, collect weekly). If no neighbouring rule beats it
either, the honest reading is that the ceiling in this action space is low and
more RL tuning cannot change the conclusion. If some rule *does* beat it, that
is a far more informative floor than "PPO ~ baseline", and it costs no
training compute at all.

Every variant runs through the identical env config used by
scripts/backtest.py (imported from it, so the two cannot drift apart).

Usage:
    uv run python scripts/heuristic_sweep.py --config configs/ppo_default.yaml \
        --processed-dir data/processed_14mo_fixed \
        --train-start 2024-05-01 --train-end 2024-12-31
"""
import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest import make_env_fn  # noqa: E402  (same env config, by construction)

from t1000.actions import Action  # noqa: E402
from t1000.baseline_policy import FullRangeBaselinePolicy  # noqa: E402
from t1000.data_loading import load_processed_dataset  # noqa: E402
from t1000.heuristic_policy import HeuristicPolicy  # noqa: E402
from t1000.metrics import compute_episode_metrics  # noqa: E402

WEEKLY = 168 / 720

# The grid: band width x hysteresis x collect cadence. Deliberately small --
# 12 cells x 5 windows = 60 episodes -- and centred on the reference point
# (wide / patience 0 / weekly) so every cell is one or two knobs away from it.
GRID = [
    HeuristicPolicy(rebalance_action=action, out_of_range_patience=patience, collect_interval_frac=collect)
    for action in (Action.REBALANCE_NARROW, Action.REBALANCE_MEDIUM, Action.REBALANCE_WIDE)
    for patience in (0, 24)
    for collect in (WEEKLY, None)
]


def paired_t(diffs: list) -> float:
    """Same statistic experiments/aggregate_leaderboard.py gates on."""
    n = len(diffs)
    if n < 2:
        return 0.0
    mean = sum(diffs) / n
    var = sum((d - mean) ** 2 for d in diffs) / (n - 1)
    if var == 0:
        return 0.0
    return mean / math.sqrt(var / n)


def run_policy(env_fn, policy, seed: int) -> dict:
    """One 720h episode. Mirrors backtest.run_baseline, plus the per-episode
    policy.reset() that HeuristicPolicy's out-of-range counter requires."""
    env = env_fn()
    if hasattr(policy, "reset"):
        policy.reset()
    obs, _ = env.reset(seed=seed)
    values = [env._portfolio_value_usd()]
    gas_total = swap_total = 0.0
    n_rebalances = 0
    steps_in_range = 0
    terminated = truncated = False
    while not (terminated or truncated):
        action, _ = policy.predict(obs, deterministic=True)
        obs, _, terminated, truncated, info = env.step(int(action))
        values.append(info["portfolio_value_usd"])
        gas_total += info["gas_cost_usd"]
        swap_total += info["swap_cost_usd"]
        steps_in_range += int(bool(info["in_range"]))
        if int(action) in (Action.REBALANCE_NARROW, Action.REBALANCE_MEDIUM, Action.REBALANCE_WIDE):
            n_rebalances += 1
    metrics = compute_episode_metrics(values, env.step_hours)
    metrics.update(
        gas_cost_usd=gas_total,
        swap_cost_usd=swap_total,
        n_rebalances=n_rebalances,
        in_range_frac=steps_in_range / max(len(values) - 1, 1),
    )
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/ppo_default.yaml")
    parser.add_argument("--processed-dir", default="data/processed_14mo_fixed")
    parser.add_argument("--manifest", default="experiments/manifest.yaml",
                        help="source of the fixed holdout windows, so this sweep is scored on "
                             "exactly the windows every PPO variant was scored on")
    parser.add_argument("--train-start", default="2024-05-01")
    parser.add_argument("--train-end", default="2024-12-31",
                        help="scopes observation-normalization stats to the training window, "
                             "matching backtest.py (see CLAUDE.md on market_stats_*)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else Path("runs/heuristic_sweep") / datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    with open(args.manifest) as f:
        windows = [tuple(w) for w in yaml.safe_load(f)["common"]["holdout_windows"]]

    hedge_enabled = cfg.get("hedge_enabled", False)
    print(f"Loading processed dataset from {args.processed_dir} ...")
    events_df, gas_df, swaps_df, snapshot_index, funding_df = load_processed_dataset(
        args.processed_dir, load_funding=hedge_enabled
    )

    policies = [FullRangeBaselinePolicy()] + GRID
    names = ["reference(baseline)"] + [p.name for p in GRID]

    rows = []
    for w_start, w_end in windows:
        env_fn = make_env_fn(
            events_df, gas_df, swaps_df, snapshot_index, w_start, w_end, cfg,
            train_start=args.train_start, train_end=args.train_end, funding_df=funding_df,
        )
        for name, policy in zip(names, policies):
            metrics = run_policy(env_fn, policy, args.seed)
            rows.append({"window_start": w_start, "window_end": w_end, "policy": name, **metrics})
            print(f"  {w_start} {name:<34} pnl={metrics['episode_pnl_usd']:+9.2f} "
                  f"sharpe={metrics['sharpe_ratio']:+6.2f} rebal={metrics['n_rebalances']:>3} "
                  f"in_range={metrics['in_range_frac']:.2f}")

    df = pd.DataFrame(rows)
    csv_path = out_dir / "heuristic_sweep_windows.csv"
    df.to_csv(csv_path, index=False)

    # Paired comparison against the reference, window by window -- the same
    # shape aggregate_leaderboard.py uses, so the |t| < 2 caveat carries over.
    ref = df[df["policy"] == "reference(baseline)"].set_index("window_start")
    summary = []
    for name in names[1:]:
        sub = df[df["policy"] == name].set_index("window_start")
        diffs = [sub.loc[w, "episode_pnl_usd"] - ref.loc[w, "episode_pnl_usd"] for w in ref.index]
        summary.append({
            "policy": name,
            "mean_pnl_usd": sub["episode_pnl_usd"].mean(),
            "total_pnl_usd": sub["episode_pnl_usd"].sum(),
            "mean_sharpe": sub["sharpe_ratio"].mean(),
            "vs_ref_total_usd": sum(diffs),
            "wins_vs_ref": sum(1 for d in diffs if d > 0),
            "beats_may_up_month": bool(diffs[-1] > 0),
            "paired_t": paired_t(diffs),
        })
    summary_df = pd.DataFrame(summary).sort_values("vs_ref_total_usd", ascending=False)
    summary_path = out_dir / "heuristic_sweep_summary.csv"
    summary_df.to_csv(summary_path, index=False)

    print("\n=== Ranked vs reference baseline (5 paired holdout windows) ===")
    print(summary_df.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    print(f"\nReference total P&L over 5 windows: {ref['episode_pnl_usd'].sum():+.2f}")
    print("|paired_t| < 2 => statistically indistinguishable from the reference "
          "(same caveat as experiments/LEADERBOARD.md).")

    with open(out_dir / "meta.json", "w") as f:
        json.dump({"config": args.config, "processed_dir": args.processed_dir,
                   "windows": windows, "seed": args.seed,
                   "train_stats_window": [args.train_start, args.train_end]}, f, indent=2)
    print(f"\nSaved -> {csv_path}\nSaved -> {summary_path}")


if __name__ == "__main__":
    main()
