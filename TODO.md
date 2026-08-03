# TODO — code review findings (env + reward)

Consolidated from the reward-function and environment reviews (`src/t1000/env.py` and supporting modules), 2026-07-22/23. Ordered by priority.

## Status check (2026-08-02): does this beat doing nothing?

After round 2 (9 variants, `experiments/LEADERBOARD.md`) and round 3 (shortlook,
shortlook x benchmark_relative, real hedge — `experiments/round3_*.md`), **no
configuration across 12+ variants and two reward-shaping approaches has beaten
the passive full-range baseline with statistical significance.** Round 2's
"best" variant (`shortlook`) is itself flagged `~ baseline` (paired |t| < 2)
and has worse total P&L than simply holding 50/50 ETH/USDC. This is the honest
state, not a setback to route around.

The infrastructure (simulator accounting, test suite, hedge mechanics, data
pipeline) is solid and reusable regardless of what comes next — that part has
real value. But every conclusion so far rests on only 5 paired 30-day holdout
windows from one 5-month stretch (Jan-May 2025, a single up-month sample),
which `LEADERBOARD.md` already flags as within-noise for most variants. Before
sinking more RL compute into this, two cheap things should settle whether
there's a real, if modest, edge to find, or whether passive full-range is
close to optimal for this pool/timeframe/notional:

- [ ] **Expand the holdout window set.** Fetch additional months via
  `scripts/fetch_data.py` (before 2024-05 and/or after 2025-06) to get more
  than one up/down-market sample — always `--dry-run` first (README's cost
  note: ~1.5GB/day scanned, the existing 14-month fetch already used ~700GB
  of the 1TB/month free tier). This only needs new backtests against
  *existing* checkpoints for windows outside the training period — no
  retraining, no additional Mac compute, until/unless a wider *training*
  window is separately decided on.
- [ ] **Simple heuristic baseline as a sanity check.** A trivial rule (e.g.
  rebalance whenever price exits the range, fixed width) run against the
  passive baseline on the same windows, with zero training cost. If even a
  simple heuristic can't beat baseline either, that's strong evidence the
  ceiling here is low regardless of policy sophistication, and further RL
  tuning is unlikely to change the conclusion.

Decide the next round based on these two results: if a real (if noisy) edge
shows up, continue refining (partial-hedge ratio, redefined hedged gate, more
seeds); if not, the honest conclusion is that passive full-range LP is
near-optimal here, which is itself a legitimate finding worth writing up. The
deployment work below stays correctly blocked either way until something
clears a statistically solid gate.

## P0 — Bugs

- [x] **Volatility features saturate at 1.0.** The env accumulates *prices* in `price_history` (`env.py:312`) and passes slices of it as `returns_24h`/`returns_7d` (`env.py:246-247`), but `realized_vol` (`observations.py:59`) expects log returns. The std of USD prices divided by `VOL_24H_SCALE = 0.05` pins the clip at 1.0 from the 2nd step onward — `volatility_24h` and `volatility_7d` become constants and the agent is blind to volatility. Fix: store `log(p_t / p_{t-1})` in the history.

- [x] **Events in the snapshot's block are dropped on reset.** `precompute_snapshots` (`snapshot.py:109-118`) saves the snapshot right after the first event with `ts >= next_snapshot_ts`; remaining events of the same block (same timestamp) end up outside the snapshot AND outside the reset replay (mask `timestamp > snap_ts`, `env.py:273`). `liquidity_net`/`liquidity_gross` from dropped Mint/Burn events stay wrong in the `tick_map` for the whole episode. Fix: only snapshot when the timestamp advances (before the first event of a new timestamp). Requires regenerating snapshots.

- [x] **Cash evaporates when computed liquidity is 0.** `_open_position` debits `investable` unconditionally (`env.py:207`) even when `_liquidity_for_budget` returns 0 (`env.py:52`) — capital vanishes and produces a large spurious negative reward. Fix: guard `if liquidity <= 0: don't open, don't debit`.

## P1 — Reward design

- [x] **Reward dominated by ETH beta, not LP skill.** Fixed via `reward_mode="benchmark_relative"` (`env.py`): subtracts the start-of-step total WETH exposure (position + uncollected WETH-denominated fees) × price change, so the reward is LP alpha (fees − IL − gas − swap) with no double-counting. See `experiments/LOG.md` round 2 for the live A/B (protects capital, but loses the up-month — alpha-only reward gives no credit for holding beta into a rally).

