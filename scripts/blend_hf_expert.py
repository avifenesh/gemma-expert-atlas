#!/usr/bin/env python3
"""Blend one same-layer HF/safetensors expert toward another expert."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import struct
import subprocess
from typing import Any

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = pathlib.Path(os.environ.get("GEMMA4_BASE_MODEL_DIR", "/data/ai-ml/hf-models/gemma4-26ba4b-base"))
DEFAULT_MANIFEST = ROOT / "public" / "data" / "expert_manifest.json"
DEFAULT_OUT_ROOT = pathlib.Path(os.environ.get("GEMMA4_SURGERY_DIR", "/data/ai-ml/hf-models/gemma4-26ba4b-surgery")) / "hf_blends"
DEFAULT_REPORT_DIR = ROOT / "data" / "surgery_experiments" / "blend_experiments"


EXPERT_RE = re.compile(r"^L(?P<layer>\d+)\.E(?P<expert>\d+)$")
EXPERT_TENSOR_KEYS = ("experts_down", "experts_gate_up")
FLOAT_DTYPE_SIZES = {"BF16": 2, "F16": 2, "F32": 4}


def parse_expert_id(value: str) -> tuple[int, int]:
    match = EXPERT_RE.fullmatch(value)
    if not match:
        raise argparse.ArgumentTypeError(f"invalid expert id: {value}")
    return int(match["layer"]), int(match["expert"])


def read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def slug_weight(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", "p")


def copy_file(source: pathlib.Path, output: pathlib.Path, force: bool) -> str:
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


def copy_checkpoint(source_dir: pathlib.Path, output_dir: pathlib.Path, force: bool) -> list[dict[str, str]]:
    if output_dir.exists():
        if not force:
            raise SystemExit(f"output directory exists; use --force to replace: {output_dir}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    copied: list[dict[str, str]] = []
    for child in sorted(source_dir.iterdir()):
        destination = output_dir / child.name
        if child.is_dir():
            shutil.copytree(child, destination, symlinks=True)
            copied.append({"path": child.name, "method": "shutil.copytree"})
        elif child.is_symlink():
            destination.symlink_to(os.readlink(child))
            copied.append({"path": child.name, "method": "symlink"})
        elif child.is_file():
            copied.append({"path": child.name, "method": copy_file(child, destination, force=False)})
    return copied


def safetensors_data_start(path: pathlib.Path) -> int:
    with path.open("rb") as handle:
        header_len = struct.unpack("<Q", handle.read(8))[0]
    return 8 + int(header_len)


def bf16_to_f32(values: np.ndarray[Any, np.dtype[np.uint16]]) -> np.ndarray[Any, np.dtype[np.float32]]:
    return (values.astype(np.uint32) << 16).view(np.float32)


def f32_to_bf16(values: np.ndarray[Any, np.dtype[np.float32]]) -> np.ndarray[Any, np.dtype[np.uint16]]:
    bits = values.astype(np.float32, copy=False).view(np.uint32)
    lsb = (bits >> 16) & 1
    rounded = bits + np.uint32(0x7FFF) + lsb
    return (rounded >> 16).astype(np.uint16)


def decode_float(raw: bytes, dtype: str) -> np.ndarray[Any, np.dtype[np.float32]]:
    if dtype == "BF16":
        return bf16_to_f32(np.frombuffer(raw, dtype="<u2"))
    if dtype == "F16":
        return np.frombuffer(raw, dtype="<f2").astype(np.float32)
    if dtype == "F32":
        return np.frombuffer(raw, dtype="<f4").astype(np.float32)
    raise ValueError(f"unsupported dtype for numeric blend: {dtype}")


def encode_float(values: np.ndarray[Any, np.dtype[np.float32]], dtype: str) -> bytes:
    if dtype == "BF16":
        return f32_to_bf16(values).astype("<u2", copy=False).tobytes()
    if dtype == "F16":
        return values.astype("<f2").tobytes()
    if dtype == "F32":
        return values.astype("<f4").tobytes()
    raise ValueError(f"unsupported dtype for numeric blend: {dtype}")


def float_dtype_size(dtype: str) -> int:
    try:
        return FLOAT_DTYPE_SIZES[dtype]
    except KeyError as exc:
        raise ValueError(f"unsupported dtype for numeric blend: {dtype}") from exc


def expert_slice(tensor: dict[str, Any], expert_index: int, data_start: int) -> tuple[int, int]:
    shape = [int(value) for value in tensor["shape"]]
    if not shape or expert_index < 0 or expert_index >= shape[0]:
        raise ValueError(f"expert {expert_index} cannot index tensor {tensor.get('name')} with shape {shape}")
    start, end = [int(value) for value in tensor["data_offsets"]]
    per_expert = (end - start) // shape[0]
    offset = data_start + start + expert_index * per_expert
    return offset, per_expert


def blend_slice(
    path: pathlib.Path,
    tensor: dict[str, Any],
    base_expert: int,
    donor_expert: int,
    donor_weight: float,
    chunk_bytes: int,
) -> dict[str, Any]:
    dtype = str(tensor["dtype"]).upper()
    data_start = safetensors_data_start(path)
    base_offset, size = expert_slice(tensor, base_expert, data_start)
    donor_offset, donor_size = expert_slice(tensor, donor_expert, data_start)
    if donor_size != size:
        raise ValueError(f"slice size mismatch for {tensor['name']}: {size} vs {donor_size}")
    item_size = float_dtype_size(dtype)
    if chunk_bytes < item_size:
        raise ValueError(f"--chunk-bytes must be at least {item_size} for {dtype}")
    chunk_bytes -= chunk_bytes % item_size
    base_weight = 1.0 - donor_weight

    with path.open("r+b") as handle:
        for relative in range(0, size, chunk_bytes):
            read_size = min(chunk_bytes, size - relative)
            handle.seek(base_offset + relative)
            base_raw = handle.read(read_size)
            handle.seek(donor_offset + relative)
            donor_raw = handle.read(read_size)
            base = decode_float(base_raw, dtype)
            donor = decode_float(donor_raw, dtype)
            blended = base * base_weight + donor * donor_weight
            handle.seek(base_offset + relative)
            handle.write(encode_float(blended, dtype))

    return {
        "bytes": size,
        "dtype": dtype,
        "file": path.name,
        "tensor": tensor["name"],
    }


def blend_router_scale(
    path: pathlib.Path,
    tensor: dict[str, Any],
    base_expert: int,
    donor_expert: int,
    donor_weight: float,
) -> dict[str, Any]:
    dtype = str(tensor["dtype"]).upper()
    return blend_slice(path, tensor, base_expert, donor_expert, donor_weight, chunk_bytes=float_dtype_size(dtype))


def planned_tensor(tensor: dict[str, Any], base_expert: int) -> dict[str, Any]:
    shape = [int(value) for value in tensor["shape"]]
    start, end = [int(value) for value in tensor["data_offsets"]]
    return {
        "bytes": (end - start) // shape[0],
        "dtype": str(tensor["dtype"]).upper(),
        "expert_index": base_expert,
        "file": tensor["file"],
        "tensor": tensor["name"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=pathlib.Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--base-expert", required=True, help="Expert slot to modify, e.g. L08.E054.")
    parser.add_argument("--donor-expert", required=True, help="Same-layer donor expert, e.g. L08.E018.")
    parser.add_argument("--donor-weight", type=float, required=True, help="Blend weight for donor expert, between 0 and 1.")
    parser.add_argument("--out-dir", type=pathlib.Path)
    parser.add_argument("--out-root", type=pathlib.Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--report-dir", type=pathlib.Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--chunk-bytes", type=int, default=64 * 1024 * 1024)
    parser.add_argument("--include-router-scale", action="store_true", help="Also blend router.per_expert_scale for the same expert slot.")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned patch without copying or modifying a checkpoint.")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not 0.0 <= args.donor_weight <= 1.0:
        raise SystemExit("--donor-weight must be between 0 and 1")
    base_layer, base_expert = parse_expert_id(args.base_expert)
    donor_layer, donor_expert = parse_expert_id(args.donor_expert)
    if base_layer != donor_layer:
        raise SystemExit("base and donor experts must be in the same layer")
    if base_expert == donor_expert:
        raise SystemExit("base and donor experts must be different")

    manifest = read_json(args.manifest)
    if manifest.get("model", {}).get("dtype") not in {"bfloat16", "float16", "float32"}:
        raise SystemExit(f"unsupported model dtype: {manifest.get('model', {}).get('dtype')}")
    layer = next((item for item in manifest["layers"] if int(item["layer"]) == base_layer), None)
    if layer is None:
        raise SystemExit(f"layer not found in manifest: {base_layer}")

    model_dir = args.model_dir.expanduser()
    if not model_dir.exists():
        raise SystemExit(f"model directory not found: {model_dir}")

    if args.out_dir:
        out_dir = args.out_dir.expanduser()
    else:
        out_name = f"{model_dir.name}.blend_{args.base_expert.replace('.', '_')}_toward_{args.donor_expert.replace('.', '_')}_w{slug_weight(args.donor_weight)}"
        out_dir = args.out_root.expanduser() / out_name

    planned = [planned_tensor(layer["tensors"][tensor_key], base_expert) for tensor_key in EXPERT_TENSOR_KEYS]
    if args.include_router_scale and "router_per_expert_scale" in layer["tensors"]:
        planned.append(planned_tensor(layer["tensors"]["router_per_expert_scale"], base_expert))

    if args.dry_run:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "dry_run": True,
                    "model_dir": str(model_dir),
                    "output_dir": str(out_dir),
                    "base_expert": args.base_expert,
                    "donor_expert": args.donor_expert,
                    "base_weight": 1.0 - args.donor_weight,
                    "donor_weight": args.donor_weight,
                    "planned": planned,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    copied = copy_checkpoint(model_dir, out_dir, args.force)
    patched: list[dict[str, Any]] = []
    for tensor_key in EXPERT_TENSOR_KEYS:
        tensor = layer["tensors"][tensor_key]
        path = out_dir / tensor["file"]
        patched.append(blend_slice(path, tensor, base_expert, donor_expert, args.donor_weight, args.chunk_bytes))

    if args.include_router_scale and "router_per_expert_scale" in layer["tensors"]:
        tensor = layer["tensors"]["router_per_expert_scale"]
        path = out_dir / tensor["file"]
        patched.append(blend_router_scale(path, tensor, base_expert, donor_expert, args.donor_weight))

    report = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "model_dir": str(model_dir),
        "output_dir": str(out_dir),
        "base_expert": args.base_expert,
        "donor_expert": args.donor_expert,
        "base_weight": 1.0 - args.donor_weight,
        "donor_weight": args.donor_weight,
        "include_router_scale": args.include_router_scale,
        "copied": copied,
        "patched": patched,
        "next_step": "Quantize this blended HF checkpoint to GGUF, then run the focused guard eval before a full bank eval.",
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.report_dir / f"blend_{args.base_expert.replace('.', '_')}_toward_{args.donor_expert.replace('.', '_')}_w{slug_weight(args.donor_weight)}.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"wrote {out_dir}")
    print(f"report {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
