# How it works

This document explains, step by step, how `T-1000` turns raw
blockchain data into a trained RL agent and, from scratch, how Uniswap V3
fee accounting works, since the whole project only makes sense once that
mechanism is understood.

No prior finance or DeFi background is assumed.

## 1. What Uniswap actually is

Imagine an automated currency exchange booth: instead of an employee
deciding the price, there's a public vault holding two kinds of token (say,
ETH and USDC). Anyone can trade one for the other directly against that
vault, and the price moves on its own as the vault's balance shifts (more
people buying ETH → less ETH left in the vault → ETH gets more expensive).
That's an AMM (automated market maker).

Whoever fills that vault with money (the "liquidity providers", or LPs)
earns a small fee (e.g. 0.05%) every time someone trades against the
vault, proportional to how much money each of them put in.

## 2. The problem Uniswap V3 solves

In the older version (V2), your money was spread across *every* possible
price, from zero to infinity, most of it was never actually used, because
the real price of ETH always stays in a reasonable range (say,
$2,000-$4,000), not at $0.0001 or $1 billion.

V3 lets you pick a **price range** where your money is active, e.g. "I
only want to provide liquidity between $2,500 and $3,500 per ETH". Outside
that range, your money simply doesn't participate in trades and earns no
fee. This is "concentrated liquidity": more capital-efficient, but it
requires picking the right range and that choice is exactly what the RL
agent in this project is learning to make.

The entire price axis is discretized into tiny steps called **ticks**
(think of them as very fine ruler markings). Your range is always "from
tick X to tick Y".

## 3. The accounting problem the `FeeEngine` solves

Now the hard part: there are thousands of LPs, each with a different
range, overlapping in complicated ways. Every time someone trades, the
price moves a little, and only the LPs whose range contains the price at
that instant should get a slice of that trade's fee.

Recomputing "who was in range, how much did each of them have" for every
LP, on every single trade, would be astronomically expensive. Uniswap V3
solves this with an elegant trick and this is the trick `fee_engine.py`
reimplements.

### The shared water-meter analogy

