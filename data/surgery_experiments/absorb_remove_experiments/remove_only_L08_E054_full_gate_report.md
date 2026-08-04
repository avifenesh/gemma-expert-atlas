# Remove-only L08.E054 full 104-task gate

Generated: 2026-08-04T22:15:24.368132+00:00

Baseline: `data/surgery_experiments/absorb_remove_experiments/evals/full_local_base_L08_E054_gate/20260621T_local_base_full_L08_E054_gate/results.json`
Variant: `data/surgery_experiments/absorb_remove_experiments/evals/full_remove_only_L08_E054_gate/20260621T_remove_only_L08_E054_full_gate/results.json`

## Summary

- balanced_reasoning_off: score 0.8005 -> 0.7981 (-0.0024), decode 142.11 -> 143.90 tok/s
- balanced_reasoning_on: score 0.8005 -> 0.7981 (-0.0024), decode 145.27 -> 143.86 tok/s

## Category Deltas

| Config | Category | Base | Variant | Delta | +/- tasks |
|---|---|---:|---:|---:|---:|
| balanced_reasoning_off | agent_orchestration | 0.958 | 0.958 | +0.000 | +0 / -0 |
| balanced_reasoning_off | code_review | 0.667 | 0.667 | +0.000 | +0 / -0 |
| balanced_reasoning_off | coding_agent | 0.708 | 0.708 | +0.000 | +0 / -0 |
| balanced_reasoning_off | eval_design | 0.667 | 0.667 | +0.000 | +0 / -0 |
| balanced_reasoning_off | expert_surgery | 0.667 | 0.667 | +0.000 | +0 / -0 |
| balanced_reasoning_off | instruction_following | 0.917 | 0.917 | +0.000 | +0 / -0 |
| balanced_reasoning_off | local_system_ops | 1.000 | 1.000 | +0.000 | +0 / -0 |
| balanced_reasoning_off | model_ops | 0.958 | 0.958 | +0.000 | +0 / -0 |
| balanced_reasoning_off | personal_research | 0.781 | 0.750 | -0.031 | +0 / -1 |
| balanced_reasoning_off | personalization_memory | 0.875 | 0.875 | +0.000 | +0 / -0 |
| balanced_reasoning_off | routine_monitoring | 0.583 | 0.583 | +0.000 | +0 / -0 |
| balanced_reasoning_off | social_support | 0.750 | 0.750 | +0.000 | +0 / -0 |
| balanced_reasoning_off | tool_recovery | 0.875 | 0.875 | +0.000 | +0 / -0 |
| balanced_reasoning_on | agent_orchestration | 0.958 | 0.958 | +0.000 | +0 / -0 |
| balanced_reasoning_on | code_review | 0.667 | 0.667 | +0.000 | +0 / -0 |
| balanced_reasoning_on | coding_agent | 0.708 | 0.708 | +0.000 | +0 / -0 |
| balanced_reasoning_on | eval_design | 0.667 | 0.667 | +0.000 | +0 / -0 |
| balanced_reasoning_on | expert_surgery | 0.667 | 0.667 | +0.000 | +0 / -0 |
| balanced_reasoning_on | instruction_following | 0.917 | 0.917 | +0.000 | +0 / -0 |
| balanced_reasoning_on | local_system_ops | 1.000 | 1.000 | +0.000 | +0 / -0 |
| balanced_reasoning_on | model_ops | 0.958 | 0.958 | +0.000 | +0 / -0 |
| balanced_reasoning_on | personal_research | 0.781 | 0.750 | -0.031 | +0 / -1 |
| balanced_reasoning_on | personalization_memory | 0.875 | 0.875 | +0.000 | +0 / -0 |
| balanced_reasoning_on | routine_monitoring | 0.583 | 0.583 | +0.000 | +0 / -0 |
| balanced_reasoning_on | social_support | 0.750 | 0.750 | +0.000 | +0 / -0 |
| balanced_reasoning_on | tool_recovery | 0.875 | 0.875 | +0.000 | +0 / -0 |

## Negative Task Deltas

| Config | Task | Category | Base | Variant | Delta |
|---|---|---|---:|---:|---:|
| balanced_reasoning_off | personal_research_005 | personal_research | 1.000 | 0.750 | -0.250 |
| balanced_reasoning_on | personal_research_005 | personal_research | 1.000 | 0.750 | -0.250 |

## Positive Task Deltas

| Config | Task | Category | Base | Variant | Delta |
|---|---|---|---:|---:|---:|
