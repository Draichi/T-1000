#!/usr/bin/env python
"""Imports an already-trained run into experiments/results/ so it appears on
the leaderboard next to the sweep variants, without retraining: runs the
manifest's holdout backtests against the run's final checkpoint and writes
the same metrics.json + equity.png + card.md a sweep variant would get.

Meant for the live runs that replaced the dropped control/benchrel arms.
Run it AFTER training finishes (needs ppo_model_final.zip), e.g.:

    python experiments/import_run.py --name batch256 \
        --checkpoint-dir checkpoints/run_14mo_gamma999_batch256 \
        --config configs/ppo_gamma999_batch256.yaml
    python experiments/import_run.py --name benchrel_b64 \
        --checkpoint-dir checkpoints/run_14mo_gamma999_benchrel \
        --config configs/ppo_gamma999_benchrel.yaml
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

EXPERIMENTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXPERIMENTS_DIR))
from preconditions import check_all  # noqa: E402
from run_sweep import (  # noqa: E402
    _repo_main_root,
    hodl_5050_pnl,
    latest_vecnormalize,
    load_manifest,
    plot_equity,
    summarize_variant,
    write_card,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="leaderboard row name (results/<name>/)")
    parser.add_argument("--checkpoint-dir", required=True,
                        help="dir with ppo_model_final.zip + vecnormalize pkls, relative to the main checkout")
    parser.add_argument("--config", required=True,
                        help="config the run was trained with, relative to the main checkout")
    parser.add_argument("--hypothesis", default="Imported live run (trained outside the sweep).")
    parser.add_argument("--manifest", default=str(EXPERIMENTS_DIR / "manifest.yaml"))
    args = parser.parse_args()

    manifest = load_manifest(Path(args.manifest))
    common = manifest["common"]
    main_root = _repo_main_root()
    python = str(main_root / ".venv" / "bin" / "python")
    check_all(main_root / common["processed_dir"], main_root)

    checkpoint_dir = main_root / args.checkpoint_dir
    checkpoint = checkpoint_dir / "ppo_model_final.zip"
    if not checkpoint.exists():
        sys.exit(f"{checkpoint} not found -- import only after training finishes")
    vecnorm = latest_vecnormalize(checkpoint_dir)

    cfg_path = main_root / args.config
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    results_dir = EXPERIMENTS_DIR / "results" / args.name
    results_dir.mkdir(parents=True, exist_ok=True)

    # Backtests run with the MAIN checkout's scripts: that is the code the
    # checkpoint was trained under (sweep worktrees may have drifted).
    windows = []
    for i, (start, end) in enumerate(common["holdout_windows"]):
        out_dir = results_dir / f"window_{i}_{start}"
        cmd = [
            python, str(main_root / "scripts" / "backtest.py"),
            "--config", str(cfg_path),
            "--processed-dir", str(main_root / common["processed_dir"]),
            "--checkpoint", str(checkpoint),
            "--vecnormalize", str(vecnorm),
            "--eval-start", start, "--eval-end", end,
            "--seed", str(common.get("seed", 0)),
            "--out-dir", str(out_dir), "--no-plot",
        ]
        print(f"[{args.name}] backtesting {start} -> {end}")
        with open(results_dir / "backtest.log", "a") as log:
            subprocess.run(cmd, cwd=main_root,
                           env={**os.environ, "PYTHONPATH": str(main_root / "src")},
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        with open(out_dir / "backtest_metrics.json") as f:
            m = json.load(f)
        m["hodl_5050_pnl_usd"] = hodl_5050_pnl(
            out_dir / "backtest_ppo_history.csv", cfg["initial_notional_usd"]
        )
        m["window"] = [start, end]
        windows.append(m)

    variant = {
        "name": args.name,
        "overrides": {"imported_from": args.checkpoint_dir, "batch_size": cfg.get("batch_size"),
                      "reward_mode": cfg.get("reward_mode", "absolute")},
        "hypothesis": args.hypothesis,
    }
    summary = summarize_variant(args.name, variant, cfg, windows)
    with open(results_dir / "metrics.json", "w") as f:
        json.dump(summary, f, indent=2)
    plot_equity(results_dir, windows)
    write_card(results_dir, summary)
    print(f"[{args.name}] imported -> {results_dir}")


if __name__ == "__main__":
    main()
