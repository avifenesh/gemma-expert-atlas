#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_CALIBRATION="${RUN_CALIBRATION:-0}"

cd "$ROOT"

npm run make-personal-agent-bank
npm run make-personal-agent-corpora

if [[ "$RUN_CALIBRATION" == "1" ]]; then
  npm run calibrate:personal-agent
else
  echo "Skipping routing calibration. Set RUN_CALIBRATION=1 to generate fresh personal-agent traces."
fi

npm run analyze:experts
npm run plan:surgery

echo "Pipeline artifacts:"
echo "  data/personal_agent_bank/tasks.jsonl"
echo "  data/personal_agent_corpora/personal_agent_corpus_manifest.json"
echo "  data/expert_usage_analysis.json"
echo "  data/surgery_experiments/plan.json"
