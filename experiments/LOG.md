# T-1000 experiment log

# Round 1 — post-fix retrains: gamma sweep (2026-07-28)

## Context

Three P0 bugs were fixed on 2026-07-23 (see `TODO.md`): volatility features
saturated at 1.0 (env fed raw prices where `realized_vol` expects log
returns), snapshot boundaries dropping same-block events, and cash
evaporating when computed liquidity was 0. The previous best checkpoint
(`run_14mo_lowent`, backtest P&L +$1,574 / Sharpe 4.55 on the old env) was
trained pre-fix, so two fresh 2M-step runs were trained on the fixed env to
(a) re-establish a baseline and (b) test one hypothesis.

**Caveat — snapshots not regenerated.** `data/processed_14mo` snapshots are
dated Jul 21, before the `snapshot.py` fix (Jul 23). Both runs therefore
trained/evaluated on snapshots produced by the old cutting logic (episode
initial states carry slightly wrong `tick_map` liquidity at snapshot
boundaries). The volatility fix and the zero-liquidity guard were active
(env-side). Model-vs-model comparisons below are internally consistent —
both saw identical data — but absolute numbers should be re-validated after
regenerating snapshots. The TODO retrain gate is NOT closed yet.

## Runs

| run | config | delta vs default |
|---|---|---|
| `run_14mo_lowent_posfix` | `configs/ppo_default.yaml` | none (γ=0.99, ent_coef=0.001) |
| `run_14mo_gamma999` | `configs/ppo_gamma999.yaml` | **γ=0.999** (episode-length credit horizon: with 1h steps, γ=0.99 ≈ 4-day horizon; the economic thesis of a rebalance — pay gas now, earn fees for weeks — needs a longer one) |

Both: 2M timesteps, train window 2024-05-01 → 2025-01-01, 8 × DummyVecEnv,
720h episodes, $10k notional, LR 3e-4 → 1e-5 linear, CPU, ~6h wall-clock
each (run in parallel, 1 core each).

## Training metrics (in-sample, 100-episode rolling means at 2M steps)

| metric | posfix (γ=0.99) | gamma999 (γ=0.999) |
|---|---|---|
| ep P&L | **$1,059** | $843 |
| ep Sharpe | **3.07** | 2.37 |
| max drawdown | **−9.6%** | −12.8% |
| rebalances/ep | 208 | 278 |
| gas/ep | $776 | $803 |
| explained_variance | 0.83 | 0.98 |

Notes:
- gamma999's `ep_rew_mean` was still climbing at 2M steps (+0.035 → +0.072 →
  +0.099 over the last three chunks) while posfix had plateaued — extending
  gamma999 is likely to help.
- The higher explained_variance under γ=0.999 is largely mechanical: with
  γ=0.999 and λ=0.95 the GAE target is dominated by the bootstrapped value
  term (γ²⁰ ≈ 0.98), so the critic partly predicts its own outputs. Not
  evidence of a better critic.
- `policy_gradient_loss` traced the expected U shape in both runs (small →
  large-magnitude mid-training → ~0 as LR decays and advantages shrink);
  final approx_kl ≈ 0.002, clip_fraction ≈ 0.008 — healthy convergence.

## Holdout backtests (2025-01 → 2025-06, five 720h monthly windows)

Each window = one 720-step episode vs the full-range LP baseline, same env
mechanics for both. `scripts/backtest.py`, seed 0, deterministic policy.

| window | baseline | posfix | diff | gamma999 | diff |
|---|---|---|---|---|---|
| 2025-01 | −$1,030 | −$2,018 | −$988 | **+$97** | **+$1,128** |
| 2025-02 | −$570 | −$351 | +$219 | **+$962** | **+$1,532** |
| 2025-03 | +$1,550 | +$16 | −$1,535 | **+$1,570** | **+$20** |
| 2025-04 | +$1,953 | +$456 | −$1,497 | **+$2,235** | **+$283** |
| 2025-05 | +$730 | −$58 | −$788 | −$981 | −$1,710 |
| **total** | **+$2,633** | **−$1,956** | | **+$3,885** | |

