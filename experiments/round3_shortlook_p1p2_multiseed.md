# Round 3 — shortlook sanity retrain + multi-seed under the P1/P2-fixed env (2026-08-01)

## Context

`src/t1000/env.py` P1/P2 fixes (see `TODO.md`): real swap cost on
rebalance/exit (fee tier + slippage, netted against the closed position's
composition), uncollected fees floating with price instead of frozen in
USD, `MarketStats` scoped to the training window only (previously leaked
eval-period volume/gas stats), plus a `searchsorted` perf fix and an
`events_df` sort assertion. The round-2 sweep winner (`shortlook`: 12h/72h
volatility lookbacks, γ=0.999, batch 64 — see `experiments/LOG.md` on
`master`, not present in this worktree; see divergence note below) was
retrained from scratch 3 times on the fixed env to check the fixes didn't
break anything and to de-noise the headline result, per `TODO.md`'s P1/P2
retrain gate.

Each run: `configs/sweep_shortlook_p1p2.yaml`, train window 2024-05-01 →
2024-12-31, 2,000,000 timesteps, 8×DummyVecEnv, CPU. No `--seed` flag exists
in `scripts/train.py`; each fresh process gets its own unseeded
init/rollout randomness. Backtests: same 5 fixed 720h holdout windows used
throughout this project (2025-01 … 2025-05), seed 0, deterministic policy,
`--train-start`/`--train-end` passed so eval-time `MarketStats` normalization
matches the checkpoint's training window.

## Results

PPO episode P&L per window (USD), baseline = passive full-range policy
(deterministic, identical across seeds — confirmed byte-identical baseline
numbers in all 3 runs):

| window | seed1 (sanity) | seed2 | seed3 | baseline |
|---|---:|---:|---:|---:|
| 2025-01 | -1,969 | -2,106 | -1,014 | -1,159 |
| 2025-02 | -1,807 | -1,985 | +353 | -2,354 |
| 2025-03 | -2,820 | -916 | -2,506 | -1,803 |
| 2025-04 | +740 | +913 | -2,339 | -155 |
| 2025-05 (up-month) | +56 | -1,120 | **+2,604** | +516 |
| **win rate vs baseline** | 2/5 | 3/5 | 3/5 | |

Aggregate across all 15 window×seed instances:
- PPO mean P&L: **-$927.73/window**, mean Sharpe: **-2.04**
- Baseline mean P&L: -$990.80/window
- PPO beats baseline in the aggregate total by only **+$949** (~$63/instance)
  — small relative to the thousands-of-dollars window-to-window variance.
- Win rate: **8/15 (53%)**.

## Diagnosis: why seed1 alone dropped so much vs the pre-fix -$405/-0.30

1. Baseline (rarely trades: 5-9 REBALANCE_WIDE/month) moved only ~2% between
   pre-fix (-$4,852 total) and post-fix (-$4,955 total) — confirms the env
   fixes didn't broadly corrupt price/fee/gas data; the effect is isolated
   to policies that trade a lot.
2. Real swap cost on PPO: $97-$444/window (avg $227) — previously an
   unpriced subsidy. Explains roughly 30% of seed1's P&L drop.
3. Remaining ~70% is behavioral: each run is a *fresh* 2M-step retrain
   (new weights), and the in-sample training rollout (`ep_pnl_usd_mean`,
   `ep_sharpe_mean`) was still climbing at 2M steps, not plateaued — same
   pattern `gamma999` showed in round 1, which `LOG.md` already documented
   as *not* a reliable holdout predictor.

## Conclusion

None of the 3 seeds clears the promotion gate from `experiments/LOG.md`
("beats the full-range baseline in ≥4/5 windows including an up-month"):
best case is 3/5 wins, and only 1 of 3 seeds wins the May up-month (the
window where beta exposure pays off). The original single-seed shortlook
number (-$405, Sharpe -0.30, 3/5 wins) was optimistic — partly from the
swap-cost subsidy now fixed, partly from single-seed training noise. Under
honest costs and 3 seeds, shortlook does not reliably beat the passive
baseline.

## Divergence note (unresolved, flagged for reconciliation)

This worktree's `HEAD` (`abe60e4`) is behind `master`'s tip; `master` has
committed `experiments/LOG.md`, `experiments/LEADERBOARD.md`, and other
files this worktree doesn't have locally (they show as absent, not just
"modified"). This file was written directly into the worktree and is
**not** merged with `master`'s `LOG.md` — reconcile manually before any
future commit that touches `experiments/`.

## Next steps (per `LOG.md` round-2's own list, now informed by round 3)

(a) multi-seed rerun — **done, this file**.
(b) shortlook × `benchmark_relative` interaction arm (best perception +
    capital-protecting reward) — untried.
(c) fresh holdout windows (2025-06 onward) to break the 5-window noise
    floor — the May up-month alone flipped sign 3 times across seeds here.
(d) if positive absolute P&L stays out of reach: the game-changing
    extensions (delta-hedge via perps, explicit out-of-pool regime sitting)
    rather than more knob-turning on range management alone.
