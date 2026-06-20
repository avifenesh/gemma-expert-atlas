#!/usr/bin/env python3
"""Create static-mask and runtime-residency plans from timeline evidence."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LLAMA_CPP = Path(os.environ.get("LLAMA_CPP", str(Path.home() / "projects" / "llama.cpp")))
GGUF_PY = LLAMA_CPP / "gguf-py"
DEFAULT_TIMELINE_SUMMARY = ROOT / "data" / "surgery_experiments" / "early_only_candidates.json"
DEFAULT_MANIFEST = ROOT / "public" / "data" / "expert_manifest.json"
DEFAULT_GGUF = Path(os.environ.get("GEMMA4_GGUF", "/data/ai-ml/hf-models/gemma4-26ba4b-qat-gguf/gemma-4-26B_q4_0-it.gguf"))
DEFAULT_OUT = ROOT / "data" / "surgery_experiments" / "runtime_eviction_plan.json"

sys.path.insert(0, str(GGUF_PY))
from gguf import GGUFReader  # noqa: E402


EXPERT_ID_RE = re.compile(r"^L(?P<layer>\d+)\.E(?P<expert>\d+)$")
GGUF_EXPERT_SUFFIXES = [
    "ffn_down_exps.weight",
    "ffn_gate_up_exps.weight",
    "ffn_down_exps.scale",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def human_bytes(value: int) -> str:
    units = ["B", "KiB", "MiB", "GiB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.2f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    raise AssertionError("unreachable")


def index_manifest(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {expert["id"]: expert for expert in manifest.get("experts", [])}


def parse_expert_id(expert_id: str) -> tuple[int, int]:
    match = EXPERT_ID_RE.fullmatch(expert_id)
    if match is None:
        raise ValueError(f"invalid expert id: {expert_id}")
    return int(match["layer"]), int(match["expert"])


def gguf_expert_bytes(path: Path, expert_ids: list[str]) -> tuple[dict[str, int], int]:
    if not path.exists():
        return {}, 0
    reader = GGUFReader(str(path), "r")
    tensors = {tensor.name: tensor for tensor in reader.tensors}
    by_id: dict[str, int] = {}
    for expert_id in expert_ids:
        layer, expert = parse_expert_id(expert_id)
        total = 0
        for suffix in GGUF_EXPERT_SUFFIXES:
            tensor = tensors[f"blk.{layer}.{suffix}"]
            shape = [int(value) for value in tensor.shape]
            total += int(tensor.n_bytes) // shape[-1]
            if shape[-1] <= expert:
                raise ValueError(f"{expert_id} cannot index blk.{layer}.{suffix} with shape {shape}")
        by_id[expert_id] = total

    total_payload = 0
    for tensor in reader.tensors:
        if any(tensor.name.endswith(suffix) for suffix in GGUF_EXPERT_SUFFIXES):
            total_payload += int(tensor.n_bytes)
    return by_id, total_payload


def classify(candidate: dict[str, Any], timeline_count: int) -> str:
    if candidate["decision"] == "never_active_in_timelines":
        return "tier_3_never_active"
    if candidate["early_only_runs"] == timeline_count and candidate["active_runs"] == timeline_count:
        return "tier_0_all_timelines"
    if candidate["early_only_runs"] >= max(2, timeline_count // 2):
        return "tier_1_frequent"
    return "tier_2_sparse"


def select_candidates(data: dict[str, Any], decisions: set[str]) -> list[dict[str, Any]]:
    if decisions == {"evict_after_prefix_candidate"}:
        return list(data.get("evict_after_prefix_candidates", []))
    return [item for item in data.get("experts", []) if item.get("decision") in decisions]


def enrich_candidates(
    candidates: list[dict[str, Any]],
    data: dict[str, Any],
    manifest: dict[str, Any],
    gguf_bytes: dict[str, int],
) -> list[dict[str, Any]]:
    by_id = index_manifest(manifest)
    timeline_count = int(data["source"]["timeline_count"])
    enriched: list[dict[str, Any]] = []
    for candidate in candidates:
        expert = by_id.get(candidate["id"], {})
        base_bytes_value = int(expert.get("total_bytes", 0))
        bytes_value = int(gguf_bytes.get(candidate["id"], base_bytes_value))
        enriched.append(
            {
                **candidate,
                "tier": classify(candidate, timeline_count),
                "evictable_bytes_after_prefix": bytes_value,
                "evictable_human_after_prefix": human_bytes(bytes_value),
                "base_weight_bytes": base_bytes_value,
                "base_weight_human": human_bytes(base_bytes_value),
                "shards": expert.get("shards", []),
                "layer_type": expert.get("layer_type"),
            }
        )
    return enriched


def summarize(candidates: list[dict[str, Any]], total_expert_bytes: int, timeline_count: int) -> dict[str, Any]:
    evictable_bytes = sum(int(item["evictable_bytes_after_prefix"]) for item in candidates)
    by_tier: dict[str, dict[str, Any]] = {}
    for tier in sorted({item["tier"] for item in candidates}):
        rows = [item for item in candidates if item["tier"] == tier]
        tier_bytes = sum(int(item["evictable_bytes_after_prefix"]) for item in rows)
        by_tier[tier] = {
            "count": len(rows),
            "evictable_bytes_after_prefix": tier_bytes,
            "evictable_human_after_prefix": human_bytes(tier_bytes),
        }
    return {
        "candidate_count": len(candidates),
        "timeline_count": timeline_count,
        "evictable_bytes_after_prefix": evictable_bytes,
        "evictable_human_after_prefix": human_bytes(evictable_bytes),
        "share_of_expert_payload": evictable_bytes / total_expert_bytes if total_expert_bytes else 0,
        "zero_later_routes": sum(int(item["total_later_count"]) for item in candidates),
        "by_tier": by_tier,
        "by_layer": dict(sorted(Counter(int(item["layer"]) for item in candidates).items())),
    }


def write_candidate_file(path: Path, candidates: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(item["id"] for item in candidates) + "\n", encoding="utf-8")


def write_csv(path: Path, candidates: list[dict[str, Any]]) -> None:
    fields = [
        "id",
        "tier",
        "layer",
        "expert",
        "early_only_runs",
        "active_runs",
        "total_early_count",
        "total_later_count",
        "evictable_human_after_prefix",
        "trim_decision",
        "personal_classification",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in candidates:
            writer.writerow({field: item.get(field) for field in fields})


def write_markdown(path: Path, plan: dict[str, Any]) -> None:
    lines = [
        "# Runtime After-Prefix Eviction Plan",
        "",
        f"Generated: {plan['created_at']}",
        "",
        "## Summary",
        "",
    ]
    summary = plan["summary"]
    lines.extend(
        [
            f"- Candidates: {summary['candidate_count']}",
            f"- Timeline runs: {summary['timeline_count']}",
            f"- Later routes inside candidate set: {summary['zero_later_routes']}",
            f"- Fast-tier bytes reclaimable after prefix: {summary['evictable_human_after_prefix']}",
            f"- Share of expert payload: {summary['share_of_expert_payload'] * 100:.2f}%",
            "",
            "## Tiers",
            "",
            "| Tier | Count | Fast-tier bytes |",
            "|---|---:|---:|",
        ]
    )
    for tier, row in summary["by_tier"].items():
        lines.append(f"| {tier} | {row['count']} | {row['evictable_human_after_prefix']} |")
    lines.extend(
        [
            "",
            "## Top Candidates",
            "",
            "| Expert | Tier | Runs | Early count | Later count | Bytes | Class |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for item in plan["candidates"][:40]:
        lines.append(
            f"| {item['id']} | {item['tier']} | {item['early_only_runs']}/{item['active_runs']} | "
            f"{item['total_early_count']} | {item['total_later_count']} | {item['evictable_human_after_prefix']} | "
            f"{item.get('personal_classification') or ''} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- Probe kind: {plan['probe_kind']}.",
            f"- Candidate file: `{plan['recommended_next_probe']['candidate_file']}`.",
            "- Static masking measures quality risk only; it does not remove MoE compute from llama.cpp.",
            "- A real speed or memory win requires runtime support or a repacked layer-specific expert layout.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline-summary", type=Path, default=DEFAULT_TIMELINE_SUMMARY)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--gguf", type=Path, default=DEFAULT_GGUF)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--candidate-file", type=Path)
    parser.add_argument(
        "--include-never-active",
        action="store_true",
        help="Add experts classified as never active in all timeline runs.",
    )
    parser.add_argument("--probe-name", default="runtime_evict_after_prefix_v0")
    parser.add_argument(
        "--probe-kind",
        default="after_prefix_runtime_residency",
        help="Human-readable kind recorded in the plan.",
    )
    args = parser.parse_args()

    data = read_json(args.timeline_summary)
    manifest = read_json(args.manifest)
    decisions = {"evict_after_prefix_candidate"}
    if args.include_never_active:
        decisions.add("never_active_in_timelines")
    raw_candidates = select_candidates(data, decisions)
    candidate_ids = [item["id"] for item in raw_candidates]
    gguf_bytes, gguf_total_expert_bytes = gguf_expert_bytes(args.gguf, candidate_ids)
    candidates = enrich_candidates(raw_candidates, data, manifest, gguf_bytes)
    total_expert_bytes = gguf_total_expert_bytes or int(
        sum(int(expert.get("total_bytes", 0)) for expert in manifest.get("experts", []))
    )
    timeline_count = int(data["source"]["timeline_count"])
    plan = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "probe_name": args.probe_name,
        "probe_kind": args.probe_kind,
        "source": {
            "timeline_summary": str(args.timeline_summary),
            "manifest": str(args.manifest),
            "gguf": str(args.gguf) if args.gguf.exists() else None,
        },
        "summary": summarize(candidates, total_expert_bytes, timeline_count),
        "candidates": candidates,
        "recommended_next_probe": {
            "name": f"{args.probe_name}_static_mask",
            "kind": "static_mask_quality_probe",
            "candidate_file": str(args.candidate_file or args.out.with_suffix(".txt")),
            "note": (
                "Use this only as a quality-risk probe. It cannot show runtime speedup because the "
                "GGUF layout and MoE compute shape are unchanged."
            ),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    candidate_file = args.candidate_file or args.out.with_suffix(".txt")
    candidate_file.parent.mkdir(parents=True, exist_ok=True)
    write_candidate_file(candidate_file, candidates)
    write_csv(args.out.with_suffix(".csv"), candidates)
    write_markdown(args.out.with_suffix(".md"), plan)
    print(f"wrote {args.out}")
    print(f"wrote {candidate_file}")
    print(json.dumps(plan["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
