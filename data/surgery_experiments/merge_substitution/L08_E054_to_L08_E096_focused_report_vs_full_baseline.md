# L08.E054 replaced by L08.E096 focused guard vs full baseline

Generated: 2026-06-20T20:30:26.761298+00:00

Baseline: `data/personal_agent_bank/runs/20260620T170017Z/results.json`
Variant: `data/surgery_experiments/merge_substitution/evals/L08_E054_to_L08_E096_focused/20260620T_L08_E054_to_E096_focused/results.json`

## Summary

- balanced_reasoning_off: score 0.5833 -> 0.4583 (-0.1250), decode 142.04 -> 145.54 tok/s
- balanced_reasoning_on: score 0.4792 -> 0.5000 (+0.0208), decode 143.94 -> 145.33 tok/s

## Category Deltas

| Config | Category | Base | Variant | Delta | +/- tasks |
|---|---|---:|---:|---:|---:|
| balanced_reasoning_off | instruction_following | 0.458 | 0.292 | -0.167 | +1 / -4 |
| balanced_reasoning_off | personalization_memory | 0.708 | 0.625 | -0.083 | +1 / -3 |
| balanced_reasoning_on | instruction_following | 0.333 | 0.375 | +0.042 | +1 / -0 |
| balanced_reasoning_on | personalization_memory | 0.625 | 0.625 | -0.000 | +2 / -2 |

## Negative Task Deltas

| Config | Task | Category | Base | Variant | Delta |
|---|---|---|---:|---:|---:|
| balanced_reasoning_off | instruction_following_008 | instruction_following | 0.667 | 0.000 | -0.667 |
| balanced_reasoning_off | personalization_memory_003 | personalization_memory | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | personalization_memory_006 | personalization_memory | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | personalization_memory_007 | personalization_memory | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | instruction_following_001 | instruction_following | 0.333 | 0.000 | -0.333 |
| balanced_reasoning_off | instruction_following_004 | instruction_following | 0.333 | 0.000 | -0.333 |
| balanced_reasoning_off | instruction_following_007 | instruction_following | 0.333 | 0.000 | -0.333 |
| balanced_reasoning_on | personalization_memory_001 | personalization_memory | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_on | personalization_memory_003 | personalization_memory | 1.000 | 0.667 | -0.333 |

## Positive Task Deltas

| Config | Task | Category | Base | Variant | Delta |
|---|---|---|---:|---:|---:|
| balanced_reasoning_off | instruction_following_002 | instruction_following | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_off | personalization_memory_004 | personalization_memory | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_on | personalization_memory_006 | personalization_memory | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_on | instruction_following_003 | instruction_following | 0.000 | 0.333 | +0.333 |
| balanced_reasoning_on | personalization_memory_008 | personalization_memory | 0.333 | 0.667 | +0.333 |
