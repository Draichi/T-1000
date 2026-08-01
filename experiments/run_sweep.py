#!/usr/bin/env python
"""Runs the experiment sweep defined in experiments/manifest.yaml.

Per variant: a dedicated git worktree (current uncommitted diff applied on
top of master, since the sweep knobs are not committed yet), a generated
config, one training subprocess, then a backtest per holdout window, saving
experiments/results/<variant>/metrics.json + equity.png + card.md.

Preconditions (dataset coverage >= 14 months, data/* git-ignored) are
asserted BEFORE anything launches; see preconditions.py. Nothing here
commits, pushes, or touches data/.

Usage:
    python experiments/run_sweep.py --dry-run          # print the plan only
    python experiments/run_sweep.py --max-parallel 2
    python experiments/run_sweep.py --variants control,benchrel
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
import threading
from pathlib import Path

import pandas as pd
import yaml

EXPERIMENTS_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = EXPERIMENTS_DIR.parent  # the worktree/checkout holding the sweep code

sys.path.insert(0, str(EXPERIMENTS_DIR))
from preconditions import check_all  # noqa: E402


def _repo_main_root() -> Path:
    """The main checkout (owns .venv and data/); SOURCE_ROOT may be a worktree."""
    common = subprocess.run(
        ["git", "-C", str(SOURCE_ROOT), "rev-parse", "--git-common-dir"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return Path(common).resolve().parent


def load_manifest(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_variant_config(manifest: dict, variant: dict) -> dict:
    with open(SOURCE_ROOT / manifest["base_config"]) as f:
        cfg = yaml.safe_load(f)
    cfg.update(manifest.get("common_overrides", {}))
    cfg.update(variant.get("overrides", {}))
    return cfg


def setup_worktree(main_root: Path, name: str) -> Path:
    wt = main_root / ".claude" / "worktrees" / f"sweep-{name}"
    if not wt.exists():
        # --detach: master is checked out in the main worktree, and git refuses
        # to check the same branch out twice. We never commit here, so a
        # detached HEAD at master is equivalent.
        subprocess.run(
            ["git", "-C", str(main_root), "worktree", "add", "--detach", str(wt), "master"],
            check=True,
        )
        # The sweep knobs (reward_mode, width_scale, gas_multiplier, lookbacks)
        # are uncommitted; replay the source worktree's diff so each variant
        # trains on the same code.
        diff = subprocess.run(
            ["git", "-C", str(SOURCE_ROOT), "diff", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout
        if diff:
            subprocess.run(
                ["git", "-C", str(wt), "apply"], input=diff, text=True, check=True,
            )
    return wt


def hodl_5050_pnl(history_csv: Path, notional: float) -> float:
    """P&L of holding 50% USDC / 50% WETH from the window's first price."""
    prices = pd.read_csv(history_csv)["price_usd"]
    return notional / 2 * (float(prices.iloc[-1]) / float(prices.iloc[0]) - 1.0)


def latest_vecnormalize(checkpoint_dir: Path) -> Path:
    pkls = sorted(
        checkpoint_dir.glob("ppo_model_vecnormalize_*_steps.pkl"),
        key=lambda p: int(p.stem.split("_")[-2]),
    )
    if not pkls:
        raise FileNotFoundError(f"no vecnormalize pkl in {checkpoint_dir}")
    return pkls[-1]