- **gamma999 beats the baseline in 4/5 windows and in total (+$3,885 vs
  +$2,633).** Its edge is concentrated in down months (Jan, Feb: capital
  preservation — max drawdown −7.6% vs baseline −18.8% in Jan); in up
  months (Mar, Apr) it roughly matches the baseline.
- **posfix inverted: best in-sample, worst out-of-sample** (1/5 wins,
  −$1,956 total). Classic overfit. Behaviorally it holds positions through
  drawdowns (181–232 HOLDs/window vs gamma999's 87–169) and chases falling
  prices with SHIFT_DOWN.
- **gamma999's failure mode is May 2025** (strong ETH rally): −$981 vs
  baseline +$730, with its highest gas spend ($953) and −22% drawdown. Its
  defensive habits (learned on a mostly sideways/down train window) misread
  the rally — repeatedly out of range / re-entering late, paying gas while
  the passive full-range baseline just rode the trend. This is also the
  regime where reward-as-ΔMTM gives the least useful signal (TODO P1: ETH
  beta dominates; benchmark-relative reward should specifically improve
  regime discrimination here).

## Conclusions

1. γ=0.999 is the better prior for this problem. The longer credit horizon
   produced a policy whose out-of-sample character (defensive, wide ranges,
   decisive exits) survives regime change better than γ=0.99's.
2. In-sample rollout metrics are not a model-selection signal here — the
   ranking inverted out-of-sample. Monthly-window holdout sweeps are cheap
   (~1 min each) and should be the default gate.
3. Both runs still sit on stale snapshots; nothing here closes the TODO
   retrain gate.

## Next steps (ordered)

1. **Regenerate snapshots** with the fixed `precompute_snapshots`
   (`scripts/build_dataset.py` over the existing raw parquet — no BigQuery
   refetch needed), then retrain gamma999 on clean data. This closes the
   P0/retrain gate; the current gamma999 numbers become the reference to
   beat.
2. **Extend gamma999** (resume with `--total-timesteps 3000000`+ and a
   lowered `learning_rate_start` in the yaml, e.g. 5e-5, per the resume
   note in `train.py`) — its learning curve had not plateaued.
3. **Attack the May failure mode = TODO P1 benchmark-relative reward**
   (subtract passive-HODL value change via `il.py`). Expected effect:
   removes the ETH-beta gradient that lets a policy look good by direction
   alone, and directly penalizes sitting out a rally relative to holding —
   the exact May error.
4. Re-run the 5-window sweep after each change; add 2+ seeds per config to
   separate signal from initialization luck.
5. When a config beats the baseline in ≥4/5 windows *including* an up-month,
   promote it to the deployment package (TODO Phase 1) as `agent_id` v1.

# Round 2 — clean data, batch size, reward shaping + config sweep (2026-07-28, in flight)

## Design

Snapshots were regenerated with the fixed cutting logic into
`data/processed_14mo_fixed` (from the existing raw 14mo parquet, no
refetch), closing round 1's stale-snapshot caveat. Three 2M-step runs were
launched in parallel on it, same train window as round 1
(2024-05-01 → 2025-01-01), each isolating one variable:

| run | config | isolates |
|---|---|---|
| `run_14mo_gamma999_fixedsnaps` | `configs/ppo_gamma999.yaml` | control: round-1 winner on clean data |
| `run_14mo_gamma999_batch256` | `configs/ppo_gamma999_batch256.yaml` | batch_size 64 → 256 |
| `run_14mo_gamma999_benchrel` | `configs/ppo_gamma999_benchrel.yaml` | `reward_mode: benchmark_relative` — reward = LP alpha (P&L minus start-of-step WETH exposure × price change); targets round 1's May-2025 rally failure |

Wall-clock note: three parallel runs contend with each other (~85k steps/h
each, ~20h+ per run, vs ~6h for round 1's two runs). Note for comparisons:
benchrel's `ep_rew_mean` is on the alpha scale and not comparable to the
absolute-reward runs — compare via `rollout/ep_pnl_usd_mean` and holdout
backtest P&L.

## Config sweep (queued behind the live runs)

`experiments/manifest.yaml` defines 6 further variants: `width_scale`
(narrow 0.5×, wide 2×), `gas_multiplier` (3×, 0.25×), shorter volatility
lookbacks (12h/72h), and a benchrel × gas3x interaction arm. Base config =
gamma999 + **batch_size 256** — adopted from the live A/B's stronger
training curves *before* holdout confirmation; if the A/B inverts on
holdout (as posfix did in round 1), the sweep should be re-run with 64.
The sweep's original control and benchrel arms were dropped as duplicates
of the live runs; those enter the leaderboard via
`experiments/import_run.py` (holdout backtests only, no retraining).

Pipeline (automated end-to-end): live trainings finish → import the 3 live
runs → `run_sweep.py --max-parallel 4` (~12h; per-variant worktrees, hard
preconditions: dataset ≥ 14 months, `data/*` git-ignored) →
`aggregate_leaderboard.py` → `experiments/LEADERBOARD.md`, ranked by mean
holdout Sharpe with paired t-tests vs the full-range and HODL 50/50
baselines (|t| < 2 over 5 windows is flagged as noise).

## Selection gate (unchanged from round 1)

Same five 720h holdout windows (2025-01 … 2025-05). Promote only a config
that beats the full-range baseline in ≥4/5 windows including an up-month.

Results — live runs (2026-07-30):

| Arm | Batch | Reward | Mean Sharpe | Total P&L | vs baseline | Wins | Worst DD |
|-----|------:|--------|------------:|----------:|------------:|-----:|---------:|
| fixedsnaps | 64 | absolute | -0.71 | -$1,735 | +$3,117 (t=1.2) | 4/5 | -19.4% |
| batch256 | 256 | absolute | -1.21 | -$4,072 | +$780 (t=0.4) | 3/5 | -31.3% |
| benchrel_b64 | 64 | benchmark-relative | -5.19 | -$984 | +$3,868 (t=1.1) | 4/5 | -9.4% |

Full-range baseline total: -$4,852; HODL 50/50 total: -$293 (Jan-May 2025
was a down market; every arm lost money in absolute terms).

1. **The batch A/B inverted on holdout**, as posfix did in round 1: batch
   256 had the stronger training curves but batch 64 (fixedsnaps) beat it
   on every holdout metric. Per the rule pre-registered in
   `manifest.yaml`, the config sweep was relaunched with `batch_size: 64`;
   fixedsnaps is now the sweep's control/anchor arm.
2. **benchmark_relative protects capital**: smallest loss (-$984), by far
   the best worst-case drawdown (-9.4%), and the only arm to beat HODL
   50/50 in 4/5 windows. But it repeats the round-1 rally failure mode,
   losing the May up-month by -$1,457 (an alpha-only reward gives no
   credit for beta, so no incentive to hold exposure into a rally). Its
   very negative Sharpe reflects a low-variance, slightly-bleeding equity
   path rather than large losses.
3. **Gate: no promotion.** fixedsnaps formally meets the 4/5-with-up-month
   rule, but the May win is +$33 and the paired t vs baseline is 1.2,
   inside noise for 5 windows. benchrel_b64 fails the up-month clause.

Config-sweep results (2026-08-01) -- 6 variants, 2M steps each, batch 64,
seed 0, evaluated on the same 5 fixed holdout windows (full table in
LEADERBOARD.md; totals in USD over the 5 windows):

| Variant | Sharpe | P&L | vs own baseline | Wins | Worst DD |
|---|---:|---:|---:|---:|---:|
| shortlook | -0.30 | -405 | +4,447 (t=1.6) | 3/5 | -24.8% |
| benchrel_gas3x | -0.44 | -3,423 | +2,394 (t=1.3) | 4/5 | -36.9% |
| gas3x | -0.91 | -3,399 | +2,418 (t=1.1) | 4/5 | -36.3% |
| gas_quarter | -1.26 | -2,718 | +852 (t=0.5) | 3/5 | -24.1% |
| wide | -1.61 | -4,820 | -1,928 (t=-0.8) | 1/5 | -29.2% |
| narrow | -3.11 | -6,133 | -869 (t=-0.4) | 2/5 | -32.1% |

Reading caveat: the baseline policy opens REBALANCE_WIDE bands, which scale
with `width_scale`, and `gas_multiplier` applies to the baseline too -- each
arm is compared against a baseline living in the same modified world.
"vs baseline" deltas are therefore not comparable across arms; absolute P&L
is comparable only where env economics are unchanged (shortlook exactly
matches the anchor's economics).

Findings:

4. **shortlook is the sweep winner and the round's headline.** Faster
   volatility features (12h/3d instead of 24h/7d) produced the best
   absolute P&L of all 9 leaderboard arms (-$405 vs anchor fixedsnaps
   -$1,735 -- a ~$1,330 improvement from an observation-only change) and
   the best Sharpe (-0.30). It recovers ~92% of the passive baseline's
   bleed and is statistically indistinguishable from HODL 50/50
   (t=-0.0), i.e. it reaches the "don't LP at all" frontier. It also won
   the May up-month vs baseline (+$1,628) but takes only 3/5 windows, so
   it fails the gate's win-count clause. Supports the perception
   hypothesis: stale volatility features were a binding constraint.
5. **Both width arms lose -- the default widths are near-optimal.**
   narrow (-$6,133) is the worst arm on the board: doubled fee density
   did not pay for the extra IL, out-of-range time, and rebalance gas.
   wide (-$4,820) even loses to its own passive baseline in 4/5 windows
   and is significantly worse than HODL (t=-3.0): with +/-4%/10%/20%
   bands the agent's actions barely differ from the baseline's, so gas
   and worse fee density dominate. Changing width in either direction
   hurts.
6. **Gas pressure shapes behavior but does not create edge.** gas3x beats
   its (3x-cost) baseline in 4/5 windows -- trained selectivity survives
   expensive-gas worlds -- but still loses the May up-month and lands at
   -$3,399. gas_quarter shows near-free rebalancing does NOT unlock
   hidden performance (-$2,718, 3/5): the current policy's caution is not
   primarily gas avoidance, and the binding constraint is policy/signal
   quality, not friction.
7. **benchrel_gas3x fixes benchrel's rally failure at a heavy price.**
   The interaction arm wins May vs baseline (+$180, where benchrel_b64
   lost it by -$1,457) and takes 4/5 windows incl. the up-month --
   formally the only gate-passing arm this round. But t=1.3 is inside
   noise, total P&L (-$3,423) is far worse than benchrel_b64's -$984,
   and worst DD balloons to -36.9% (vs benchrel_b64's -9.4%): the 3x gas
   pressure traded benchrel's capital protection for baseline-relative
   wins. No promotion.
8. **Gate: no promotion (round 2 closes).** benchrel_gas3x passes the
   formal clauses but is inside noise and strictly dominated on absolute
   metrics; shortlook has the best absolute numbers but only 3/5 wins.
   Every arm remains at or below the HODL frontier: range management
   alone did not turn P&L positive in this (mostly down) regime.

Round-2 conclusion and next steps: the cheapest lever found is
observation quality (shortlook), not reward shaping, width, or gas.
Natural round-3 candidates, in order: (a) multi-seed rerun of shortlook
to de-noise the headline result; (b) shortlook x benchmark_relative
interaction arm (best perception + capital-protecting reward); (c) fresh
holdout windows (2025-06 onward) to break the 5-window noise floor;
(d) if positive absolute P&L stays out of reach, the game-changing
extensions documented earlier (delta hedge via perps, explicit
out-of-pool regime sitting) rather than more knob-turning.
