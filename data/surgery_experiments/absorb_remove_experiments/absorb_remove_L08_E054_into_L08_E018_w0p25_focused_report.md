# Absorb L08.E054 into L08.E018 (w=0.25) then remove, focused guard

Generated: 2026-08-04T22:15:24.330293+00:00

Baseline: `data/surgery_experiments/blend_experiments/evals/local_base_focused/20260621T_local_base_focused/results.json`
Variant: `data/surgery_experiments/absorb_remove_experiments/evals/absorb_remove_L08_E054_into_L08_E018_w0p25_focused/absorb_remove_L08_E054_into_L08_E018_w0p25_focused_absorb_remove/results.json`

## Summary

- balanced_reasoning_off: score 0.8250 -> 0.8417 (+0.0167), decode 141.59 -> 142.73 tok/s
- balanced_reasoning_on: score 0.8250 -> 0.8417 (+0.0167), decode 142.20 -> 146.61 tok/s

## Category Deltas

| Config | Category | Base | Variant | Delta | +/- tasks |
|---|---|---:|---:|---:|---:|
| balanced_reasoning_off | coding_agent | 0.708 | 0.667 | -0.042 | +1 / -2 |
| balanced_reasoning_off | instruction_following | 0.917 | 0.833 | -0.083 | +1 / -2 |
| balanced_reasoning_off | personalization_memory | 0.875 | 1.000 | +0.125 | +2 / -0 |
| balanced_reasoning_off | social_support | 0.750 | 0.708 | -0.042 | +1 / -2 |
| balanced_reasoning_off | tool_recovery | 0.875 | 1.000 | +0.125 | +2 / -0 |
| balanced_reasoning_on | coding_agent | 0.708 | 0.667 | -0.042 | +1 / -2 |
| balanced_reasoning_on | instruction_following | 0.917 | 0.833 | -0.083 | +1 / -2 |
| balanced_reasoning_on | personalization_memory | 0.875 | 1.000 | +0.125 | +2 / -0 |
| balanced_reasoning_on | social_support | 0.750 | 0.708 | -0.042 | +1 / -2 |
| balanced_reasoning_on | tool_recovery | 0.875 | 1.000 | +0.125 | +2 / -0 |

## Negative Task Deltas

| Config | Task | Category | Base | Variant | Delta |
|---|---|---|---:|---:|---:|
| balanced_reasoning_off | instruction_following_002 | instruction_following | 1.000 | 0.333 | -0.667 |
| balanced_reasoning_off | instruction_following_008 | instruction_following | 1.000 | 0.333 | -0.667 |
| balanced_reasoning_off | social_support_004 | social_support | 0.667 | 0.000 | -0.667 |
| balanced_reasoning_off | coding_agent_003 | coding_agent | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | coding_agent_008 | coding_agent | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | social_support_001 | social_support | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_on | instruction_following_002 | instruction_following | 1.000 | 0.333 | -0.667 |
| balanced_reasoning_on | instruction_following_008 | instruction_following | 1.000 | 0.333 | -0.667 |
| balanced_reasoning_on | social_support_004 | social_support | 0.667 | 0.000 | -0.667 |
| balanced_reasoning_on | coding_agent_003 | coding_agent | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_on | coding_agent_008 | coding_agent | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_on | social_support_001 | social_support | 1.000 | 0.667 | -0.333 |

## Positive Task Deltas

| Config | Task | Category | Base | Variant | Delta |
|---|---|---|---:|---:|---:|
| balanced_reasoning_off | instruction_following_001 | instruction_following | 0.333 | 1.000 | +0.667 |
| balanced_reasoning_off | personalization_memory_003 | personalization_memory | 0.333 | 1.000 | +0.667 |
| balanced_reasoning_off | tool_recovery_007 | tool_recovery | 0.333 | 1.000 | +0.667 |
| balanced_reasoning_off | social_support_006 | social_support | 0.000 | 0.667 | +0.667 |
| balanced_reasoning_off | coding_agent_007 | coding_agent | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_off | personalization_memory_001 | personalization_memory | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_off | tool_recovery_002 | tool_recovery | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_on | instruction_following_001 | instruction_following | 0.333 | 1.000 | +0.667 |
| balanced_reasoning_on | personalization_memory_003 | personalization_memory | 0.333 | 1.000 | +0.667 |
| balanced_reasoning_on | tool_recovery_007 | tool_recovery | 0.333 | 1.000 | +0.667 |
| balanced_reasoning_on | social_support_006 | social_support | 0.000 | 0.667 | +0.667 |
| balanced_reasoning_on | coding_agent_007 | coding_agent | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_on | personalization_memory_001 | personalization_memory | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_on | tool_recovery_002 | tool_recovery | 0.667 | 1.000 | +0.333 |
