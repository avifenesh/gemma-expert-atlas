#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CATEGORIES="${CATEGORIES:-personal_research,tool_recovery,coding_agent,code_review,routine_monitoring,personalization_memory,agent_orchestration,model_ops,expert_surgery,social_support,instruction_following,local_system_ops,eval_design}"
MODE="${MODE:-reasoning_off}"
CTX="${CTX:-512}"
CHUNK_CHARS="${CHUNK_CHARS:-6500}"
MAX_CHUNKS="${MAX_CHUNKS:-4}"
EARLY_CHUNKS="${EARLY_CHUNKS:-1}"
SKIP_EXISTING="${SKIP_EXISTING:-0}"

extra_args=()
if [[ "$SKIP_EXISTING" == "1" ]]; then
  extra_args+=(--skip-existing)
fi

IFS=',' read -r -a category_list <<< "$CATEGORIES"
for category in "${category_list[@]}"; do
  category="${category//[[:space:]]/}"
  [[ -n "$category" ]] || continue

  prompts="$ROOT/data/personal_agent_corpora/${category}_${MODE}.txt"
  label="${category}_${MODE}_timeline${MAX_CHUNKS}"
  echo "==> $label"
  python3 "$ROOT/scripts/run_routing_timeline.py" \
    --label "$label" \
    --prompts "$prompts" \
    --ctx "$CTX" \
    --chunk-chars "$CHUNK_CHARS" \
    --max-chunks "$MAX_CHUNKS" \
    --early-chunks "$EARLY_CHUNKS" \
    "${extra_args[@]}"
done

python3 "$ROOT/scripts/combine_routing_timelines.py"
