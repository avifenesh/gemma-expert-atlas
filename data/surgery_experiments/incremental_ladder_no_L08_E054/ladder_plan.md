# Incremental Expert Mask Ladder

Generated: 2026-06-20T20:11:55.422844+00:00

## Rule

- Each step adds exactly one expert to the previous accepted set.
- The default order starts with experts that were active only in the early window across every timeline.
- Static masking is a quality-risk probe only; speed and memory wins require a repacked/runtime layout.

## Steps

| Step | Add | Tier | Runs | Early | Later | Cumulative | File |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | L26.E093 | tier_0_all_timelines | 13/13 | 42 | 0 | 3.19 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_001_L26_E093.txt` |
| 2 | L09.E029 | tier_0_all_timelines | 13/13 | 39 | 0 | 6.38 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_002_L09_E029.txt` |
| 3 | L16.E025 | tier_0_all_timelines | 13/13 | 30 | 0 | 9.57 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_003_L16_E025.txt` |
| 4 | L02.E025 | tier_0_all_timelines | 13/13 | 26 | 0 | 12.76 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_004_L02_E025.txt` |
| 5 | L00.E036 | tier_0_all_timelines | 13/13 | 13 | 0 | 15.95 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_005_L00_E036.txt` |
| 6 | L04.E083 | tier_0_all_timelines | 13/13 | 13 | 0 | 19.14 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_006_L04_E083.txt` |
| 7 | L05.E096 | tier_0_all_timelines | 13/13 | 13 | 0 | 22.33 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_007_L05_E096.txt` |
| 8 | L27.E086 | tier_0_all_timelines | 13/13 | 13 | 0 | 25.52 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_008_L27_E086.txt` |
| 9 | L02.E034 | tier_1_frequent | 10/10 | 10 | 0 | 28.71 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_009_L02_E034.txt` |
| 10 | L17.E079 | tier_1_frequent | 9/9 | 9 | 0 | 31.90 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_010_L17_E079.txt` |
| 11 | L22.E000 | tier_1_frequent | 9/9 | 9 | 0 | 35.09 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_011_L22_E000.txt` |
| 12 | L22.E117 | tier_1_frequent | 9/9 | 9 | 0 | 38.29 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_012_L22_E117.txt` |
| 13 | L15.E084 | tier_1_frequent | 8/8 | 8 | 0 | 41.48 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_013_L15_E084.txt` |
| 14 | L28.E099 | tier_1_frequent | 7/7 | 9 | 0 | 44.67 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_014_L28_E099.txt` |
| 15 | L12.E104 | tier_1_frequent | 6/6 | 6 | 0 | 47.86 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_015_L12_E104.txt` |
| 16 | L13.E087 | tier_1_frequent | 6/6 | 6 | 0 | 51.05 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_016_L13_E087.txt` |
| 17 | L16.E058 | tier_2_sparse | 5/5 | 6 | 0 | 54.24 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_017_L16_E058.txt` |
| 18 | L27.E013 | tier_2_sparse | 5/5 | 6 | 0 | 57.43 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_018_L27_E013.txt` |
| 19 | L05.E035 | tier_2_sparse | 5/5 | 5 | 0 | 60.62 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_019_L05_E035.txt` |
| 20 | L14.E010 | tier_2_sparse | 5/5 | 5 | 0 | 63.81 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_020_L14_E010.txt` |
| 21 | L15.E036 | tier_2_sparse | 5/5 | 5 | 0 | 67.00 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_021_L15_E036.txt` |
| 22 | L17.E081 | tier_2_sparse | 5/5 | 5 | 0 | 70.19 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_022_L17_E081.txt` |
| 23 | L20.E000 | tier_2_sparse | 5/5 | 5 | 0 | 73.38 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_023_L20_E000.txt` |
| 24 | L16.E009 | tier_2_sparse | 4/4 | 4 | 0 | 76.57 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_024_L16_E009.txt` |
| 25 | L23.E001 | tier_2_sparse | 4/4 | 4 | 0 | 79.76 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_025_L23_E001.txt` |
| 26 | L18.E064 | tier_2_sparse | 3/3 | 4 | 0 | 82.95 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_026_L18_E064.txt` |
| 27 | L23.E086 | tier_2_sparse | 3/3 | 4 | 0 | 86.14 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_027_L23_E086.txt` |
| 28 | L07.E121 | tier_2_sparse | 3/3 | 3 | 0 | 89.33 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_028_L07_E121.txt` |
| 29 | L16.E082 | tier_2_sparse | 2/2 | 2 | 0 | 92.52 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_029_L16_E082.txt` |
| 30 | L27.E105 | tier_2_sparse | 2/2 | 2 | 0 | 95.71 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_030_L27_E105.txt` |
| 31 | L06.E054 | tier_2_sparse | 1/1 | 1 | 0 | 98.90 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_031_L06_E054.txt` |
| 32 | L08.E100 | tier_2_sparse | 1/1 | 1 | 0 | 102.09 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_032_L08_E100.txt` |
| 33 | L09.E116 | tier_2_sparse | 1/1 | 1 | 0 | 105.28 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_033_L09_E116.txt` |
| 34 | L10.E024 | tier_2_sparse | 1/1 | 1 | 0 | 108.47 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_034_L10_E024.txt` |
| 35 | L11.E026 | tier_2_sparse | 1/1 | 1 | 0 | 111.67 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_035_L11_E026.txt` |
| 36 | L14.E003 | tier_2_sparse | 1/1 | 1 | 0 | 114.86 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_036_L14_E003.txt` |
| 37 | L14.E109 | tier_2_sparse | 1/1 | 1 | 0 | 118.05 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_037_L14_E109.txt` |
| 38 | L15.E110 | tier_2_sparse | 1/1 | 1 | 0 | 121.24 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_038_L15_E110.txt` |
| 39 | L17.E008 | tier_2_sparse | 1/1 | 1 | 0 | 124.43 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_039_L17_E008.txt` |
| 40 | L22.E002 | tier_2_sparse | 1/1 | 1 | 0 | 127.62 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_040_L22_E002.txt` |
| 41 | L24.E012 | tier_2_sparse | 1/1 | 1 | 0 | 130.81 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_041_L24_E012.txt` |
| 42 | L25.E115 | tier_2_sparse | 1/1 | 1 | 0 | 134.00 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_042_L25_E115.txt` |
| 43 | L26.E063 | tier_2_sparse | 1/1 | 1 | 0 | 137.19 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_043_L26_E063.txt` |
| 44 | L28.E078 | tier_2_sparse | 1/1 | 1 | 0 | 140.38 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_044_L28_E078.txt` |
| 45 | L29.E068 | tier_2_sparse | 1/1 | 1 | 0 | 143.57 MiB | `data/surgery_experiments/incremental_ladder_no_L08_E054/step_045_L29_E068.txt` |
