# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A research PoC: a PPO agent (Stable-Baselines3) that manages a concentrated
liquidity position on the Uniswap V3 ETH/USDC 0.05% pool
(`0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640`), trained against a simulator
that reimplements Uniswap V3 tick-level fee accounting from raw on-chain
event logs. The goal is a methodologically sound experiment, not a profitable
strategy — see the disclaimer in `README.md` and the honest status assessment
at the top of `TODO.md`.

`docs/HOW_IT_WORKS.md` explains the domain (Uniswap V3 fee accounting) from
scratch; read it before touching `fee_engine.py` or `tick_math.py`.

## Commands

```bash
uv sync                                        # install (Python 3.11, uv-managed)
uv run pytest tests/ -q                        # full suite (112 tests, ~seconds)
uv run pytest tests/test_env.py -q             # one file
uv run pytest tests/test_env.py -k hedge -q    # one subset by name
uv run tensorboard --logdir runs/tensorboard   # training curves
```

There is no linter or formatter configured — don't invent one.

Full pipeline (each step's output feeds the next):

```bash
# 1. BigQuery -> data/raw/ -- ALWAYS --dry-run first, this bills real quota
uv run python scripts/fetch_data.py --project <gcp-project-id> --start ... --end ... --dry-run
# 2. decode events + precompute snapshots -> data/processed*/
uv run python scripts/build_dataset.py --raw-dir data/raw --out-dir data/processed
# 3. simulator vs. real on-chain settlement (Collect - Burn)
uv run python scripts/validate.py --processed-dir data/processed
# 4. train (auto-resumes from the latest checkpoint in --checkpoint-dir)
uv run python scripts/train.py --config configs/ppo_default.yaml \
  --processed-dir data/processed_14mo_fixed \
  --train-start 2024-05-01 --train-end 2024-12-31 --total-timesteps 2000000
# 5. trained checkpoint vs. full-range baseline over one window
uv run python scripts/backtest.py --config <same config> --checkpoint <...zip> \
  --vecnormalize <...pkl> --eval-start 2025-01-01 --eval-end 2025-01-31 --train-end 2024-12-31
```

`scripts/fetch_funding.py` (Binance ETHUSDT funding rates, public/no-auth) is
only needed for `hedge_enabled` configs; `build_dataset.py` passes
`funding_rate.parquet` through to the processed dir.

BigQuery cost: the logs query scans **~1.5GB/day**; a 14-month fetch uses
~700GB of the 1TB/month free tier. Every rerun bills again. `--project`
defaults to the author's own project ID and must be passed explicitly.

## Architecture

Five layers, bottom-up. Each is separately tested; a bug low in the stack
silently corrupts everything above it.

1. **`tick_math.py`** — tick ↔ price ↔ sqrtPriceX96 and `LiquidityAmounts`,
   mirroring the on-chain Solidity libraries. Tested against known vectors.
2. **`fee_engine.py`** — replays real `Mint`/`Burn`/`Swap` events in strict
   `(block_number, log_index)` order to reconstruct `tick_map` (per-tick
   `liquidity_net`/`feeGrowthOutside`) and `PoolState`. Two design rules that
   are load-bearing:
   - Swaps are **replayed** from the real post-swap `(sqrtPriceX96, tick,
     liquidity)`, never simulated. No hypothetical price impact — this is why
     `validate.py`'s comparison against real settlement is meaningful.
   - **Shadow ticks** (`liquidity_net=0`, refcounted) let the engine track
     `feeGrowthOutside` at the agent's arbitrary chosen range boundaries
     without perturbing real active liquidity.
3. **`snapshot.py`** — replaying from genesis on every `env.reset()` is far
   too slow, so the engine state is pickled periodically to
   `data/processed*/snapshots/`. `reset()` loads the nearest snapshot at-or-
   before its sampled start and replays only the remainder.
4. **`env.py`** (`UniswapV3LPEnv`) — the Gymnasium env. `Discrete(8)` actions
   (`actions.py`), 20-feature `Box` observation (`observations.py`, `OBS_DIM`).
5. **`scripts/train.py` / `scripts/backtest.py`** — SB3 PPO with
   VecNormalize + checkpoint resume; backtest runs the checkpoint and
   `baseline_policy.py` through *the same env config* for a paired comparison.

### The portfolio accounting invariant (read before touching the reward)

`portfolio_value_usd = cash_usd + position_value_usd + unclaimed_fees_usd +
hedge_margin_usd`, and the per-step reward is just the change in that single
number, scaled by `initial_notional_usd`. Fees, impermanent loss, gas, and
swap costs are **already reflected in it** (fees raise `unclaimed_fees_usd`,
costs debit `cash_usd`, IL shows up as the position marking differently than
cash would have). Adding "fees − IL − gas" as separate reward terms
double-counts them. `unclaimed_fees_usd` is a computed property, not a stored
number: its WETH-denominated half floats with price until `COLLECT`.

Two mutually exclusive ways to remove ETH beta from the signal, enforced by a
`ValueError` in `__init__`:
- `reward_mode="benchmark_relative"` — *synthetic*: subtracts
  `prev_weth_exposure * price_change_usd` from the reward only.
- `hedge_enabled=True` (requires `funding_df`) — *real*: a short perp sized to
  `_total_weth_exposure()`, settled into the segregated `hedge_margin_usd`
  ledger. Deliberately kept out of `cash_usd` so a losing hedge can't starve
  the gas reserve and strand the position out of range.

### Env invariants worth knowing

- All timestamps are forced to **tz-aware UTC, ns precision** on ingest; real
  data is tz-aware, test fixtures usually aren't.
- `events_df` must be sorted by timestamp — `__init__` raises rather than
  re-sorting, because `reset()`/`step()` locate their slice via
  `Series.searchsorted` (an O(N) boolean mask used to be the training
  bottleneck).
- `market_stats_start`/`market_stats_end` scope observation-normalization
  stats independently of the replay window. At **eval** time these must be the
  *training* window, so normalization matches what the checkpoint saw —
  passing the eval window leaks, omitting them uses the whole dataset.
- `cash_usd` never enters the observation vector. That's what makes the
  hedge-on/hedge-off zero-training smoke test valid: identical action
  sequences, LP mechanics byte-identical, `portfolio_value_usd` differing by
  exactly the cumulative hedge P&L.
- Big integers (`sqrt_price_x96`, `liquidity`, `amount*`) are stored as
  **decimal strings** in parquet (int64 overflow) and parsed back in
  `data_loading.py:BIGINT_FIELDS`.

## Experiment workflow

Config knobs (`reward_mode`, `width_scale`, `gas_multiplier`,
`vol_lookback_short_hours`/`_long_hours`, `hedge_enabled`) are plain YAML keys
read by `train.py`/`backtest.py` and validated in `UniswapV3LPEnv.__init__`.

```bash
python experiments/preconditions.py --processed-dir data/processed_14mo_fixed
python experiments/run_sweep.py --dry-run          # print the plan
python experiments/run_sweep.py --max-parallel 2
python experiments/aggregate_leaderboard.py        # -> experiments/LEADERBOARD.md
python experiments/import_run.py --name <n> --checkpoint-dir <...> --config <...>
```

`experiments/manifest.yaml` defines the variants and the **fixed holdout set**
— five 720h windows over Jan–May 2025, identical for every variant, never seen
in training (`train_end: 2024-12-31`). `run_sweep.py` gives each variant its
own git worktree with the current uncommitted diff applied, so all variants
train on the same code. `preconditions.py` hard-fails if the dataset spans
<420 days — a previous run was silently wasted on a 2-month slice.

**Promotion gate** (re-baselined 2026-08-19, all three conditions): beat
**HODL 50/50** in ≥4/5 holdout windows, *including the up-month*, at paired
`t ≥ 2`. Enforced in `aggregate_leaderboard.py`, which prints the specific
failing condition per variant and refuses to emit a README snippet when
nothing passes.

The reference used to be the passive full-range baseline. It was replaced
because `experiments/round4_heuristic_sweep.md` showed that baseline is a weak
opponent: one integer of rebalance patience beats it by +$4,370 over five
windows at `t = 2.65`, more than any trained variant ever achieved with
significance. Every `vs full-range` number in rounds 1–3 is inflated by roughly
that much; the column is kept in `LEADERBOARD.md` for continuity only.

Three details that are load-bearing:
- The **up-month is detected, not hardcoded** — it's the window where HODL
  earns most. That's the window a policy can only win by holding real
  exposure, which is what stops a cash-sitting policy from clearing the gate
  by dodging drawdowns. `benchrel_b64` beats HODL in 4/5 windows and still
  fails on exactly this.
- Ranking is by mean Sharpe but the **gate is on P&L**, deliberately: over 5
  windows of 30 days Sharpe moves more with path noise than with policy
  quality, so it orders the table without deciding promotion.
- The round-3c objection (HODL is an incoherent target for `hedge_enabled`
  arms, since hedging gives up the appreciation HODL captures) is *accepted
  and overruled on purpose*: the gate measures decision relevance — whether a
  policy beats what the capital would otherwise do — not like-for-like risk.
  A hedged arm that loses to HODL has lost, and that is the intended reading.

As of round 4, **nothing clears this gate**: no RL variant and no rule-based
cell beats HODL 50/50 (best: -$584 vs -$293, `t = -0.20`).

Write-ups: `experiments/LOG.md` (chronological rounds),
`experiments/LEADERBOARD.md` (generated — don't hand-edit),
`experiments/round3_*.md` / `round4_*.md` (per-arm reports; follow their
per-window table + win-rate + gate-check format for comparability).

## Data and artifact conventions

`data/`, `checkpoints/`, `runs/`, and `experiments/results/` are **all
gitignored** — never expect them in `git status`, never commit them.

Multiple processed datasets coexist and are not interchangeable:
- `data/processed_14mo_fixed` — the real one (2024-05-01 → 2025-06-30,
  snapshots regenerated after the `snapshot.py` boundary fix). Use this.
- `data/processed_14mo` — same span, **pre-fix snapshots**. Results from it
  are internally consistent but not comparable to the fixed ones.
- `data/processed` — the 2-month PoC slice; `preconditions.py` rejects it.

Any change to `snapshot.py`'s cutting logic or to `fee_engine.py`'s state
requires **regenerating snapshots** (`build_dataset.py`) before results mean
anything — checkpoints trained on stale snapshots aren't comparable.

## Conventions

- All repository artifacts (code, comments, docs, commit messages) are in
  **English**, even though the working conversation may be in Portuguese.
- Comments in this codebase explain *why*, often citing the bug or experiment
  that motivated the line. Match that density and style; don't strip them.
- Cost/estimate simplifications (`SWAP_SLIPPAGE_RATE`, `FUNDING_PERIOD_HOURS`
  amortization, `gas_model.DEFAULT_GAS_UNITS`) are documented approximations,
  not oversights — see `README.md`'s "Known limitations" before "fixing" one.
