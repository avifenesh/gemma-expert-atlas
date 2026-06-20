#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "$ROOT/scripts/make_calibration_corpus.py" --mode mixed --out "$ROOT/data/calibration_mixed.txt"
python3 "$ROOT/scripts/make_calibration_corpus.py" --mode reasoning_off --out "$ROOT/data/calibration_reasoning_off.txt"
python3 "$ROOT/scripts/make_calibration_corpus.py" --mode reasoning_on --out "$ROOT/data/calibration_reasoning_on.txt"

run_trace() {
  local label="$1"
  local prompts="$2"
  local parse_special="$3"
  local imatrix="$ROOT/data/routing-${label}.gguf"
  local json="$ROOT/public/data/routing_trace_${label}.json"

  PROMPTS="$prompts" OUT="$imatrix" PARSE_SPECIAL="$parse_special" "$ROOT/scripts/run_routing_calibration.sh"
  python3 "$ROOT/scripts/import_imatrix_counts.py" \
    --label "$label" \
    --manifest "$ROOT/public/data/expert_manifest.json" \
    --imatrix "$imatrix" \
    --out "$json"
}

run_trace mixed "$ROOT/data/calibration_mixed.txt" 0
run_trace reasoning_off "$ROOT/data/calibration_reasoning_off.txt" 1
run_trace reasoning_on "$ROOT/data/calibration_reasoning_on.txt" 1

cp "$ROOT/public/data/routing_trace_mixed.json" "$ROOT/public/data/routing_trace.json"

python3 "$ROOT/scripts/combine_routing_traces.py" \
  --default mixed \
  --trace mixed="$ROOT/public/data/routing_trace_mixed.json" \
  --trace reasoning_off="$ROOT/public/data/routing_trace_reasoning_off.json" \
  --trace reasoning_on="$ROOT/public/data/routing_trace_reasoning_on.json" \
  --out "$ROOT/public/data/routing_traces.json"