def run_variant(manifest: dict, variant: dict, args, python: str, main_root: Path) -> None:
    name = variant["name"]
    common = manifest["common"]
    results_dir = EXPERIMENTS_DIR / "results" / name
    results_dir.mkdir(parents=True, exist_ok=True)

    wt = setup_worktree(main_root, name) if not args.dry_run else Path(f"<worktree sweep-{name}>")
    cfg = build_variant_config(manifest, variant)
    cfg_path = wt / "configs" / f"sweep_{name}.yaml"
    if not args.dry_run:
        with open(cfg_path, "w") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)

    env = {"PYTHONPATH": str(wt / "src")}
    checkpoint_dir = wt / "checkpoints" / f"sweep_{name}"
    log_dir = wt / "runs" / f"sweep_{name}"
    processed_dir = str(main_root / common["processed_dir"])

    train_cmd = [
        python, str(wt / "scripts" / "train.py"),
        "--config", str(cfg_path),
        "--processed-dir", processed_dir,
        "--train-start", common["train_start"],
        "--train-end", common["train_end"],
        "--total-timesteps", str(common["total_timesteps"]),
        "--checkpoint-dir", str(checkpoint_dir),
        "--log-dir", str(log_dir),
    ]
    if args.dry_run:
        print(f"[{name}] would run: {shlex.join(train_cmd)}")
        return

    if not args.skip_train:
        with open(results_dir / "train.log", "w") as log:
            subprocess.run(train_cmd, cwd=wt, env={**os.environ, **env},
                           stdout=log, stderr=subprocess.STDOUT, check=True)

    checkpoint = checkpoint_dir / "ppo_model_final.zip"
    vecnorm = latest_vecnormalize(checkpoint_dir)

    windows = []
    for i, (start, end) in enumerate(common["holdout_windows"]):
        out_dir = results_dir / f"window_{i}_{start}"
        backtest_cmd = [
            python, str(wt / "scripts" / "backtest.py"),
            "--config", str(cfg_path),
            "--processed-dir", processed_dir,
            "--checkpoint", str(checkpoint),
            "--vecnormalize", str(vecnorm),
            "--eval-start", start, "--eval-end", end,
            "--seed", str(common.get("seed", 0)),
            "--out-dir", str(out_dir), "--no-plot",
        ]
        with open(results_dir / "backtest.log", "a") as log:
            subprocess.run(backtest_cmd, cwd=wt, env={**os.environ, **env},
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        with open(out_dir / "backtest_metrics.json") as f:
            m = json.load(f)
        m["hodl_5050_pnl_usd"] = hodl_5050_pnl(
            out_dir / "backtest_ppo_history.csv", cfg["initial_notional_usd"]
        )
        m["window"] = [start, end]
        windows.append(m)

    summary = summarize_variant(name, variant, cfg, windows)
    with open(results_dir / "metrics.json", "w") as f:
        json.dump(summary, f, indent=2)
    plot_equity(results_dir, windows)
    write_card(results_dir, summary)
    print(f"[{name}] done -> {results_dir}")


def summarize_variant(name: str, variant: dict, cfg: dict, windows: list) -> dict:
    ppo = [w["ppo"]["episode_pnl_usd"] for w in windows]
    base = [w["baseline"]["episode_pnl_usd"] for w in windows]
    hodl = [w["hodl_5050_pnl_usd"] for w in windows]
    return {
        "name": name,
        "overrides": variant.get("overrides", {}),
        "hypothesis": variant.get("hypothesis", ""),
        "windows": windows,
        "ppo_total_pnl_usd": sum(ppo),
        "baseline_total_pnl_usd": sum(base),
        "hodl_total_pnl_usd": sum(hodl),
        "windows_beating_baseline": sum(p > b for p, b in zip(ppo, base)),
        "windows_beating_hodl": sum(p > h for p, h in zip(ppo, hodl)),
        "ppo_mean_sharpe": sum(w["ppo"]["sharpe_ratio"] for w in windows) / len(windows),
        "ppo_worst_drawdown": min(w["ppo"]["max_drawdown"] for w in windows),
    }


def plot_equity(results_dir: Path, windows: list) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(windows), figsize=(4 * len(windows), 3.2), sharey=True)
    for idx, (ax, w) in enumerate(zip(axes, windows)):
        for i, label in enumerate(("baseline", "ppo")):
            csv = results_dir / f"window_{idx}_{w['window'][0]}" / f"backtest_{label}_history.csv"
            pv = pd.read_csv(csv)["portfolio_value_usd"]
            ax.plot(pv, label=label, color=["tab:gray", "tab:blue"][i])
        ax.set_title(w["window"][0], fontsize=9)
    axes[0].set_ylabel("Portfolio value (USD)")
    axes[-1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(results_dir / "equity.png", dpi=140)
    plt.close(fig)


def write_card(results_dir: Path, s: dict) -> None:
    n = len(s["windows"])
    lines = [
        f"# {s['name']}",
        f"Overrides: {json.dumps(s['overrides']) or '{}'}",
        f"Hypothesis: {s['hypothesis'].strip()}",
        f"PPO total P&L: ${s['ppo_total_pnl_usd']:+,.0f} over {n} holdout windows",
        f"Full-range baseline: ${s['baseline_total_pnl_usd']:+,.0f} | HODL 50/50: ${s['hodl_total_pnl_usd']:+,.0f}",
        f"Windows beating baseline: {s['windows_beating_baseline']}/{n} | beating HODL: {s['windows_beating_hodl']}/{n}",
        f"Mean Sharpe: {s['ppo_mean_sharpe']:.2f} | worst drawdown: {s['ppo_worst_drawdown']:.1%}",
        "Per-window P&L vs baseline: "
        + ", ".join(
            f"{w['window'][0][:7]} {w['ppo']['episode_pnl_usd'] - w['baseline']['episode_pnl_usd']:+,.0f}"
            for w in s["windows"]
        ),
        f"Verdict: {'beats' if s['ppo_total_pnl_usd'] > s['baseline_total_pnl_usd'] else 'loses to'} baseline in aggregate",
        "See metrics.json / equity.png in this directory for details.",
    ]
    (results_dir / "card.md").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(EXPERIMENTS_DIR / "manifest.yaml"))
    parser.add_argument("--max-parallel", type=int, default=2,
                        help="concurrent variant trainings (each uses ~1 core / 1.6 GB)")
    parser.add_argument("--variants", default=None, help="comma-separated subset of variant names")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-train", action="store_true",
                        help="reuse existing checkpoints, only (re)run backtests + reports")
    args = parser.parse_args()

    manifest = load_manifest(Path(args.manifest))
    main_root = _repo_main_root()
    python = str(main_root / ".venv" / "bin" / "python")

    # Hard gate: never start a sweep on a truncated dataset or with data/
    # committable. Runs even for --dry-run so the plan is known-valid.
    check_all(main_root / manifest["common"]["processed_dir"], main_root)

    variants = manifest["variants"]
    if args.variants:
        wanted = set(args.variants.split(","))
        unknown = wanted - {v["name"] for v in variants}
        if unknown:
            sys.exit(f"unknown variants: {sorted(unknown)}")
        variants = [v for v in variants if v["name"] in wanted]

    sem = threading.Semaphore(args.max_parallel)
    errors = []

    def worker(variant):
        with sem:
            try:
                run_variant(manifest, variant, args, python, main_root)
            except Exception as e:  # surface per-variant failures at the end
                errors.append((variant["name"], repr(e)))

    threads = [threading.Thread(target=worker, args=(v,), name=v["name"]) for v in variants]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if errors:
        for name, err in errors:
            print(f"[{name}] FAILED: {err}", file=sys.stderr)
        sys.exit(1)
    if not args.dry_run:
        print("\nSweep complete. Next: python experiments/aggregate_leaderboard.py")


if __name__ == "__main__":
    main()
