# TODO — code review findings (env + reward)

Consolidated from the reward-function and environment reviews (`src/t1000/env.py` and supporting modules), 2026-07-22/23. Ordered by priority.

## P0 — Bugs

- [x] **Volatility features saturate at 1.0.** The env accumulates *prices* in `price_history` (`env.py:312`) and passes slices of it as `returns_24h`/`returns_7d` (`env.py:246-247`), but `realized_vol` (`observations.py:59`) expects log returns. The std of USD prices divided by `VOL_24H_SCALE = 0.05` pins the clip at 1.0 from the 2nd step onward — `volatility_24h` and `volatility_7d` become constants and the agent is blind to volatility. Fix: store `log(p_t / p_{t-1})` in the history.

- [x] **Events in the snapshot's block are dropped on reset.** `precompute_snapshots` (`snapshot.py:109-118`) saves the snapshot right after the first event with `ts >= next_snapshot_ts`; remaining events of the same block (same timestamp) end up outside the snapshot AND outside the reset replay (mask `timestamp > snap_ts`, `env.py:273`). `liquidity_net`/`liquidity_gross` from dropped Mint/Burn events stay wrong in the `tick_map` for the whole episode. Fix: only snapshot when the timestamp advances (before the first event of a new timestamp). Requires regenerating snapshots.

- [x] **Cash evaporates when computed liquidity is 0.** `_open_position` debits `investable` unconditionally (`env.py:207`) even when `_liquidity_for_budget` returns 0 (`env.py:52`) — capital vanishes and produces a large spurious negative reward. Fix: guard `if liquidity <= 0: don't open, don't debit`.

## P1 — Reward design

- [ ] **Reward dominated by ETH beta, not LP skill.** Reward = ΔMTM includes direct price exposure while in position; LP alpha (fees − IL − gas) is buried in noise and the agent can learn mere market direction from the training window. Recommended fix: benchmark-relative reward — subtract the value change of a passive HODL of the position's current token composition (`impermanent_loss_usd` in `il.py:25` already does nearly this). It becomes implicit "fees − IL − gas" with no double-counting.

- [ ] **Rebalancing has no swap cost.** `_close_position`/`_open_position` (`env.py:186`, `env.py:199`) convert position↔cash at mid price with no pool fee or slippage — gas only. Frequent rebalances are systematically underpriced; backtests overstate live execution. Fix: charge fee tier + estimated slippage on the notional swapped when opening/closing.

- [ ] **Uncollected fees are frozen in USD.** Each accrued chunk is converted at the then-current price and never floats again (`env.py:179`); the WETH portion should track the price until `COLLECT`. As is, `COLLECT`'s reward is strictly −gas (its only instrumental value: refilling cash for the gas-affordability check at `env.py:216`).

## P2 — Performance

- [ ] **O(N) mask over the entire `events_df` on every step/reset.** `env.py:295` and `env.py:273` build boolean masks over the whole DataFrame — with millions of events × 720 steps × n_envs, this is the training bottleneck. Fix: pre-extract the timestamp column as a numpy array and use `np.searchsorted` (O(log N)).

## P2 — Data hygiene / leakage

- [ ] **`MarketStats` computed over the full dataset.** `train.py:213`/`backtest.py:203` pass the entire `swaps_df`/`gas_df`; volume mean/std and gas percentiles (`env.py:123`) include the evaluation period during training. Fix: filter by the env's `start_ts`/`end_ts` before computing.

- [ ] **`events_df` is neither sorted nor validated.** The env sorts `gas_df` but trusts that `events_df` arrives in (block, log_index) order (`env.py:106-112`). Add a defensive sort or a monotonicity assert.

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

## Deployment — HITL advisory dashboard (planned)

Decisions: agent is advisory-only (human executes on mainnet manually and confirms fills); data feed = BigQuery behind an `EventSource` interface (RPC/web3 later); FastAPI + plain HTML; hourly cadence; validation via paper-trading on real mainnet data (no testnet — Sepolia pools have no organic liquidity, the signal is meaningless there). Full design in the plan file; summary checklist:

