#!/usr/bin/env python
"""Aggregates experiments/results/*/metrics.json into experiments/LEADERBOARD.md.

**The promotion reference is HODL 50/50** (hold half USDC, half WETH from the
window's first price), not the full-range LP baseline. Re-baselined 2026-08-19
after `experiments/round4_heuristic_sweep.md` showed the full-range policy is a
weak opponent: one integer of rebalance patience beats it by +$4,370 over five
windows at paired t=2.65, more than any trained variant achieved with
significance. Scoring against it overstated every result by roughly that much.
HODL 50/50 is the reference because it is the actual opportunity cost -- the
thing a person with this capital would otherwise do with it.

Ranking stays risk-adjusted (mean holdout Sharpe, ties by total P&L), which is
deliberately *not* the gate: with ~5 windows of 30 days, Sharpe varies more
with path noise than with policy quality, so it orders the table while the gate
decides promotion.

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
# Promotion needs all-but-one window, so a single unlucky path can't sink an
# otherwise consistent variant -- and can't be tuned away either.
GATE_ALLOWED_LOSSES = 1


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
    # HODL is the reference now, so "indistinguishable" is about HODL alone.
    # Beating the full-range baseline is kept as a column for continuity with
    # rounds 1-3, not as evidence of anything.
    s["indistinguishable"] = abs(s["t_vs_hodl"]) < T_STAT_THRESHOLD

    # The up-month is found, not hardcoded: it's the window where HODL earns
    # the most, i.e. where price appreciation dominates its return. That's the
    # window a policy can only win by actually holding exposure, which is what
    # stops a cash-sitting policy from clearing the gate by dodging drawdowns.
    up_month = max(range(len(hodl)), key=lambda i: hodl[i])
    s["up_month_window"] = s["windows"][up_month]["eval_start"]
    s["beats_up_month"] = ppo[up_month] > hodl[up_month]

    n_wins = sum(1 for p, h in zip(ppo, hodl) if p > h)
    s["windows_beating_hodl"] = n_wins
    s["gate_wins_ok"] = n_wins >= len(hodl) - GATE_ALLOWED_LOSSES
    s["gate_significant"] = s["t_vs_hodl"] >= T_STAT_THRESHOLD
    s["passes_gate"] = s["gate_wins_ok"] and s["beats_up_month"] and s["gate_significant"]
    return s


def gate_failure_reason(s: dict, n: int) -> str:
    """Why a variant failed, so the table says what would have to change."""
    if s["passes_gate"]:
        return "PROMOTE"
    reasons = []
    if not s["gate_wins_ok"]:
        reasons.append(f"{s['windows_beating_hodl']}/{n} wins")
    if not s["beats_up_month"]:
        reasons.append("loses up-month")
    if not s["gate_significant"]:
        reasons.append(f"t={s['t_vs_hodl']:.1f}")
    return ", ".join(reasons)


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

    up_month = summaries[0]["up_month_window"]
    lines = [
        "# Experiment sweep leaderboard",
        "",
        f"Generated {date.today().isoformat()} from experiments/results/ "
        f"({len(summaries)} variants x {n} holdout windows). "
        "Ranked by mean holdout Sharpe (risk-adjusted), ties by total P&L.",
        "",
        "**Promotion gate (all three, vs HODL 50/50):** beat HODL in "
        f"{n - GATE_ALLOWED_LOSSES}/{n} windows, *including* the up-month "
        f"({up_month}), at paired t >= {T_STAT_THRESHOLD:.0f}. The reference is "
        "HODL, not the full-range LP baseline -- see "
        "`experiments/round4_heuristic_sweep.md` for why the old reference was "
        "too weak to promote against. The `vs full-range` column is kept for "
        "continuity with rounds 1-3 only.",
        "",
        "| # | Variant | Mean Sharpe | Total P&L | vs HODL 50/50 | Wins vs HODL | Up-month | vs full-range | Worst DD | Gate |",
        "|---|---------|------------:|----------:|--------------:|-------------:|:--------:|--------------:|---------:|------|",
    ]
    for i, s in enumerate(summaries, 1):
        lines.append(
            f"| {i} | {s['name']} | {s['ppo_mean_sharpe']:.2f} "
            f"| ${s['ppo_total_pnl_usd']:+,.0f} "
            f"| ${s['ppo_total_pnl_usd'] - s['hodl_total_pnl_usd']:+,.0f} (t={s['t_vs_hodl']:.1f}) "
            f"| {s['windows_beating_hodl']}/{n} "
            f"| {'yes' if s['beats_up_month'] else 'no'} "
            f"| ${s['ppo_total_pnl_usd'] - s['baseline_total_pnl_usd']:+,.0f} (t={s['t_vs_baseline']:.1f}) "
            f"| {s['ppo_worst_drawdown']:.1%} "
            f"| {gate_failure_reason(s, n)} |"
        )

    promoted = [s["name"] for s in summaries if s["passes_gate"]]
    flagged = [s["name"] for s in summaries if s["indistinguishable"]]
    lines += [
        "",
        "## Gate result",
        "",
        ("**No variant clears the gate.** " if not promoted else
         "Clearing the gate: " + ", ".join(promoted) + ". "),
        "",
        "## Statistically indistinguishable from HODL 50/50",
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
    if winner["passes_gate"]:
        lines += [
            "",
            "## Proposed README diff for the winner",
            "",
            readme_diff_for(winner, len(summaries)),
            "",
        ]
    else:
        # Deliberately no diff to copy-paste: the top of a ranking is not a
        # result, and offering the snippet anyway is how a noise-level variant
        # ends up quoted in the README as a finding.
        lines += [
            "",
            "## No README diff proposed",
            "",
            f"`{winner['name']}` only tops the Sharpe ranking; it fails the gate "
            f"({gate_failure_reason(winner, n)}). Nothing here is promotable, so "
            "no README snippet is generated.",
            "",
        ]

    out = EXPERIMENTS_DIR / "LEADERBOARD.md"
    out.write_text("\n".join(lines))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
