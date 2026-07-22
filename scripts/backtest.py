#!/usr/bin/env python
"""Backtest a trained PPO checkpoint against the full-range baseline over a
held-out period, running BOTH through the exact same env mechanics for an
apples-to-apples comparison.

Usage:
    uv run python scripts/backtest.py --checkpoint checkpoints/ppo_model_final.zip \
        --vecnormalize checkpoints/ppo_model_vecnormalize_4096_steps.pkl \
        --eval-start 2024-06-11 --eval-end 2024-07-01
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from t1000.baseline_policy import FullRangeBaselinePolicy
from t1000.data_loading import load_processed_dataset
from t1000.env import UniswapV3LPEnv
from t1000.metrics import compute_episode_metrics
from t1000.tick_math import human_price_usd_per_eth, sqrt_price_x96_from_tick


def make_env_fn(events_df, gas_df, swaps_df, snapshot_index, start_ts, end_ts, cfg):
    def _init():
        return UniswapV3LPEnv(
            events_df=events_df,
            gas_df=gas_df,
            swaps_df=swaps_df,
            snapshot_index=snapshot_index,
            start_ts=start_ts,
            end_ts=end_ts,
            episode_hours=cfg["episode_hours"],
            step_hours=cfg["step_hours"],
            initial_notional_usd=cfg["initial_notional_usd"],
        )

    return _init


def _range_prices(env) -> tuple:
    if env.position_tick_lower is None:
        return None, None
    lo = human_price_usd_per_eth(sqrt_price_x96_from_tick(env.position_tick_lower))
    hi = human_price_usd_per_eth(sqrt_price_x96_from_tick(env.position_tick_upper))
    return min(lo, hi), max(lo, hi)


def _new_history(env) -> dict:
    lo, hi = _range_prices(env)
    return {
        "portfolio_value_usd": [env._portfolio_value_usd()],
        "price_usd": [env._current_price()],
        "range_lower_usd": [lo],
        "range_upper_usd": [hi],
        "gas_cost_usd": [0.0],
        "in_range": [False],
    }


def _append_history(history: dict, env, info: dict) -> None:
    lo, hi = _range_prices(env)
    history["portfolio_value_usd"].append(info["portfolio_value_usd"])
    history["price_usd"].append(env._current_price())
    history["range_lower_usd"].append(lo)
    history["range_upper_usd"].append(hi)
    history["gas_cost_usd"].append(info["gas_cost_usd"])
    history["in_range"].append(info["in_range"])


def run_baseline(env_fn, seed: int) -> dict:
    env = env_fn()
    policy = FullRangeBaselinePolicy()
    obs, _ = env.reset(seed=seed)
    history = _new_history(env)
    terminated = truncated = False
    while not (terminated or truncated):
        action, _ = policy.predict(obs, deterministic=True)
        obs, _, terminated, truncated, info = env.step(int(action))
        _append_history(history, env, info)
    return history


def run_ppo(model_path, vecnorm_path, env_fn, seed: int) -> dict:
    venv = DummyVecEnv([env_fn])
    venv = VecNormalize.load(str(vecnorm_path), venv)
    venv.training = False
    venv.norm_reward = False
    model = PPO.load(str(model_path), device="cpu")

    venv.seed(seed)
    obs = venv.reset()
    raw_env = venv.venv.envs[0]
    history = _new_history(raw_env)
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, _, dones, infos = venv.step(action)
        done = bool(dones[0])
        _append_history(history, raw_env, infos[0])
    return history


def plot_backtest(baseline_history: dict, ppo_history: dict, step_hours: float, out_path: Path) -> None:
    hours_b = [i * step_hours for i in range(len(baseline_history["portfolio_value_usd"]))]
    hours_p = [i * step_hours for i in range(len(ppo_history["portfolio_value_usd"]))]

    fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=True)

    ax = axes[0]
    ax.plot(hours_b, baseline_history["portfolio_value_usd"], label="baseline (full-range)", color="tab:gray")
    ax.plot(hours_p, ppo_history["portfolio_value_usd"], label="PPO", color="tab:blue")
    ax.set_ylabel("Portfolio value (USD)")
    ax.set_title("Backtest: PPO vs full-range baseline")
    ax.legend()

    ax = axes[1]
    ax.plot(hours_p, ppo_history["price_usd"], label="ETH/USD price", color="black", linewidth=1)
    ax.fill_between(
        hours_b,
        pd.Series(baseline_history["range_lower_usd"], dtype=float),
        pd.Series(baseline_history["range_upper_usd"], dtype=float),
        step="post",
        alpha=0.15,
        color="tab:gray",
        label="baseline range",
    )
    ax.fill_between(
        hours_p,
        pd.Series(ppo_history["range_lower_usd"], dtype=float),
        pd.Series(ppo_history["range_upper_usd"], dtype=float),
        step="post",
        alpha=0.25,
        color="tab:blue",
        label="PPO range",
    )
    ax.set_ylabel("Price (USD/ETH)")
    ax.legend()

    ax = axes[2]
    baseline_cum_gas = pd.Series(baseline_history["gas_cost_usd"]).cumsum()
    ppo_cum_gas = pd.Series(ppo_history["gas_cost_usd"]).cumsum()
    ax.plot(hours_b, baseline_cum_gas, label="baseline cumulative gas", color="tab:gray")
    ax.plot(hours_p, ppo_cum_gas, label="PPO cumulative gas", color="tab:blue")
    ax.set_ylabel("Cumulative gas cost (USD)")
    ax.set_xlabel("Hours into episode")
    ax.legend()

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/ppo_default.yaml")
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--vecnormalize", required=True)
    parser.add_argument("--eval-start", required=True)
    parser.add_argument("--eval-end", required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--out-dir",
        default=None,
        help="directory to save this run's outputs (default: runs/backtest/<timestamp>, so repeated runs don't overwrite each other)",
    )
    parser.add_argument("--no-plot", action="store_true", help="skip generating the comparison plot")
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else Path("runs/backtest") / datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    print("Loading processed dataset...")
    events_df, gas_df, swaps_df, snapshot_index = load_processed_dataset(args.processed_dir)

    env_fn = make_env_fn(events_df, gas_df, swaps_df, snapshot_index, args.eval_start, args.eval_end, cfg)

    print("Running baseline (full-range) policy...")
    baseline_history = run_baseline(env_fn, args.seed)
    baseline_metrics = compute_episode_metrics(baseline_history["portfolio_value_usd"], cfg["step_hours"])

    print("Running trained PPO policy...")
    ppo_history = run_ppo(args.checkpoint, args.vecnormalize, env_fn, args.seed)
    ppo_metrics = compute_episode_metrics(ppo_history["portfolio_value_usd"], cfg["step_hours"])

    result = {
        "checkpoint": str(args.checkpoint),
        "vecnormalize": str(args.vecnormalize),
        "eval_start": args.eval_start,
        "eval_end": args.eval_end,
        "seed": args.seed,
        "baseline": baseline_metrics,
        "ppo": ppo_metrics,
    }
    print(json.dumps(result, indent=2))

    metrics_path = out_dir / "backtest_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved -> {metrics_path}")

    pd.DataFrame(baseline_history).to_csv(out_dir / "backtest_baseline_history.csv", index_label="step")
    pd.DataFrame(ppo_history).to_csv(out_dir / "backtest_ppo_history.csv", index_label="step")
    print(f"Saved -> {out_dir / 'backtest_baseline_history.csv'}")
    print(f"Saved -> {out_dir / 'backtest_ppo_history.csv'}")

    if not args.no_plot:
        plot_path = out_dir / "backtest_plot.png"
        plot_backtest(baseline_history, ppo_history, cfg["step_hours"], plot_path)
        print(f"Saved -> {plot_path}")

    pnl_diff = ppo_metrics["episode_pnl_usd"] - baseline_metrics["episode_pnl_usd"]
    verdict = "PPO outperforms baseline" if pnl_diff > 0 else "PPO underperforms baseline"
    print(f"\n{verdict}: PPO P&L {ppo_metrics['episode_pnl_usd']:.2f} vs baseline {baseline_metrics['episode_pnl_usd']:.2f} (diff {pnl_diff:+.2f})")


if __name__ == "__main__":
    main()