- [ ] **Retrain gate (blocking).** The best checkpoint (`run_14mo_lowent`) was trained on pre-fix code (saturated volatility features, old snapshot cut). After the P0 fixes the obs distribution changed: regenerate snapshots, retrain, re-backtest before any live artifact is exported.
- [ ] **Post-retrain check: did the policy absorb the volatility signal?** Plot the distribution of chosen actions bucketed by `volatility_24h`/`volatility_7d` over backtest rollouts. Expected if the (now un-saturated) features are being used: REBALANCE_NARROW dominates in low-vol buckets, WIDE/EXIT_TO_CASH grow in high-vol buckets. A flat distribution across buckets means the features still carry no weight. Also sanity-log early in training that both features vary in (0, 1) instead of pinning at 1.0.
- [ ] **Phase 0:** add `fastapi`/`uvicorn`; extract `decode_logs` from `build_dataset.py` into `src/t1000/`; add `MarketStats.from_precomputed(...)`.
- [ ] **Phase 1 — `PinnedLPEnv` + deployment package.** Subclass `UniswapV3LPEnv` (pinned non-random reset, `append_events`, `apply_confirmed_execution`, state persistence via `snapshot.py`). Inference without VecEnv wrapping: standalone `vecnorm.normalize_obs` + `PPO.predict(deterministic=True)`; parity tests vs `backtest.py:105-122`. Package = model.zip + vecnormalize.pkl + market_stats.json + sorted base-fee array + gas_units + manifest (sha256, git commit, obs/action shapes — `DeploymentPackage.load` hard-fails on mismatch).
- [ ] **Phase 2 — ingestion.** `BigQueryEventSource` (reuses `fetch_data.py` queries), monthly parquet store with decimal-string bigints, cursor + `(block_number, log_index)` dedup, one-time backfill from last processed snapshot to now.
- [ ] **Phase 3 (v1) — paper trading + read-only dashboard.** Hourly asyncio loop (idempotent, cursor advances only on success), PPO + baseline paper sessions, staleness guard ("DO NOT ACT" if data > 2h old), equity chart + `compute_episode_metrics`.
- [ ] **Phase 4 (v2) — HITL.** Recommendation card (action, target range in USD, gas estimate, swap-cost warning, baseline opinion, action probs), confirm form (actual ticks/USD/gas/tx hash; "did nothing" is valid), manual reconcile form, append-only ledger.
- [ ] **Free-tier internet hosting.** Recommended: Google Cloud Run (GCP creds already exist for BigQuery) — scale-to-zero web service + Cloud Scheduler firing the hourly tick endpoint + state/history in GCS (all within free tiers). Alternatives: Fly.io with a small volume, HF Spaces (Docker). Being public, the HITL endpoints (`/api/confirm`, `/api/reconcile`) must require a secret token; read-only pages can stay open.
- [ ] **Performance history since deploy.** Append-only per-tick ledger in durable storage (GCS): timestamp, agent_id, action recommended, portfolio value (paper + HITL-tracked), price, data freshness. Never overwritten on restarts/redeploys; equity curve and metrics always rendered from the full ledger since day zero.
- [ ] **Multi-agent support + comparison.** Deployment packages are versioned per agent (`deploy/<agent_id>/` with manifest identity); every history row is keyed by `agent_id`. Swapping in a new agent starts a new ledger segment without touching the old one; the dashboard overlays current vs previous agents' equity on one chart with deploy-date markers, and a retired agent can optionally keep running in shadow (paper) mode for a true A/B against the active one.

## Strengths (don't touch without reason)

- Single-number portfolio accounting (fees/IL/gas already embedded, no double-counting) and normalization by initial notional.
- Refcounted shadow ticks for `feeGrowthInside` of synthetic ranges without perturbing real liquidity.
- Replay trusting on-chain post-swap state (no simulated price impact) + `liquidity_mismatches` counter.
- Correct `terminated`/`truncated` semantics; info captured inside step because of VecEnv auto-reset.
