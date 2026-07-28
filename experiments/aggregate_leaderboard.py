#!/usr/bin/env python
"""Aggregates experiments/results/*/metrics.json into experiments/LEADERBOARD.md.

Ranking is by risk-adjusted return (mean holdout Sharpe, ties broken by total
P&L). Each variant's edge over the full-range and HODL-50/50 baselines is
tested with a paired t-statistic across the holdout windows; with only ~5
windows, |t| < 2 is flagged as statistically indistinguishable from the
baseline rather than a real edge.

Usage:
    python experiments/aggregate_leaderboard.py
"""
import json
import math
from datetime import date
from pathlib import Path

EXPERIMENTS_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EXPERIMENTS_DIR / "results"
T_STAT_THRESHOLD = 2.0


def paired_t(diffs: list) -> float:
    n = len(diffs)
    if n < 2:
        return 0.0
    mean = sum(diffs) / n
    var = sum((d - mean) ** 2 for d in diffs) / (n - 1)
    if var == 0:
        return 0.0
    return mean / math.sqrt(var / n)


def load_summaries() -> list:
    summaries = []
    for path in sorted(RESULTS_DIR.glob("*/metrics.json")):
        with open(path) as f:
            summaries.append(json.load(f))
    return summaries


def enrich(s: dict) -> dict:
    ppo = [w["ppo"]["episode_pnl_usd"] for w in s["windows"]]
    base = [w["baseline"]["episode_pnl_usd"] for w in s["windows"]]
    hodl = [w["hodl_5050_pnl_usd"] for w in s["windows"]]
    s["t_vs_baseline"] = paired_t([p - b for p, b in zip(ppo, base)])
    s["t_vs_hodl"] = paired_t([p - h for p, h in zip(ppo, hodl)])
    s["indistinguishable"] = (
        abs(s["t_vs_baseline"]) < T_STAT_THRESHOLD and abs(s["t_vs_hodl"]) < T_STAT_THRESHOLD
    )
    return s


def readme_diff_for(winner: dict, n_variants: int) -> str:
    n = len(winner["windows"])
    added = [
        "## Best sweep variant: " + winner["name"],
        "",
        f"Selected from a {n_variants}-variant sweep (see `experiments/LEADERBOARD.md`), "
        f"holdout = {n} unseen 30-day windows (Jan-May 2025):",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Config overrides | `{json.dumps(winner['overrides'])}` |",
        f"| Total holdout P&L | ${winner['ppo_total_pnl_usd']:+,.0f} "
        f"(baseline ${winner['baseline_total_pnl_usd']:+,.0f}, "
        f"HODL ${winner['hodl_total_pnl_usd']:+,.0f}) |",
        f"| Windows beating baseline | {winner['windows_beating_baseline']}/{n} |",
        f"| Mean Sharpe / worst drawdown | {winner['ppo_mean_sharpe']:.2f} / "
        f"{winner['ppo_worst_drawdown']:.1%} |",
    ]
    lines = ["```diff", "--- a/README.md", "+++ b/README.md",
             "@@ results section: append after the existing results table @@"]
    lines += [f"+{l}" for l in added]
    lines.append("```")
    return "\n".join(lines)


def main():
    summaries = [enrich(s) for s in load_summaries()]
    if not summaries:
        raise SystemExit(f"no results under {RESULTS_DIR} -- run experiments/run_sweep.py first")
    summaries.sort(key=lambda s: (s["ppo_mean_sharpe"], s["ppo_total_pnl_usd"]), reverse=True)
    n = len(summaries[0]["windows"])

    lines = [
        "# Experiment sweep leaderboard",
        "",
        f"Generated {date.today().isoformat()} from experiments/results/ "
        f"({len(summaries)} variants x {n} holdout windows). "
        "Ranked by mean holdout Sharpe (risk-adjusted), ties by total P&L. "
        f"`~ baseline` = paired |t| < {T_STAT_THRESHOLD:.0f} vs BOTH baselines: "
        "treat as noise, not edge.",
        "",
        "| # | Variant | Mean Sharpe | Total P&L | vs full-range | vs HODL 50/50 | Wins | Worst DD | Signal |",
        "|---|---------|------------:|----------:|--------------:|--------------:|-----:|---------:|--------|",
    ]
    for i, s in enumerate(summaries, 1):
        lines.append(
            f"| {i} | {s['name']} | {s['ppo_mean_sharpe']:.2f} "
            f"| ${s['ppo_total_pnl_usd']:+,.0f} "
            f"| ${s['ppo_total_pnl_usd'] - s['baseline_total_pnl_usd']:+,.0f} (t={s['t_vs_baseline']:.1f}) "
            f"| ${s['ppo_total_pnl_usd'] - s['hodl_total_pnl_usd']:+,.0f} (t={s['t_vs_hodl']:.1f}) "
            f"| {s['windows_beating_baseline']}/{n} "
            f"| {s['ppo_worst_drawdown']:.1%} "
            f"| {'~ baseline' if s['indistinguishable'] else 'distinct'} |"
        )

    flagged = [s["name"] for s in summaries if s["indistinguishable"]]
    lines += [
        "",
        "## Statistically indistinguishable from baseline",
        "",
        ("None." if not flagged else
         "- " + "\n- ".join(flagged) + f"\n\nWith only {n} paired windows, these deltas are "
         "within noise; do not promote them on P&L alone."),
        "",
        "## Per-variant cards",
        "",
    ]
    for s in summaries:
        lines.append(f"- [{s['name']}](results/{s['name']}/card.md) -- "
                     f"overrides `{json.dumps(s['overrides'])}`")

    winner = summaries[0]
    lines += [
        "",
        "## Proposed README diff for the winner"
        + (" (CAUTION: winner is itself ~ baseline)" if winner["indistinguishable"] else ""),
        "",
        readme_diff_for(winner, len(summaries)),
        "",
    ]

    out = EXPERIMENTS_DIR / "LEADERBOARD.md"
    out.write_text("\n".join(lines))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
