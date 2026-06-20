# Trim Decision Report

Generated: 2026-06-20T16:03:31.411183+00:00

## Summary

- Traces accumulated: 55 ({'general': 3, 'personal_agent': 26, 'theme': 26})
- Experts: 3840
- Decisions: {'keep': 2708, 'needs_more_data': 94, 'protect': 1025, 'trim_ablation_candidate': 9, 'trim_watchlist_cold': 4}

## Stages

### trim_probe_zero_all_v0

- Decision: ablate_first
- Candidate count: 5
- Estimated packed expert bytes: 56.72 MiB
- Note: One zero-across-all expert per layer, intended to test the reversible trim path.

```text
L00.E042
L01.E017
L02.E089
L03.E115
L04.E060
```

### trim_zero_all_v1

- Decision: best_first_trim_candidate
- Candidate count: 7
- Estimated packed expert bytes: 79.41 MiB
- Note: Zero selections across all accumulated traces, capped per layer.

```text
L00.E042
L00.E082
L01.E017
L01.E019
L02.E089
L03.E115
L04.E060
```

### trim_zero_plus_tiny_v2

- Decision: only_after_v1_eval_passes
- Candidate count: 11
- Estimated packed expert bytes: 124.78 MiB
- Note: Adds tiny nonzero experts only after zero-all trimming passes eval.

```text
L00.E042
L00.E082
L01.E017
L01.E019
L02.E089
L03.E115
L04.E060
L03.E041
L10.E044
L13.E055
L05.E122
```

## Top Zero-Across-All Candidates

| Expert | Layer | Bytes | Personal class |
|---|---:|---:|---|
| L00.E042 | 0 | 11.34 MiB | globally_dead |
| L00.E082 | 0 | 11.34 MiB | globally_dead |
| L01.E017 | 1 | 11.34 MiB | globally_dead |
| L01.E019 | 1 | 11.34 MiB | globally_dead |
| L01.E063 | 1 | 11.34 MiB | globally_dead |
| L01.E075 | 1 | 11.34 MiB | globally_dead |
| L02.E089 | 2 | 11.34 MiB | globally_dead |
| L03.E115 | 3 | 11.34 MiB | globally_dead |
| L04.E060 | 4 | 11.34 MiB | globally_dead |

## Cold Watchlist

| Expert | Active traces | Total count | Max share | Personal class |
|---|---:|---:|---:|---|
| L03.E041 | 1 | 1 | 0.000031 | globally_dead |
| L10.E044 | 1 | 1 | 0.000031 | globally_dead |
| L13.E055 | 1 | 1 | 0.000061 | globally_dead |
| L05.E122 | 2 | 2 | 0.000031 | globally_dead |

## Rules

- Routing nominates trim candidates.
- Baseline eval plus trimmed eval decides whether a trim is accepted.
- Router disabling is the reversible probe; memory savings require checkpoint repacking.
- Any task-hot/protected expert is kept regardless of global coldness.
