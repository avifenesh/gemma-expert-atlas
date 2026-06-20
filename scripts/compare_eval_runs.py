#!/usr/bin/env python3
"""Compare two run_kv_cache_eval result files."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "surgery_experiments" / "eval_comparison.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def index_results(data: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    rows = {}
    for row in data.get("results", []):
        key = (row["config"]["name"], row["task_id"])
        rows[key] = row
    return rows


def summarize(data: dict[str, Any]) -> dict[str, Any]:
    by_name = {item["name"]: item for item in data.get("summaries", [])}
    return by_name


def compare(base: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    base_rows = index_results(base)
    variant_rows = index_results(variant)
    keys = sorted(set(base_rows) | set(variant_rows))
    rows = []
    for key in keys:
        base_row = base_rows.get(key)
        variant_row = variant_rows.get(key)
        rows.append(
            {
                "config": key[0],
                "task_id": key[1],
                "baseline_score": base_row.get("score") if base_row else None,
                "variant_score": variant_row.get("score") if variant_row else None,
                "delta_score": (variant_row.get("score") - base_row.get("score")) if base_row and variant_row else None,
                "baseline_elapsed_ms": base_row.get("elapsed_ms") if base_row else None,
                "variant_elapsed_ms": variant_row.get("elapsed_ms") if variant_row else None,
                "baseline_decode_tokens_per_second": (base_row.get("timings") or {}).get("predicted_per_second") if base_row else None,
                "variant_decode_tokens_per_second": (variant_row.get("timings") or {}).get("predicted_per_second") if variant_row else None,
            }
        )

    summary_rows = []
    base_summary = summarize(base)
    variant_summary = summarize(variant)
    for name in sorted(set(base_summary) | set(variant_summary)):
        left = base_summary.get(name)
        right = variant_summary.get(name)
        summary_rows.append(
            {
                "config": name,
                "baseline_mean_score": left.get("mean_score") if left else None,
                "variant_mean_score": right.get("mean_score") if right else None,
                "delta_mean_score": (right.get("mean_score") - left.get("mean_score")) if left and right else None,
                "baseline_min_score": left.get("min_score") if left else None,
                "variant_min_score": right.get("min_score") if right else None,
                "delta_min_score": (right.get("min_score") - left.get("min_score")) if left and right else None,
                "baseline_decode_tokens_per_second": left.get("mean_decode_tokens_per_second") if left else None,
                "variant_decode_tokens_per_second": right.get("mean_decode_tokens_per_second") if right else None,
                "delta_decode_tokens_per_second": (
                    right.get("mean_decode_tokens_per_second") - left.get("mean_decode_tokens_per_second")
                )
                if left and right
                else None,
                "tasks": right.get("tasks") if right else left.get("tasks") if left else None,
            }
        )
    return {"summary": summary_rows, "tasks": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--variant", type=Path, required=True)
    parser.add_argument("--variant-name", default="variant")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    baseline = read_json(args.baseline)
    variant = read_json(args.variant)
    comparison = compare(baseline, variant)
    output = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "baseline": str(args.baseline),
        "variant": str(args.variant),
        "variant_name": args.variant_name,
        **comparison,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(json.dumps(output["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
