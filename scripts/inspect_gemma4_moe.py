#!/usr/bin/env python3
"""Build a static MoE expert manifest from a Gemma 4 HF checkpoint.

This intentionally avoids torch/transformers/safetensors dependencies. The
safetensors header contains tensor names, dtypes, shapes, and byte offsets, so
we can map the checkpoint without touching the large weight payloads.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import pathlib
import re
import struct
from collections import Counter, defaultdict
from typing import Any


DTYPE_BYTES = {
    "F64": 8,
    "F32": 4,
    "F16": 2,
    "BF16": 2,
    "I64": 8,
    "I32": 4,
    "I16": 2,
    "I8": 1,
    "U8": 1,
    "BOOL": 1,
}


def read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def read_safetensors_header(path: pathlib.Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        raw_len = handle.read(8)
        if len(raw_len) != 8:
            raise ValueError(f"{path} is too small to be a safetensors file")
        header_len = struct.unpack("<Q", raw_len)[0]
        header = json.loads(handle.read(header_len))

    tensors: dict[str, Any] = {}
    for name, meta in header.items():
        if name == "__metadata__":
            continue
        start, end = meta["data_offsets"]
        tensors[name] = {
            "dtype": meta["dtype"],
            "shape": meta["shape"],
            "data_offsets": [start, end],
            "bytes": end - start,
        }
    return {
        "header_bytes": header_len,
        "metadata": header.get("__metadata__", {}),
        "tensors": tensors,
    }


def product(values: list[int]) -> int:
    out = 1
    for value in values:
        out *= value
    return out


def tensor_bytes_from_shape(dtype: str, shape: list[int]) -> int:
    return product(shape) * DTYPE_BYTES.get(dtype, 0)


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


def tensor_pattern(name: str) -> str:
    name = re.sub(r"\.layers\.\d+\.", ".layers.N.", name)
    name = re.sub(r"\.experts\.\d+\.", ".experts.E.", name)
    return name


def shard_number(file_name: str) -> int | None:
    match = re.search(r"model-(\d+)-of-\d+\.safetensors", file_name)
    if not match:
        return None
    return int(match.group(1))


def packed_expert_slice(tensor: dict[str, Any], expert: int) -> dict[str, Any] | None:
    shape = tensor["shape"]
    if not shape or shape[0] <= expert:
        return None
    start, end = tensor["data_offsets"]
    slice_bytes = (end - start) // shape[0]
    return {
        "relative_offsets": [start + expert * slice_bytes, start + (expert + 1) * slice_bytes],
        "bytes": slice_bytes,
        "human_bytes": human_bytes(slice_bytes),
    }


def build_manifest(model_dir: pathlib.Path) -> dict[str, Any]:
    config = read_json(model_dir / "config.json")
    index = read_json(model_dir / "model.safetensors.index.json")
    weight_map: dict[str, str] = index["weight_map"]
    text_config = config["text_config"]
    shard_names = sorted(set(weight_map.values()))

    shard_headers: dict[str, Any] = {}
    for shard in shard_names:
        shard_path = model_dir / shard
        header = read_safetensors_header(shard_path)
        shard_headers[shard] = {
            **header,
            "file_size": shard_path.stat().st_size,
        }

    tensor_map: dict[str, dict[str, Any]] = {}
    for name, file_name in weight_map.items():
        header_tensors = shard_headers[file_name]["tensors"]
        if name not in header_tensors:
            raise KeyError(f"{name} is in index but not in {file_name}")
        meta = header_tensors[name]
        expected_bytes = tensor_bytes_from_shape(meta["dtype"], meta["shape"])
        tensor_map[name] = {
            "name": name,
            "file": file_name,
            "shard_number": shard_number(file_name),
            "dtype": meta["dtype"],
            "shape": meta["shape"],
            "data_offsets": meta["data_offsets"],
            "bytes": meta["bytes"],
            "human_bytes": human_bytes(meta["bytes"]),
            "expected_bytes": expected_bytes,
            "matches_shape_bytes": expected_bytes == meta["bytes"],
            "pattern": tensor_pattern(name),
        }

    num_layers = int(text_config["num_hidden_layers"])
    num_experts = int(text_config["num_experts"])
    top_k = int(text_config["top_k_experts"])
    layer_types = text_config["layer_types"]

    layers: list[dict[str, Any]] = []
    expert_records: list[dict[str, Any]] = []
    layer_type_counts: Counter[str] = Counter()
    split_expert_layers: list[int] = []

    for layer in range(num_layers):
        prefix = f"model.language_model.layers.{layer}"
        layer_type = layer_types[layer]
        layer_type_counts[layer_type] += 1

        names = {
            "experts_down": f"{prefix}.experts.down_proj",
            "experts_gate_up": f"{prefix}.experts.gate_up_proj",
            "router_proj": f"{prefix}.router.proj.weight",
            "router_scale": f"{prefix}.router.scale",
            "router_per_expert_scale": f"{prefix}.router.per_expert_scale",
            "shared_mlp_down": f"{prefix}.mlp.down_proj.weight",
            "shared_mlp_gate": f"{prefix}.mlp.gate_proj.weight",
            "shared_mlp_up": f"{prefix}.mlp.up_proj.weight",
        }

        found = {key: tensor_map[name] for key, name in names.items() if name in tensor_map}
        layer_tensor_names = [name for name in tensor_map if name.startswith(prefix + ".")]
        layer_bytes = sum(tensor_map[name]["bytes"] for name in layer_tensor_names)
        expert_group_bytes = sum(found[key]["bytes"] for key in ("experts_down", "experts_gate_up") if key in found)
        router_bytes = sum(found[key]["bytes"] for key in ("router_proj", "router_scale", "router_per_expert_scale") if key in found)
        shared_mlp_bytes = sum(found[key]["bytes"] for key in ("shared_mlp_down", "shared_mlp_gate", "shared_mlp_up") if key in found)

        expert_files = sorted({found[key]["file"] for key in ("experts_down", "experts_gate_up") if key in found})
        expert_shards = sorted({found[key]["shard_number"] for key in ("experts_down", "experts_gate_up") if key in found})
        if len(expert_files) > 1:
            split_expert_layers.append(layer)

        per_expert_bytes = 0
        for key in ("experts_down", "experts_gate_up"):
            if key in found:
                per_expert_bytes += found[key]["bytes"] // num_experts

        layer_entry = {
            "layer": layer,
            "layer_label": f"L{layer:02d}",
            "layer_type": layer_type,
            "is_full_attention": layer_type == "full_attention",
            "bytes": layer_bytes,
            "human_bytes": human_bytes(layer_bytes),
            "expert_group_bytes": expert_group_bytes,
            "expert_group_human_bytes": human_bytes(expert_group_bytes),
            "per_expert_bytes": per_expert_bytes,
            "per_expert_human_bytes": human_bytes(per_expert_bytes),
            "router_bytes": router_bytes,
            "router_human_bytes": human_bytes(router_bytes),
            "shared_mlp_bytes": shared_mlp_bytes,
            "shared_mlp_human_bytes": human_bytes(shared_mlp_bytes),
            "expert_files": expert_files,
            "expert_shards": expert_shards,
            "is_expert_split_across_shards": len(expert_files) > 1,
            "tensors": found,
        }
        layers.append(layer_entry)

        for expert in range(num_experts):
            down_slice = packed_expert_slice(found["experts_down"], expert) if "experts_down" in found else None
            gate_up_slice = packed_expert_slice(found["experts_gate_up"], expert) if "experts_gate_up" in found else None
            expert_records.append(
                {
                    "id": f"L{layer:02d}.E{expert:03d}",
                    "layer": layer,
                    "expert": expert,
                    "layer_type": layer_type,
                    "is_full_attention": layer_type == "full_attention",
                    "files": expert_files,
                    "shards": expert_shards,
                    "is_split_across_shards": len(expert_files) > 1,
                    "total_bytes": per_expert_bytes,
                    "human_total_bytes": human_bytes(per_expert_bytes),
                    "down_proj": {
                        "file": found["experts_down"]["file"],
                        "shape": found["experts_down"]["shape"],
                        "slice": down_slice,
                    }
                    if "experts_down" in found
                    else None,
                    "gate_up_proj": {
                        "file": found["experts_gate_up"]["file"],
                        "shape": found["experts_gate_up"]["shape"],
                        "slice": gate_up_slice,
                    }
                    if "experts_gate_up" in found
                    else None,
                    "routing": None,
                }
            )

    shard_stats = []
    tensors_by_file: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for tensor in tensor_map.values():
        tensors_by_file[tensor["file"]].append(tensor)

    for shard in shard_names:
        tensors = tensors_by_file[shard]
        text_bytes = sum(t["bytes"] for t in tensors if t["name"].startswith("model.language_model."))
        vision_bytes = sum(t["bytes"] for t in tensors if t["name"].startswith("model.vision_tower."))
        shard_stats.append(
            {
                "file": shard,
                "shard_number": shard_number(shard),
                "file_size": shard_headers[shard]["file_size"],
                "human_file_size": human_bytes(shard_headers[shard]["file_size"]),
                "header_bytes": shard_headers[shard]["header_bytes"],
                "tensor_count": len(tensors),
                "tensor_bytes": sum(t["bytes"] for t in tensors),
                "human_tensor_bytes": human_bytes(sum(t["bytes"] for t in tensors)),
                "text_bytes": text_bytes,
                "human_text_bytes": human_bytes(text_bytes),
                "vision_bytes": vision_bytes,
                "human_vision_bytes": human_bytes(vision_bytes),
            }
        )

    pattern_counts = Counter(tensor["pattern"] for tensor in tensor_map.values())
    tensor_patterns = [
        {"pattern": pattern, "count": count}
        for pattern, count in sorted(pattern_counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    total_expert_bytes = sum(layer["expert_group_bytes"] for layer in layers)
    total_router_bytes = sum(layer["router_bytes"] for layer in layers)
    total_shared_mlp_bytes = sum(layer["shared_mlp_bytes"] for layer in layers)
    total_layer_bytes = sum(layer["bytes"] for layer in layers)

    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "model_dir": str(model_dir),
        "model": {
            "architecture": config.get("architectures", ["unknown"])[0],
            "model_type": config.get("model_type"),
            "text_model_type": text_config.get("model_type"),
            "dtype": config.get("dtype") or text_config.get("dtype"),
            "num_hidden_layers": num_layers,
            "num_experts": num_experts,
            "top_k_experts": top_k,
            "hidden_size": text_config.get("hidden_size"),
            "moe_intermediate_size": text_config.get("moe_intermediate_size"),
            "intermediate_size": text_config.get("intermediate_size"),
            "max_position_embeddings": text_config.get("max_position_embeddings"),
            "sliding_window": text_config.get("sliding_window"),
            "vocab_size": text_config.get("vocab_size"),
            "total_parameters": int(index.get("metadata", {}).get("total_parameters", 0)),
            "total_size": int(index.get("metadata", {}).get("total_size", 0)),
            "human_total_size": human_bytes(int(index.get("metadata", {}).get("total_size", 0))),
            "layer_type_counts": dict(layer_type_counts),
        },
        "summary": {
            "tensor_count": len(tensor_map),
            "shard_count": len(shard_names),
            "expert_record_count": len(expert_records),
            "total_layer_bytes": total_layer_bytes,
            "human_total_layer_bytes": human_bytes(total_layer_bytes),
            "total_expert_group_bytes": total_expert_bytes,
            "human_total_expert_group_bytes": human_bytes(total_expert_bytes),
            "total_router_bytes": total_router_bytes,
            "human_total_router_bytes": human_bytes(total_router_bytes),
            "total_shared_mlp_bytes": total_shared_mlp_bytes,
            "human_total_shared_mlp_bytes": human_bytes(total_shared_mlp_bytes),
            "expert_layers_split_across_shards": split_expert_layers,
            "expert_layer_split_count": len(split_expert_layers),
            "per_layer_expert_bytes_mean": math.floor(total_expert_bytes / max(num_layers, 1)),
            "per_expert_bytes": layers[0]["per_expert_bytes"] if layers else 0,
            "human_per_expert_bytes": human_bytes(layers[0]["per_expert_bytes"] if layers else 0),
        },
        "shards": shard_stats,
        "layers": layers,
        "experts": expert_records,
        "tensor_patterns": tensor_patterns,
        "routing_trace": {
            "status": "pending",
            "description": "Static manifest only. Add calibration traces later to populate usage and probability overlays.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=pathlib.Path, required=True, help="HF checkpoint directory")
    parser.add_argument("--out", type=pathlib.Path, required=True, help="Output manifest JSON path")
    args = parser.parse_args()

    model_dir = args.model_dir.expanduser().resolve()
    if not model_dir.exists():
        raise SystemExit(f"model directory does not exist: {model_dir}")

    manifest = build_manifest(model_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    print(f"model: {manifest['model']['architecture']} ({manifest['model']['human_total_size']})")
    print(f"experts: {manifest['summary']['expert_record_count']} records")
    print(f"per expert: {manifest['summary']['human_per_expert_bytes']}")
    print(f"expert payload: {manifest['summary']['human_total_expert_group_bytes']}")


if __name__ == "__main__":
    main()
