#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LLAMA_CPP="${LLAMA_CPP:-$HOME/projects/llama.cpp}"
MODEL="${MODEL:-/data/ai-ml/hf-models/gemma4-26ba4b-qat-gguf/gemma-4-26B_q4_0-it.gguf}"
PROMPTS="${PROMPTS:-$ROOT/data/calibration_mixed.txt}"
OUT="${OUT:-$ROOT/data/routing-imatrix.gguf}"
CTX="${CTX:-512}"
CHUNKS="${CHUNKS:-8}"
PARSE_SPECIAL="${PARSE_SPECIAL:-0}"
LABEL="${LABEL:-routing}"
IMPORT_OUT="${IMPORT_OUT:-$ROOT/public/data/routing_trace.json}"
SKIP_IMPORT="${SKIP_IMPORT:-0}"

extra_args=()
if [[ "$PARSE_SPECIAL" == "1" ]]; then
  extra_args+=(--parse-special)
fi

"$LLAMA_CPP/build/bin/llama-imatrix" \
  -m "$MODEL" \
  -f "$PROMPTS" \
  -o "$OUT" \
  -c "$CTX" \
  -b "$CTX" \
  -ub 128 \
  --chunks "$CHUNKS" \
  --no-ppl \
  -fa on \
  -ngl auto \
  --cache-type-k q8_0 \
  --cache-type-v q5_1 \
  "${extra_args[@]}"

if [[ "$SKIP_IMPORT" != "1" ]]; then
  python3 "$ROOT/scripts/import_imatrix_counts.py" \
    --label "$LABEL" \
    --manifest "$ROOT/public/data/expert_manifest.json" \
    --imatrix "$OUT" \
    --out "$IMPORT_OUT"
fi
