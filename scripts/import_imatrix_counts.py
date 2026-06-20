#!/usr/bin/env python3
"""Import llama.cpp imatrix MoE expert counts into Expert Atlas routing JSON."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import struct
from collections import defaultdict
from typing import Any, BinaryIO


GGUF_TYPE_UINT8 = 0
GGUF_TYPE_INT8 = 1
GGUF_TYPE_UINT16 = 2
GGUF_TYPE_INT16 = 3
GGUF_TYPE_UINT32 = 4
GGUF_TYPE_INT32 = 5
GGUF_TYPE_FLOAT32 = 6
GGUF_TYPE_BOOL = 7
GGUF_TYPE_STRING = 8
GGUF_TYPE_ARRAY = 9
GGUF_TYPE_UINT64 = 10
GGUF_TYPE_INT64 = 11
GGUF_TYPE_FLOAT64 = 12

GGML_TYPE_F32 = 0
GGML_TYPE_SIZE = {
    GGML_TYPE_F32: 4,
}


def read_u32(handle: BinaryIO) -> int:
    return struct.unpack("<I", handle.read(4))[0]


def read_u64(handle: BinaryIO) -> int:
    return struct.unpack("<Q", handle.read(8))[0]


def read_string(handle: BinaryIO) -> str:
    length = read_u64(handle)
    return handle.read(length).decode("utf-8")


def read_scalar(handle: BinaryIO, value_type: int) -> Any:
    if value_type == GGUF_TYPE_UINT8:
        return struct.unpack("<B", handle.read(1))[0]
    if value_type == GGUF_TYPE_INT8:
        return struct.unpack("<b", handle.read(1))[0]
    if value_type == GGUF_TYPE_UINT16:
        return struct.unpack("<H", handle.read(2))[0]
    if value_type == GGUF_TYPE_INT16:
        return struct.unpack("<h", handle.read(2))[0]
    if value_type == GGUF_TYPE_UINT32:
        return read_u32(handle)
    if value_type == GGUF_TYPE_INT32:
        return struct.unpack("<i", handle.read(4))[0]
    if value_type == GGUF_TYPE_FLOAT32:
        return struct.unpack("<f", handle.read(4))[0]
    if value_type == GGUF_TYPE_BOOL:
        return struct.unpack("<?", handle.read(1))[0]
    if value_type == GGUF_TYPE_STRING:
        return read_string(handle)
    if value_type == GGUF_TYPE_UINT64:
        return read_u64(handle)
    if value_type == GGUF_TYPE_INT64:
        return struct.unpack("<q", handle.read(8))[0]
    if value_type == GGUF_TYPE_FLOAT64:
        return struct.unpack("<d", handle.read(8))[0]
    raise ValueError(f"unsupported GGUF scalar type {value_type}")


def read_kv_value(handle: BinaryIO, value_type: int) -> Any:
    if value_type != GGUF_TYPE_ARRAY:
        return read_scalar(handle, value_type)
    item_type = read_u32(handle)
    count = read_u64(handle)
    return [read_scalar(handle, item_type) for _ in range(count)]


def align(value: int, alignment: int) -> int:
    return value if value % alignment == 0 else value + alignment - (value % alignment)


def read_gguf(path: pathlib.Path) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    with path.open("rb") as handle:
        magic = handle.read(4)
        if magic != b"GGUF":
            raise ValueError(f"{path} is not a GGUF file")
        version = read_u32(handle)
        if version not in (2, 3):
            raise ValueError(f"unsupported GGUF version {version}")
        tensor_count = read_u64(handle)
        kv_count = read_u64(handle)

        kvs: dict[str, Any] = {}
        for _ in range(kv_count):
            key = read_string(handle)
            value_type = read_u32(handle)
            kvs[key] = read_kv_value(handle, value_type)

        tensors: list[dict[str, Any]] = []
        for _ in range(tensor_count):
            name = read_string(handle)
            n_dims = read_u32(handle)
            dims = [read_u64(handle) for _ in range(n_dims)]
            ggml_type = read_u32(handle)
            offset = read_u64(handle)
            tensors.append({"name": name, "dims": dims, "type": ggml_type, "offset": offset})

        alignment = int(kvs.get("general.alignment", 32))
        data_offset = align(handle.tell(), alignment)
        return kvs, tensors, data_offset


def tensor_element_count(dims: list[int]) -> int:
    count = 1
    for dim in dims:
        count *= dim
    return count


def read_f32_tensor(path: pathlib.Path, tensor: dict[str, Any], data_offset: int) -> list[float]:
    if tensor["type"] != GGML_TYPE_F32:
        raise ValueError(f"{tensor['name']} is not F32")
    count = tensor_element_count(tensor["dims"])
    with path.open("rb") as handle:
        handle.seek(data_offset + tensor["offset"])
        raw = handle.read(count * GGML_TYPE_SIZE[GGML_TYPE_F32])
    return list(struct.unpack(f"<{count}f", raw))


def layer_from_tensor_name(name: str) -> int | None:
    match = re.search(r"(?:^|\.)blk\.(\d+)\.", name)
    if match:
        return int(match.group(1))
    return None


def score_counts_tensor(name: str) -> int:
    lowered = name.lower()
    if "ffn_down" in lowered:
        return 4
    if "ffn_gate" in lowered or "ffn_up" in lowered:
        return 3
    if "exp" in lowered or "moe" in lowered:
        return 2
    return 1


def import_counts(manifest_path: pathlib.Path, imatrix_path: pathlib.Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    kvs, tensors, data_offset = read_gguf(imatrix_path)

    counts_by_layer: dict[int, list[tuple[str, list[float]]]] = defaultdict(list)
    for tensor in tensors:
        name = tensor["name"]
        if not name.endswith(".counts"):
            continue
        if tensor["dims"] not in ([1, manifest["model"]["num_experts"]], [manifest["model"]["num_experts"], 1]):
            continue
        layer = layer_from_tensor_name(name)
        if layer is None:
            continue
        counts = read_f32_tensor(imatrix_path, tensor, data_offset)
        counts_by_layer[layer].append((name, counts))

    layers = []
    experts = []
    total_selections = 0
    for layer_record in manifest["layers"]:
        layer = layer_record["layer"]
        candidates = counts_by_layer.get(layer, [])
        if candidates:
            tensor_name, counts = sorted(candidates, key=lambda item: score_counts_tensor(item[0]), reverse=True)[0]
        else:
            tensor_name, counts = "", [0.0] * manifest["model"]["num_experts"]

        int_counts = [int(round(value)) for value in counts]
        layer_total = sum(int_counts)
        total_selections += layer_total
        nonzero = sum(1 for value in int_counts if value > 0)
        max_count = max(int_counts) if int_counts else 0
        min_nonzero = min((value for value in int_counts if value > 0), default=0)
        mean = layer_total / len(int_counts) if int_counts else 0

        layers.append(
            {
                "layer": layer,
                "layer_label": layer_record["layer_label"],
                "layer_type": layer_record["layer_type"],
                "source_tensor": tensor_name,
                "total_selections": layer_total,
                "nonzero_experts": nonzero,
                "zero_experts": len(int_counts) - nonzero,
                "max_count": max_count,
                "min_nonzero_count": min_nonzero,
                "mean_count": mean,
                "counts": int_counts,
            }
        )

        denom = layer_total if layer_total else 1
        for expert, count in enumerate(int_counts):
            experts.append(
                {
                    "id": f"L{layer:02d}.E{expert:03d}",
                    "layer": layer,
                    "expert": expert,
                    "count": count,
                    "share": count / denom,
                    "rank": 1 + sum(1 for other in int_counts if other > count),
                }
            )

    hot = sorted(experts, key=lambda item: item["count"], reverse=True)[:24]
    cold = sorted(experts, key=lambda item: (item["count"], item["layer"], item["expert"]))[:24]

    return {
        "schema_version": 1,
        "status": "ready",
        "source": {
            "kind": "llama.cpp imatrix",
            "imatrix_path": str(imatrix_path),
            "datasets": kvs.get("imatrix.datasets", []),
            "chunk_count": kvs.get("imatrix.chunk_count"),
            "chunk_size": kvs.get("imatrix.chunk_size"),
        },
        "model": {
            "num_layers": manifest["model"]["num_hidden_layers"],
            "num_experts": manifest["model"]["num_experts"],
            "top_k_experts": manifest["model"]["top_k_experts"],
        },
        "summary": {
            "total_selections": total_selections,
            "max_count": max((expert["count"] for expert in experts), default=0),
            "zero_expert_slots": sum(1 for expert in experts if expert["count"] == 0),
            "nonzero_expert_slots": sum(1 for expert in experts if expert["count"] > 0),
            "layers_with_counts": sum(1 for layer in layers if layer["total_selections"] > 0),
        },
        "layers": layers,
        "experts": experts,
        "hot_experts": hot,
        "cold_experts": cold,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path, default=pathlib.Path("public/data/expert_manifest.json"))
    parser.add_argument("--imatrix", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("public/data/routing_trace.json"))
    parser.add_argument("--label", default="routing")
    args = parser.parse_args()

    routing = import_counts(args.manifest, args.imatrix)
    routing["label"] = args.label
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(routing, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    print(f"layers with counts: {routing['summary']['layers_with_counts']}")
    print(f"total selections: {routing['summary']['total_selections']}")
    print(f"zero expert slots: {routing['summary']['zero_expert_slots']}")


if __name__ == "__main__":
    main()
