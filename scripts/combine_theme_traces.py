#!/usr/bin/env python3
"""Combine per-theme routing traces into one dashboard bundle."""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any


def load_trace(spec: str) -> tuple[str, str, dict[str, Any]]:
    if "=" not in spec or ":" not in spec.split("=", 1)[0]:
        raise ValueError("trace spec must be theme:mode=path")
    left, path = spec.split("=", 1)
    theme, mode = left.split(":", 1)
    trace = json.loads(pathlib.Path(path).read_text())
    trace["label"] = f"{theme}_{mode}"
    trace["theme"] = theme
    trace["mode"] = mode
    return theme, mode, trace


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


def load_theme_labels(path: pathlib.Path | None) -> dict[str, str]:
    if not path or not path.exists():
        return {}
    manifest = json.loads(path.read_text())
    return {theme["key"]: theme.get("label", theme["key"].replace("_", " ")) for theme in manifest.get("themes", [])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", action="append", required=True, help="theme:mode=path")
    parser.add_argument("--theme-manifest", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("public/data/theme_routing_traces.json"))
    args = parser.parse_args()

    labels = load_theme_labels(args.theme_manifest)
    traces: dict[str, dict[str, Any]] = {}
    for spec in args.trace:
        theme, mode, trace = load_trace(spec)
        traces.setdefault(theme, {})[mode] = trace

    comparisons = {}
    for theme, mode_traces in traces.items():
        if "reasoning_on" in mode_traces and "reasoning_off" in mode_traces:
            comparisons[theme] = compare(mode_traces["reasoning_on"], mode_traces["reasoning_off"])

    bundle = {
        "schema_version": 1,
        "summary": {
            "theme_count": len(traces),
            "trace_count": sum(len(mode_traces) for mode_traces in traces.values()),
            "themes": sorted(traces),
        },
        "themes": {
            theme: {
                "label": labels.get(theme, theme.replace("_", " ")),
                "modes": sorted(mode_traces),
            }
            for theme, mode_traces in sorted(traces.items())
        },
        "traces": traces,
        "comparisons": comparisons,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    print(f"themes {', '.join(sorted(traces))}")


if __name__ == "__main__":
    main()