Picture a water pipe (the "total fees accumulated per unit of money
invested") that only ever goes up, never down. Every time a trade happens,
if your range was "active" (contained the price at that moment), the meter
ticks up a little, proportional to the fee charged divided by the total
active money at that moment. To know how much *you* earned, you just need
the meter reading from when you entered and the reading now the
difference, multiplied by how much you invested, is your fee. Nobody needs
to recompute anything per LP on every trade; the meter does the heavy
lifting once, globally.

This is `fee_growth_global0_x128` / `fee_growth_global1_x128` in the code
(`src/t1000/fee_engine.py`) a counter that only grows (one per
token, since a pool has two).

### Isolating "just what happened inside my range"

The global meter sums up everything, at every price. To know how much
accrued *only inside* your specific range (`tick_lower` to `tick_upper`),
Uniswap keeps, at every tick boundary, a second meter called
`fee_growth_outside` "how much has the global meter accumulated on the
far side of this boundary, looking away from the current price".

With these two kinds of meter (global, and the "outside" one at each
boundary), you can compute your range's share by subtraction: `inside my
range = global - what accumulated below my range - what accumulated above
my range`. It's the same logic as "area under a curve between two points =
total area minus the leftover ends" - just applied to accumulated fees
instead of area. This is the `fee_growth_inside()` method
(`fee_engine.py`), and it's the exact formula the real Uniswap contract
uses.

## 4. What the `FeeEngine` actually does

`FeeEngine` is a simulator that **replays the pool's real history** (every
`Swap`, `Mint`: someone adding money to a range and `Burn`: someone
withdrawing money) event by event, in the exact order they happened on
chain, updating those meters exactly like the real contract would:

1. **On a trade (`Swap`)**: the price moves from one tick to another. If
   that movement crosses other LPs' range boundaries, the engine walks
   through each crossed segment (`_walk_segments`), computing how much fee
   was generated in that small piece of the move and updating the meters
   just like the water pipe that only goes up. Crucially, it **does not
   invent** the resulting price, it uses the real price that happened
   on-chain, only recomputing the fee meters on top of that. This removes
   an entire source of error (no need to simulate how the market would
   react to a trade).
2. **On a deposit or withdrawal (`Mint`/`Burn`)**: updates how much money is
   "active" at each tick boundary.
3. **"Shadow ticks": the trick that makes RL possible**: the RL agent may
   want to try a price range that *never actually existed* in history (no
   real LP used exactly those boundaries). The engine allows marking those
   hypothetical boundaries anyway (`open_shadow_position`), just so it can
   read the "outside" meter there without affecting the pool's real
   accounting. It's like hanging an extra water meter on a pipe that
   already exists, just to read values at a point nobody had instrumented
   before, without disturbing the real flow.

### Why this is easy to get wrong

If this accounting is implemented incorrectly for example, forgetting to
update a boundary meter when crossing a tick, or applying the fee at the
wrong point in the sequence, the simulator will claim that some price
range earned fees it would never actually earn in reality. The RL agent
would then "learn" to exploit that accounting bug instead of learning the
real strategy of where to place liquidity. That's why the project has a
validation step (`scripts/validate.py`) comparing the numbers `FeeEngine`
produces against what real LP positions actually collected on-chain
(`Collect - Burn`): matching to within 0.000001% on clean cases. That's
the guarantee that the "meter" the agent sees is the same meter the real
Uniswap contract uses, not an approximation.

## 5. The full pipeline, step by step

### Step 1 - Ingest: BigQuery → raw events (`scripts/fetch_data.py`)

Fetches `logs` and `blocks` for the ETH/USDC 0.05% pool directly from
BigQuery's public Ethereum mainnet dataset, plus
`NonfungiblePositionManager` transactions. No need to run an RPC node,
the `Swap`/`Mint`/`Burn`/`Collect` event data is already encoded in the log
topics/data.

### Step 2 - Decode and reconstruct fee accounting (`scripts/build_dataset.py` → `fee_engine.py`)

This is the technical core of the project, described in detail above:
decoding the raw log events and replaying them through `FeeEngine` to
reconstruct tick-level liquidity and fee-growth state.

`src/t1000/il.py` computes position value via `amounts_for_liquidity`
(the V3 curve math) instead of the classic closed-form formula
`2*sqrt(r)/(1+r) - 1`, which only holds for a full-range position, needed
because the agent can end up outside its range.

### Step 3 - Snapshots for fast reset (`src/t1000/snapshot.py`)

Without this, every `env.reset()` would have to replay the pool's entire
history from genesis, infeasible for training with millions of steps.
`precompute_snapshots()` serializes the `FeeEngine` (pickle+gzip) at a
regular cadence; `env.reset()` loads the nearest snapshot at or before the
sampled start time and only replays the short remainder.

### Step 4 - Validate against reality (`scripts/validate.py`)

Selects real positions with an unambiguous `(owner, tickLower, tickUpper)`
mapping, replays `FeeEngine` over the same window, and compares simulated
fees (via `feeGrowthInside`) against real `Collect - Burn`. Result:
0.000001% divergence on short-duration positions. This turns the simulator
from "looks reasonable" into "numerically proven correct" within the
tested domain.

### Step 5 - RL environment (`src/t1000/env.py`)

On every `step()`:

1. Apply all real events (`Swap`/`Mint`/`Burn`) that occurred during the
   step's time window to the `FeeEngine` — the market "happens"
   independently of the agent's action.
2. Accrue the agent's position's unclaimed fees via `feeGrowthInside`.
3. Apply the chosen action — `HOLD`/`COLLECT`/rebalance/`EXIT_TO_CASH` —
   debiting gas in USD computed from that block's real
   `base_fee_per_gas` (`src/t1000/gas_model.py`); if there isn't
   enough cash, the action becomes a no-op (mirrors an on-chain revert).
4. `reward = Δportfolio_value_usd / initial_notional`, where
   `portfolio_value = cash + position_value (mark-to-market via il.py) +
   unclaimed_fees` — fees, impermanent loss, and gas are all already baked
   into that single number.

### Step 6 — Observation (`src/t1000/observations.py`)

A vector of stationary features, not raw price: log-return relative to the
episode's start, realized volatility (24h/7d), volume z-score, a
**10-bucket liquidity histogram around the current tick** (gives the agent
visibility into local market depth), the position's relative range,
normalized unclaimed fees, fraction of time since the last rebalance, and
the current gas percentile.

### Step 7 — Training (`scripts/train.py`, PPO via Stable-Baselines3)

`Discrete(8)` action space → `MlpPolicy` (128×128). Checkpointing with
automatic resume (`reset_num_timesteps=False`) — designed to survive
spot-instance preemption. Per-episode metrics (P&L, Sharpe, drawdown,
gas-adjusted APR) are logged to JSONL.

### Step 8 — Backtest (`scripts/backtest.py`)

Runs the trained checkpoint and a baseline (fixed full-range, rebalances
only when the price leaves the range) through the **same environment
mechanics**, guaranteeing a fair comparison (same gas costs, same fee
engine).

## 6. The action space

`Discrete(8)` (`src/t1000/actions.py`), each index with a fixed,
tested meaning:

| Action | Effect |
|---|---|
| `HOLD` | do nothing |
| `COLLECT` | claim accrued fees to cash |
| `REBALANCE_NARROW` | close and reopen at ±2% around current tick |
| `REBALANCE_MEDIUM` | close and reopen at ±5% |
| `REBALANCE_WIDE` | close and reopen at ±10% |
| `SHIFT_UP` | same width, recentered above current tick |
| `SHIFT_DOWN` | same width, recentered below current tick |
| `EXIT_TO_CASH` | close the position, hold cash until the next rebalance |

Each rebalance/shift/exit action carries the gas cost of the underlying
contract calls it implies (`burn`, `collect`, `mint`), estimated from that
block's real `base_fee_per_gas`.

## 7. Why this matters

The core technical differentiator here isn't the RL algorithm (PPO is a
standard choice) — it's that **the simulator was built to be correct, and
that correctness was proven, not assumed**. Most RL-for-DeFi/AMM projects
treat the environment as an implementation detail and train against an
unvalidated approximation. Here, the thing the agent is optimizing — fees
from a concentrated-liquidity AMM — only exists because the contract's
tick/fee-growth math was replicated exactly; any error in that layer would
silently propagate into a useless policy (an agent "learning" to exploit a
simulator bug instead of the real mechanics of Uniswap V3). The validation
step against real `Collect - Burn` data closes that trust loop, which is
exactly the step that's usually missing in this kind of project.

## 8. Known limitations

See the [README](../README.md#known-limitations-read-before-interpreting-the-results)
for the full list: short bootstrap window, no market-impact modeling, no
guarantee of beating the baseline, and approximate gas calibration.
