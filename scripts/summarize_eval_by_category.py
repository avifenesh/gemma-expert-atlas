#!/usr/bin/env python3
"""Summarize eval deltas by task category."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKS = ROOT / "data" / "personal_agent_bank" / "tasks.jsonl"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_categories(path: Path) -> dict[str, str]:
    categories: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            task = json.loads(line)
            categories[str(task["id"])] = str(task.get("category", "unknown"))
    return categories


def config_name(row: dict[str, Any]) -> str:
    config = row.get("config")
    if isinstance(config, dict):
        return str(config.get("name"))
    return str(config)


def index_results(data: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(config_name(row), str(row["task_id"])): row for row in data.get("results", [])}


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize(base: dict[str, Any], variant: dict[str, Any], categories: dict[str, str]) -> dict[str, Any]:
    base_rows = index_results(base)
    variant_rows = index_results(variant)
    task_rows: list[dict[str, Any]] = []
    for key in sorted(set(base_rows) & set(variant_rows)):
        base_row = base_rows[key]
        variant_row = variant_rows[key]
        base_score = float(base_row.get("score", 0.0))
        variant_score = float(variant_row.get("score", 0.0))
        task_rows.append(
            {
                "config": key[0],
                "task_id": key[1],
                "category": categories.get(key[1], "unknown"),
                "baseline_score": base_score,
                "variant_score": variant_score,
                "delta_score": variant_score - base_score,
                "baseline_decode_tokens_per_second": (base_row.get("timings") or {}).get("predicted_per_second"),
                "variant_decode_tokens_per_second": (variant_row.get("timings") or {}).get("predicted_per_second"),
            }
        )

    summary_rows: list[dict[str, Any]] = []
    category_rows: list[dict[str, Any]] = []
    for config in sorted({row["config"] for row in task_rows}):
        config_items = [row for row in task_rows if row["config"] == config]
        base_tps = [
            float(row["baseline_decode_tokens_per_second"])
            for row in config_items
            if row["baseline_decode_tokens_per_second"] is not None
        ]
        variant_tps = [
            float(row["variant_decode_tokens_per_second"])
            for row in config_items
            if row["variant_decode_tokens_per_second"] is not None
        ]
        summary_rows.append(
            {
                "config": config,
                "tasks": len(config_items),
                "baseline_mean_score": mean([row["baseline_score"] for row in config_items]),
                "variant_mean_score": mean([row["variant_score"] for row in config_items]),
                "delta_mean_score": mean([row["delta_score"] for row in config_items]),
                "baseline_decode_tokens_per_second": mean(base_tps) if base_tps else None,
                "variant_decode_tokens_per_second": mean(variant_tps) if variant_tps else None,
                "delta_decode_tokens_per_second": (mean(variant_tps) - mean(base_tps)) if base_tps and variant_tps else None,
            }
        )

        by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in config_items:
            by_category[row["category"]].append(row)
        for category, items in sorted(by_category.items()):
            category_rows.append(
                {
                    "config": config,
                    "category": category,
                    "tasks": len(items),
                    "baseline_mean": mean([row["baseline_score"] for row in items]),
                    "variant_mean": mean([row["variant_score"] for row in items]),
                    "delta_mean": mean([row["delta_score"] for row in items]),
                    "negative_tasks": sum(1 for row in items if row["delta_score"] < 0),
                    "positive_tasks": sum(1 for row in items if row["delta_score"] > 0),
                }
            )

    negative = sorted(
        [row for row in task_rows if row["delta_score"] < 0],
        key=lambda row: (row["config"], row["delta_score"], row["task_id"]),
    )
    positive = sorted(
        [row for row in task_rows if row["delta_score"] > 0],
        key=lambda row: (row["config"], -row["delta_score"], row["task_id"]),
    )
    return {
        "summary": summary_rows,
        "category_deltas": category_rows,
        "negative_tasks": negative,
        "positive_tasks": positive,
        "tasks": task_rows,
    }


def write_markdown(path: Path, report: dict[str, Any], title: str) -> None:
    lines = [
        f"# {title}",
        "",
        f"Generated: {report['created_at']}",
        "",
        f"Baseline: `{report['baseline']}`",
        f"Variant: `{report['variant']}`",
        "",
        "## Summary",
        "",
    ]
    for row in report["summary"]:
        base_tps = row["baseline_decode_tokens_per_second"]
        variant_tps = row["variant_decode_tokens_per_second"]
        if base_tps is None or variant_tps is None:
            speed = "decode unavailable"
        else:
            speed = f"decode {base_tps:.2f} -> {variant_tps:.2f} tok/s"
        lines.append(
            f"- {row['config']}: score {row['baseline_mean_score']:.4f} -> "
            f"{row['variant_mean_score']:.4f} ({row['delta_mean_score']:+.4f}), {speed}"
        )

    lines.extend(
        [
            "",
            "## Category Deltas",
            "",
            "| Config | Category | Base | Variant | Delta | +/- tasks |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in report["category_deltas"]:
        lines.append(
            f"| {row['config']} | {row['category']} | {row['baseline_mean']:.3f} | "
            f"{row['variant_mean']:.3f} | {row['delta_mean']:+.3f} | "
            f"+{row['positive_tasks']} / -{row['negative_tasks']} |"
        )

    lines.extend(
        [
            "",
            "## Negative Task Deltas",
            "",
            "| Config | Task | Category | Base | Variant | Delta |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for row in report["negative_tasks"][:80]:
        lines.append(
            f"| {row['config']} | {row['task_id']} | {row['category']} | "
            f"{row['baseline_score']:.3f} | {row['variant_score']:.3f} | {row['delta_score']:+.3f} |"
        )

    lines.extend(
        [
            "",
            "## Positive Task Deltas",
            "",
            "| Config | Task | Category | Base | Variant | Delta |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for row in report["positive_tasks"][:80]:
        lines.append(
            f"| {row['config']} | {row['task_id']} | {row['category']} | "
            f"{row['baseline_score']:.3f} | {row['variant_score']:.3f} | {row['delta_score']:+.3f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--variant", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--out", type=Path, required=True, help="Markdown report path.")
    parser.add_argument("--json-out", type=Path, help="Defaults to --out with .json suffix.")
    parser.add_argument("--title", default="Eval Category Delta Report")
    args = parser.parse_args()

    result = summarize(read_json(args.baseline), read_json(args.variant), load_categories(args.tasks))
    report = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "baseline": str(args.baseline),
        "variant": str(args.variant),
        "tasks_file": str(args.tasks),
        **result,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    json_path = args.json_out or args.out.with_suffix(".json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(args.out, report, args.title)
    print(f"wrote {args.out}")
    print(f"wrote {json_path}")
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
