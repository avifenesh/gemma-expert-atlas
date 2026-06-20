# Expert Surgery Loop

This is the public guide to the Gemma MoE expert-surgery work in this repo. The
goal is to turn expert-routing evidence into small, reversible probes and then
record every triage decision with enough context that a reader can reconstruct
why a candidate moved forward, stopped, or stayed yellow.

The decision trail lives in
[expert_triage_ledger.md](expert_triage_ledger.md).

## Purpose

The project studies Gemma 4 26B A4B expert behavior on a local personal-agent
workload: tool recovery, coding-agent loops, routine monitoring,
personalization memory, social support, model ops, eval design, and related
research tasks.

The work is deliberately conservative:

- Routing nominates candidates; evals decide whether they survive.
- "Unused here" means unused by this prompt bank and decoding setup, not unused
  by the model in general.
- Static masking measures quality risk. It does not prove runtime speed or
  memory savings by itself.
- Replacement and merge ideas need same-layer evidence plus focused guards
  before the full eval.

## Experiment Protocol

1. Generate or refresh a task bank and routing traces.
2. Classify experts from routing evidence.
3. Build the smallest candidate set that tests one hypothesis.
4. Run a reversible probe: static mask, focused substitution guard, runtime
   eviction proxy, or full personal-agent eval.
5. Compare against the recorded baseline at task and category level.
6. Record the decision in
   [expert_triage_ledger.md](expert_triage_ledger.md) as `ok/yellow`,
   `yellow`, `rejected`, `full_eval_pending`, or `accepted`.

Do not promote a candidate from aggregate score alone. Task-level regressions in
exact-format, instruction-following, personalization-memory, tool-recovery,
coding-agent, or social-support tasks can block a probe even when the mean score
looks fine.

## Current Snapshot

- Runtime eviction after prefix, 46 candidates: `ok/yellow`. It remains useful
  as a runtime-residency or repacked-layout idea; static masking alone does not
  make it a deployment win.
- Combined early-then-silent plus never-active set, 248 candidates: `rejected`.
  The set was too broad and the full eval had enough mixed/negative movement to
  stop it.
- `L08.E054` single zero-mask probe: `yellow`. It raised aggregate scores but
  still produced guard regressions.
- `L08.E054 -> L08.E096` focused substitution: `rejected`.
- `L08.E054 -> L08.E018` substitution: `yellow` after full eval. It improved
  aggregate reasoning-off and preserved the focused guard better than
  `L08.E096`, but protected-category drops block acceptance.

See the ledger for artifact links and rationale.

## Pipeline

Generate the large task bank:

```bash
npm run make-personal-agent-bank
```

Generate matching routing corpora:

```bash
npm run make-personal-agent-corpora
```

Run personal-agent routing calibration:

```bash
npm run calibrate:personal-agent
```

Analyze expert usage:

```bash
npm run analyze:experts
```

Create a conservative surgery plan:

```bash
npm run plan:surgery
```

Run the lightweight setup pipeline without expensive calibration:

```bash
npm run pipeline:surgery
```

Run the full pipeline with fresh routing traces:

```bash
RUN_CALIBRATION=1 npm run pipeline:surgery
```

## Artifact Map

- Task banks: `data/personal_agent_bank/tasks.jsonl`,
  `data/personal_agent_eval/tasks.jsonl`
- Corpus inputs: `data/personal_agent_corpora/*.txt`,
  `data/theme_corpora/*.txt`
- Dashboard-ready routing data: `public/data/personal_agent_routing_traces.json`,
  `public/data/theme_routing_traces.json`
- Expert usage summaries: `data/expert_usage_analysis.json`,
  `public/data/expert_usage_analysis.json`
- Surgery plans and reports: `data/surgery_experiments/`
- Runtime eviction plans: `data/surgery_experiments/runtime_eviction_plan.*`
- Combined static-mask plans:
  `data/surgery_experiments/combined_static_mask_plan.*`
- Focused substitution reports:
  `data/surgery_experiments/merge_substitution/*_focused_report.md`

## Classifications

`analyze:experts` assigns each expert one of:

- `globally_dead`: never selected in the trace bundle
- `cold_trim_candidate`: rarely selected and never meaningfully active
- `low_use_merge_candidate`: low-use but not dead; needs similarity checks
- `ordinary`: active enough to leave alone for now
- `task_hot_protect`: unusually important for at least one task family
- `always_hot_protect`: broadly active and should not be edited in early passes

Trim candidates are capped per layer. This prevents the first experiment from
emptying one layer just because one calibration slice was narrow.

## Surgery Variants

The generated plan contains four variants:

- `baseline`: no expert edits
- `trim_cold_v1`: reversible removal/disable of conservative cold candidates
- `merge_low_use_v1`: merge low-use experts only after weight-similarity checks
- `add_specialist_v1`: reserved for router-adapted specialist capacity

## Eval Gates

A surgery variant fails if:

- any exact-marker or strict-format task fails
- tool recovery, coding-agent, or personalization-memory drops by more than 0.02
- social-support quality becomes robotic or misses the target user tone
- a protected task-hot expert was removed or overwritten
- speed improves but scenario coverage for the target workload is lost

The first successful variant should be faster or lighter while staying within
baseline quality on the large personal-agent bank. Until then, candidates are
research artifacts, not accepted model edits.
