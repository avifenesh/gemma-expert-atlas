#!/usr/bin/env python3
"""Accumulate routing evidence and produce trim-stage decisions."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "public" / "data" / "expert_manifest.json"
DEFAULT_ANALYSIS = ROOT / "data" / "expert_usage_analysis.json"
DEFAULT_PLAN = ROOT / "data" / "surgery_experiments" / "plan.json"
DEFAULT_OUT = ROOT / "data" / "surgery_experiments" / "trim_decision_report.json"
DEFAULT_MD = ROOT / "data" / "surgery_experiments" / "trim_decision_report.md"
DEFAULT_CSV = ROOT / "data" / "surgery_experiments" / "trim_decision_report.csv"
DEFAULT_BUNDLES = [
    ("personal_agent", ROOT / "public" / "data" / "personal_agent_routing_traces.json"),
    ("theme", ROOT / "public" / "data" / "theme_routing_traces.json"),
    ("general", ROOT / "public" / "data" / "routing_traces.json"),
]
PROTECTED = {"always_hot_protect", "task_hot_protect"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def parse_bundle_arg(value: str) -> tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.stem, path
    label, raw_path = value.split("=", 1)
    return label, Path(raw_path)


def iter_bundle_traces(label: str, path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    bundle = read_json(path)
    if "experts" in bundle:
        return [{"dataset": label, "name": label, "mode": None, "trace": bundle}]

    traces = bundle.get("traces", {})
    records: list[dict[str, Any]] = []
    for key, value in traces.items():
        if isinstance(value, dict) and "experts" in value:
            records.append({"dataset": label, "name": f"{label}:{key}", "mode": key, "trace": value})
            continue
        if not isinstance(value, dict):
            continue
        for mode, trace in value.items():
            if isinstance(trace, dict) and "experts" in trace:
                records.append({"dataset": label, "name": f"{label}:{key}:{mode}", "theme": key, "mode": mode, "trace": trace})
    return records


def human_bytes(num_bytes: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(num_bytes)
    for unit in units:
        if abs(value) < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{num_bytes} B"


def cap_by_layer(rows: list[dict[str, Any]], max_per_layer: int, limit: int) -> list[str]:
    counts: dict[int, int] = defaultdict(int)
    out: list[str] = []
    for row in rows:
        layer = int(row["layer"])
        if counts[layer] >= max_per_layer:
            continue
        counts[layer] += 1
        out.append(row["id"])
        if len(out) >= limit:
            break
    return out


def decision_for(row: dict[str, Any]) -> tuple[str, str]:
    if row["personal_classification"] in PROTECTED:
        return "protect", "personal-agent analysis marks this expert protected"
    if row["hot_runs"]:
        return "protect", "expert appears in top-rank hot runs"
    if row["total_count"] == 0:
        return "trim_ablation_candidate", "zero selections across all accumulated traces"
    if row["active_traces"] <= 2 and row["total_count"] <= 4 and row["max_share"] <= 0.00015:
        return "trim_watchlist_cold", "tiny nonzero use; collect more traces before removal"
    if row["personal_classification"] in {"globally_dead", "cold_trim_candidate"}:
        return "needs_more_data", "cold in personal-agent analysis but not cold across all accumulated traces"
    return "keep", "observed enough usage to keep for now"


def build_rows(
    manifest: dict[str, Any],
    analysis: dict[str, Any],
    plan: dict[str, Any],
    trace_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    manifest_experts = {expert["id"]: expert for expert in manifest["experts"]}
    analysis_experts = {expert["id"]: expert for expert in analysis.get("experts", [])}
    trim_plan = set()
    for variant in plan.get("variants", []):
        if variant.get("name") == "trim_cold_v1":
            trim_plan.update(variant.get("candidate_experts", []))

    observations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trace_record in trace_records:
        trace = trace_record["trace"]
        for expert in trace.get("experts", []):
            observations[expert["id"]].append(
                {
                    "dataset": trace_record["dataset"],
                    "run": trace_record["name"],
                    "mode": trace_record.get("mode"),
                    "count": int(expert.get("count", 0)),
                    "share": float(expert.get("share", 0.0)),
                    "rank": int(expert.get("rank", 999999)),
                }
            )

    rows: list[dict[str, Any]] = []
    trace_count = len(trace_records)
    for expert_id, manifest_expert in manifest_experts.items():
        obs_by_run = {obs["run"]: obs for obs in observations.get(expert_id, [])}
        counts: list[int] = []
        shares: list[float] = []
        ranks: list[int] = []
        hot_runs: list[str] = []
        by_dataset: dict[str, dict[str, int]] = defaultdict(lambda: {"traces": 0, "active": 0, "count": 0})
        by_mode: dict[str, dict[str, int]] = defaultdict(lambda: {"traces": 0, "active": 0, "count": 0})

        for trace_record in trace_records:
            dataset = trace_record["dataset"]
            mode = str(trace_record.get("mode") or "unknown")
            obs = obs_by_run.get(trace_record["name"], {"count": 0, "share": 0.0, "rank": 999999})
            count = int(obs["count"])
            share = float(obs["share"])
            rank = int(obs["rank"])
            counts.append(count)
            shares.append(share)
            ranks.append(rank)
            by_dataset[dataset]["traces"] += 1
            by_dataset[dataset]["count"] += count
            by_mode[mode]["traces"] += 1
            by_mode[mode]["count"] += count
            if count > 0:
                by_dataset[dataset]["active"] += 1
                by_mode[mode]["active"] += 1
            if rank <= 8:
                hot_runs.append(trace_record["name"])

        total_count = sum(counts)
        active_traces = sum(1 for count in counts if count > 0)
        row = {
            "id": expert_id,
            "layer": int(manifest_expert["layer"]),
            "expert": int(manifest_expert["expert"]),
            "layer_type": manifest_expert.get("layer_type"),
            "bytes": int(manifest_expert.get("total_bytes", 0)),
            "human_bytes": manifest_expert.get("human_total_bytes"),
            "trace_count": trace_count,
            "total_count": total_count,
            "active_traces": active_traces,
            "zero_traces": trace_count - active_traces,
            "max_share": max(shares) if shares else 0.0,
            "mean_share": (sum(shares) / trace_count) if trace_count else 0.0,
            "best_rank": min(ranks) if ranks else None,
            "hot_runs": hot_runs[:12],
            "personal_classification": analysis_experts.get(expert_id, {}).get("classification", "unknown"),
            "personal_total_count": analysis_experts.get(expert_id, {}).get("total_count"),
            "personal_active_runs": analysis_experts.get(expert_id, {}).get("active_runs"),
            "in_trim_plan": expert_id in trim_plan,
            "by_dataset": dict(sorted(by_dataset.items())),
            "by_mode": dict(sorted(by_mode.items())),
        }
        decision, reason = decision_for(row)
        row["decision"] = decision
        row["reason"] = reason
        rows.append(row)

    return sorted(rows, key=lambda row: (row["total_count"], row["active_traces"], row["max_share"], row["layer"], row["expert"]))


def summarize(rows: list[dict[str, Any]], trace_records: list[dict[str, Any]]) -> dict[str, Any]:
    by_decision: dict[str, int] = defaultdict(int)
    by_personal_class: dict[str, int] = defaultdict(int)
    for row in rows:
        by_decision[row["decision"]] += 1
        by_personal_class[row["personal_classification"]] += 1
    by_dataset: dict[str, int] = defaultdict(int)
    for trace_record in trace_records:
        by_dataset[trace_record["dataset"]] += 1
    return {
        "expert_count": len(rows),
        "trace_count": len(trace_records),
        "trace_count_by_dataset": dict(sorted(by_dataset.items())),
        "decision_counts": dict(sorted(by_decision.items())),
        "personal_classification_counts": dict(sorted(by_personal_class.items())),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "id",
        "decision",
        "reason",
        "layer",
        "expert",
        "layer_type",
        "total_count",
        "active_traces",
        "zero_traces",
        "max_share",
        "best_rank",
        "personal_classification",
        "personal_total_count",
        "in_trim_plan",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    stages = report["trim_stages"]
    candidates = report["candidates"]
    lines = [
        "# Trim Decision Report",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Summary",
        "",
        f"- Traces accumulated: {summary['trace_count']} ({summary['trace_count_by_dataset']})",
        f"- Experts: {summary['expert_count']}",
        f"- Decisions: {summary['decision_counts']}",
        "",
        "## Stages",
        "",
    ]
    for stage in stages:
        lines.extend(
            [
                f"### {stage['name']}",
                "",
                f"- Decision: {stage['decision']}",
                f"- Candidate count: {len(stage['candidate_experts'])}",
                f"- Estimated packed expert bytes: {stage['human_estimated_expert_bytes']}",
                f"- Note: {stage['note']}",
                "",
                "```text",
                "\n".join(stage["candidate_experts"][:80]) or "(none)",
                "```",
                "",
            ]
        )

    lines.extend(["## Top Zero-Across-All Candidates", "", "| Expert | Layer | Bytes | Personal class |", "|---|---:|---:|---|"])
    for row in candidates["zero_across_all"][:40]:
        lines.append(f"| {row['id']} | {row['layer']} | {row['human_bytes']} | {row['personal_classification']} |")
    lines.extend(["", "## Cold Watchlist", "", "| Expert | Active traces | Total count | Max share | Personal class |", "|---|---:|---:|---:|---|"])
    for row in candidates["cold_watchlist"][:40]:
        lines.append(
            f"| {row['id']} | {row['active_traces']} | {row['total_count']} | {row['max_share']:.6f} | {row['personal_classification']} |"
        )
    lines.extend(
        [
            "",
            "## Rules",
            "",
            "- Routing nominates trim candidates.",
            "- Baseline eval plus trimmed eval decides whether a trim is accepted.",
            "- Router disabling is the reversible probe; memory savings require checkpoint repacking.",
            "- Any task-hot/protected expert is kept regardless of global coldness.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--bundle", action="append", default=[], help="label=path trace bundle; defaults to personal_agent, theme, general")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    parser.add_argument("--csv-out", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--stage0-per-layer", type=int, default=1)
    parser.add_argument("--stage1-per-layer", type=int, default=2)
    parser.add_argument("--stage-limit", type=int, default=64)
    args = parser.parse_args()

    bundles = [parse_bundle_arg(value) for value in args.bundle] if args.bundle else DEFAULT_BUNDLES
    trace_records: list[dict[str, Any]] = []
    bundle_sources = []
    for label, path in bundles:
        records = iter_bundle_traces(label, path)
        trace_records.extend(records)
        bundle_sources.append({"label": label, "path": str(path), "trace_count": len(records)})
    if not trace_records:
        raise SystemExit("no trace records found")

    manifest = read_json(args.manifest)
    analysis = read_json(args.analysis)
    plan = read_json(args.plan)
    rows = build_rows(manifest, analysis, plan, trace_records)

    zero_all = [row for row in rows if row["decision"] == "trim_ablation_candidate"]
    cold_watchlist = [row for row in rows if row["decision"] == "trim_watchlist_cold"]
    needs_more_data = [row for row in rows if row["decision"] == "needs_more_data"]
    protected = [row for row in rows if row["decision"] == "protect"]

    stage0_ids = cap_by_layer(zero_all, args.stage0_per_layer, args.stage_limit)
    stage1_ids = cap_by_layer(zero_all, args.stage1_per_layer, args.stage_limit)
    stage2_pool = zero_all + cold_watchlist
    stage2_ids = cap_by_layer(stage2_pool, args.stage1_per_layer, args.stage_limit)

    def stage(name: str, decision: str, candidate_ids: list[str], note: str) -> dict[str, Any]:
        bytes_total = sum(int(next(row for row in rows if row["id"] == expert_id)["bytes"]) for expert_id in candidate_ids)
        return {
            "name": name,
            "decision": decision,
            "candidate_experts": candidate_ids,
            "estimated_expert_bytes": bytes_total,
            "human_estimated_expert_bytes": human_bytes(bytes_total),
            "note": note,
        }

    report = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "sources": {
            "manifest": str(args.manifest),
            "analysis": str(args.analysis),
            "plan": str(args.plan),
            "trace_bundles": bundle_sources,
        },
        "summary": summarize(rows, trace_records),
        "trim_stages": [
            stage(
                "trim_probe_zero_all_v0",
                "ablate_first",
                stage0_ids,
                "One zero-across-all expert per layer, intended to test the reversible trim path.",
            ),
            stage(
                "trim_zero_all_v1",
                "best_first_trim_candidate",
                stage1_ids,
                "Zero selections across all accumulated traces, capped per layer.",
            ),
            stage(
                "trim_zero_plus_tiny_v2",
                "only_after_v1_eval_passes",
                stage2_ids,
                "Adds tiny nonzero experts only after zero-all trimming passes eval.",
            ),
        ],
        "candidates": {
            "zero_across_all": zero_all,
            "cold_watchlist": cold_watchlist,
            "needs_more_data": needs_more_data[:240],
            "protected": protected[:240],
        },
        "all_experts": rows,
        "rules": [
            "Routing can nominate experts for trim.",
            "Only evals can approve a trim.",
            "A reversible router-disable ablation should come before checkpoint repacking.",
            "Memory savings require physically repacking or deleting expert tensor rows.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(args.md_out, report)
    write_csv(args.csv_out, rows)
    print(f"wrote {args.out}")
    print(f"wrote {args.md_out}")
    print(f"wrote {args.csv_out}")
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    for item in report["trim_stages"]:
        print(f"{item['name']}: {len(item['candidate_experts'])} experts, {item['human_estimated_expert_bytes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
