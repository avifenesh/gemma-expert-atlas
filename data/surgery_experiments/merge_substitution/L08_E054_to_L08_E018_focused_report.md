# L08.E054 replaced by L08.E018 focused guard

Generated: 2026-06-20T20:36:22.896752+00:00

Baseline: `data/surgery_experiments/merge_substitution/evals/baseline_focused/20260620T_baseline_focused/results.json`
Variant: `data/surgery_experiments/merge_substitution/evals/L08_E054_to_L08_E018_focused/20260620T_L08_E054_to_E018_focused/results.json`

## Summary

- balanced_reasoning_off: score 0.5833 -> 0.6042 (+0.0208), decode 145.87 -> 145.01 tok/s
- balanced_reasoning_on: score 0.4792 -> 0.4792 (+0.0000), decode 145.75 -> 144.51 tok/s

## Category Deltas

| Config | Category | Base | Variant | Delta | +/- tasks |
|---|---|---:|---:|---:|---:|
| balanced_reasoning_off | instruction_following | 0.458 | 0.542 | +0.083 | +2 / -0 |
| balanced_reasoning_off | personalization_memory | 0.708 | 0.667 | -0.042 | +1 / -2 |
| balanced_reasoning_on | instruction_following | 0.333 | 0.375 | +0.042 | +2 / -1 |
| balanced_reasoning_on | personalization_memory | 0.625 | 0.583 | -0.042 | +0 / -1 |

## Negative Task Deltas

| Config | Task | Category | Base | Variant | Delta |
|---|---|---|---:|---:|---:|
| balanced_reasoning_off | personalization_memory_006 | personalization_memory | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | personalization_memory_007 | personalization_memory | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_on | personalization_memory_001 | personalization_memory | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_on | instruction_following_006 | instruction_following | 0.333 | 0.000 | -0.333 |

## Positive Task Deltas

| Config | Task | Category | Base | Variant | Delta |
|---|---|---|---:|---:|---:|
| balanced_reasoning_off | instruction_following_004 | instruction_following | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_off | instruction_following_007 | instruction_following | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_off | personalization_memory_008 | personalization_memory | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_on | instruction_following_005 | instruction_following | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_on | instruction_following_003 | instruction_following | 0.000 | 0.333 | +0.333 |
