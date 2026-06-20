#!/usr/bin/env python3
"""Remove workstation-specific paths from publishable JSON/Markdown artifacts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = [
    ROOT / "public" / "data",
    ROOT / "data" / "surgery_experiments",
]
TEXT_SUFFIXES = {".csv", ".json", ".md", ".txt"}


def replacement_pairs(root: Path) -> list[tuple[str, str]]:
    home = Path.home()
    return [
        (str(root) + "/", ""),
        (str(root), "."),
        (str(home) + "/", "~/"),
        ("/data/ai-ml/hf-models/gemma4-26ba4b-base", "${GEMMA4_BASE_MODEL_DIR}"),
        (
            "/data/ai-ml/hf-models/gemma4-26ba4b-qat-gguf/gemma-4-26B_q4_0-it.gguf",
            "${GEMMA4_GGUF}",
        ),
        ("/data/ai-ml/hf-models/gemma4-26ba4b-surgery", "${GEMMA4_SURGERY_DIR}"),
    ]


def scrub_text(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def scrub_json(value: Any, pairs: list[tuple[str, str]]) -> Any:
    if isinstance(value, str):
        return scrub_text(value, pairs)
    if isinstance(value, list):
        return [scrub_json(item, pairs) for item in value]
    if isinstance(value, dict):
        return {key: scrub_json(item, pairs) for key, item in value.items()}
    return value


def iter_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        path = path.expanduser()
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(child for child in path.rglob("*") if child.is_file() and child.suffix in TEXT_SUFFIXES)
    return sorted(set(files))


def sanitize_file(path: Path, pairs: list[tuple[str, str]]) -> bool:
    original = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        try:
            data = json.loads(original)
        except json.JSONDecodeError:
            updated = scrub_text(original, pairs)
        else:
            updated = json.dumps(scrub_json(data, pairs), indent=2, sort_keys=True) + "\n"
    else:
        updated = scrub_text(original, pairs)

    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=DEFAULT_TARGETS)
    args = parser.parse_args()

    pairs = replacement_pairs(ROOT)
    changed = [path for path in iter_files(args.paths) if sanitize_file(path, pairs)]
    for path in changed:
        print(path.relative_to(ROOT))
    print(f"sanitized {len(changed)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
