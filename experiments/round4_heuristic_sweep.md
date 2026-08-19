# Round 4 — rule-based grid sweep, zero training (2026-08-19)

## Context

`TODO.md`'s "Status check (2026-08-02)" called for a simple heuristic
baseline as a cheap sanity check on whether the ceiling in this action
space is low enough that no amount of RL tuning matters. Inspecting
`src/t1000/baseline_policy.py` first turned up the premise error: the
reference policy every PPO variant has been scored against **is already
that heuristic** — `FullRangeBaselinePolicy` rebalances `REBALANCE_WIDE`
(±10%) the instant price leaves the range and collects weekly. The
literal TODO item was therefore already satisfied, and vacuous.

The check that still had value: sweep the *neighbourhood* of that
reference point. If nearby rules do no better, the reference is near a
local optimum and the low ceiling is real. If some rule does much better,
then every published PPO result was measured against a poorly chosen
reference — and the RL-vs-baseline framing needs rereading.

The second reading turned out to be the correct one.

Grid: band width (narrow ±2% / medium ±5% / wide ±10%) × out-of-range
patience (0 / 24 steps) × periodic collect (weekly / never) = 12 cells,
plus the reference itself, over the same five fixed 720h holdout windows
from `experiments/manifest.yaml`. 65 episodes, no training compute.
`scripts/heuristic_sweep.py` imports `make_env_fn` from
`scripts/backtest.py` so the env config cannot drift from what the PPO
runs used.

**Equivalence check**: the `(wide, patience=0, weekly)` cell reproduced
the reference bit-for-bit end to end — identical −$4,954.29 total P&L
across all five windows — which is what makes these numbers directly
comparable to `experiments/LEADERBOARD.md`. Also asserted at the unit
level over 200 random observations in `tests/test_heuristic_policy.py`.

## Results

Episode P&L per window (USD), 720h each, $10,000 notional:

| Window | reference (wide, p0, weekly) | wide, p24, no-collect | medium, p24, no-collect | HODL 50/50 |
|---|---:|---:|---:|---:|
| 2025-01 | -1,159.19 | **+752.19** | +660.18 | -126.57 |
| 2025-02 | -2,354.25 | **-1,518.20** | -2,029.61 | -1,181.75 |
| 2025-03 | -1,802.52 | **-736.64** | -961.38 | -960.86 |
| 2025-04 | -154.57 | -290.80 | **+88.04** | -80.97 |
| 2025-05 (up-month) | +516.25 | +1,209.04 | **+1,432.10** | +2,056.91 |
| **Total** | **-4,954.29** | **-584.39** | **-810.68** | **-293.25** |

Full grid ranked by edge over the reference:

| Policy | Total P&L | vs reference | Wins | Beats May | t vs ref | vs HODL | t vs HODL |
|---|---:|---:|---:|:---:|---:|---:|---:|
| wide, p24, no-collect | -584 | **+4,370** | 4/5 | yes | 2.65 | -291 | -0.20 |
| medium, p24, no-collect | -811 | **+4,144** | 5/5 | yes | 2.94 | -517 | -0.35 |
| narrow, p24, no-collect | -1,929 | +3,025 | 4/5 | yes | 2.12 | -1,636 | -1.86 |
| narrow, p24, weekly | -2,005 | +2,949 | 4/5 | yes | 2.02 | -1,712 | -1.90 |
| wide, p24, weekly | -2,160 | +2,794 | 4/5 | yes | 2.69 | -1,867 | -1.83 |
| medium, p24, weekly | -2,454 | +2,500 | 5/5 | yes | 3.53 | -2,161 | -2.10 |
| wide, p0, no-collect | -4,397 | +558 | 5/5 | yes | 2.02 | -4,104 | -3.44 |
| **reference** (= wide, p0, weekly) | -4,954 | 0 | — | — | — | -4,661 | -3.83 |
| medium, p0, no-collect | -5,488 | -534 | 2/5 | yes | -0.63 | -5,195 | -6.41 |
| medium, p0, weekly | -5,523 | -569 | 2/5 | yes | -0.69 | -5,230 | -6.51 |
| narrow, p0, either | -9,385 | -4,431 | 0/5 | no | -5.98 | -9,092 | -7.76 |

## Two findings

**1. The reference baseline is badly chosen, and this inflated every
"PPO ≈ baseline" verdict.** Adding 24 hours of patience before
re-centering — one integer — improves the reference by **+$4,370 over
five windows at paired t = 2.65**, i.e. statistically distinct by the
project's own `T_STAT_THRESHOLD = 2.0`. For comparison, the best PPO
variant on `LEADERBOARD.md` (`shortlook`) gained +$4,447 over the same
reference at **t = 1.6**, and was correctly flagged `~ baseline`. A
one-line rule matches two million training timesteps' worth of edge, and
does so with a statistic that clears the bar the RL runs never did.

The mechanism is not primarily gas. In January the reference rebalanced
6× for $510 of gas and stayed 99% in range, yet lost -$1,159 where the
patient rule earned +$752 with 1 rebalance and $10 of gas — a $1,911
swing of which only ~$500 is gas and swap cost. The rest is
**crystallized impermanent loss**: every re-center realizes the
divergence loss instead of leaving it to mean-revert, so chasing price in
a choppy month ratchets losses in. Staying 90-98% in range instead of 99%
is nearly free in forgone fees and saves that ratchet. The reference's
99%-in-range discipline is a cost centre, not a virtue.

**2. Nothing beats HODL 50/50 — including the best heuristic.** The top
cell finishes -$584 against HODL's -$293 (t = -0.20, indistinguishable);
no cell in the grid beats it, and the six patience-0 cells lose to it
decisively (t = -3.4 to -7.8). This reproduces `LEADERBOARD.md`'s
`vs HODL 50/50` column, where no PPO variant beat HODL either. Across
roughly 25 distinct configurations now — 13 RL, 12 rule-based —
**not one has beaten simply holding the two tokens**, and the best of
them is statistically tied with it.

## Conclusion

The "is the ceiling low?" question is answered, and the answer is yes,
but with an important qualification. There *is* real, statistically
detectable structure in this action space — patience beats haste by a
wide, significant margin — so the flat RL results were partly an artifact
of comparing against an unnecessarily weak reference. But that structure
tops out at parity with holding the tokens: active LP management on this
pool, at this notional, over this period, is at best a tie with doing
nothing, after fees, gas, swap costs and IL.

That is a legitimate finding and it is cheap and solid — five paired
windows, zero training compute, a statistic that clears the project's own
gate. It is also a finding the existing promotion gate cannot express,
since that gate is defined against the full-range reference this round
just showed to be a weak opponent.

## Next steps

(a) **Re-baseline the gate.** Replace `FullRangeBaselinePolicy` as the
    promotion reference with the best rule-based cell (wide, patience 24,
    no periodic collect), or make HODL 50/50 the primary gate. Any future
    RL result scored against the current reference overstates its edge by
    roughly $4,400 over five windows. Note this raises the bar sharply:
    no existing checkpoint would clear it.
(b) **Retire, do not re-tune.** No RL arm has cleared the HODL bar, and
    the rule-based sweep now bounds what is achievable in this action
    space at approximately that bar. Further hyperparameter or reward
    tuning against the old reference would be measuring the wrong thing.
(c) **Fresh windows before any stronger claim.** Everything here still
    rests on five 30-day windows from one 5-month stretch with a single
    up-month (`TODO.md`'s other open item). The patience effect is large
    enough to survive that caveat; the HODL parity conclusion is the one
    that would most benefit from more samples.
