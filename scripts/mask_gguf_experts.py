#!/usr/bin/env python3
"""Create a GGUF copy with selected MoE experts zero-masked."""

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
DEFAULT_REPORT = ROOT / "data" / "surgery_experiments" / "trim_decision_report.json"
DEFAULT_OUT_DIR = pathlib.Path(os.environ.get("GEMMA4_SURGERY_DIR", "/data/ai-ml/hf-models/gemma4-26ba4b-surgery"))
DEFAULT_MANIFEST_DIR = ROOT / "data" / "surgery_experiments" / "masked_models"

sys.path.insert(0, str(GGUF_PY))
from gguf import GGUFReader  # noqa: E402


def read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def parse_expert_id(expert_id: str) -> tuple[int, int]:
    match = re.fullmatch(r"L(\d+)\.E(\d+)", expert_id)
    if not match:
        raise ValueError(f"invalid expert id: {expert_id}")
    return int(match.group(1)), int(match.group(2))


def stage_experts(report: dict[str, Any], stage_name: str) -> list[str]:
    for stage in report.get("trim_stages", []):
        if stage.get("name") == stage_name:
            return list(stage.get("candidate_experts", []))
    raise KeyError(f"stage not found: {stage_name}")


def read_expert_file(path: pathlib.Path) -> list[str]:
    expert_ids: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.split("#", 1)[0].strip()
        if value:
            expert_ids.append(value)
    return expert_ids


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


def zero_range(handle: Any, offset: int, size: int, chunk_size: int) -> None:
    handle.seek(offset)
    remaining = size
    zero = b"\x00" * min(chunk_size, size)
    while remaining:
        n = min(remaining, len(zero))
        handle.write(zero[:n])
        remaining -= n


def mask_ranges(reader: GGUFReader, expert_ids: list[str], include_router: bool) -> list[dict[str, Any]]:
    tensors = tensor_by_name(reader)
    ranges: list[dict[str, Any]] = []
    projection_suffixes = [
        "ffn_down_exps.weight",
        "ffn_gate_up_exps.weight",
        "ffn_down_exps.scale",
    ]
    if include_router:
        projection_suffixes.append("ffn_gate_inp.weight")

    for expert_id in expert_ids:
        layer, expert = parse_expert_id(expert_id)
        for suffix in projection_suffixes:
            tensor_name = f"blk.{layer}.{suffix}"
            tensor = tensors.get(tensor_name)
            if tensor is None:
                raise KeyError(f"tensor not found: {tensor_name}")

            shape = [int(value) for value in tensor.shape]
            if not shape or shape[-1] <= expert:
                raise ValueError(f"{expert_id} cannot index tensor {tensor_name} with shape {shape}")

            per_expert_bytes = int(tensor.n_bytes) // shape[-1]
            start = int(tensor.data_offset) + expert * per_expert_bytes
            ranges.append(
                {
                    "expert_id": expert_id,
                    "layer": layer,
                    "expert": expert,
                    "tensor": tensor_name,
                    "tensor_type": str(tensor.tensor_type),
                    "shape": shape,
                    "offset": start,
                    "bytes": per_expert_bytes,
                    "end": start + per_expert_bytes,
                }
            )
    return ranges


def verify_zero(path: pathlib.Path, ranges: list[dict[str, Any]], sample_bytes: int = 4096) -> list[dict[str, Any]]:
    checks = []
    with path.open("rb") as handle:
        for item in ranges:
            handle.seek(int(item["offset"]))
            raw = handle.read(min(sample_bytes, int(item["bytes"])))
            checks.append(
                {
                    "expert_id": item["expert_id"],
                    "tensor": item["tensor"],
                    "offset": item["offset"],
                    "sample_bytes": len(raw),
                    "sample_is_zero": all(byte == 0 for byte in raw),
                }
            )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--out-dir", type=pathlib.Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=pathlib.Path, default=DEFAULT_REPORT)
    parser.add_argument("--stage", default="trim_probe_zero_all_v0")
    parser.add_argument("--expert", action="append", default=[], help="Expert id to mask; overrides/extends stage experts")
    parser.add_argument("--expert-file", action="append", type=pathlib.Path, default=[], help="File with one expert id per line.")
    parser.add_argument("--manifest-dir", type=pathlib.Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--mask-router", action="store_true", help="Also zero ffn_gate_inp.weight expert columns")
    parser.add_argument("--chunk-size", type=int, default=8 * 1024 * 1024)
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"source model not found: {source}")

    report = read_json(args.report)
    file_experts = [expert_id for path in args.expert_file for expert_id in read_expert_file(path)]
    manual_experts = [*args.expert, *file_experts]
    try:
        expert_ids = stage_experts(report, args.stage)
    except KeyError:
        if not manual_experts:
            raise SystemExit(f"stage not found: {args.stage}")
        expert_ids = []
    for expert_id in args.expert:
        if expert_id not in expert_ids:
            expert_ids.append(expert_id)
    for expert_id in file_experts:
        if expert_id not in expert_ids:
            expert_ids.append(expert_id)
    if not expert_ids:
        raise SystemExit("no experts selected for masking")

    output = args.out
    if output is None:
        output = args.out_dir / f"{source.stem}.{args.stage}.masked.gguf"
    output = output.expanduser().resolve()

    copy_method = copy_model(source, output, args.force)
    reader = GGUFReader(str(output), "r")
    ranges = mask_ranges(reader, expert_ids, args.mask_router)

    with output.open("r+b") as handle:
        for item in ranges:
            zero_range(handle, int(item["offset"]), int(item["bytes"]), args.chunk_size)

    verification = verify_zero(output, ranges)
    if not all(item["sample_is_zero"] for item in verification):
        bad = [item for item in verification if not item["sample_is_zero"]]
        raise SystemExit(f"zero verification failed: {bad[:3]}")

    masked_bytes = sum(int(item["bytes"]) for item in ranges)
    manifest = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "source": str(source),
        "output": str(output),
        "copy_method": copy_method,
        "stage": args.stage,
        "experts": expert_ids,
        "mask_router": args.mask_router,
        "masked_range_count": len(ranges),
        "masked_bytes": masked_bytes,
        "masked_mib": masked_bytes / (1024 * 1024),
        "ranges": ranges,
        "verification": verification,
        "note": (
            "This is an output-zero mask in a model copy. It does not remove router choices, "
            "and it does not reduce file size or memory until tensors are repacked."
        ),
    }
    args.manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.manifest_dir / f"{output.stem}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"wrote masked model: {output}")
    print(f"wrote manifest: {manifest_path}")
    print(f"experts: {', '.join(expert_ids)}")
    print(f"masked ranges: {len(ranges)}")
    print(f"masked bytes: {masked_bytes} ({masked_bytes / (1024 * 1024):.2f} MiB)")
    print(f"copy method: {copy_method}")
    print(f"size: {os.path.getsize(output)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
