# Incremental Ladder Step 001 L08.E054

Generated: 2026-06-20T20:11:00.877354+00:00

Baseline: `data/personal_agent_bank/runs/20260620T170017Z/results.json`
Variant: `data/surgery_experiments/incremental_ladder/evals/step_001_L08_E054/20260620T_step001_full/results.json`

## Summary

- balanced_reasoning_off: score 0.7596 -> 0.7716 (+0.0120), decode 142.55 -> 144.61 tok/s
- balanced_reasoning_on: score 0.7436 -> 0.7508 (+0.0072), decode 144.52 -> 141.50 tok/s

## Category Deltas

| Config | Category | Base | Variant | Delta | +/- tasks |
|---|---|---:|---:|---:|---:|
| balanced_reasoning_off | agent_orchestration | 0.917 | 0.875 | -0.042 | +0 / -1 |
| balanced_reasoning_off | code_review | 0.625 | 0.708 | +0.083 | +2 / -0 |
| balanced_reasoning_off | coding_agent | 0.833 | 0.875 | +0.042 | +2 / -1 |
| balanced_reasoning_off | eval_design | 0.875 | 0.875 | +0.000 | +2 / -2 |
| balanced_reasoning_off | expert_surgery | 0.792 | 0.792 | +0.000 | +1 / -1 |
| balanced_reasoning_off | instruction_following | 0.458 | 0.458 | +0.000 | +3 / -2 |
| balanced_reasoning_off | local_system_ops | 0.958 | 0.917 | -0.042 | +0 / -1 |
| balanced_reasoning_off | model_ops | 0.917 | 0.875 | -0.042 | +1 / -2 |
| balanced_reasoning_off | personal_research | 0.625 | 0.656 | +0.031 | +2 / -1 |
| balanced_reasoning_off | personalization_memory | 0.708 | 0.625 | -0.083 | +1 / -2 |
| balanced_reasoning_off | routine_monitoring | 0.667 | 0.750 | +0.083 | +3 / -1 |
| balanced_reasoning_off | social_support | 0.542 | 0.667 | +0.125 | +2 / -0 |
| balanced_reasoning_off | tool_recovery | 0.958 | 0.958 | +0.000 | +1 / -1 |
| balanced_reasoning_on | agent_orchestration | 0.958 | 0.958 | +0.000 | +1 / -1 |
| balanced_reasoning_on | code_review | 0.625 | 0.625 | +0.000 | +1 / -1 |
| balanced_reasoning_on | coding_agent | 0.875 | 0.833 | -0.042 | +1 / -2 |
| balanced_reasoning_on | eval_design | 0.875 | 0.917 | +0.042 | +2 / -1 |
| balanced_reasoning_on | expert_surgery | 0.708 | 0.750 | +0.042 | +1 / -0 |
| balanced_reasoning_on | instruction_following | 0.333 | 0.375 | +0.042 | +2 / -1 |
| balanced_reasoning_on | local_system_ops | 0.958 | 0.917 | -0.042 | +0 / -1 |
| balanced_reasoning_on | model_ops | 0.875 | 0.875 | +0.000 | +1 / -1 |
| balanced_reasoning_on | personal_research | 0.625 | 0.594 | -0.031 | +1 / -1 |
| balanced_reasoning_on | personalization_memory | 0.625 | 0.542 | -0.083 | +1 / -3 |
| balanced_reasoning_on | routine_monitoring | 0.708 | 0.792 | +0.083 | +2 / -0 |
| balanced_reasoning_on | social_support | 0.542 | 0.583 | +0.042 | +2 / -2 |
| balanced_reasoning_on | tool_recovery | 0.958 | 1.000 | +0.042 | +1 / -0 |

## Negative Task Deltas

