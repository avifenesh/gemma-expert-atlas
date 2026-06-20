#!/usr/bin/env python3
"""Classify MoE experts from task-family routing traces."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACES = ROOT / "public" / "data" / "personal_agent_routing_traces.json"
FALLBACK_TRACES = ROOT / "public" / "data" / "theme_routing_traces.json"
DEFAULT_MANIFEST = ROOT / "public" / "data" / "expert_manifest.json"
DEFAULT_OUT = ROOT / "data" / "expert_usage_analysis.json"
DEFAULT_PUBLIC_OUT = ROOT / "public" / "data" / "expert_usage_analysis.json"


def load_bundle(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text())
    if path == DEFAULT_TRACES and FALLBACK_TRACES.exists():
        return json.loads(FALLBACK_TRACES.read_text())
    raise SystemExit(f"trace bundle not found: {path}")


def iter_runs(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for theme, mode_traces in bundle.get("traces", {}).items():
        for mode, trace in mode_traces.items():
            runs.append({"theme": theme, "mode": mode, "trace": trace, "name": f"{theme}:{mode}"})
    return runs


def vector_cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def classify(metrics: dict[str, Any], args: argparse.Namespace) -> str:
    if metrics["active_runs"] == 0:
        return "globally_dead"
    if metrics["active_rate"] >= args.always_hot_active_rate and metrics["mean_share"] >= args.always_hot_mean_share:
        return "always_hot_protect"
    if metrics["top_rank_runs"] >= args.protect_top_rank_runs or metrics["max_share"] >= args.protect_max_share:
        return "task_hot_protect"
    if metrics["active_rate"] <= args.cold_active_rate and metrics["max_share"] <= args.cold_max_share:
        return "cold_trim_candidate"
    if metrics["active_rate"] <= args.low_use_active_rate and metrics["max_share"] <= args.low_use_max_share:
        return "low_use_merge_candidate"
    return "ordinary"


def cap_by_layer(items: list[dict[str, Any]], max_per_layer: int) -> list[dict[str, Any]]:
    by_layer: dict[int, int] = defaultdict(int)
    capped = []
    for item in items:
        layer = int(item["layer"])
        if by_layer[layer] >= max_per_layer:
            continue
        by_layer[layer] += 1
        capped.append(item)
    return capped


def build_metrics(manifest: dict[str, Any], runs: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    run_names = [run["name"] for run in runs]
    profiles: dict[str, list[float]] = {}
    experts_by_id = {expert["id"]: expert for expert in manifest["experts"]}
    observations: dict[str, list[dict[str, Any]]] = {expert_id: [] for expert_id in experts_by_id}

    for run in runs:
        for expert in run["trace"].get("experts", []):
            observations.setdefault(expert["id"], []).append(
                {
                    "theme": run["theme"],
                    "mode": run["mode"],
                    "count": int(expert.get("count", 0)),
                    "share": float(expert.get("share", 0.0)),
                    "rank": int(expert.get("rank", 999999)),
                }
            )

    rows: list[dict[str, Any]] = []
    for expert_id, manifest_expert in experts_by_id.items():
        obs_by_run = {(obs["theme"], obs["mode"]): obs for obs in observations.get(expert_id, [])}
        counts: list[int] = []
        shares: list[float] = []
        ranks: list[int] = []
        hot_runs: list[str] = []
        active_runs = 0
        top_rank_runs = 0

        for run in runs:
            obs = obs_by_run.get((run["theme"], run["mode"]), {"count": 0, "share": 0.0, "rank": 999999})
            count = int(obs["count"])
            share = float(obs["share"])
            rank = int(obs["rank"])
            counts.append(count)
            shares.append(share)
            ranks.append(rank)
            if count > 0:
                active_runs += 1
            if rank <= args.top_rank:
                top_rank_runs += 1
                hot_runs.append(run["name"])

        profile = shares
        profiles[expert_id] = profile
        total_runs = len(runs) or 1
        mean_share = sum(shares) / total_runs
        active_rate = active_runs / total_runs
        sorted_shares = sorted(shares, reverse=True)
        max_share = sorted_shares[0] if sorted_shares else 0.0
        second_share = sorted_shares[1] if len(sorted_shares) > 1 else 0.0
        burst_ratio = max_share / (mean_share + 1e-12)
        row = {
            "id": expert_id,
            "layer": int(manifest_expert["layer"]),
            "expert": int(manifest_expert["expert"]),
            "layer_type": manifest_expert.get("layer_type"),
            "total_count": sum(counts),
            "active_runs": active_runs,
            "active_rate": active_rate,
            "zero_runs": total_runs - active_runs,
            "mean_share": mean_share,
            "max_share": max_share,
            "second_share": second_share,
            "burst_ratio": burst_ratio,
            "best_rank": min(ranks) if ranks else None,
            "top_rank_runs": top_rank_runs,
            "hot_runs": hot_runs[:8],
            "classification": "",
        }
        row["classification"] = classify(row, args)
        rows.append(row)

    merge_candidates = [row for row in rows if row["classification"] == "low_use_merge_candidate"]
    ordinary_or_hot = [
        row
        for row in rows
        if row["classification"] in {"ordinary", "task_hot_protect", "always_hot_protect"}
    ]
    by_layer_candidates: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in ordinary_or_hot:
        by_layer_candidates[int(row["layer"])].append(row)

    for row in merge_candidates:
        candidates = [item for item in by_layer_candidates[int(row["layer"])] if item["id"] != row["id"]]
        scored = [
            (vector_cosine(profiles[row["id"]], profiles[item["id"]]), item)
            for item in candidates
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        if scored:
            row["routing_merge_target"] = {
                "id": scored[0][1]["id"],
                "similarity": scored[0][0],
                "warning": "routing-profile similarity only; require weight-space check before merging",
            }
    return rows


def summarize(rows: list[dict[str, Any]], runs: list[dict[str, Any]]) -> dict[str, Any]:
    by_class: dict[str, int] = defaultdict(int)
    for row in rows:
        by_class[row["classification"]] += 1
    return {
        "run_count": len(runs),
        "runs": [run["name"] for run in runs],
        "expert_count": len(rows),
        "classification_counts": dict(sorted(by_class.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--traces", type=Path, default=DEFAULT_TRACES)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--public-out", type=Path, default=DEFAULT_PUBLIC_OUT)
    parser.add_argument("--top-rank", type=int, default=8)
    parser.add_argument("--protect-top-rank-runs", type=int, default=2)
    parser.add_argument("--protect-max-share", type=float, default=0.035)
    parser.add_argument("--always-hot-active-rate", type=float, default=0.90)
    parser.add_argument("--always-hot-mean-share", type=float, default=0.012)
    parser.add_argument("--cold-active-rate", type=float, default=0.10)
    parser.add_argument("--cold-max-share", type=float, default=0.0015)
    parser.add_argument("--low-use-active-rate", type=float, default=0.35)
    parser.add_argument("--low-use-max-share", type=float, default=0.006)
    parser.add_argument("--max-trim-per-layer", type=int, default=8)
    parser.add_argument("--max-candidates", type=int, default=160)
    args = parser.parse_args()

    bundle = load_bundle(args.traces)
    manifest = json.loads(args.manifest.read_text())
    runs = iter_runs(bundle)
    rows = build_metrics(manifest, runs, args)

    trim_candidates = sorted(
        [row for row in rows if row["classification"] in {"globally_dead", "cold_trim_candidate"}],
        key=lambda row: (row["total_count"], row["active_rate"], row["max_share"], row["layer"], row["expert"]),
    )
    merge_candidates = sorted(
        [row for row in rows if row["classification"] == "low_use_merge_candidate"],
        key=lambda row: (row["active_rate"], row["max_share"], row["total_count"], row["layer"], row["expert"]),
    )
    protected = sorted(
        [row for row in rows if row["classification"] in {"always_hot_protect", "task_hot_protect"}],
        key=lambda row: (-row["max_share"], -row["top_rank_runs"], row["layer"], row["expert"]),
    )
    task_hot = sorted(
        [row for row in rows if row["classification"] == "task_hot_protect"],
        key=lambda row: (-row["burst_ratio"], -row["max_share"], row["layer"], row["expert"]),
    )
    capped_trim = cap_by_layer(trim_candidates, args.max_trim_per_layer)

    output = {
        "schema_version": 1,
        "source": {
            "traces": str(args.traces if args.traces.exists() else FALLBACK_TRACES),
            "manifest": str(args.manifest),
            "note": "routing-only usage analysis; merge/add decisions need eval and weight-similarity evidence",
        },
        "thresholds": {
            "top_rank": args.top_rank,
            "protect_top_rank_runs": args.protect_top_rank_runs,
            "protect_max_share": args.protect_max_share,
            "always_hot_active_rate": args.always_hot_active_rate,
            "always_hot_mean_share": args.always_hot_mean_share,
            "cold_active_rate": args.cold_active_rate,
            "cold_max_share": args.cold_max_share,
            "low_use_active_rate": args.low_use_active_rate,
            "low_use_max_share": args.low_use_max_share,
            "max_trim_per_layer": args.max_trim_per_layer,
        },
        "summary": summarize(rows, runs),
        "candidates": {
            "trim": capped_trim[: args.max_candidates],
            "trim_uncapped_count": len(trim_candidates),
            "merge": merge_candidates[: args.max_candidates],
            "protected": protected[: args.max_candidates],
            "task_hot": task_hot[: args.max_candidates],
        },
        "experts": sorted(rows, key=lambda row: (row["layer"], row["expert"])),
        "surgery_warnings": [
            "Do not delete globally cold experts until a baseline eval and a trimmed-model eval are both available.",
            "Do not merge low-use experts from routing alone; add a weight-space similarity check first.",
            "Do not add experts by copying tensors alone; adding capacity requires router adaptation and a task-specific eval win.",
            "Protect any expert that is task-hot in a narrow personal-agent family even if it is cold globally.",
        ],
    }

    for path in (args.out, args.public_out):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {path}")
    print(json.dumps(output["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
