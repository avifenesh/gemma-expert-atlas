#!/usr/bin/env python3
"""Score candidate MoE expert merges with direct weight-space similarity."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import pathlib
import re
import struct
from functools import lru_cache
from typing import Any

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = pathlib.Path("/data/ai-ml/hf-models/gemma4-26ba4b-base")
DEFAULT_USAGE = ROOT / "data" / "expert_usage_analysis.json"
DEFAULT_PLAN = ROOT / "data" / "surgery_experiments" / "plan.json"
DEFAULT_OUT = ROOT / "data" / "surgery_experiments" / "merge_weight_similarity.json"


def read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def parse_expert_id(expert_id: str) -> tuple[int, int]:
    match = re.fullmatch(r"L(\d+)\.E(\d+)", expert_id)
    if not match:
        raise ValueError(f"invalid expert id: {expert_id}")
    return int(match.group(1)), int(match.group(2))


def product(values: list[int]) -> int:
    out = 1
    for value in values:
        out *= value
    return out


def tensor_name(layer: int, projection: str) -> str:
    if projection == "gate_up":
        return f"model.language_model.layers.{layer}.experts.gate_up_proj"
    if projection == "down":
        return f"model.language_model.layers.{layer}.experts.down_proj"
    raise ValueError(f"unknown projection: {projection}")


def read_safetensors_header(path: pathlib.Path) -> tuple[int, dict[str, Any]]:
    with path.open("rb") as handle:
        raw_len = handle.read(8)
        if len(raw_len) != 8:
            raise ValueError(f"{path} is too small to be a safetensors file")
        header_len = struct.unpack("<Q", raw_len)[0]
        header = json.loads(handle.read(header_len))
    return header_len, {name: meta for name, meta in header.items() if name != "__metadata__"}


class SliceReader:
    def __init__(self, model_dir: pathlib.Path):
        self.model_dir = model_dir
        index = read_json(model_dir / "model.safetensors.index.json")
        self.weight_map: dict[str, str] = index["weight_map"]

    @lru_cache(maxsize=None)
    def header(self, file_name: str) -> tuple[int, dict[str, Any]]:
        return read_safetensors_header(self.model_dir / file_name)

    def read_expert_slice(self, expert_id: str, projection: str) -> np.ndarray:
        layer, expert = parse_expert_id(expert_id)
        name = tensor_name(layer, projection)
        file_name = self.weight_map[name]
        header_len, tensors = self.header(file_name)
        meta = tensors[name]
        dtype = meta["dtype"]
        shape = meta["shape"]
        if expert >= shape[0]:
            raise ValueError(f"{expert_id} exceeds first dimension of {name}: {shape[0]}")

        data_start, data_end = meta["data_offsets"]
        slice_bytes = (data_end - data_start) // shape[0]
        file_offset = 8 + header_len + data_start + expert * slice_bytes

        with (self.model_dir / file_name).open("rb") as handle:
            handle.seek(file_offset)
            raw = handle.read(slice_bytes)
        if len(raw) != slice_bytes:
            raise ValueError(f"short read for {expert_id} {projection}: {len(raw)} != {slice_bytes}")

        return decode_weight_bytes(raw, dtype, product(shape[1:]))


def decode_weight_bytes(raw: bytes, dtype: str, expected_values: int) -> np.ndarray:
    if dtype == "BF16":
        values = np.frombuffer(raw, dtype="<u2")
        arr = (values.astype(np.uint32) << 16).view(np.float32)
    elif dtype == "F16":
        arr = np.frombuffer(raw, dtype="<f2").astype(np.float32)
    elif dtype == "F32":
        arr = np.frombuffer(raw, dtype="<f4")
    else:
        raise ValueError(f"unsupported dtype for expert similarity: {dtype}")

    if arr.size != expected_values:
        raise ValueError(f"decoded {arr.size} values, expected {expected_values}")
    return arr


def vector_stats(source: np.ndarray, target: np.ndarray) -> dict[str, float | int]:
    if source.shape != target.shape:
        raise ValueError(f"shape mismatch: {source.shape} != {target.shape}")

    diff = source - target
    dot = float(np.dot(source, target))
    source_norm_sq = float(np.dot(source, source))
    target_norm_sq = float(np.dot(target, target))
    denom = math.sqrt(source_norm_sq * target_norm_sq)
    cosine = dot / denom if denom else 0.0
    source_norm = math.sqrt(source_norm_sq)
    target_norm = math.sqrt(target_norm_sq)

    return {
        "values": int(source.size),
        "cosine": cosine,
        "dot": dot,
        "source_norm": source_norm,
        "target_norm": target_norm,
        "norm_ratio": source_norm / target_norm if target_norm else 0.0,
        "mean_abs_delta": float(np.mean(np.abs(diff))),
        "rms_delta": float(np.sqrt(np.mean(diff * diff))),
    }


def combined_cosine(parts: list[dict[str, float | int]]) -> float:
    dot = sum(float(part["dot"]) for part in parts)
    source_norm_sq = sum(float(part["source_norm"]) ** 2 for part in parts)
    target_norm_sq = sum(float(part["target_norm"]) ** 2 for part in parts)
    denom = math.sqrt(source_norm_sq * target_norm_sq)
    return dot / denom if denom else 0.0


def routing_clean(source: dict[str, Any], target: dict[str, Any], routing_similarity: float) -> bool:
    protected = {"always_hot_protect", "task_hot_protect"}
    return (
        not source.get("hot_runs")
        and target["classification"] not in protected
        and routing_similarity >= 0.7
        and source["total_count"] <= 20
        and source["active_runs"] <= 9
        and source["best_rank"] >= 100
    )


def score_pair(pair: dict[str, Any], reader: SliceReader, experts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source_id = pair["source"]
    target_id = pair["target"]
    source_usage = experts[source_id]
    target_usage = experts[target_id]

    gate_up = vector_stats(reader.read_expert_slice(source_id, "gate_up"), reader.read_expert_slice(target_id, "gate_up"))
    down = vector_stats(reader.read_expert_slice(source_id, "down"), reader.read_expert_slice(target_id, "down"))
    combined = combined_cosine([gate_up, down])

    return {
        "source": source_id,
        "target": target_id,
        "routing_similarity": pair["routing_similarity"],
        "routing_clean": routing_clean(source_usage, target_usage, pair["routing_similarity"]),
        "combined_cosine": combined,
        "gate_up": gate_up,
        "down": down,
        "source_usage": {
            "classification": source_usage["classification"],
            "total_count": source_usage["total_count"],
            "active_runs": source_usage["active_runs"],
            "zero_runs": source_usage["zero_runs"],
            "best_rank": source_usage["best_rank"],
            "max_share": source_usage["max_share"],
            "hot_runs": source_usage.get("hot_runs", []),
        },
        "target_usage": {
            "classification": target_usage["classification"],
            "total_count": target_usage["total_count"],
            "active_runs": target_usage["active_runs"],
            "zero_runs": target_usage["zero_runs"],
            "best_rank": target_usage["best_rank"],
            "max_share": target_usage["max_share"],
            "hot_runs": target_usage.get("hot_runs", []),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=pathlib.Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--usage", type=pathlib.Path, default=DEFAULT_USAGE)
    parser.add_argument("--plan", type=pathlib.Path, default=DEFAULT_PLAN)
    parser.add_argument("--variant", default="merge_low_use_v1")
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=0, help="Score only the first N routing pairs after plan ordering")
    args = parser.parse_args()

    usage = read_json(args.usage)
    plan = read_json(args.plan)
    variants = {variant["name"]: variant for variant in plan["variants"]}
    if args.variant not in variants:
        raise SystemExit(f"variant not found: {args.variant}")

    pairs = variants[args.variant].get("candidate_pairs", [])
    if args.limit:
        pairs = pairs[: args.limit]

    experts = {expert["id"]: expert for expert in usage["experts"]}
    reader = SliceReader(args.model_dir.expanduser().resolve())

    scored = [score_pair(pair, reader, experts) for pair in pairs]
    by_combined = sorted(scored, key=lambda row: row["combined_cosine"], reverse=True)
    by_routing_clean = sorted(
        [row for row in scored if row["routing_clean"]],
        key=lambda row: (row["combined_cosine"], row["routing_similarity"]),
        reverse=True,
    )

    out = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "model_dir": str(reader.model_dir),
        "usage_path": str(args.usage),
        "plan_path": str(args.plan),
        "variant": args.variant,
        "scored_pair_count": len(scored),
        "notes": [
            "Cosine is computed on aligned flattened tensor slices.",
            "This does not prove functional equivalence; hidden-unit permutations can hide similarity.",
            "Use this as a merge prefilter before ablation evals, not as the eval itself.",
        ],
        "top_by_weight": by_combined[:20],
        "top_routing_clean_by_weight": by_routing_clean[:20],
        "pairs": scored,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    print(f"scored pairs: {len(scored)}")
    if by_routing_clean:
        best = by_routing_clean[0]
        print(
            "best routing-clean by weight: "
            f"{best['source']} -> {best['target']} "
            f"combined={best['combined_cosine']:.6f} "
            f"gate_up={best['gate_up']['cosine']:.6f} "
            f"down={best['down']['cosine']:.6f}"
        )
    if by_combined:
        best = by_combined[0]
        print(
            "best overall by weight: "
            f"{best['source']} -> {best['target']} "
            f"combined={best['combined_cosine']:.6f} "
            f"gate_up={best['gate_up']['cosine']:.6f} "
            f"down={best['down']['cosine']:.6f}"
        )


if __name__ == "__main__":
    main()
