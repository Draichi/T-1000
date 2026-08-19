# Experiment sweep leaderboard

Generated 2026-08-19 from experiments/results/ (9 variants x 5 holdout windows). Ranked by mean holdout Sharpe (risk-adjusted), ties by total P&L.

**Promotion gate (all three, vs HODL 50/50):** beat HODL in 4/5 windows, *including* the up-month (2025-05-01), at paired t >= 2. The reference is HODL, not the full-range LP baseline -- see `experiments/round4_heuristic_sweep.md` for why the old reference was too weak to promote against. The `vs full-range` column is kept for continuity with rounds 1-3 only.

| # | Variant | Mean Sharpe | Total P&L | vs HODL 50/50 | Wins vs HODL | Up-month | vs full-range | Worst DD | Gate |
|---|---------|------------:|----------:|--------------:|-------------:|:--------:|--------------:|---------:|------|
| 1 | shortlook | -0.30 | $-405 | $-111 (t=-0.0) | 3/5 | yes | $+4,447 (t=1.6) | -24.8% | 3/5 wins, t=-0.0 |
| 2 | benchrel_gas3x | -0.44 | $-3,423 | $-3,130 (t=-1.4) | 1/5 | no | $+2,394 (t=1.3) | -36.9% | 1/5 wins, loses up-month, t=-1.4 |
| 3 | fixedsnaps | -0.71 | $-1,735 | $-1,442 (t=-0.5) | 2/5 | no | $+3,117 (t=1.2) | -19.4% | 2/5 wins, loses up-month, t=-0.5 |
| 4 | gas3x | -0.91 | $-3,399 | $-3,105 (t=-1.0) | 2/5 | no | $+2,418 (t=1.1) | -36.3% | 2/5 wins, loses up-month, t=-1.0 |
| 5 | batch256 | -1.21 | $-4,072 | $-3,779 (t=-2.1) | 0/5 | no | $+780 (t=0.4) | -31.3% | 0/5 wins, loses up-month, t=-2.1 |
| 6 | gas_quarter | -1.26 | $-2,718 | $-2,425 (t=-1.3) | 2/5 | no | $+852 (t=0.5) | -24.1% | 2/5 wins, loses up-month, t=-1.3 |
| 7 | wide | -1.61 | $-4,820 | $-4,527 (t=-3.0) | 1/5 | no | $-1,928 (t=-0.8) | -29.2% | 1/5 wins, loses up-month, t=-3.0 |
| 8 | narrow | -3.11 | $-6,133 | $-5,840 (t=-2.7) | 1/5 | no | $-869 (t=-0.4) | -32.1% | 1/5 wins, loses up-month, t=-2.7 |
| 9 | benchrel_b64 | -5.19 | $-984 | $-690 (t=-0.2) | 4/5 | no | $+3,868 (t=1.1) | -9.4% | loses up-month, t=-0.2 |

## Gate result

**No variant clears the gate.** 

## Statistically indistinguishable from HODL 50/50

- shortlook
- benchrel_gas3x
- fixedsnaps
- gas3x
- gas_quarter
- benchrel_b64

With only 5 paired windows, these deltas are within noise; do not promote them on P&L alone.

## Per-variant cards

- [shortlook](results/shortlook/card.md) -- overrides `{"vol_lookback_short_hours": 12, "vol_lookback_long_hours": 72}`
- [benchrel_gas3x](results/benchrel_gas3x/card.md) -- overrides `{"reward_mode": "benchmark_relative", "gas_multiplier": 3.0}`
- [fixedsnaps](results/fixedsnaps/card.md) -- overrides `{"imported_from": "checkpoints/run_14mo_gamma999_fixedsnaps", "batch_size": 64, "reward_mode": "absolute"}`
- [gas3x](results/gas3x/card.md) -- overrides `{"gas_multiplier": 3.0}`
- [batch256](results/batch256/card.md) -- overrides `{"imported_from": "checkpoints/run_14mo_gamma999_batch256", "batch_size": 256, "reward_mode": "absolute"}`
- [gas_quarter](results/gas_quarter/card.md) -- overrides `{"gas_multiplier": 0.25}`
- [wide](results/wide/card.md) -- overrides `{"width_scale": 2.0}`
- [narrow](results/narrow/card.md) -- overrides `{"width_scale": 0.5}`
- [benchrel_b64](results/benchrel_b64/card.md) -- overrides `{"imported_from": "checkpoints/run_14mo_gamma999_benchrel", "batch_size": 64, "reward_mode": "benchmark_relative"}`

## No README diff proposed

`shortlook` only tops the Sharpe ranking; it fails the gate (3/5 wins, t=-0.0). Nothing here is promotable, so no README snippet is generated.
