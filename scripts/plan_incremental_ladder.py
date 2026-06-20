#!/usr/bin/env python3
"""Plan slow cumulative expert-mask ladder steps."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "data" / "surgery_experiments" / "runtime_eviction_plan.json"
DEFAULT_OUT_DIR = ROOT / "data" / "surgery_experiments" / "incremental_ladder"

TIER_RANK = {
    "tier_0_all_timelines": 0,
    "tier_1_frequent": 1,
    "tier_2_sparse": 2,
    "tier_3_never_active": 3,
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_").replace(".", "_")


def human_bytes(value: int) -> str:
    units = ["B", "KiB", "MiB", "GiB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.2f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    raise AssertionError("unreachable")


def candidate_sort_key(item: dict[str, Any]) -> tuple[int, int, int, int, int, int, int, str]:
    return (
        TIER_RANK.get(str(item.get("tier", "")), 99),
        -int(item.get("early_only_runs", 0)),
        -int(item.get("active_runs", 0)),
        int(item.get("total_later_count", 0)),
        -int(item.get("total_early_count", 0)),
        int(item.get("layer", 999)),
        int(item.get("expert", 999)),
        str(item.get("id", "")),
    )


def write_expert_file(path: Path, expert_ids: list[str]) -> None:
    path.write_text("\n".join(expert_ids) + "\n", encoding="utf-8")


def read_expert_file(path: Path) -> list[str]:
    expert_ids: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.split("#", 1)[0].strip()
        if value:
            expert_ids.append(value)
    return expert_ids


def write_csv(path: Path, steps: list[dict[str, Any]]) -> None:
    fields = [
        "step",
        "stage",
        "added_expert",
        "tier",
        "layer",
        "expert",
        "early_only_runs",
        "active_runs",
        "total_early_count",
        "total_later_count",
        "cumulative_experts",
        "cumulative_human",
        "candidate_file",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for step in steps:
            candidate = step["candidate"]
            writer.writerow(
                {
                    "step": step["step"],
                    "stage": step["stage"],
                    "added_expert": step["added_expert"],
                    "tier": candidate.get("tier"),
                    "layer": candidate.get("layer"),
                    "expert": candidate.get("expert"),
                    "early_only_runs": candidate.get("early_only_runs"),
                    "active_runs": candidate.get("active_runs"),
                    "total_early_count": candidate.get("total_early_count"),
                    "total_later_count": candidate.get("total_later_count"),
                    "cumulative_experts": len(step["cumulative_experts"]),
                    "cumulative_human": step["cumulative_human"],
                    "candidate_file": step["candidate_file"],
                }
            )


def write_markdown(path: Path, plan: dict[str, Any]) -> None:
    lines = [
        "# Incremental Expert Mask Ladder",
        "",
        f"Generated: {plan['created_at']}",
        "",
        "## Rule",
        "",
        "- Each step adds exactly one expert to the previous accepted set.",
        "- The default order starts with experts that were active only in the early window across every timeline.",
        "- Static masking is a quality-risk probe only; speed and memory wins require a repacked/runtime layout.",
        "",
        "## Steps",
        "",
        "| Step | Add | Tier | Runs | Early | Later | Cumulative | File |",
        "|---:|---|---|---:|---:|---:|---:|---|",
    ]
    for step in plan["steps"]:
        candidate = step["candidate"]
        lines.append(
            f"| {step['step']} | {step['added_expert']} | {candidate.get('tier')} | "
            f"{candidate.get('early_only_runs')}/{candidate.get('active_runs')} | "
            f"{candidate.get('total_early_count')} | {candidate.get('total_later_count')} | "
            f"{step['cumulative_human']} | `{step['candidate_file']}` |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--max-steps", type=int, default=46)
    parser.add_argument(
        "--tier",
        action="append",
        default=[],
        help="Optional tier filter. Repeatable. Defaults to all tiers in the source plan.",
    )
    parser.add_argument("--exclude", action="append", default=[], help="Expert id to exclude from the ladder.")
    parser.add_argument("--exclude-file", action="append", type=Path, default=[], help="File with expert ids to exclude.")
    parser.add_argument("--prefix", default="early_then_silent_ladder")
    args = parser.parse_args()

    source = read_json(args.plan)
    candidates = list(source.get("candidates", []))
    excluded = set(args.exclude)
    for path in args.exclude_file:
        excluded.update(read_expert_file(path))
    if excluded:
        candidates = [item for item in candidates if item.get("id") not in excluded]
    if args.tier:
        wanted = set(args.tier)
        candidates = [item for item in candidates if item.get("tier") in wanted]
    candidates = sorted(candidates, key=candidate_sort_key)[: args.max_steps]
    if not candidates:
        raise SystemExit("no candidates selected")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    cumulative: list[str] = []
    cumulative_bytes = 0
    steps: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, start=1):
        expert_id = str(candidate["id"])
        cumulative.append(expert_id)
        cumulative_bytes += int(candidate.get("evictable_bytes_after_prefix", 0))
        stage = f"{args.prefix}_step_{index:03d}_{slug(expert_id)}"
        candidate_file = args.out_dir / f"step_{index:03d}_{slug(expert_id)}.txt"
        write_expert_file(candidate_file, cumulative)
        steps.append(
            {
                "step": index,
                "stage": stage,
                "added_expert": expert_id,
                "candidate": candidate,
                "cumulative_experts": list(cumulative),
                "cumulative_bytes": cumulative_bytes,
                "cumulative_human": human_bytes(cumulative_bytes),
                "candidate_file": str(candidate_file),
            }
        )

    output = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "source_plan": str(args.plan),
        "prefix": args.prefix,
        "excluded_experts": sorted(excluded),
        "sort_order": [
            "tier",
            "early_only_runs desc",
            "active_runs desc",
            "total_later_count asc",
            "total_early_count desc",
            "layer asc",
            "expert asc",
        ],
        "gate_note": (
            "Run each cumulative step against the same baseline. Accept a step only if protected "
            "reasoning-off categories stay flat enough for the intended use."
        ),
        "steps": steps,
    }

    json_path = args.out_dir / "ladder_plan.json"
    csv_path = args.out_dir / "ladder_plan.csv"
    md_path = args.out_dir / "ladder_plan.md"
    json_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, steps)
    write_markdown(md_path, output)
    print(f"wrote {json_path}")
    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")
    print(json.dumps({"steps": len(steps), "first": steps[0], "last": steps[-1]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
