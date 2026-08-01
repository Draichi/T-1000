# Experiment sweep leaderboard

Generated 2026-08-01 from experiments/results/ (9 variants x 5 holdout windows). Ranked by mean holdout Sharpe (risk-adjusted), ties by total P&L. `~ baseline` = paired |t| < 2 vs BOTH baselines: treat as noise, not edge.

| # | Variant | Mean Sharpe | Total P&L | vs full-range | vs HODL 50/50 | Wins | Worst DD | Signal |
|---|---------|------------:|----------:|--------------:|--------------:|-----:|---------:|--------|
| 1 | shortlook | -0.30 | $-405 | $+4,447 (t=1.6) | $-111 (t=-0.0) | 3/5 | -24.8% | ~ baseline |
| 2 | benchrel_gas3x | -0.44 | $-3,423 | $+2,394 (t=1.3) | $-3,130 (t=-1.4) | 4/5 | -36.9% | ~ baseline |
| 3 | fixedsnaps | -0.71 | $-1,735 | $+3,117 (t=1.2) | $-1,442 (t=-0.5) | 4/5 | -19.4% | ~ baseline |
| 4 | gas3x | -0.91 | $-3,399 | $+2,418 (t=1.1) | $-3,105 (t=-1.0) | 4/5 | -36.3% | ~ baseline |
| 5 | batch256 | -1.21 | $-4,072 | $+780 (t=0.4) | $-3,779 (t=-2.1) | 3/5 | -31.3% | distinct |
| 6 | gas_quarter | -1.26 | $-2,718 | $+852 (t=0.5) | $-2,425 (t=-1.3) | 3/5 | -24.1% | ~ baseline |
| 7 | wide | -1.61 | $-4,820 | $-1,928 (t=-0.8) | $-4,527 (t=-3.0) | 1/5 | -29.2% | distinct |
| 8 | narrow | -3.11 | $-6,133 | $-869 (t=-0.4) | $-5,840 (t=-2.7) | 2/5 | -32.1% | distinct |
| 9 | benchrel_b64 | -5.19 | $-984 | $+3,868 (t=1.1) | $-690 (t=-0.2) | 4/5 | -9.4% | ~ baseline |

## Statistically indistinguishable from baseline

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

## Proposed README diff for the winner (CAUTION: winner is itself ~ baseline)

```diff
--- a/README.md
+++ b/README.md
@@ results section: append after the existing results table @@
+## Best sweep variant: shortlook
+
+Selected from a 9-variant sweep (see `experiments/LEADERBOARD.md`), holdout = 5 unseen 30-day windows (Jan-May 2025):
+
+| Metric | Value |
+|---|---|
+| Config overrides | `{"vol_lookback_short_hours": 12, "vol_lookback_long_hours": 72}` |
+| Total holdout P&L | $-405 (baseline $-4,852, HODL $-293) |
+| Windows beating baseline | 3/5 |
+| Mean Sharpe / worst drawdown | -0.30 / -24.8% |
```