| Config | Task | Category | Base | Variant | Delta |
|---|---|---|---:|---:|---:|
| balanced_reasoning_off | personalization_memory_007 | personalization_memory | 1.000 | 0.333 | -0.667 |
| balanced_reasoning_off | instruction_following_008 | instruction_following | 0.667 | 0.000 | -0.667 |
| balanced_reasoning_off | agent_orchestration_006 | agent_orchestration | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | coding_agent_002 | coding_agent | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | eval_design_006 | eval_design | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | eval_design_007 | eval_design | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | expert_surgery_004 | expert_surgery | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | local_system_ops_007 | local_system_ops | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | model_ops_004 | model_ops | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | personalization_memory_006 | personalization_memory | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | routine_monitoring_001 | routine_monitoring | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | tool_recovery_006 | tool_recovery | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_off | instruction_following_002 | instruction_following | 0.667 | 0.333 | -0.333 |
| balanced_reasoning_off | model_ops_006 | model_ops | 0.667 | 0.333 | -0.333 |
| balanced_reasoning_off | personal_research_008 | personal_research | 0.750 | 0.500 | -0.250 |
| balanced_reasoning_on | personal_research_006 | personal_research | 1.000 | 0.500 | -0.500 |
| balanced_reasoning_on | agent_orchestration_001 | agent_orchestration | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_on | coding_agent_002 | coding_agent | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_on | coding_agent_003 | coding_agent | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_on | eval_design_005 | eval_design | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_on | local_system_ops_007 | local_system_ops | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_on | model_ops_003 | model_ops | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_on | personalization_memory_001 | personalization_memory | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_on | personalization_memory_003 | personalization_memory | 1.000 | 0.667 | -0.333 |
| balanced_reasoning_on | code_review_005 | code_review | 0.667 | 0.333 | -0.333 |
| balanced_reasoning_on | instruction_following_006 | instruction_following | 0.333 | 0.000 | -0.333 |
| balanced_reasoning_on | personalization_memory_006 | personalization_memory | 0.667 | 0.333 | -0.333 |
| balanced_reasoning_on | social_support_003 | social_support | 0.667 | 0.333 | -0.333 |
| balanced_reasoning_on | social_support_005 | social_support | 0.667 | 0.333 | -0.333 |

## Positive Task Deltas

| Config | Task | Category | Base | Variant | Delta |
|---|---|---|---:|---:|---:|
| balanced_reasoning_off | social_support_004 | social_support | 0.000 | 0.667 | +0.667 |
| balanced_reasoning_off | code_review_007 | code_review | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_off | coding_agent_003 | coding_agent | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_off | coding_agent_005 | coding_agent | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_off | eval_design_005 | eval_design | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_off | eval_design_008 | eval_design | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_off | expert_surgery_005 | expert_surgery | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_off | instruction_following_005 | instruction_following | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_off | model_ops_008 | model_ops | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_off | routine_monitoring_003 | routine_monitoring | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_off | routine_monitoring_008 | routine_monitoring | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_off | tool_recovery_002 | tool_recovery | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_off | code_review_005 | code_review | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_off | instruction_following_004 | instruction_following | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_off | instruction_following_007 | instruction_following | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_off | personalization_memory_008 | personalization_memory | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_off | routine_monitoring_004 | routine_monitoring | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_off | social_support_006 | social_support | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_off | personal_research_003 | personal_research | 0.500 | 0.750 | +0.250 |
| balanced_reasoning_off | personal_research_006 | personal_research | 0.500 | 0.750 | +0.250 |
| balanced_reasoning_on | social_support_006 | social_support | 0.000 | 0.667 | +0.667 |
| balanced_reasoning_on | agent_orchestration_007 | agent_orchestration | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_on | coding_agent_008 | coding_agent | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_on | eval_design_004 | eval_design | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_on | eval_design_007 | eval_design | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_on | model_ops_004 | model_ops | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_on | routine_monitoring_008 | routine_monitoring | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_on | tool_recovery_002 | tool_recovery | 0.667 | 1.000 | +0.333 |
| balanced_reasoning_on | code_review_003 | code_review | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_on | expert_surgery_008 | expert_surgery | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_on | instruction_following_002 | instruction_following | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_on | instruction_following_003 | instruction_following | 0.000 | 0.333 | +0.333 |
| balanced_reasoning_on | personalization_memory_004 | personalization_memory | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_on | routine_monitoring_003 | routine_monitoring | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_on | social_support_002 | social_support | 0.333 | 0.667 | +0.333 |
| balanced_reasoning_on | personal_research_007 | personal_research | 0.250 | 0.500 | +0.250 |
