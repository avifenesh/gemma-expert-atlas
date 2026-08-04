# Expert Triage Decision Ledger

This ledger is the public trail for expert-surgery decisions. It records what
was tried, which artifacts back the call, and what should happen next. A row is
not a claim about the model in general; it is a decision for this repo's current
Gemma 4 26B A4B traces, prompts, scripts, and local eval setup.

## Status Terms

- `ok/yellow`: plausible enough to keep investigating, but not accepted as a
  checkpoint edit.
- `yellow`: signal is mixed; use it to choose the next probe, not as a pass.
- `planned`: tooling or protocol exists, but no eval result has been recorded.
- `rejected`: do not continue this candidate in its current form unless new
  evidence changes the premise.
- `full_eval_pending`: focused guard looked good enough to justify the full
  personal-agent bank; not accepted until that eval passes.
- `accepted`: reserved for a probe that passes the full gate and has a clear
  deployment or artifact path.

## Decisions So Far

| Date | ID | Candidate | Probe | Evidence | Decision | Notes / next step |
|---|---|---|---|---|---|---|
| 2026-06-20 | runtime-evict-after-prefix-v0 | 46 after-prefix runtime-residency candidates | Static mask as a quality-risk proxy for experts whose observed routes occur before the prefix boundary | `data/surgery_experiments/runtime_eviction_plan.md`; `data/surgery_experiments/runtime_evict_after_prefix_v0_static_mask_full_report.md` | ok/yellow | Keep the idea alive for runtime or repacked-layout work. Static masking showed no collapse, but it does not prove a llama.cpp speed or memory win. |
| 2026-06-20 | combined-early-silent-never-active-v0 | 248 combined early-then-silent plus never-active candidates | Broad layer-specific static mask | `data/surgery_experiments/combined_static_mask_plan.md`; `data/surgery_experiments/combined_early_then_silent_plus_never_active_v0_static_mask_full_report.md` | rejected | Too broad. The full eval had mixed aggregate movement and enough negative task/category deltas to stop this combined set. |
| 2026-06-20 | zero-mask-L08-E054 | `L08.E054` | Single-expert zero mask in the incremental ladder | `data/surgery_experiments/incremental_ladder/step_001_L08_E054_report.md` | yellow | Aggregate scores moved up, but there were guard-task regressions, especially around personalization memory and instruction following. Useful as a clue, not a pass. |
| 2026-06-20 | replace-L08-E054-with-L08-E096 | `L08.E054 -> L08.E096` | Focused substitution guard on instruction following and personalization memory | `data/surgery_experiments/merge_substitution/L08_E054_to_L08_E096_focused_report.md`; `data/surgery_experiments/merge_substitution/L08_E054_to_L08_E096_focused_report_vs_full_baseline.md` | rejected | The focused off run dropped and instruction-following regressions were too large. |
| 2026-06-20 | replace-L08-E054-with-L08-E018-focused | `L08.E054 -> L08.E018` | Focused substitution guard on instruction following and personalization memory | `data/surgery_experiments/merge_substitution/L08_E054_to_L08_E018_focused_report.md` | ok/yellow | Focused guard was good enough to try the full personal-agent bank. It beat `L08.E096` on the reasoning-off guard. |
| 2026-06-20 | replace-L08-E054-with-L08-E018-full | `L08.E054 -> L08.E018` | Full personal-agent bank substitution eval | `data/surgery_experiments/merge_substitution/L08_E054_to_L08_E018_full_report.md`; `data/surgery_experiments/merge_substitution/eval_comparison_L08_E054_to_L08_E018_full.json` | yellow | Aggregate scores improved or stayed flat, and instruction following recovered, but protected-category drops remained: personalization-memory reasoning-off, plus agent-orchestration and coding in reasoning-on. Do not accept as a hard replacement; next probe should try a gentler blend or a different same-layer target. |
| 2026-06-21 | blend-L08-E054-toward-L08-E018-w0p25-focused | `L08.E054 <- 0.75*E054 + 0.25*E018` (blend in place, expert kept) | Focused 40-task guard, q4_0, reasoning on and off | `scripts/blend_hf_expert.py`; `data/surgery_experiments/blend_experiments/blend_L08_E054_to_L08_E018_w0p25_focused_report.md` | rejected | Exactly flat: 0.8250 -> 0.8250 in both reasoning modes, zero task-level deltas, decode 142.20 -> 142.14 tok/s (on) and 141.59 -> 140.88 (off). The blend keeps the expert in place, so there is no size or speed win to pay for; superseded by the absorb+remove probe below. |
| 2026-06-21 | remove-only-L08-E054-focused | `L08.E054` removed, weights redistributed by renorm | Focused 40-task guard, q4_0, reasoning on and off | `data/surgery_experiments/absorb_remove_experiments/remove_only_L08_E054_focused_report.md` | ok/yellow | Aggregate flat at 0.8250 vs base 0.8250 with zero task-level deltas, and decode improved 142.20 -> 148.45 tok/s (on) and 141.59 -> 147.27 (off). Good enough to justify the full 104-task gate (next row). |
| 2026-06-21 | absorb-remove-L08-E054-into-L08-E018-w0p25-focused | `L08.E018 <- E018 + 0.25*E054`, then `L08.E054` removed | Focused 40-task guard, q4_0, reasoning on and off | `data/surgery_experiments/absorb_remove_experiments/absorb_remove_L08_E054_into_L08_E018_w0p25_focused_report.md` | yellow | Best focused aggregate so far: 0.8250 -> 0.8417 (+0.0167) in both reasoning modes, decode 142.20 -> 146.61 tok/s (on), with personalization memory and tool recovery both +0.125. But it trips the gate as-is: coding-agent dropped -0.042 (over the 0.02 protected bar, two `patch` checks lost), instruction following dropped -0.083 including a `format` check failure on `instruction_following_008`, and social support dropped -0.042. Signal, not a pass. Next probe: full 104-task gate to see whether the coding/instruction regressions are real or focused-bank noise, since remove-only (same removal, no absorb) passed the full gate cleanly. |
| 2026-06-21 | remove-only-L08-E054-full-gate | `L08.E054` removed, weights redistributed by renorm | Full 104-task personal-agent gate, q4_0, reasoning on and off | `data/surgery_experiments/absorb_remove_experiments/remove_only_L08_E054_full_gate_report.md` | accepted | Passes the gate: aggregate 0.8005 -> 0.7981 (-0.0024, within the 0.02 bar) in both reasoning modes. Task-level review found a single regression, `personal_research_005` 1.00 -> 0.75 in both modes (personal_research -0.031, not a protected family); tool recovery, coding-agent, and personalization memory were unchanged and no exact-format task newly failed. Decode was roughly flat on the full bank (145.27 -> 143.86 on, 142.11 -> 143.90 off), so the focused-bank speed win did not clearly reproduce; the accepted artifact is the `remove_L08_E054` local-q4_0 GGUF and the win per removed expert is small. Next step: extend the removal ladder from this base and run the absorb+remove variant through the same full gate. |

## Recording Future Entries

Add one row for every triage decision that changes what we do next. Use a stable
ID, not just a prose title. Keep the row short and link to generated artifacts
instead of copying full reports into this file.

Each entry should include:

- date in UTC
- stable ID, such as `replace-L08-E054-with-L08-E018-full`
- exact candidate set or expert mapping
- probe type, such as static mask, runtime eviction, substitution guard, or full
  personal-agent eval
- artifact paths for the plan, baseline, variant, and comparison report
- decision status from the vocabulary above
- one concrete next step or stop condition

Do not mark a probe `accepted` from aggregate score alone. The full gate also
needs task-level review for exact-format failures, protected task families,
personalization memory, tool recovery, and any regression that would make the
model worse for the target workload.
