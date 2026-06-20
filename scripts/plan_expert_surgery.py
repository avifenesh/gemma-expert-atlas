#!/usr/bin/env python3
"""Create a conservative expert-surgery experiment plan from usage analysis."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANALYSIS = ROOT / "data" / "expert_usage_analysis.json"
DEFAULT_OUT = ROOT / "data" / "surgery_experiments" / "plan.json"


def ids(rows: list[dict[str, Any]], limit: int) -> list[str]:
    return [str(row["id"]) for row in rows[:limit]]


def merge_pairs(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    pairs = []
    for row in rows:
        target = row.get("routing_merge_target")
        if not target:
            continue
        pairs.append(
            {
                "source": row["id"],
                "target": target["id"],
                "routing_similarity": target["similarity"],
                "warning": target["warning"],
            }
        )
        if len(pairs) >= limit:
            break
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--trim-limit", type=int, default=64)
    parser.add_argument("--merge-limit", type=int, default=64)
    parser.add_argument("--task-hot-limit", type=int, default=64)
    args = parser.parse_args()

    analysis = json.loads(args.analysis.read_text())
    candidates = analysis.get("candidates", {})
    trim = candidates.get("trim", [])
    merge = candidates.get("merge", [])
    task_hot = candidates.get("task_hot", [])

    plan = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_analysis": str(args.analysis),
        "principle": (
            "Expert surgery is accepted only when a model variant improves memory or speed "
            "without task-family regressions on the personal-agent eval bank."
        ),
        "variants": [
            {
                "name": "baseline",
                "kind": "control",
                "description": "Original model, current quantization, no expert edits.",
                "candidate_experts": [],
                "required_before": [],
            },
            {
                "name": "trim_cold_v1",
                "kind": "trim",
                "description": "Remove or disable the most conservative globally-dead/cold candidates, capped per layer.",
                "candidate_experts": ids(trim, args.trim_limit),
                "required_before": [
                    "Confirm candidates are not task-hot in personal-agent routing traces.",
                    "Implement a reversible surgery path and preserve original metadata.",
                    "Run baseline eval on the same task bank and cache/reasoning settings.",
                ],
            },
            {
                "name": "merge_low_use_v1",
                "kind": "merge",
                "description": "Merge low-use candidates into same-layer experts after routing and weight-similarity checks.",
                "candidate_pairs": merge_pairs(merge, args.merge_limit),
                "required_before": [
                    "Add weight-space similarity for gate_up_proj and down_proj tensors.",
                    "Do not merge if source and target are task-hot for different families.",
                    "Compare against trim_cold_v1 rather than assuming merge is safer.",
                ],
            },
            {
                "name": "add_specialist_v1",
                "kind": "add",
                "description": (
                    "Reserved specialist-capacity experiment. Use task-hot winners from one variant to guide "
                    "new or copied experts, then adapt the router and validate scenario-level wins."
                ),
                "protected_task_hot_experts": ids(task_hot, args.task_hot_limit),
                "required_before": [
                    "Identify a task family where a variant wins and another variant regresses.",
                    "Inspect which experts are uniquely active in the winning scenario.",
                    "Train, route-tune, or otherwise adapt router behavior; tensor copying alone is not enough.",
                ],
            },
        ],
        "eval_gates": {
            "required_suites": [
                "personal_agent_bank",
                "kv_cache_eval",
                "routing_calibration",
            ],
            "hard_failures": [
                "Any exact-marker or JSON-format task fails.",
                "Tool-recovery, coding-agent, or personalization-memory family mean score drops below baseline by more than 0.02.",
                "Any social-support task becomes robotic, unsafe, or ignores the user's requested tone.",
                "A variant improves speed but loses scenario coverage needed by Avi's personal-agent workload.",
            ],
            "success_criteria": [
                "Memory or latency improves versus baseline.",
                "Overall personal-agent mean score is at least baseline minus 0.01.",
                "No task family drops below its baseline minimum score.",
                "Routing analysis shows no protected task-hot expert was removed or overwritten.",
            ],
        },
        "commands": {
            "generate_bank": "npm run make-personal-agent-bank",
            "smoke_eval": "python3 scripts/run_kv_cache_eval.py --tasks data/personal_agent_bank/tasks.jsonl --runs-dir data/personal_agent_bank/runs --limit 8 --reasoning-sweep on,off --cache-config balanced:q8_0:q5_1",
            "full_eval": "npm run eval:personal-agent-bank:both",
            "routing": "npm run calibrate:personal-agent",
            "analyze": "npm run analyze:experts",
        },
        "warnings": analysis.get("surgery_warnings", []),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"variants: {', '.join(variant['name'] for variant in plan['variants'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
