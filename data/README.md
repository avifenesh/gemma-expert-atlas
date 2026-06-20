# Data Boundary

This repo commits curated, dashboard-ready evidence and compact experiment
summaries. Raw local corpora, generated task banks, per-task eval runs, imatrix
files, and GGUF model outputs are intentionally ignored.

The important public artifacts are:

- `public/data/*.json`: data used by the Expert Atlas UI.
- `public/data/*_traces/*.json`: per-theme routing summaries used to rebuild
  the combined dashboard bundles.
- `data/surgery_experiments/*.md|*.json|*.csv|*.txt`: compact triage plans and
  comparison reports.
- `data/kv_cache_eval/tasks.jsonl`: the small non-personal KV-cache eval seed.

Regenerate ignored inputs locally with the scripts in `scripts/`.
