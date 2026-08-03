# Round 3b — shortlook x benchmark_relative interaction, 3 seeds (2026-08-02)

## Context

Follows `experiments/round3_shortlook_p1p2_multiseed.md`: plain shortlook
(12h/72h vol lookbacks) does not reliably beat the passive baseline under
real swap costs (mean P&L -$927.73/window, 53% win rate, no seed cleared
the promotion gate). This arm tests the interaction candidate flagged in
`experiments/LOG.md`'s round-2 next-steps list: shortlook's faster
volatility perception combined with `reward_mode: benchmark_relative`
(alpha-only reward — see `configs/sweep_shortlook_benchrel_p1p2.yaml`),
on the same P1/P2-fixed env, same train window (2024-05-01 → 2024-12-31),
2M timesteps, 3 seeds launched together from the start (per the seed
variance lesson from round 3a).

## Results

PPO episode P&L per window (USD), same baseline as round 3a (deterministic,
identical across seeds):

| window | seed1 | seed2 | seed3 | baseline |
|---|---:|---:|---:|---:|
| 2025-01 | -126 | -65 | -624 | -1,159 |
| 2025-02 | -231 | -7 | +97 | -2,354 |
| 2025-03 | -379 | -16 | -385 | -1,803 |
| 2025-04 | -112 | -9 | -389 | -155 |
| 2025-05 (up-month) | -1,302 | -354 | +27 | +516 |
| **win rate vs baseline** | 4/5 | 4/5 | 3/5 | |

Aggregate across all 15 window×seed instances:
- PPO mean P&L: **-$258.33/window** (vs plain shortlook's -$927.73)
- Baseline mean P&L: -$990.80/window (unchanged, deterministic policy)
- PPO beats baseline by **+$732.47/window on average** (~11x the plain
  shortlook edge of +$63/instance); aggregate total edge: +$10,990 over 15
  instances (vs shortlook's +$949).
- Win rate: **11/15 (73%)**, vs shortlook's 53%.
- Mean Sharpe: -5.68 (worse-looking than shortlook's -2.04, but see below
  — this is a low-variance/small-P&L artifact, not large losses; matches
  the pre-fix `benchrel_b64` characterization in `LOG.md`: "very negative
  Sharpe reflects a low-variance, slightly-bleeding equity path").

## Behavioral driver

Action mix (2025-01 window, all 3 seeds): 90-99% HOLD (654-712 of 721
steps), vs 61-68% HOLD for plain shortlook. Swap cost $2-26/window (vs
plain shortlook's $97-444) and correspondingly low gas spend. The
alpha-only reward evidently makes near-total inaction the safest policy
once trading has a real cost — it avoids the baseline's IL/fee-driven
bleed in down months almost entirely (e.g. seed2: -$7, -$16, -$9 across
three months, essentially breakeven) at the cost of also sitting out any
upside.

## Gate check

None of the 3 seeds formally clears the promotion gate ("beats baseline in
≥4/5 windows *including* an up-month"): seed1 and seed2 hit the 4/5
win-count but both miss it specifically on May (the up-month); seed3 gets
3/5 and also misses May. Zero of 3 seeds win the up-month — same or
slightly worse than plain shortlook's 1/3 — but the *margin* of the May
miss is smaller and shrinking with the better seed: seed1 -$1,818,
seed2 -$870, seed3 -$489 (average -$1,059, vs pre-fix `benchrel_b64`'s
single-run miss of -$1,457). This is a genuine, if partial, improvement
in the specific failure mode `LOG.md` flagged for benchmark_relative: the
faster vol features let the best seed (seed3) come within $489 of holding
the rally instead of a much larger miss, but do not solve it outright.

## Conclusion

This arm is a materially stronger candidate than plain shortlook under
real costs — 11x the baseline edge, 73% vs 53% win rate, and much smaller,
more controlled worst-case losses — but still does not pass the formal
promotion gate because it structurally can't capture beta in an up-month
(the known limitation of an alpha-only reward with no incentive to hold
exposure into a rally). No promotion.

## Next steps (unchanged from round 3a's list, (b) now done)

(a) multi-seed rerun of shortlook — done (round 3a).
(b) shortlook x benchmark_relative interaction — **done, this file**.
    Confirms capital protection, does not fix the up-month gap.
(c) fresh holdout windows (2025-06 onward) to break the 5-window noise
    floor and get more than one up-month sample.
(d) if positive absolute P&L stays out of reach: the game-changing
    extensions (delta-hedge via perps to capture beta separately from the
    LP alpha reward, explicit out-of-pool regime sitting) — this round's
    result makes the case for (d) more directly: the reward already
    protects capital well, the missing piece is specifically a mechanism
    to hold beta through rallies without reintroducing the IL exposure
    that benchmark_relative was designed to remove.
