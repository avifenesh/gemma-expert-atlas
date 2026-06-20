#!/usr/bin/env python3
"""Run ordered routing probes and find experts that fire early then disappear."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any

from import_imatrix_counts import import_counts


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_LLAMA_CPP = pathlib.Path(os.environ.get("LLAMA_CPP", str(pathlib.Path.home() / "projects" / "llama.cpp")))
DEFAULT_MODEL = pathlib.Path(os.environ.get("GEMMA4_GGUF", "/data/ai-ml/hf-models/gemma4-26ba4b-qat-gguf/gemma-4-26B_q4_0-it.gguf"))
DEFAULT_PROMPTS = ROOT / "data" / "personal_agent_corpora" / "personal_research_reasoning_off.txt"
DEFAULT_WORK_DIR = ROOT / "data" / "routing_timeline"
DEFAULT_OUT = ROOT / "public" / "data" / "routing_timeline.json"
DEFAULT_MANIFEST = ROOT / "public" / "data" / "expert_manifest.json"


def split_text(text: str, target_chars: int, max_chunks: int | None) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for line in text.splitlines(keepends=True):
        if current and size + len(line) > target_chars:
            chunks.append("".join(current))
            current = []
            size = 0
            if max_chunks is not None and len(chunks) >= max_chunks:
                return chunks
        current.append(line)
        size += len(line)
    if current and (max_chunks is None or len(chunks) < max_chunks):
        chunks.append("".join(current))
    return [chunk for chunk in chunks if chunk.strip()]


def expert_index(trace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {expert["id"]: expert for expert in trace["experts"]}


def classify_expert(chunk_counts: list[int], early_chunks: int) -> str:
    active = [idx for idx, count in enumerate(chunk_counts) if count > 0]
    if not active:
        return "never_active"
    first = active[0]
    last = active[-1]
    if first < early_chunks and last < early_chunks:
        return "early_only"
    if first >= early_chunks:
        return "late_only"
    if len(active) == len(chunk_counts):
        return "persistent"
    return "intermittent"


def build_timeline(
    traces: list[dict[str, Any]],
    prompt_path: pathlib.Path,
    model_path: pathlib.Path,
    chunk_files: list[pathlib.Path],
    ctx: int,
    early_chunks: int,
    label: str,
) -> dict[str, Any]:
    by_chunk = [expert_index(trace) for trace in traces]
    ids = sorted(by_chunk[0])
    experts = []
    for expert_id in ids:
        first = by_chunk[0][expert_id]
        counts = [int(chunk[expert_id]["count"]) for chunk in by_chunk]
        active_chunks = [idx for idx, count in enumerate(counts) if count > 0]
        early_count = sum(counts[:early_chunks])
        later_count = sum(counts[early_chunks:])
        total = early_count + later_count
        status = classify_expert(counts, early_chunks)
        experts.append(
            {
                "id": expert_id,
                "layer": first["layer"],
                "expert": first["expert"],
                "chunk_counts": counts,
                "total_count": total,
                "early_count": early_count,
                "later_count": later_count,
                "active_chunks": len(active_chunks),
                "first_active_chunk": active_chunks[0] if active_chunks else None,
                "last_active_chunk": active_chunks[-1] if active_chunks else None,
                "early_share": early_count / total if total else 0.0,
                "status": status,
            }
        )

    early_only = sorted(
        (expert for expert in experts if expert["status"] == "early_only" and expert["early_count"] > 0),
        key=lambda item: (-item["early_count"], item["layer"], item["expert"]),
    )
    late_only = sorted(
        (expert for expert in experts if expert["status"] == "late_only"),
        key=lambda item: (-item["total_count"], item["layer"], item["expert"]),
    )
    intermittent = sorted(
        (expert for expert in experts if expert["status"] == "intermittent"),
        key=lambda item: (-item["total_count"], item["layer"], item["expert"]),
    )

    return {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "label": label,
        "source": {
            "prompt_path": str(prompt_path),
            "model": str(model_path),
            "ctx": ctx,
            "chunk_count": len(traces),
            "early_chunks": early_chunks,
            "chunk_files": [str(path) for path in chunk_files],
        },
        "summary": {
            "expert_count": len(experts),
            "early_only_count": len(early_only),
            "late_only_count": len(late_only),
            "intermittent_count": len(intermittent),
            "persistent_count": sum(1 for expert in experts if expert["status"] == "persistent"),
            "never_active_count": sum(1 for expert in experts if expert["status"] == "never_active"),
            "total_selections": sum(trace["summary"]["total_selections"] for trace in traces),
        },
        "chunks": [
            {
                "index": idx,
                "prompt_file": str(chunk_files[idx]),
                "total_selections": trace["summary"]["total_selections"],
                "zero_expert_slots": trace["summary"]["zero_expert_slots"],
                "nonzero_expert_slots": trace["summary"]["nonzero_expert_slots"],
            }
            for idx, trace in enumerate(traces)
        ],
        "experts": experts,
        "early_only_experts": early_only[:48],
        "late_only_experts": late_only[:48],
        "intermittent_experts": intermittent[:48],
        "note": (
            "Timeline is built from ordered separate imatrix probes. It measures activation by corpus chunk, "
            "not token-by-token router state inside one generation."
        ),
    }


def run_imatrix(
    llama_cpp: pathlib.Path,
    model: pathlib.Path,
    prompt_file: pathlib.Path,
    out_file: pathlib.Path,
    log_file: pathlib.Path,
    ctx: int,
    ngl: str,
    flash_attn: str,
) -> None:
    cmd = [
        str(llama_cpp / "build" / "bin" / "llama-imatrix"),
        "-m",
        str(model),
        "-f",
        str(prompt_file),
        "-o",
        str(out_file),
        "-c",
        str(ctx),
        "-b",
        str(ctx),
        "-ub",
        "128",
        "--chunks",
        "1",
        "--no-ppl",
        "--parse-special",
        "-fa",
        flash_attn,
        "-ngl",
        ngl,
        "--cache-type-k",
        "q8_0",
        "--cache-type-v",
        "q5_1",
    ]
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("w", encoding="utf-8") as handle:
        handle.write("$ " + " ".join(cmd) + "\n\n")
        handle.flush()
        subprocess.run(cmd, check=True, stdout=handle, stderr=subprocess.STDOUT)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts", type=pathlib.Path, default=DEFAULT_PROMPTS)
    parser.add_argument("--model", type=pathlib.Path, default=DEFAULT_MODEL)
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--llama-cpp", type=pathlib.Path, default=pathlib.Path(os.environ.get("LLAMA_CPP", DEFAULT_LLAMA_CPP)))
    parser.add_argument("--work-dir", type=pathlib.Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--label", default="personal_research_reasoning_off")
    parser.add_argument("--ctx", type=int, default=1024)
    parser.add_argument("--chunk-chars", type=int, default=3600)
    parser.add_argument("--max-chunks", type=int, default=8)
    parser.add_argument("--early-chunks", type=int, default=1)
    parser.add_argument("--ngl", default="auto")
    parser.add_argument("--flash-attn", default="on", choices=["on", "off", "auto"])
    parser.add_argument("--keep-imatrix", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    prompts = args.prompts.expanduser().resolve()
    model = args.model.expanduser().resolve()
    if not prompts.exists():
        raise SystemExit(f"prompt corpus not found: {prompts}")
    if not model.exists():
        raise SystemExit(f"model not found: {model}")
    if args.early_chunks < 1:
        raise SystemExit("--early-chunks must be >= 1")

    work_dir = args.work_dir.expanduser().resolve() / args.label
    chunk_dir = work_dir / "chunks"
    imatrix_dir = work_dir / "imatrix"
    trace_dir = work_dir / "traces"
    for path in (chunk_dir, imatrix_dir, trace_dir):
        path.mkdir(parents=True, exist_ok=True)

    chunks = split_text(prompts.read_text(encoding="utf-8"), args.chunk_chars, args.max_chunks)
    if args.early_chunks >= len(chunks):
        raise SystemExit(f"--early-chunks must be smaller than chunk count ({len(chunks)})")

    traces: list[dict[str, Any]] = []
    chunk_files: list[pathlib.Path] = []
    for idx, chunk in enumerate(chunks):
        chunk_file = chunk_dir / f"chunk_{idx:02d}.txt"
        imatrix_file = imatrix_dir / f"chunk_{idx:02d}.gguf"
        trace_file = trace_dir / f"chunk_{idx:02d}.json"
        log_file = work_dir / "logs" / f"chunk_{idx:02d}.log"
        chunk_file.write_text(chunk, encoding="utf-8")
        chunk_files.append(chunk_file)

        if not (args.skip_existing and trace_file.exists()):
            print(f"==> timeline chunk {idx + 1}/{len(chunks)}")
            if not (args.skip_existing and imatrix_file.exists()):
                run_imatrix(args.llama_cpp, model, chunk_file, imatrix_file, log_file, args.ctx, args.ngl, args.flash_attn)
            trace = import_counts(args.manifest, imatrix_file)
            trace["label"] = f"{args.label}_chunk_{idx:02d}"
            trace_file.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            if not args.keep_imatrix:
                imatrix_file.unlink(missing_ok=True)
        traces.append(json.loads(trace_file.read_text(encoding="utf-8")))

    timeline = build_timeline(traces, prompts, model, chunk_files, args.ctx, args.early_chunks, args.label)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(timeline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.copy2(args.out, work_dir / "routing_timeline.json")

    print(f"wrote {args.out}")
    print(f"chunks: {timeline['source']['chunk_count']}")
    print(f"early-only experts: {timeline['summary']['early_only_count']}")
    print(f"late-only experts: {timeline['summary']['late_only_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
