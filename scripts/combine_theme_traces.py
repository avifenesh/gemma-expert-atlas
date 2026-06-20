#!/usr/bin/env python3
"""Combine per-theme routing traces into one dashboard bundle."""

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


def load_trace(spec: str) -> tuple[str, str, pathlib.Path, dict[str, Any]]:
    if "=" not in spec or ":" not in spec.split("=", 1)[0]:
        raise ValueError("trace spec must be theme:mode=path")
    left, path = spec.split("=", 1)
    theme, mode = left.split(":", 1)
    trace_path = pathlib.Path(path)
    trace = json.loads(trace_path.read_text())
    trace["label"] = f"{theme}_{mode}"
    trace["theme"] = theme
    trace["mode"] = mode
    return theme, mode, trace_path, trace


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


def trace_reference(theme: str, mode: str, path: pathlib.Path, trace: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": trace.get("label", f"{theme}_{mode}"),
        "mode": mode,
        "path": public_url(path),
        "source": trace.get("source", {}),
        "summary": trace.get("summary", {}),
        "theme": theme,
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
    parser.add_argument("--embed-traces", action="store_true", help="Embed full per-theme traces instead of lightweight references.")
    parser.add_argument("--embed-comparison-experts", action="store_true", help="Embed full reasoning comparison expert lists.")
    args = parser.parse_args()

    labels = load_theme_labels(args.theme_manifest)
    traces: dict[str, dict[str, Any]] = {}
    trace_refs: dict[str, dict[str, Any]] = {}
    for spec in args.trace:
        theme, mode, path, trace = load_trace(spec)
        traces.setdefault(theme, {})[mode] = trace
        trace_refs.setdefault(theme, {})[mode] = trace_reference(theme, mode, path, trace)

    comparisons = {}
    for theme, mode_traces in traces.items():
        if "reasoning_on" in mode_traces and "reasoning_off" in mode_traces:
            comparisons[theme] = compare(
                mode_traces["reasoning_on"],
                mode_traces["reasoning_off"],
                args.embed_comparison_experts,
            )

    bundle = {
        "schema_version": 2,
        "bundle_kind": "embedded_traces" if args.embed_traces else "lazy_trace_index",
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
        "traces": traces if args.embed_traces else trace_refs,
        "comparisons": comparisons,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    print(f"themes {', '.join(sorted(traces))}")


if __name__ == "__main__":
    main()
