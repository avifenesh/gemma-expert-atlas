#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
THEMES="${THEMES:-machine_learning,coding,debugging,website_building,io_uring_writing,code_testing,tool_calling,math,factual_knowledge,psychology,relationship_help,agent_orchestration,moe_training,personal_research,tool_recovery,routine_monitoring,personalization_memory,coding_agent,social_support,agentic_kv_cache}"
REPEATS="${REPEATS:-5}"
CTX="${CTX:-512}"
CHUNKS="${CHUNKS:-4}"
KEEP_IMATRIX="${KEEP_IMATRIX:-0}"

CORPUS_DIR="$ROOT/data/theme_corpora"
TRACE_DIR="$ROOT/public/data/theme_traces"
IMATRIX_DIR="$ROOT/data/theme_imatrix"

python3 "$ROOT/scripts/make_theme_corpora.py" \
  --themes "$THEMES" \
  --repeats "$REPEATS" \
  --out-dir "$CORPUS_DIR"

mkdir -p "$TRACE_DIR" "$IMATRIX_DIR"

IFS=',' read -r -a theme_list <<< "$THEMES"
combine_args=()

for theme in "${theme_list[@]}"; do
  theme="${theme//[[:space:]]/}"
  [[ -n "$theme" ]] || continue
  for mode in reasoning_off reasoning_on; do
    prompts="$CORPUS_DIR/${theme}_${mode}.txt"
    imatrix="$IMATRIX_DIR/${theme}_${mode}.gguf"
    json="$TRACE_DIR/routing_trace_${theme}_${mode}.json"
    label="${theme}_${mode}"

    echo "==> $label"
    PROMPTS="$prompts" \
      OUT="$imatrix" \
      PARSE_SPECIAL=1 \
      CTX="$CTX" \
      CHUNKS="$CHUNKS" \
      LABEL="$label" \
      IMPORT_OUT="$json" \
      "$ROOT/scripts/run_routing_calibration.sh"

    combine_args+=(--trace "${theme}:${mode}=${json}")
    if [[ "$KEEP_IMATRIX" != "1" ]]; then
      rm -f "$imatrix"
    fi
  done
done

python3 "$ROOT/scripts/combine_theme_traces.py" \
  --theme-manifest "$CORPUS_DIR/theme_manifest.json" \
  "${combine_args[@]}" \
  --out "$ROOT/public/data/theme_routing_traces.json"
