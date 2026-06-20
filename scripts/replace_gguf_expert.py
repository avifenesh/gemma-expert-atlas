#!/usr/bin/env python3
"""Create a GGUF copy where one expert slot is replaced by another same-layer expert."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
LLAMA_CPP = pathlib.Path(os.environ.get("LLAMA_CPP", str(pathlib.Path.home() / "projects" / "llama.cpp")))
GGUF_PY = LLAMA_CPP / "gguf-py"
DEFAULT_SOURCE = pathlib.Path(os.environ.get("GEMMA4_GGUF", "/data/ai-ml/hf-models/gemma4-26ba4b-qat-gguf/gemma-4-26B_q4_0-it.gguf"))
DEFAULT_OUT_DIR = pathlib.Path(os.environ.get("GEMMA4_SURGERY_DIR", "/data/ai-ml/hf-models/gemma4-26ba4b-surgery"))
DEFAULT_MANIFEST_DIR = ROOT / "data" / "surgery_experiments" / "replaced_models"

sys.path.insert(0, str(GGUF_PY))
from gguf import GGUFReader  # noqa: E402


PROJECTION_SUFFIXES = [
    "ffn_down_exps.weight",
    "ffn_gate_up_exps.weight",
    "ffn_down_exps.scale",
]


def parse_expert_id(expert_id: str) -> tuple[int, int]:
    match = re.fullmatch(r"L(\d+)\.E(\d+)", expert_id)
    if not match:
        raise ValueError(f"invalid expert id: {expert_id}")
    return int(match.group(1)), int(match.group(2))


def tensor_by_name(reader: GGUFReader) -> dict[str, Any]:
    return {tensor.name: tensor for tensor in reader.tensors}


def copy_model(source: pathlib.Path, output: pathlib.Path, force: bool) -> str:
    if output.exists():
        if not force:
            return "existing"
        output.unlink()

    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["cp", "--reflink=auto", "--sparse=always", str(source), str(output)], check=True)
        return "cp --reflink=auto --sparse=always"
    except (OSError, subprocess.CalledProcessError):
        shutil.copy2(source, output)
        return "shutil.copy2"


def expert_range(tensor: Any, expert: int) -> dict[str, Any]:
    shape = [int(value) for value in tensor.shape]
    if not shape or shape[-1] <= expert:
        raise ValueError(f"expert {expert} cannot index tensor {tensor.name} with shape {shape}")
    per_expert_bytes = int(tensor.n_bytes) // shape[-1]
    offset = int(tensor.data_offset) + expert * per_expert_bytes
    return {
        "tensor": tensor.name,
        "tensor_type": str(tensor.tensor_type),
        "shape": shape,
        "offset": offset,
        "bytes": per_expert_bytes,
        "end": offset + per_expert_bytes,
    }


def replacement_ranges(reader: GGUFReader, source_id: str, target_id: str) -> list[dict[str, Any]]:
    source_layer, source_expert = parse_expert_id(source_id)
    target_layer, target_expert = parse_expert_id(target_id)
    if source_layer != target_layer:
        raise ValueError(f"replacement must be same-layer: {source_id} vs {target_id}")

    tensors = tensor_by_name(reader)
    ranges: list[dict[str, Any]] = []
    for suffix in PROJECTION_SUFFIXES:
        tensor_name = f"blk.{source_layer}.{suffix}"
        tensor = tensors.get(tensor_name)
        if tensor is None:
            raise KeyError(f"tensor not found: {tensor_name}")
        source_range = expert_range(tensor, source_expert)
        target_range = expert_range(tensor, target_expert)
        ranges.append(
            {
                "source_expert_id": source_id,
                "target_expert_id": target_id,
                "layer": source_layer,
                "tensor": tensor_name,
                "source": source_range,
                "target": target_range,
            }
        )
    return ranges


def copy_ranges(path: pathlib.Path, ranges: list[dict[str, Any]], chunk_size: int) -> None:
    with path.open("r+b") as handle:
        for item in ranges:
            source_range = item["source"]
            target_range = item["target"]
            if int(source_range["bytes"]) != int(target_range["bytes"]):
                raise ValueError(f"range size mismatch for {item['tensor']}")
            remaining = int(source_range["bytes"])
            source_offset = int(source_range["offset"])
            target_offset = int(target_range["offset"])
            done = 0
            while remaining:
                n = min(chunk_size, remaining)
                handle.seek(target_offset + done)
                raw = handle.read(n)
                if len(raw) != n:
                    raise ValueError(f"short read for {item['tensor']}: {len(raw)} != {n}")
                handle.seek(source_offset + done)
                handle.write(raw)
                done += n
                remaining -= n


def verify_replacement(path: pathlib.Path, ranges: list[dict[str, Any]], sample_bytes: int = 4096) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with path.open("rb") as handle:
        for item in ranges:
            source_range = item["source"]
            target_range = item["target"]
            n = min(sample_bytes, int(source_range["bytes"]))
            handle.seek(int(source_range["offset"]))
            source_raw = handle.read(n)
            handle.seek(int(target_range["offset"]))
            target_raw = handle.read(n)
            checks.append(
                {
                    "tensor": item["tensor"],
                    "sample_bytes": n,
                    "source_matches_target": source_raw == target_raw,
                    "source_offset": source_range["offset"],
                    "target_offset": target_range["offset"],
                }
            )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-model", type=pathlib.Path, default=DEFAULT_SOURCE)
    parser.add_argument("--source-expert", required=True, help="Expert slot to overwrite, e.g. L08.E054.")
    parser.add_argument("--target-expert", required=True, help="Same-layer expert to copy from, e.g. L08.E096.")
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--out-dir", type=pathlib.Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest-dir", type=pathlib.Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=8 * 1024 * 1024)
    args = parser.parse_args()

    model = args.source_model.expanduser().resolve()
    if not model.exists():
        raise SystemExit(f"source model not found: {model}")

    if args.out is None:
        output = args.out_dir / f"{model.stem}.{args.source_expert}_replaced_by_{args.target_expert}.gguf"
    else:
        output = args.out
    output = output.expanduser().resolve()

    copy_method = copy_model(model, output, args.force)
    reader = GGUFReader(str(output), "r")
    ranges = replacement_ranges(reader, args.source_expert, args.target_expert)
    copy_ranges(output, ranges, args.chunk_size)
    verification = verify_replacement(output, ranges)
    if not all(item["source_matches_target"] for item in verification):
        raise SystemExit(f"replacement verification failed: {verification}")

    copied_bytes = sum(int(item["source"]["bytes"]) for item in ranges)
    manifest = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "source_model": str(model),
        "output": str(output),
        "copy_method": copy_method,
        "source_expert": args.source_expert,
        "target_expert": args.target_expert,
        "copied_range_count": len(ranges),
        "copied_bytes": copied_bytes,
        "copied_mib": copied_bytes / (1024 * 1024),
        "ranges": ranges,
        "verification": verification,
        "note": (
            "This is a substitution probe, not a true merge. It tests whether the target expert can "
            "stand in when the router selects the source expert slot."
        ),
    }
    args.manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.manifest_dir / f"{output.stem}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"wrote replaced model: {output}")
    print(f"wrote manifest: {manifest_path}")
    print(f"source expert: {args.source_expert}")
    print(f"target expert: {args.target_expert}")
    print(f"copied ranges: {len(ranges)}")
    print(f"copied bytes: {copied_bytes} ({copied_bytes / (1024 * 1024):.2f} MiB)")
    print(f"copy method: {copy_method}")
    print(f"size: {os.path.getsize(output)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
