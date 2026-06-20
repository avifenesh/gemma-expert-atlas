# Data Boundary

This repo commits curated, dashboard-ready evidence and compact experiment
summaries. Raw local corpora, generated task banks, per-task eval runs, imatrix
files, and GGUF model outputs are intentionally ignored.

The important public artifacts are:

- `public/data/*_routing_traces.json` and `public/data/routing_traces.json`:
  slim dashboard indexes with trace paths, summaries, and top reasoning deltas.
- `public/data/*_traces/*.json` and `public/data/routing_trace_*.json`: full
  per-trace expert arrays loaded on demand by the dashboard.
- `data/surgery_experiments/*.md|*.json|*.csv|*.txt`: compact triage plans and
  comparison reports.
- `data/kv_cache_eval/tasks.jsonl`: the small non-personal KV-cache eval seed.

Regenerate ignored inputs locally with the scripts in `scripts/`.
