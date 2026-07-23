#!/usr/bin/env python
"""Render an animated GIF of a saved backtest run (from scripts/backtest.py),
showing portfolio value, price/position-range, cumulative gas, and the
agent's current action evolve step by step -- for recording a demo video of
"the agent working".

Usage:
    uv run python scripts/animate_backtest.py --history-dir runs/backtest/20260722_154527
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Patch


def load_history(history_dir: Path, name: str) -> pd.DataFrame:
    return pd.read_csv(history_dir / f"backtest_{name}_history.csv", parse_dates=["timestamp"])


def animate(baseline: pd.DataFrame, ppo: pd.DataFrame, out_path: Path, fps: int, stride: int) -> None:
    n = min(len(baseline), len(ppo))
    baseline = baseline.iloc[:n]
    ppo = ppo.iloc[:n]
    frame_indices = list(range(1, n, stride))
    if frame_indices[-1] != n - 1:
        frame_indices.append(n - 1)

    with plt.style.context("dark_background"):
        fig, (ax_val, ax_price, ax_gas) = plt.subplots(3, 1, figsize=(11, 9), dpi=100, sharex=True)

        x_min, x_max = ppo["timestamp"].iloc[0], ppo["timestamp"].iloc[-1]
        val_min = min(baseline["portfolio_value_usd"].min(), ppo["portfolio_value_usd"].min())
        val_max = max(baseline["portfolio_value_usd"].max(), ppo["portfolio_value_usd"].max())
        price_min = min(
            baseline["range_lower_usd"].min(skipna=True),
            ppo["range_lower_usd"].min(skipna=True),
            ppo["price_usd"].min(),
        )
        price_max = max(
            baseline["range_upper_usd"].max(skipna=True),
            ppo["range_upper_usd"].max(skipna=True),
            ppo["price_usd"].max(),
        )
        baseline_cum_gas = baseline["gas_cost_usd"].cumsum()
        ppo_cum_gas = ppo["gas_cost_usd"].cumsum()
        gas_max = max(baseline_cum_gas.max(), ppo_cum_gas.max())

        ax_val.set_xlim(x_min, x_max)
        ax_val.set_ylim(val_min * 0.98, val_max * 1.02)
        ax_val.set_ylabel("Portfolio value (USD)")
        ax_val.set_title("Backtest: PPO agent vs full-range baseline")

        ax_price.set_ylim(price_min * 0.95, price_max * 1.05)
        ax_price.set_ylabel("Price (USD/ETH)")

        ax_gas.set_ylim(0, gas_max * 1.05)
        ax_gas.set_ylabel("Cumulative gas cost (USD)")
        ax_gas.set_xlabel("Date")
        fig.autofmt_xdate()

        baseline_color = "silver"
        ppo_color = "dodgerblue"

        (line_val_b,) = ax_val.plot([], [], color=baseline_color, label="baseline (full-range)")
        (line_val_p,) = ax_val.plot([], [], color=ppo_color, label="PPO")
        (dot_val_b,) = ax_val.plot([], [], "o", color=baseline_color)
        (dot_val_p,) = ax_val.plot([], [], "o", color=ppo_color)
        ax_val.legend(loc="upper left")

        (line_price,) = ax_price.plot([], [], color="white", linewidth=1, label="ETH/USD price")
        range_b_patch = Patch(color=baseline_color, alpha=0.2, label="baseline range")
        range_p_patch = Patch(color=ppo_color, alpha=0.3, label="PPO range")
        ax_price.legend(handles=[line_price, range_b_patch, range_p_patch], loc="upper left")
        action_text = ax_price.text(
            0.99,
            0.95,
            "",
            transform=ax_price.transAxes,
            ha="right",
            va="top",
            fontsize=13,
            fontweight="bold",
            color="white",
            bbox=dict(boxstyle="round", facecolor="#222222", edgecolor="white"),
        )

        (line_gas_b,) = ax_gas.plot([], [], color=baseline_color, label="baseline cumulative gas")
        (line_gas_p,) = ax_gas.plot([], [], color=ppo_color, label="PPO cumulative gas")
        ax_gas.legend(loc="upper left")

        date_text = fig.text(0.5, 0.965, "", ha="center", fontsize=11, color="white")

        state = {"fill_b": None, "fill_p": None}

        def update(i):
            line_val_b.set_data(baseline["timestamp"].iloc[: i + 1], baseline["portfolio_value_usd"].iloc[: i + 1])
            line_val_p.set_data(ppo["timestamp"].iloc[: i + 1], ppo["portfolio_value_usd"].iloc[: i + 1])
            dot_val_b.set_data([baseline["timestamp"].iloc[i]], [baseline["portfolio_value_usd"].iloc[i]])
            dot_val_p.set_data([ppo["timestamp"].iloc[i]], [ppo["portfolio_value_usd"].iloc[i]])

            line_price.set_data(ppo["timestamp"].iloc[: i + 1], ppo["price_usd"].iloc[: i + 1])

            if state["fill_b"] is not None:
                state["fill_b"].remove()
                state["fill_p"].remove()
            state["fill_b"] = ax_price.fill_between(
                baseline["timestamp"].iloc[: i + 1],
                baseline["range_lower_usd"].iloc[: i + 1],
                baseline["range_upper_usd"].iloc[: i + 1],
                step="post",
                color=baseline_color,
                alpha=0.2,
            )
            state["fill_p"] = ax_price.fill_between(
                ppo["timestamp"].iloc[: i + 1],
                ppo["range_lower_usd"].iloc[: i + 1],
                ppo["range_upper_usd"].iloc[: i + 1],
                step="post",
                color=ppo_color,
                alpha=0.3,
            )

            action = ppo["action"].iloc[i]
            action = "-" if pd.isna(action) else action
            action_text.set_text(f"Action: {action}")
            action_text.set_color("white" if action in ("-", "HOLD") else "orange")

            line_gas_b.set_data(baseline["timestamp"].iloc[: i + 1], baseline_cum_gas.iloc[: i + 1])
            line_gas_p.set_data(ppo["timestamp"].iloc[: i + 1], ppo_cum_gas.iloc[: i + 1])

            date_text.set_text(ppo["timestamp"].iloc[i].strftime("%Y-%m-%d %H:%M"))

            return (
                line_val_b,
                line_val_p,
                dot_val_b,
                dot_val_p,
                line_price,
                line_gas_b,
                line_gas_p,
                action_text,
                date_text,
            )

        fig.tight_layout(rect=(0, 0, 1, 0.96))

        anim = FuncAnimation(fig, update, frames=frame_indices, blit=False)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        anim.save(str(out_path), writer=PillowWriter(fps=fps))
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history-dir", required=True, help="a runs/backtest/<timestamp> dir from scripts/backtest.py")
    parser.add_argument("--out", default=None, help="default: <history-dir>/backtest_animation.gif")
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--stride", type=int, default=1, help="render every Nth step (2 = half the frames, faster/smaller file)")
    args = parser.parse_args()

    history_dir = Path(args.history_dir)
    baseline = load_history(history_dir, "baseline")
    ppo = load_history(history_dir, "ppo")

    out_path = Path(args.out) if args.out else history_dir / "backtest_animation.gif"
    n_frames = len(range(1, min(len(baseline), len(ppo)), args.stride)) + 1
    print(f"Rendering ~{n_frames} frames at {args.fps} fps...")
    animate(baseline, ppo, out_path, args.fps, args.stride)
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    main()
