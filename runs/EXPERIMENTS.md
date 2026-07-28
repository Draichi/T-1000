# Experiment log — post-fix retrains: gamma sweep (2026-07-28)

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