- [x] **`benchmark_relative` is synthetic, not real hedged P&L.** Implemented `hedge_enabled`/`funding_df` on `UniswapV3LPEnv`: a real short-perp hedge sized to `_total_weth_exposure()`, settled into a segregated `hedge_margin_usd` ledger every step via `_hedge_price_pnl_usd`/`_hedge_funding_usd` (kept out of `cash_usd` so a losing hedge can't strand the LP position — see the P0-style bug this fixed, caught by a real-data zero-training smoke test before any retrain compute was spent). Mutually exclusive with `reward_mode="benchmark_relative"` (both would remove the same beta term — see `env.py`'s `__init__` validation). 3-seed retrain results in `experiments/round3_hedge_p1p2_multiseed.md`: mechanically correct and the best seed beats a *hedged* full-range baseline in 5/5 holdout windows including the May up-month — but no seed beats the *original* (unhedged) baseline gate, and by construction none ever could in a strong up-month, since hedging deliberately cancels the price appreciation that makes the unhedged baseline win there. **Conclusion: the promotion gate as originally defined is not a coherent target for hedged configs** — it needs a hedged reference baseline, or a partial-hedge ratio that lets some beta through, to be evaluated meaningfully. See "Next steps" below before pursuing either.

- [x] **Rebalancing has no swap cost.** `_open_position` now charges `fee_tier + estimated_slippage` on the notional that must actually move from one token to the other when opening a position, netted against what a just-closed position already held (`_position_amount1_usd`/`_swap_cost_usd`); `EXIT_TO_CASH` charges the full WETH-denominated side, since cash carries zero price exposure. Reported separately in `info["swap_cost_usd"]` (backtest CSVs, TensorBoard).

- [x] **Uncollected fees are frozen in USD.** `unclaimed_fees_usd` is now a computed property over token-unit accrual (`unclaimed_fee_amount0`/`unclaimed_fee_amount1`); the WETH-denominated portion floats with the current price on every read and only stops moving once `COLLECT` withdraws it. `benchmark_relative`'s exposure netting was extended to include it (`_total_weth_exposure`), since it now carries real price exposure too.

## P2 — Performance

- [x] **O(N) mask over the entire `events_df` on every step/reset.** Replaced with `Series.searchsorted` (binary search) over the now-asserted-sorted timestamp column, same pattern already used for `gas_df`'s base-fee lookup.

## P2 — Data hygiene / leakage

- [x] **`MarketStats` computed over the full dataset.** `UniswapV3LPEnv` now accepts `market_stats_start`/`market_stats_end` to scope stats computation independently of the episode replay window. `train.py` passes its own train window (fixes the leakage automatically — training stats no longer see the holdout months). `backtest.py`/`run_sweep.py` pass the *training* window explicitly so eval-time normalization matches what the checkpoint was actually trained on, instead of leaking eval-period stats or drifting to eval-window stats; falls back to the unfiltered dataset when omitted, for backward compat with ad-hoc manual runs.

- [x] **`events_df` is neither sorted nor validated.** `UniswapV3LPEnv.__init__` now raises if `events_df["timestamp"]` isn't monotonically increasing (also required by the searchsorted fix above).

## P3 — Realism and observation

- [ ] No-op actions due to insufficient gas are silent (`env.py:216-220`) — no penalty, no obs flag; the agent can't tell them apart from a HOLD.
- [ ] `COLLECT` with no open position pays gas for nothing (`env.py:226`); rebalancing to an identical range pays full burn+collect+mint.
- [ ] Observation exposes neither cash nor an explicit `has_position` flag — `tick_lower_rel = 0.0` for "no position" aliases with a range centered on the current tick (`observations.py:108-111`).
- [ ] The agent's liquidity neither dilutes fees nor moves price — assumed and documented (`fee_engine.py:12`); fine at small notional, revisit if scaling up.

## P3 — Minor

- [ ] The "24h"/"7d" volatility windows are actually 24/168 *steps* — names lie when `step_hours != 1` (`env.py:246-247`).
- [ ] `_current_base_fee` clamps to the first row when `current_ts` predates the `gas_df` — uses future gas instead of failing (`env.py:152`).
- [ ] `self._np_random_local` is assigned and never used (`env.py:128`).
- [ ] Degenerate case: if `end_ts - start_ts < episode_hours`, the episode starts at `start_ts` and runs past `end_ts` up to `data_end_ts` (`env.py:265-269`).
- [ ] Cheap sanity clamp on the fee deltas in `_accrue_fees` (`env.py:175-176`): a wrapped delta ≈ 2^256 × float would blow up the reward; currently unreachable thanks to shadow-tick pinning, but it protects against bad data.

## Strengths (don't touch without reason)

- Single-number portfolio accounting (fees/IL/gas already embedded, no double-counting) and normalization by initial notional.
- Refcounted shadow ticks for `feeGrowthInside` of synthetic ranges without perturbing real liquidity.
- Replay trusting on-chain post-swap state (no simulated price impact) + `liquidity_mismatches` counter.
- Correct `terminated`/`truncated` semantics; info captured inside step because of VecEnv auto-reset.
