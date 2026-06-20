#!/usr/bin/env python3
"""Combine routing timeline runs into early-only expert surgery candidates."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import pathlib
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_TIMELINE_ROOT = ROOT / "data" / "routing_timeline"
DEFAULT_TRIM_REPORT = ROOT / "data" / "surgery_experiments" / "trim_decision_report.json"
DEFAULT_OUT = ROOT / "data" / "surgery_experiments" / "early_only_candidates.json"
DEFAULT_PUBLIC_OUT = ROOT / "public" / "data" / "routing_timeline_summary.json"


def read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_timelines(paths: list[pathlib.Path]) -> list[dict[str, Any]]:
    timelines = [read_json(path) for path in paths]
    return sorted(timelines, key=lambda item: item["label"])


def load_trim_decisions(path: pathlib.Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    report = read_json(path)
    return {item["id"]: item for item in report.get("all_experts", [])}


def gather(paths: list[pathlib.Path], trim_report: pathlib.Path) -> dict[str, Any]:
    timelines = load_timelines(paths)
    trim_by_id = load_trim_decisions(trim_report)
    by_id: dict[str, dict[str, Any]] = {}

    for timeline in timelines:
        label = timeline["label"]
        for expert in timeline["experts"]:
            row = by_id.setdefault(
                expert["id"],
                {
                    "id": expert["id"],
                    "layer": expert["layer"],
                    "expert": expert["expert"],
                    "timeline_count": 0,
                    "active_runs": 0,
                    "early_only_runs": 0,
                    "late_only_runs": 0,
                    "intermittent_runs": 0,
                    "persistent_runs": 0,
                    "never_active_runs": 0,
                    "later_active_runs": 0,
                    "total_count": 0,
                    "total_early_count": 0,
                    "total_later_count": 0,
                    "max_early_count": 0,
                    "max_later_count": 0,
                    "early_only_labels": [],
                    "later_active_labels": [],
                    "status_by_label": {},
                },
            )
            status = expert["status"]
            early_count = int(expert["early_count"])
            later_count = int(expert["later_count"])
            total_count = int(expert["total_count"])

            row["timeline_count"] += 1
            row[f"{status}_runs"] += 1
            row["total_count"] += total_count
            row["total_early_count"] += early_count
            row["total_later_count"] += later_count
            row["max_early_count"] = max(row["max_early_count"], early_count)
            row["max_later_count"] = max(row["max_later_count"], later_count)
            row["status_by_label"][label] = status
            if total_count > 0:
                row["active_runs"] += 1
            if status == "early_only":
                row["early_only_labels"].append(label)
            if later_count > 0:
                row["later_active_runs"] += 1
                row["later_active_labels"].append(label)

    for row in by_id.values():
        active_runs = max(1, int(row["active_runs"]))
        row["early_only_rate_active"] = row["early_only_runs"] / active_runs
        row["later_share"] = row["total_later_count"] / max(1, row["total_count"])
        trim = trim_by_id.get(row["id"], {})
        row["trim_decision"] = trim.get("decision")
        row["personal_classification"] = trim.get("personal_classification")

        if row["total_early_count"] > 0 and row["later_active_runs"] == 0:
            row["decision"] = "evict_after_prefix_candidate"
            row["reason"] = "active only in the early timeline window; no later chunk use observed"
        elif row["early_only_runs"] > 0 and row["later_active_runs"] <= 1 and row["later_share"] <= 0.02:
            row["decision"] = "evict_watchlist_tiny_later"
            row["reason"] = "mostly early-only with tiny later activity"
        elif row["never_active_runs"] == row["timeline_count"]:
            row["decision"] = "never_active_in_timelines"
            row["reason"] = "not activated in any timeline run"
        elif row["later_active_runs"] > 0:
            row["decision"] = "keep_runtime_later_used"
            row["reason"] = "used after the early window in at least one timeline"
        else:
            row["decision"] = "needs_more_data"
            row["reason"] = "insufficient or mixed timeline evidence"

    candidates = sorted(
        by_id.values(),
        key=lambda item: (
            item["decision"] != "evict_after_prefix_candidate",
            -item["early_only_runs"],
            -item["total_early_count"],
            item["layer"],
            item["expert"],
        ),
    )
    evict = [item for item in candidates if item["decision"] == "evict_after_prefix_candidate"]
    watch = [item for item in candidates if item["decision"] == "evict_watchlist_tiny_later"]
    never = [item for item in candidates if item["decision"] == "never_active_in_timelines"]

    return {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "source": {
            "timeline_paths": [str(path) for path in paths],
            "timeline_labels": [timeline["label"] for timeline in timelines],
            "timeline_count": len(timelines),
            "trim_report": str(trim_report) if trim_report.exists() else None,
        },
        "summary": {
            "expert_count": len(candidates),
            "evict_after_prefix_candidate_count": len(evict),
            "evict_watchlist_tiny_later_count": len(watch),
            "never_active_in_timelines_count": len(never),
            "keep_runtime_later_used_count": sum(1 for item in candidates if item["decision"] == "keep_runtime_later_used"),
        },
        "experts": candidates,
        "evict_after_prefix_candidates": evict[:128],
        "evict_watchlist_tiny_later": watch[:128],
        "never_active_in_timelines": never[:128],
        "note": (
            "Evict-after-prefix candidates are not permanent prune candidates. They were active early, "
            "so full removal can damage prompt/bootstrap behavior; the efficient path is runtime eviction "
            "or tiered placement after the prefix window."
        ),
    }


def write_csv(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "id",
        "layer",
        "expert",
        "decision",
        "active_runs",
        "early_only_runs",
        "later_active_runs",
        "total_early_count",
        "total_later_count",
        "early_only_rate_active",
        "later_share",
        "trim_decision",
        "personal_classification",
        "early_only_labels",
        "later_active_labels",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out = {field: row.get(field) for field in fields}
            out["early_only_labels"] = ";".join(row.get("early_only_labels", []))
            out["later_active_labels"] = ";".join(row.get("later_active_labels", []))
            writer.writerow(out)


def write_markdown(path: pathlib.Path, data: dict[str, Any]) -> None:
    lines = [
        "# Early-Only Routing Candidates",
        "",
        f"Generated: {data['created_at']}",
        "",
        "## Summary",
        "",
    ]
    for key, value in data["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Top Evict-After-Prefix Candidates",
            "",
            "| Expert | Early-only runs | Active runs | Early count | Later count | Trim decision | Labels |",
            "|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in data["evict_after_prefix_candidates"][:30]:
        labels = ", ".join(row["early_only_labels"][:4])
        if len(row["early_only_labels"]) > 4:
            labels += ", ..."
        lines.append(
            f"| {row['id']} | {row['early_only_runs']} | {row['active_runs']} | "
            f"{row['total_early_count']} | {row['total_later_count']} | {row.get('trim_decision') or ''} | {labels} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- These are candidates for runtime eviction or lower-tier placement after the prefix window.",
            "- They are not safe permanent-prune candidates, because the evidence says they are used early.",
            "- A clean speed win still requires runtime support that stops carrying these experts after the early window.",
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", action="append", type=pathlib.Path, help="Timeline JSON; default scans data/routing_timeline/*/routing_timeline.json")
    parser.add_argument("--timeline-root", type=pathlib.Path, default=DEFAULT_TIMELINE_ROOT)
    parser.add_argument("--trim-report", type=pathlib.Path, default=DEFAULT_TRIM_REPORT)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--public-out", type=pathlib.Path, default=DEFAULT_PUBLIC_OUT)
    args = parser.parse_args()

    paths = args.timeline or sorted(args.timeline_root.glob("*/routing_timeline.json"))
    if not paths:
        raise SystemExit("no timeline files found")

    data = gather(paths, args.trim_report)
    public_data = {
        key: data[key]
        for key in [
            "schema_version",
            "created_at",
            "source",
            "summary",
            "evict_after_prefix_candidates",
            "evict_watchlist_tiny_later",
            "never_active_in_timelines",
            "note",
        ]
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.public_out.parent.mkdir(parents=True, exist_ok=True)
    args.public_out.write_text(json.dumps(public_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(args.out.with_suffix(".csv"), data["experts"])
    write_markdown(args.out.with_suffix(".md"), data)

    print(f"wrote {args.out}")
    print(f"wrote {args.public_out}")
    print(json.dumps(data["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
