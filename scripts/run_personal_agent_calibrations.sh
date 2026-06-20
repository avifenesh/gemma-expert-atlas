#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CATEGORIES="${CATEGORIES:-personal_research,tool_recovery,coding_agent,code_review,routine_monitoring,personalization_memory,agent_orchestration,model_ops,expert_surgery,social_support,instruction_following,local_system_ops,eval_design}"
REPEATS="${REPEATS:-2}"
CTX="${CTX:-1024}"
CHUNKS="${CHUNKS:-4}"
KEEP_IMATRIX="${KEEP_IMATRIX:-0}"

TASKS="$ROOT/data/personal_agent_bank/tasks.jsonl"
CORPUS_DIR="$ROOT/data/personal_agent_corpora"
TRACE_DIR="$ROOT/public/data/personal_agent_traces"
IMATRIX_DIR="$ROOT/data/personal_agent_imatrix"

python3 "$ROOT/scripts/make_personal_agent_bank.py" --out "$TASKS"
python3 "$ROOT/scripts/make_personal_agent_corpora.py" \
  --tasks "$TASKS" \
  --categories "$CATEGORIES" \
  --repeats "$REPEATS" \
  --out-dir "$CORPUS_DIR"

mkdir -p "$TRACE_DIR" "$IMATRIX_DIR"

IFS=',' read -r -a category_list <<< "$CATEGORIES"
combine_args=()

for category in "${category_list[@]}"; do
  category="${category//[[:space:]]/}"
  [[ -n "$category" ]] || continue
  for mode in reasoning_off reasoning_on; do
    prompts="$CORPUS_DIR/${category}_${mode}.txt"
    imatrix="$IMATRIX_DIR/${category}_${mode}.gguf"
    json="$TRACE_DIR/routing_trace_${category}_${mode}.json"
    label="${category}_${mode}"

    echo "==> $label"
    PROMPTS="$prompts" \
      OUT="$imatrix" \
      PARSE_SPECIAL=1 \
      CTX="$CTX" \
      CHUNKS="$CHUNKS" \
      LABEL="$label" \
      IMPORT_OUT="$json" \
      "$ROOT/scripts/run_routing_calibration.sh"

    combine_args+=(--trace "${category}:${mode}=${json}")
    if [[ "$KEEP_IMATRIX" != "1" ]]; then
      rm -f "$imatrix"
    fi
  done
done

python3 "$ROOT/scripts/combine_theme_traces.py" \
  "${combine_args[@]}" \
  --out "$ROOT/public/data/personal_agent_routing_traces.json"
