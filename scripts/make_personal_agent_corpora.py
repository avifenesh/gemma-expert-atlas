#!/usr/bin/env python3
"""Create routing-calibration corpora from the personal-agent task bank."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKS = ROOT / "data" / "personal_agent_bank" / "tasks.jsonl"
DEFAULT_OUT_DIR = ROOT / "data" / "personal_agent_corpora"


def load_tasks(path: Path) -> list[dict[str, Any]]:
    tasks = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                tasks.append(json.loads(line))
    return tasks


def direct_answer(category: str) -> str:
    return (
        f"Direct answer for {category}: decide the action, name the evidence to inspect, "
        "state the exact tool or command when known, and stop after a compact validation note."
    )


def thought_answer(category: str) -> str:
    return (
        "<|channel>thought\n"
        f"We need solve a {category} personal-agent task. Identify constraints, separate evidence from inference, "
        "choose tools or commands, protect user preferences and secrets, and define validation before finalizing.\n"
        "<channel|>\n"
        f"Final answer for {category}: give the decision, plan, evidence, and validation gate."
    )


def chat_turn(system_text: str, user_text: str, assistant_text: str, *, thinking: bool) -> str:
    think = "<|think|>\n" if thinking else ""
    return (
        f"<|turn>system\n{think}{system_text}<turn|>\n"
        f"<|turn>user\n{user_text}<turn|>\n"
        f"<|turn>model\n{assistant_text}<turn|>\n"
    )


def build_corpus(category: str, tasks: list[dict[str, Any]], mode: str, repeats: int, max_prompt_chars: int) -> str:
    sections: list[str] = []
    for repeat in range(repeats):
        sections.append(f"\n\n## Personal-agent family: {category} / pass {repeat + 1}\n")
        for task in tasks:
            prompt = str(task["prompt"])
            if max_prompt_chars > 0 and len(prompt) > max_prompt_chars:
                prompt = prompt[:max_prompt_chars] + "\n[TRUNCATED FOR ROUTING CALIBRATION]"
            if mode == "reasoning_off":
                sections.append(
                    chat_turn(
                        "Reasoning mode disabled. Answer directly and concisely.",
                        prompt,
                        direct_answer(category),
                        thinking=False,
                    )
                )
            elif mode == "reasoning_on":
                sections.append(
                    chat_turn(
                        "Reasoning mode enabled. Think before answering, then provide the final answer.",
                        prompt,
                        thought_answer(category),
                        thinking=True,
                    )
                )
            else:
                raise ValueError(f"unknown mode {mode}")
            sections.append(f"<!-- task={task['id']} mode={mode} -->\n")
    return "".join(sections).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--categories", help="Comma-separated category filter.")
    parser.add_argument("--max-prompt-chars", type=int, default=9000)
    args = parser.parse_args()

    tasks = load_tasks(args.tasks)
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        by_category[str(task["category"])].append(task)

    selected = sorted(by_category)
    if args.categories:
        wanted = [item.strip() for item in args.categories.split(",") if item.strip()]
        unknown = [item for item in wanted if item not in by_category]
        if unknown:
            raise SystemExit(f"unknown categories: {', '.join(unknown)}")
        selected = wanted

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "source_tasks": str(args.tasks),
        "repeats": args.repeats,
        "categories": [],
    }

    for category in selected:
        files: dict[str, str] = {}
        for mode in ("reasoning_off", "reasoning_on"):
            corpus = build_corpus(category, by_category[category], mode, args.repeats, args.max_prompt_chars)
            path = args.out_dir / f"{category}_{mode}.txt"
            path.write_text(corpus, encoding="utf-8")
            files[mode] = str(path)
            print(f"wrote {path} ({len(corpus.encode('utf-8'))} bytes)")
        manifest["categories"].append(
            {
                "key": category,
                "label": category.replace("_", " "),
                "task_count": len(by_category[category]),
                "files": files,
            }
        )

    manifest_path = args.out_dir / "personal_agent_corpus_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
