#!/usr/bin/env python3
"""Combine multiple routing trace JSON files for the dashboard."""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any


def load_trace(spec: str) -> tuple[str, dict[str, Any]]:
    if "=" not in spec:
        raise ValueError("trace spec must be label=path")
    label, path = spec.split("=", 1)
    trace = json.loads(pathlib.Path(path).read_text())
    trace["label"] = label
    return label, trace


def compare(on: dict[str, Any], off: dict[str, Any]) -> dict[str, Any]:
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
    return {
        "top_reasoning_on": sorted(experts, key=lambda item: item["delta_count"], reverse=True)[:24],
        "top_reasoning_off": sorted(experts, key=lambda item: item["delta_count"])[:24],
        "experts": experts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", action="append", required=True, help="label=path")
    parser.add_argument("--default", default="mixed")
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("public/data/routing_traces.json"))
    args = parser.parse_args()

    traces = dict(load_trace(spec) for spec in args.trace)
    bundle: dict[str, Any] = {
        "schema_version": 1,
        "default_trace": args.default,
        "traces": traces,
        "comparisons": {},
    }
    if "reasoning_on" in traces and "reasoning_off" in traces:
        bundle["comparisons"]["reasoning_on_vs_off"] = compare(traces["reasoning_on"], traces["reasoning_off"])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    print("traces", ", ".join(traces))


if __name__ == "__main__":
    main()
