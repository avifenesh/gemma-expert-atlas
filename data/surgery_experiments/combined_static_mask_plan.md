# Runtime After-Prefix Eviction Plan

Generated: 2026-06-20T19:21:30.527951+00:00

## Summary

- Candidates: 248
- Timeline runs: 13
- Later routes inside candidate set: 0
- Fast-tier bytes reclaimable after prefix: 791.23 MiB
- Share of expert payload: 6.46%

## Tiers

| Tier | Count | Fast-tier bytes |
|---|---:|---:|
| tier_0_all_timelines | 9 | 28.71 MiB |
| tier_1_frequent | 8 | 25.52 MiB |
| tier_2_sparse | 29 | 92.52 MiB |
| tier_3_never_active | 202 | 644.47 MiB |

## Top Candidates

| Expert | Tier | Runs | Early count | Later count | Bytes | Class |
|---|---|---:|---:|---:|---:|---|
| L08.E054 | tier_0_all_timelines | 13/13 | 49 | 0 | 3.19 MiB | ordinary |
| L26.E093 | tier_0_all_timelines | 13/13 | 42 | 0 | 3.19 MiB | ordinary |
| L09.E029 | tier_0_all_timelines | 13/13 | 39 | 0 | 3.19 MiB | ordinary |
| L16.E025 | tier_0_all_timelines | 13/13 | 30 | 0 | 3.19 MiB | ordinary |
| L02.E025 | tier_0_all_timelines | 13/13 | 26 | 0 | 3.19 MiB | ordinary |
| L00.E036 | tier_0_all_timelines | 13/13 | 13 | 0 | 3.19 MiB | ordinary |
| L04.E083 | tier_0_all_timelines | 13/13 | 13 | 0 | 3.19 MiB | ordinary |
| L05.E096 | tier_0_all_timelines | 13/13 | 13 | 0 | 3.19 MiB | ordinary |
| L27.E086 | tier_0_all_timelines | 13/13 | 13 | 0 | 3.19 MiB | ordinary |
| L02.E034 | tier_1_frequent | 10/10 | 10 | 0 | 3.19 MiB | ordinary |
| L17.E079 | tier_1_frequent | 9/9 | 9 | 0 | 3.19 MiB | ordinary |
| L22.E000 | tier_1_frequent | 9/9 | 9 | 0 | 3.19 MiB | ordinary |
| L22.E117 | tier_1_frequent | 9/9 | 9 | 0 | 3.19 MiB | ordinary |
| L15.E084 | tier_1_frequent | 8/8 | 8 | 0 | 3.19 MiB | ordinary |
| L28.E099 | tier_1_frequent | 7/7 | 9 | 0 | 3.19 MiB | ordinary |
| L12.E104 | tier_1_frequent | 6/6 | 6 | 0 | 3.19 MiB | ordinary |
| L13.E087 | tier_1_frequent | 6/6 | 6 | 0 | 3.19 MiB | ordinary |
| L16.E058 | tier_2_sparse | 5/5 | 6 | 0 | 3.19 MiB | ordinary |
| L27.E013 | tier_2_sparse | 5/5 | 6 | 0 | 3.19 MiB | ordinary |
| L05.E035 | tier_2_sparse | 5/5 | 5 | 0 | 3.19 MiB | low_use_merge_candidate |
| L14.E010 | tier_2_sparse | 5/5 | 5 | 0 | 3.19 MiB | ordinary |
| L15.E036 | tier_2_sparse | 5/5 | 5 | 0 | 3.19 MiB | low_use_merge_candidate |
| L17.E081 | tier_2_sparse | 5/5 | 5 | 0 | 3.19 MiB | ordinary |
| L20.E000 | tier_2_sparse | 5/5 | 5 | 0 | 3.19 MiB | ordinary |
| L16.E009 | tier_2_sparse | 4/4 | 4 | 0 | 3.19 MiB | ordinary |
| L23.E001 | tier_2_sparse | 4/4 | 4 | 0 | 3.19 MiB | ordinary |
| L18.E064 | tier_2_sparse | 3/3 | 4 | 0 | 3.19 MiB | ordinary |
| L23.E086 | tier_2_sparse | 3/3 | 4 | 0 | 3.19 MiB | ordinary |
| L07.E121 | tier_2_sparse | 3/3 | 3 | 0 | 3.19 MiB | ordinary |
| L16.E082 | tier_2_sparse | 2/2 | 2 | 0 | 3.19 MiB | cold_trim_candidate |
| L27.E105 | tier_2_sparse | 2/2 | 2 | 0 | 3.19 MiB | ordinary |
| L06.E054 | tier_2_sparse | 1/1 | 1 | 0 | 3.19 MiB | low_use_merge_candidate |
| L08.E100 | tier_2_sparse | 1/1 | 1 | 0 | 3.19 MiB | low_use_merge_candidate |
| L09.E116 | tier_2_sparse | 1/1 | 1 | 0 | 3.19 MiB | low_use_merge_candidate |
| L10.E024 | tier_2_sparse | 1/1 | 1 | 0 | 3.19 MiB | cold_trim_candidate |
| L11.E026 | tier_2_sparse | 1/1 | 1 | 0 | 3.19 MiB | ordinary |
| L14.E003 | tier_2_sparse | 1/1 | 1 | 0 | 3.19 MiB | cold_trim_candidate |
| L14.E109 | tier_2_sparse | 1/1 | 1 | 0 | 3.19 MiB | ordinary |
| L15.E110 | tier_2_sparse | 1/1 | 1 | 0 | 3.19 MiB | ordinary |
| L17.E008 | tier_2_sparse | 1/1 | 1 | 0 | 3.19 MiB | low_use_merge_candidate |

## Interpretation

- Probe kind: combined_layer_specific_static_mask.
- Candidate file: `data/surgery_experiments/combined_early_then_silent_plus_never_active_v0.txt`.
- Static masking measures quality risk only; it does not remove MoE compute from llama.cpp.
- A real speed or memory win requires runtime support or a repacked layer-specific expert layout.
