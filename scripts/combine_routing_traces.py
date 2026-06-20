#!/usr/bin/env python3
"""Combine multiple routing trace JSON files for the dashboard."""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any


PUBLIC_ROOT = pathlib.Path("public").resolve()


def public_url(path: pathlib.Path) -> str:
    resolved = path.resolve()
    try:
        return "/" + resolved.relative_to(PUBLIC_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_trace(spec: str) -> tuple[str, pathlib.Path, dict[str, Any]]:
    if "=" not in spec:
        raise ValueError("trace spec must be label=path")
    label, path = spec.split("=", 1)
    trace_path = pathlib.Path(path)
    trace = json.loads(trace_path.read_text())
    trace["label"] = label
    return label, trace_path, trace


def compare(on: dict[str, Any], off: dict[str, Any], include_experts: bool) -> dict[str, Any]:
    off_by_id = {expert["id"]: expert for expert in off["experts"]}
    experts = []
    for expert in on["experts"]:
        base = off_by_id.get(expert["id"], {"count": 0, "share": 0.0})
        experts.append(
            {
                "id": expert["id"],
                "layer": expert["layer"],
                "expert": expert["expert"],
                "on_count": expert["count"],
                "off_count": base["count"],
                "delta_count": expert["count"] - base["count"],
                "on_share": expert["share"],
                "off_share": base["share"],
                "delta_share": expert["share"] - base["share"],
            }
        )
    comparison: dict[str, Any] = {
        "top_reasoning_on": sorted(experts, key=lambda item: item["delta_count"], reverse=True)[:24],
        "top_reasoning_off": sorted(experts, key=lambda item: item["delta_count"])[:24],
    }
    if include_experts:
        comparison["experts"] = experts
    return comparison


def trace_reference(label: str, path: pathlib.Path, trace: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": label,
        "path": public_url(path),
        "source": trace.get("source", {}),
        "summary": trace.get("summary", {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", action="append", required=True, help="label=path")
    parser.add_argument("--default", default="mixed")
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("public/data/routing_traces.json"))
    parser.add_argument("--embed-traces", action="store_true", help="Embed full traces instead of lightweight references.")
    parser.add_argument("--embed-comparison-experts", action="store_true", help="Embed full reasoning comparison expert lists.")
    args = parser.parse_args()

    loaded = [load_trace(spec) for spec in args.trace]
    traces = {label: trace for label, _path, trace in loaded}
    trace_refs = {label: trace_reference(label, path, trace) for label, path, trace in loaded}
    bundle: dict[str, Any] = {
        "schema_version": 2,
        "bundle_kind": "embedded_traces" if args.embed_traces else "lazy_trace_index",
        "default_trace": args.default,
        "traces": traces if args.embed_traces else trace_refs,
        "comparisons": {},
    }
    if "reasoning_on" in traces and "reasoning_off" in traces:
        bundle["comparisons"]["reasoning_on_vs_off"] = compare(
            traces["reasoning_on"],
            traces["reasoning_off"],
            args.embed_comparison_experts,
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    print("traces", ", ".join(traces))


if __name__ == "__main__":
    main()
