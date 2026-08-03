# Round 3c — real delta-hedge via perp, 3 seeds (2026-08-02)

## Context

Follows `experiments/round3_shortlook_benchrel_multiseed.md`: the
`benchmark_relative` synthetic reward protects capital well (73% win rate)
but structurally can't capture an up-market month, since it gives the
agent zero incentive to hold ETH exposure. The plan (see
`.claude/plans/como-seria-para-deployar-lively-rivest.md`) was to
implement a **real** short-perp hedge sized to the position's WETH
exposure, so the agent could keep providing liquidity (earning fees)
through a rally while price risk is neutralized by the hedge, instead of
avoiding exposure by sitting in cash. `hedge_enabled: true` is mutually
exclusive with `reward_mode: benchmark_relative` (same beta term, real vs
synthetic — see `configs/sweep_hedge_p1p2.yaml`), so this arm uses
`reward_mode: absolute` with the hedge doing the beta-neutralization
instead. Default 24h/168h vol lookbacks (not combined with shortlook —
one change at a time). Same train window (2024-05-01 → 2024-12-31), 2M
timesteps, 3 seeds launched together from the start.

Phases 0-2 (mechanics, unit tests, real Binance funding data, zero-training
smoke test) were validated before spending any retrain compute — see the
plan file for the full methodology and the smoke-test results (LP
mechanics byte-identical hedge on/off; `portfolio_value_usd` diff exactly
matches cumulative `hedge_pnl_usd`, max abs error 0.0 on both an up-month
and a down-month window).

## A methodology note before the results

`scripts/backtest.py` runs *both* the PPO policy and the deterministic
`FullRangeBaselinePolicy` through the same env config. Since this
config has `hedge_enabled: true`, **the baseline reported in this
experiment's own `backtest_metrics.json` is also hedged** — not the
plain passive baseline used as the promotion-gate reference in every
prior round. A hedged full-range baseline is a materially different (and
in up-months, much worse-looking) number than the unhedged one, because
the hedge cancels the exact price appreciation that makes an unhedged
full-range position profitable in a rally. Comparing hedged PPO against
the *unhedged* baseline is not apples-to-apples — by construction, no
hedged strategy can win a month where price alone would have been the
dominant source of return, since hedging deliberately gives that up in
exchange for lower variance. Both comparisons are reported below.

## Results

PPO episode P&L per window (USD):

| window | hedged baseline | unhedged baseline (gate ref) | seed1 | seed2 | seed3 |
|---|---:|---:|---:|---:|---:|
| 2025-01 | -470 | -1,159 | -369 | -193 | -405 |
| 2025-02 | -728 | -2,354 | -161 | -179 | -753 |
| 2025-03 | -530 | -1,803 | -510 | -187 | -226 |
| 2025-04 | -345 | -155 | -213 | -214 | -224 |
| 2025-05 (up-month) | -375 | +516 | -259 | -551 | -2,602 |
| **win rate vs hedged baseline** | | | **5/5** | **4/5** | 3/5 |
| **win rate vs unhedged baseline** | | | 3/5 | 3/5 | 3/5 |

Mean P&L: hedged baseline -$489.5/window, unhedged baseline -$991.0/window
(same deterministic passive numbers used in rounds 2/3a/3b). PPO mean:
seed1 -$302.4, seed2 -$264.8, seed3 -$841.9 (seed3 dragged down entirely
by the May outlier below).

## Seed3's May outlier is overtrading, not a hedge bug

Seed3's -$2,602 May result stood out enough to dig into directly.
`hedge_pnl_usd` that window sums to only -$16.5 — the hedge itself is
fine. The loss is $1,700 gas + $766 swap cost from 238 REBALANCE_WIDE +
168 SHIFT_UP actions across 721 steps (56% of steps trigger some
reposition). This is a bad-seed convergence failure (excessive trading
frequency), the same seed-to-seed variance category flagged since round
3a — not a correctness issue in the hedge mechanics. Seed1 and seed2 spent
$225-453 on gas that same window, ~4-8x less.

## Gate check

**Against the unhedged baseline (the literal existing gate)**: all 3 seeds
land at 3/5, missing April and May every time. April misses are narrow
(PPO -$213 to -$224 vs baseline -$155, a ~$60-70 gap — funding/hedging
overhead in a month where price barely moved). May misses are the
expected structural outcome discussed above: the hedge caps PPO's May
upside at "fees minus hedge cost," while the unhedged baseline captured
the full rally (+$516). **No seed clears the gate as formally defined**,
and by construction, no hedged config can clear it in a month where price
appreciation is the dominant driver of the passive baseline's return —
this isn't a tunable weakness, it's what "neutralizing beta" means.

**Against the properly-comparable hedged baseline**: seed1 wins all 5/5
windows including May (-$259 vs -$375, a genuine +$116 edge over hedged
full-range even in the up-month), seed2 wins 4/5 (loses May by -$176),
seed3 wins 3/5 (loses Feb narrowly, loses May badly to its own
overtrading). This is the fairer test of "does the RL policy add value on
top of naive full-range + hedge?" and the answer for the best seed is a
clean, if modest, yes.

## Conclusion

The hedge mechanics are correct and the trading behavior is sound for the
best seed (seed1 beats a hedged passive baseline in every window,
including the up-month it was designed to fix). But hedging structurally
cannot make a policy beat the *unhedged* baseline in a strong up-month,
since that's precisely the return source being neutralized — the
promotion gate as originally defined (beat the unhedged passive baseline
in ≥4/5 windows including May) is not a coherent target for any hedged
arm. No promotion under the existing gate; the real finding is that the
gate itself needs a hedged reference baseline to evaluate hedged
strategies meaningfully.

## Next steps

(a) Decide on a hedge-appropriate gate: compare hedged PPO against a
    hedged passive baseline (seed1 already clears this 5/5), and treat
    "beat the unhedged baseline" as a separate, harder question that's
    only answerable by *not* fully hedging — e.g. a partial-hedge ratio
    (hedge less than 100% of exposure) that lets some beta through.
(b) Investigate seed3's overtrading (238 REBALANCE_WIDE in one month) —
    possibly an entropy coefficient or gas-cost-in-reward tuning issue
    worth a dedicated look given it wiped out an otherwise-plausible seed.
(c) Fresh holdout windows (2025-06 onward, per round 3b's unchanged
    next-step (c)) to get more than one up-month sample and separate
    real signal from the 5-window noise floor.
