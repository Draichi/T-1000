# T-1000

PoC: a Deep RL (PPO) agent that decides how to manage a concentrated
liquidity position on the Uniswap V3 ETH/USDC 0.05% pool
(`0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640`): hold, collect fees, or
re-adjust the range. Maximizing fees earned minus impermanent loss minus
gas cost, against a simulator validated with real on-chain data.

For a beginner-friendly, step-by-step explanation of how the simulator and
the RL pipeline actually work under the hood (including how Uniswap V3 fee
accounting works, explained from scratch), see
[`docs/HOW_IT_WORKS.md`](docs/HOW_IT_WORKS.md).

## Security-oriented design principles

This is classical RL, not an LLM system, but it's built around a few
principles that carry over directly from AI security/safety engineering:

- **Don't trust the reward, verify it against ground truth.** RL agents are
  well known for exploiting bugs in their reward function or environment
  model instead of solving the intended task (a core concern in AI safety
  literature, e.g. Amodei et al., *Concrete Problems in AI Safety*). Here,
  the entire environment (`FeeEngine`) reimplements Uniswap V3's tick-level
  fee accounting from raw on-chain logs, an accounting bug wouldn't just be
  a wrong number, it would silently teach the agent to "earn" fees that
  don't exist in reality. That's why the project ships a dedicated check
  (`scripts/validate.py`) comparing the simulator's output against
  independently-observable, real on-chain settlement (`Collect - Burn`)
  before ever trusting it to train an agent. See
  [`docs/HOW_IT_WORKS.md`](docs/HOW_IT_WORKS.md#why-this-is-easy-to-get-wrong).
- **Fail closed on out-of-distribution states, don't extrapolate silently.**
  While iterating on this project, a backtest episode that ran past the
  edge of the historical dataset kept stepping with a frozen price instead
  of ending, and the (undertrained) policy fell into a degenerate loop
  calling `COLLECT` every step, bleeding gas for fees that weren't
  accruing, a textbook out-of-distribution failure, not a training problem.
  The fix wasn't to patch that one backtest window, it was to make the
  environment fail closed: detect when it's about to step past
  ground-truth data and terminate the episode there, instead of silently
  extrapolating into an unvalidated regime (`src/t1000/env.py`).
- **Cost-aware by construction, not by penalty tuning.** Every action
  incurs real transaction cost (gas, calibrated from historical
  `base_fee_per_gas`), so the trained policy can't optimize a reward that
  quietly ignores execution cost, a common source of unsafe or unrealistic
  policies in financial and security-adjacent RL settings, where the
  cheapest-looking action on paper is often the one an unconstrained agent
  over-selects.

## Setup

Requires [`uv`](https://docs.astral.sh/uv/) and a Google Cloud account with
BigQuery access (the 1TB/month free tier is enough). You'll need your own GCP
project with billing enabled (billing is what unlocks the free tier's query
quota; the public `crypto_ethereum` dataset itself is free to query within
that quota) — BigQuery bills the *querying* project, not the dataset owner.

```bash
uv sync
gcloud auth login                              # if not already authenticated
gcloud auth application-default login          # ADC, required by the BigQuery Python client
```

`scripts/fetch_data.py` defaults `--project` to `uniswap-rl`, which is this
author's own GCP project ID, it won't work for you. Pass your project's ID
explicitly on every `fetch_data.py` invocation:

```bash
uv run python scripts/fetch_data.py --project <your-gcp-project-id> --start ... --end ... --dry-run
```

## Structure

```
scripts/
  fetch_data.py       # BigQuery -> data/raw/*.parquet (logs, blocks, NFPM txs)
  build_dataset.py    # decodes events, generates data/processed/*.parquet + snapshots
  validate.py          # validates the simulator against real on-chain position P&L
  train.py              # PPO training with checkpointing/resume
  backtest.py            # compares a trained checkpoint vs a full-range baseline
src/t1000/          # main package (simulator, Gymnasium env, etc.)
tests/                    # pytest
configs/ppo_default.yaml  # PPO hyperparameters
```

## 1. Fetch historical data (BigQuery)

```bash
# always run --dry-run first to see estimated bytes before spending quota
uv run python scripts/fetch_data.py --project <your-gcp-project-id> --start 2024-05-01 --end 2024-07-01 --dry-run
uv run python scripts/fetch_data.py --project <your-gcp-project-id> --start 2024-05-01 --end 2024-07-01
```

**Mind the free-tier cost**: the logs query scans ~1.5GB/day (most of the
cost). A 14-month window (as originally planned for 8 months of training +
6 of backtesting) scans ~700GB, still within the 1TB/month free tier, but
using ~70% of it in a single run. For this PoC we use a reduced 2-month
window (2024-05-01 to 2024-07-01, ~91GB), enough to prove the end-to-end
pipeline with a reduced local training run. For a full training run on a
cloud GPU, fetch a wider window (adjusting `--start`/`--end`). Every rerun
bills scanned bytes again.

## 2. Build the processed dataset

```bash
uv run python scripts/build_dataset.py --raw-dir data/raw --out-dir data/processed
```

Decodes the Swap/Mint/Burn/Collect events (no RPC needed, everything is
already in BigQuery's `data`/`topics`), generates
`swaps.parquet`/`mints.parquet`/`burns.parquet`/`collects.parquet`/`gas.parquet`,
and does a full replay through the fee engine (`fee_engine.py`) to
precompute daily snapshots of pool state in `data/processed/snapshots/`
(needed so `env.reset()` is fast, without re-simulating from genesis on
every episode).

At the end, it prints a "liquidity self-check mismatches" counter: how many
swaps had their recomputed active liquidity diverge from the real on-chain
reported value. This is expected to be non-zero, it reflects real
positions that already existed before the start of the fetched window (see
the limitations section below), and serves as a data-quality signal, not a
fatal error (the simulator always self-corrects using the real liquidity
value reported on every swap).

## 3. Run the tests

```bash
uv run pytest tests/ -q
```

Covers: tick math (known vectors), the fee engine (a synthetic scenario
with hand-calculated values, including tick crossing and "shadow ticks"),
impermanent loss (cross-checked against the classic closed-form full-range
formula), the Gymnasium environment contract, the baseline policy, metrics,
and checkpoint resume.

## 4. Validate the simulator against real on-chain data

```bash
uv run python scripts/validate.py --processed-dir data/processed
```

Methodology: pick real positions with an unambiguous `(owner, tickLower,
tickUpper)` mapping (owner != NonfungiblePositionManager, or a range never
reused by that owner), replay the simulator over the same window, and
compare simulated fees (via `feeGrowthInside`) against real
`Collect - Burn`.

**Result obtained** (2024-05-01 to 2024-07-01 window, ETH/USDC 0.05% pool):
for short-duration positions (their whole relevant history is guaranteed to
be inside the fetched window), maximum divergence of **0.000001%**, well
below the <0.5% target. Long-duration positions (weeks) that touch ticks
with liquidity history predating the bootstrap window show large
divergence. This is a known limitation of the short bootstrap window, not
a bug in the fee engine (see the limitations section). The script
automatically separates and labels the two groups
(`--max-duration-blocks`).

## 5. Train (reduced local PPO)

```bash
uv run python scripts/train.py \
  --train-start 2024-05-01 --train-end 2024-06-10 \
  --total-timesteps 4096 --n-envs 2
```

- Checkpoints (`checkpoints/ppo_model_<N>_steps.zip` +
  `ppo_model_vecnormalize_<N>_steps.pkl`) are saved every
  `checkpoint_save_freq` steps (`configs/ppo_default.yaml`). Running the
  same command again **automatically resumes** from the last checkpoint
  (`reset_num_timesteps=False`), a spot instance losing the VM mid-training
  loses at most that step interval.
- Per-episode metrics (P&L, Sharpe, max drawdown, gas-adjusted APR, cumulative
  gas cost, rebalance count) go to `runs/episode_metrics.jsonl` (one line per
  finished episode, per sub-environment).
- Live training is also logged to TensorBoard (`runs/tensorboard/`):
  standard SB3 scalars (`rollout/ep_rew_mean`, `train/entropy_loss`,
  `train/approx_kl`, ...) plus two custom ones, a 100-episode rolling mean of
  `rollout/ep_gas_cost_mean` and `rollout/ep_rebalance_count_mean`, useful to
  watch whether the agent is learning to stop over-rebalancing as training
  progresses. Launch it with:
  ```bash
  uv run tensorboard --logdir runs/tensorboard
  ```
  then open `http://localhost:6006`. Resumed runs (`reset_num_timesteps=False`)
  append to the same run folder, so the curve stays continuous across
  checkpoint resumes.
- **Full training on a cloud GPU**: increase `--total-timesteps` (the
  original plan targets millions of steps), point `--n-envs` at the
  instance's core count, use `--subproc` (SubprocVecEnv) for real
  cross-process parallelism, and change `device: cuda` in
  `configs/ppo_default.yaml`. Since checkpoints already live in
  `checkpoints/`, just point that folder at persistent storage (mounted
  bucket, persistent disk) to survive spot-instance preemption.

**Result obtained on the reduced local run** (4096 steps, ~40s on CPU): the
still essentially-random policy (few PPO updates) rebalances the range
excessively often, repeatedly paying gas, an expected and documented
outcome, not a goal of this run (see `runs/episode_metrics.jsonl`).

## 6. Backtest vs baseline

```bash
uv run python scripts/backtest.py \
  --checkpoint checkpoints/ppo_model_final.zip \
  --vecnormalize checkpoints/ppo_model_vecnormalize_4000_steps.pkl \
  --eval-start 2024-06-11 --eval-end 2024-06-25
```

Runs the trained checkpoint (deterministic) and the baseline policy
(fixed full-range, only rebalances when the price leaves the range,
collects fees weekly) through the **same environment mechanics**, for a
direct comparison. Each run gets its own timestamped directory (default
`runs/backtest/<timestamp>/`, override with `--out-dir`) so repeated runs
never overwrite each other. Generates `backtest_metrics.json` (P&L, Sharpe,
max drawdown, and gas-adjusted APR for both, plus the checkpoint/eval window
used), `backtest_baseline_history.csv` / `backtest_ppo_history.csv`
(per-step history), and `backtest_plot.png` (a 3-panel comparison: portfolio
value, price with position-range bands, cumulative gas cost) unless
`--no-plot` is passed.

**Result obtained**: with the reduced local training run (4096 steps), PPO
**does not beat** the baseline (P&L of -7563 vs -930 USD over the 2-week
test window), expected for such a short training run. The full training
pipeline (millions of steps on a GPU) is the natural next step to give the
agent a real chance at learning a competitive policy.

## Known limitations (read before interpreting the results)

1. **Short bootstrap window**: we fetch only 2 months of events
   (`Mint`/`Burn`/`Swap`) for this PoC, not since the pool's genesis
   (2021). This means ticks touched by real positions opened before
   2024-05-01 and not yet closed end up with incomplete fee accounting in
   our `tick_map`, the simulator always self-corrects using the real
   liquidity reported on every swap, so this doesn't corrupt the
   price/pool state, only fee attribution for long-duration positions that
   depend on those specific ticks. Empirically validated: short-duration
   positions (not dependent on old history) reach <0.0001% divergence;
   long-duration positions can diverge significantly.
2. **No market impact**: the agent's own liquidity is treated as negligible
   relative to the pool's real liquidity, historical prices are an exact
   replay of real swaps, without simulating the effect of the agent's
   position on the execution price.
3. **"Beating the baseline in 6 months" is not guaranteed by the
   architecture**, it's an empirical result of training. With this run's
   reduced local training, we honestly document that the agent does not
   yet beat the baseline; this is expected, and the full cloud-GPU training
   pipeline is what gives that comparison a fair chance.
4. **Gas calibration is approximate**: `gas_model.DEFAULT_GAS_UNITS` uses
   order-of-magnitude estimates (not a precise decoding of
   NonfungiblePositionManager function selectors, which often bundle
   multiple actions via `multicall` and would make per-action gas
   attribution ambiguous). `build_dataset.py` computes a "blurred" median
   (all NFPM interactions) only as a sanity signal.
