# T-1000

PoC: a Deep RL (PPO) agent that decides how to manage a concentrated
liquidity position on the Uniswap V3 ETH/USDC 0.05% pool
(`0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640`): hold, collect fees, or
re-adjust the range. Maximizing fees earned minus impermanent loss minus
gas cost, against a simulator validated with real on-chain data.

![preview](./preview.gif)

Animated replay of a backtest over a 6-month held-out period (2025-01-01 to
2025-06-30) the agent never trained on. Top panel: portfolio value over
time, PPO (blue) vs. the full-range baseline (gray). Middle panel: the
ETH/USD price (white line) with each policy's current position range drawn
as a band underneath it, plus the PPO agent's action for that step in the
top-right corner. Bottom panel: cumulative gas cost paid by each policy. As
the price falls and later recovers, the PPO agent repeatedly narrows and
shifts its range to stay concentrated near the current price (and exits to
cash during the roughest stretch), trading a higher gas bill for
better fee capture and less exposure to impermanent loss than the static
baseline. That is what the agent *does*; whether it is worth doing is a
separate question, answered in the [Conclusion](#conclusion): it is not.

For a beginner-friendly, step-by-step explanation of how the simulator and
the RL pipeline actually work under the hood (including how Uniswap V3 fee
accounting works, explained from scratch), see
[`docs/HOW_IT_WORKS.md`](docs/HOW_IT_WORKS.md).


## Conclusion

**The study finished with a negative result: active management of a
concentrated liquidity position on this pool does not beat simply holding
the two tokens.** This holds across 25 distinct configurations (13 trained
PPO variants and 12 deterministic rule-based policies), evaluated on five
fixed 30-day holdout windows (Jan-May 2025) that no policy trained on.

Totals over the five paired windows, $10,000 notional each:

| Policy | Total P&L | vs HODL 50/50 | Windows won | Paired t |
|---|---:|---:|:---:|---:|
| HODL 50/50 (hold half USDC, half WETH) | **-$293** | n/a | n/a | n/a |
| Best rule (±10% band, 24h patience, no periodic collect) | -$584 | -$291 | 2/5 | -0.20 |
| Best PPO variant (`shortlook`) | -$405 | -$111 | 3/5 | -0.0 |
| Full-range baseline (the original reference) | -$4,954 | -$4,661 | 0/5 | -3.83 |

Nothing clears the promotion gate (beat HODL in ≥4/5 windows, including the
up-month, at paired |t| ≥ 2). The best performers are *statistically tied*
with holding the tokens, not ahead of it.

### Why: the mechanism, not just the scoreboard

A concentrated liquidity position is economically a **short volatility**
position: you are short gamma, and the fee income is the premium you collect
for it. Impermanent loss is not a tax to be outsmarted, it is the downside of
the option you sold. So the question is never "can the agent beat IL?" but
"does the premium pay for the gamma?"

By the portfolio identity, `P&L_LP ≈ P&L_HODL + fees - IL - costs`. For the
best rule-based policy that gives **fees - IL ≈ -$185 over five months on
$10,000**, against ~$106 of gas and swap costs. Fee income and impermanent
loss cancel almost exactly. The ETH/USDC 0.05% pool is approximately
efficiently priced, which is what one should expect from the tightest fee
tier on the most liquid pair, where professional market makers and JIT
liquidity exist precisely to arbitrage that spread to zero.

(This figure is derived from the accounting identity, not measured
directly. Measuring fees and IL as separate logged series would make it a
result rather than an inference.)

What a policy *does* control is not the size of IL but its
**crystallization**. For a range that is never rebalanced, IL depends only on
the start and end price: it is path-independent. Path dependence enters
solely through rebalancing: every re-centering realizes the divergence and
resets the reference basket. Chasing price in a choppy month therefore
ratchets losses in. That controllable surface was worth about $4,400 over the
five windows, and a single constant, waiting 24 hours before re-centering,
captured nearly all of it.

A related consequence: the delta-hedged arm (short perp sized to the
position's WETH exposure) could not fix this either, because **a delta hedge
neutralizes the linear term while IL is the second-order one**. Delta is not
gamma. Hedging IL would require options, not perpetual futures.

### The methodological finding

For most of this project's life, every result was scored against a passive
full-range baseline. That reference turned out to be a weak opponent: adding
24 hours of rebalance patience beats it by **+$4,370 over five windows at
paired t = 2.65**, statistically distinct, where the best trained variant
managed +$4,447 at t = 1.6 and was correctly flagged as noise. A one-line
rule matched two million training timesteps' worth of apparent edge, and
cleared a significance bar the RL runs never did.

The consequence is uncomfortable and worth stating plainly: twelve PPO
variants were trained, ranked and discussed against a benchmark that was
measuring the wrong thing. No unit test catches this: the code was correct,
the statistics were correct, and the conclusion was wrong because the
comparison was unfair. The gate was re-baselined onto HODL 50/50 (the actual
opportunity cost of the capital) in
[`experiments/aggregate_leaderboard.py`](experiments/aggregate_leaderboard.py);
the full analysis is in
[`experiments/round4_heuristic_sweep.md`](experiments/round4_heuristic_sweep.md).

**If you take one transferable lesson from this repository, take this one:
sweep the neighbourhood of your baseline before you spend compute beating
it.** A benchmark does not measure a result, it defines one.

### Scope of the claim

The negative result is well-supported *within its scope* and should not be
read wider than it is. It covers one pool, one fee tier, one notional, and
five 30-day windows drawn from a single five-month stretch with only one
up-month. Market impact is not modeled. The "fees ≈ IL" decomposition is
derived rather than measured. A wider fetch (more months, more market
regimes) is the cheapest way to strengthen or overturn it, and needs no
retraining, only new backtests against existing checkpoints.

What the project does deliver: a Uniswap V3 fee simulator validated against
real on-chain settlement to 0.000001% on short-duration positions, a paired
evaluation harness with an explicit statistical gate, and an honest negative
result with an identified mechanism. A negative result with a mechanism is a
finding; it is only the finance literature that has the bad habit of not
publishing them.


## Setup

Requires [`uv`](https://docs.astral.sh/uv/) and a Google Cloud account with
BigQuery access (the 1TB/month free tier is enough). You'll need your own GCP
project with billing enabled (billing is what unlocks the free tier's query
quota; the public `crypto_ethereum` dataset itself is free to query within
that quota). BigQuery bills the *querying* project, not the dataset owner.

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

### Structure

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

### 1. Fetch historical data (BigQuery)

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

### 2. Build the processed dataset

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

### 3. Run the tests

```bash
uv run pytest tests/ -q
```

Covers: tick math (known vectors), the fee engine (a synthetic scenario
with hand-calculated values, including tick crossing and "shadow ticks"),
impermanent loss (cross-checked against the classic closed-form full-range
formula), the Gymnasium environment contract, the baseline policy, metrics,
and checkpoint resume.

### 4. Validate the simulator against real on-chain data

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

### 5. Train (reduced local PPO)

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

### 6. Backtest vs baseline

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
test window), expected for such a short training run.

With a full training run (2M timesteps, 8 months of the 14-month dataset,
`ent_coef` lowered from 0.01 to 0.001 after diagnosing excessive policy
entropy/action-thrashing in an earlier checkpoint), PPO beats the full-range
baseline over one 6-month held-out period: P&L of +1574 vs -29 USD, Sharpe
4.55 vs 0.14, and a smaller max drawdown (-9.0% vs -13.4%), at the cost of
paying more gas ($330 vs $68).

**This single-window result did not survive systematic evaluation.** Read
the [Conclusion](#conclusion) before citing it. Across five paired holdout
windows the same class of policy is statistically tied with HODL 50/50, and
the full-range baseline it beats here is itself beaten by a one-line rule.
Both facts point the same way: a single favourable window against a weak
reference is not evidence of edge.


## Security-oriented design principles

RL agents are well known for exploiting bugs in their reward function or environment
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
3. **The agent does not beat holding the two tokens.** See the
   [Conclusion](#conclusion). Single-window wins over the full-range
   baseline (reported in step 6 above) did not survive evaluation across
   five paired holdout windows, and the full-range baseline itself is beaten
   by a trivial rule. Treat any "beats the baseline" claim in this
   repository as scoped to its specific window and reference.
4. **Gas calibration is approximate**: `gas_model.DEFAULT_GAS_UNITS` uses
   order-of-magnitude estimates (not a precise decoding of
   NonfungiblePositionManager function selectors, which often bundle
   multiple actions via `multicall` and would make per-action gas
   attribution ambiguous). `build_dataset.py` computes a "blurred" median
   (all NFPM interactions) only as a sanity signal.

## Disclaimer

This project's goal is to apply Deep RL to a real, financially-grounded
environment, not to produce a profitable trading strategy. It is a research
PoC: the simulator has known limitations (see above), the agent is not
validated for live capital, and nothing here constitutes financial advice.
Any commercial or real-money use of this code, including deploying the
trained agent to manage a real Uniswap V3 position, is done entirely at
your own risk. The author assumes no responsibility for financial losses
resulting from such use.
