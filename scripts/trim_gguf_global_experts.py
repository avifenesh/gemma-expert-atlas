#!/usr/bin/env python3
"""Physically remove global MoE expert slots from a GGUF model.

This trims the same expert index in every MoE layer and lowers the model-wide
expert_count metadata. That is the largest surgery stock GGUF/llama.cpp can
represent without a custom per-layer expert map.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys
from typing import Any

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[1]
LLAMA_CPP = pathlib.Path(os.environ.get("LLAMA_CPP", str(pathlib.Path.home() / "projects" / "llama.cpp")))
GGUF_PY = LLAMA_CPP / "gguf-py"
DEFAULT_SOURCE = pathlib.Path(os.environ.get("GEMMA4_GGUF", "/data/ai-ml/hf-models/gemma4-26ba4b-qat-gguf/gemma-4-26B_q4_0-it.gguf"))
DEFAULT_OUT_DIR = pathlib.Path(os.environ.get("GEMMA4_SURGERY_DIR", "/data/ai-ml/hf-models/gemma4-26ba4b-surgery"))
DEFAULT_MANIFEST_DIR = ROOT / "data" / "surgery_experiments" / "trimmed_models"

sys.path.insert(0, str(GGUF_PY))
from gguf import GGUFReader, GGUFValueType, GGUFWriter  # noqa: E402


EXPERT_TENSOR_RE = re.compile(
    r"^blk\.(?P<layer>\d+)\.(?P<suffix>"
    r"ffn_down_exps\.scale|"
    r"ffn_down_exps\.weight|"
    r"ffn_gate_inp\.weight|"
    r"ffn_gate_up_exps\.weight"
    r")$"
)


def parse_indices(raw: list[str]) -> list[int]:
    indices: list[int] = []
    for value in raw:
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            indices.append(int(part))
    deduped = sorted(set(indices))
    if not deduped:
        raise SystemExit("at least one --expert-index is required")
    return deduped


def field_value(field: Any) -> Any:
    return field.contents()


def output_data_shape(data: np.ndarray[Any, Any], remove_indices: list[int] | None) -> tuple[int, ...]:
    if remove_indices is None:
        return tuple(int(dim) for dim in data.shape)
    return (int(data.shape[0]) - len(remove_indices), *[int(dim) for dim in data.shape[1:]])


def trimmed_tensor_data(data: np.ndarray[Any, Any], remove_indices: list[int]) -> np.ndarray[Any, Any]:
    keep = np.ones(data.shape[0], dtype=bool)
    keep[remove_indices] = False
    return np.ascontiguousarray(data[keep])


def is_expert_tensor(name: str) -> bool:
    return EXPERT_TENSOR_RE.match(name) is not None


def add_metadata(
    reader: GGUFReader,
    writer: GGUFWriter,
    arch: str,
    old_count: int,
    new_count: int,
    remove_indices: list[int],
) -> None:
    expert_count_key = f"{arch}.expert_count"
    for field in reader.fields.values():
        if field.name.startswith("GGUF.") or field.name == "general.architecture":
            continue

        value_type = field.types[0]
        sub_type = field.types[-1] if value_type == GGUFValueType.ARRAY else None
        value = field_value(field)

        if field.name == expert_count_key:
            value = new_count

        writer.add_key_value(field.name, value, value_type, sub_type=sub_type)

    writer.add_string("gemma_expert_atlas.surgery_type", "global_expert_trim")
    writer.add_string(
        "gemma_expert_atlas.surgery_note",
        "Same expert index removed from every MoE layer for stock GGUF compatibility.",
    )
    writer.add_key_value(
        "gemma_expert_atlas.removed_global_expert_indices",
        remove_indices,
        GGUFValueType.ARRAY,
        sub_type=GGUFValueType.UINT32,
    )
    writer.add_uint32("gemma_expert_atlas.original_expert_count", old_count)
    writer.add_uint32("gemma_expert_atlas.trimmed_expert_count", new_count)


def copy_tensor_infos(
    reader: GGUFReader,
    writer: GGUFWriter,
    old_count: int,
    remove_indices: list[int],
) -> list[dict[str, Any]]:
    changed: list[dict[str, Any]] = []
    for tensor in reader.tensors:
        remove = remove_indices if is_expert_tensor(tensor.name) else None
        if remove is not None and int(tensor.data.shape[0]) != old_count:
            raise ValueError(f"{tensor.name} expected first data axis {old_count}, got {tensor.data.shape}")

        raw_shape = output_data_shape(tensor.data, remove)
        nbytes = int(np.prod(raw_shape, dtype=np.int64)) * int(tensor.data.dtype.itemsize)
        writer.add_tensor_info(
            tensor.name,
            raw_shape,
            tensor.data.dtype,
            nbytes,
            raw_dtype=tensor.tensor_type,
        )

        if remove is not None:
            changed.append(
                {
                    "name": tensor.name,
                    "old_data_shape": [int(dim) for dim in tensor.data.shape],
                    "new_data_shape": list(raw_shape),
                    "old_bytes": int(tensor.data.nbytes),
                    "new_bytes": nbytes,
                    "saved_bytes": int(tensor.data.nbytes) - nbytes,
                }
            )
    return changed


def write_tensors(reader: GGUFReader, writer: GGUFWriter, remove_indices: list[int], verbose: bool) -> None:
    total = len(reader.tensors)
    for idx, tensor in enumerate(reader.tensors, start=1):
        if is_expert_tensor(tensor.name):
            data = trimmed_tensor_data(tensor.data, remove_indices)
        else:
            data = tensor.data

        if verbose:
            print(f"[{idx:03d}/{total:03d}] {tensor.name} {tuple(data.shape)} {data.nbytes / (1024 * 1024):.2f} MiB")

        writer.write_tensor_data(data, tensor_endianess=reader.endianess)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--out-dir", type=pathlib.Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest-dir", type=pathlib.Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--expert-index", action="append", default=[], help="Global expert index to remove; repeat or comma-separate.")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"source model not found: {source}")

    remove_indices = parse_indices(args.expert_index)
    output = args.out
    if output is None:
        suffix = "-".join(f"E{idx:03d}" for idx in remove_indices)
        output = args.out_dir / f"{source.stem}.global_trim_{suffix}.gguf"
    output = output.expanduser().resolve()
    tmp_output = output.with_name(f"{output.name}.tmp")

    if output.exists() and not args.force:
        raise SystemExit(f"output exists; pass --force to overwrite: {output}")
    if tmp_output.exists():
        tmp_output.unlink()

    reader = GGUFReader(str(source), "r")
    arch_field = reader.get_field("general.architecture")
    if arch_field is None:
        raise SystemExit("general.architecture metadata not found")
    arch = str(arch_field.contents())

    expert_count_field = reader.get_field(f"{arch}.expert_count")
    if expert_count_field is None:
        raise SystemExit(f"{arch}.expert_count metadata not found")
    old_count = int(expert_count_field.contents())
    if remove_indices[-1] >= old_count or remove_indices[0] < 0:
        raise SystemExit(f"expert indices must be in [0, {old_count - 1}]")
    new_count = old_count - len(remove_indices)
    if new_count <= 0:
        raise SystemExit("cannot remove all experts")

    output.parent.mkdir(parents=True, exist_ok=True)
    writer = GGUFWriter(str(tmp_output), arch=arch, endianess=reader.endianess)
    alignment_field = reader.get_field("general.alignment")
    if alignment_field is not None:
        alignment = int(alignment_field.contents())
        writer.data_alignment = alignment

    add_metadata(reader, writer, arch, old_count, new_count, remove_indices)
    changed = copy_tensor_infos(reader, writer, old_count, remove_indices)

    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_ti_data_to_file()
    write_tensors(reader, writer, remove_indices, args.verbose)
    writer.close()

    if output.exists():
        output.unlink()
    os.replace(tmp_output, output)

    saved_bytes = sum(item["saved_bytes"] for item in changed)
    manifest = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "source": str(source),
        "output": str(output),
        "surgery_type": "global_expert_trim",
        "removed_global_expert_indices": remove_indices,
        "original_expert_count": old_count,
        "trimmed_expert_count": new_count,
        "changed_tensor_count": len(changed),
        "changed_tensors": changed,
        "saved_bytes_from_tensors": saved_bytes,
        "saved_mib_from_tensors": saved_bytes / (1024 * 1024),
        "source_size_bytes": source.stat().st_size,
        "output_size_bytes": output.stat().st_size,
        "file_size_delta_bytes": output.stat().st_size - source.stat().st_size,
        "note": (
            "This is a stock-GGUF-compatible global trim. It removes the same expert index "
            "from every MoE layer, not arbitrary layer-specific experts."
        ),
    }
    args.manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.manifest_dir / f"{output.stem}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"wrote trimmed model: {output}")
    print(f"wrote manifest: {manifest_path}")
    print(f"removed global expert indices: {', '.join(str(idx) for idx in remove_indices)}")
    print(f"expert_count: {old_count} -> {new_count}")
    print(f"changed tensors: {len(changed)}")
    print(f"tensor bytes saved: {saved_bytes} ({saved_bytes / (1024 * 1024):.2f} MiB)")
    print(f"file size: {source.stat().st_size} -> {output.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
