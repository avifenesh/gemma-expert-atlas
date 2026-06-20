#!/usr/bin/env python3
"""Create a small agentic KV-cache quantization eval dataset."""

from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "kv_cache_eval" / "tasks.jsonl"
DEFAULT_SOURCES = ROOT / "data" / "kv_cache_eval" / "sources.json"

SOURCES = [
    {
        "id": "kivi",
        "title": "KIVI: A Tuning-Free Asymmetric 2bit Quantization for KV Cache",
        "url": "https://arxiv.org/abs/2402.02750",
        "type": "paper",
        "insights": [
            "KV cache memory grows with batch size and context length and can become the serving bottleneck.",
            "KIVI argues key cache and value cache have different quantization structure: K per-channel, V per-token.",
            "KV-cache quantization should be tested with quality, peak memory, and throughput, not memory alone.",
        ],
    },
    {
        "id": "hf_transformers_kv_cache",
        "title": "Transformers cache strategies: QuantizedCache",
        "url": "https://huggingface.co/docs/transformers/en/kv_cache",
        "type": "official-docs",
        "insights": [
            "Hugging Face exposes a QuantizedCache to reduce KV memory.",
            "The documented backends include HQQ with int2, int4, int8 and Quanto with int2, int4.",
            "The cache implementation is an inference-time strategy, distinct from model-weight quantization.",
        ],
    },
    {
        "id": "hf_blog_kv_cache_quant",
        "title": "Unlocking Longer Generation with Key-Value Cache Quantization",
        "url": "https://huggingface.co/blog/kv-cache-quantization",
        "type": "engineering-note",
        "insights": [
            "KV-cache quantization is useful when longer context or larger batch would otherwise hit memory limits.",
            "Evaluation should include long-generation and long-context behavior, not only short prompt quality.",
            "Quantized KV implementations can keep a small residual cache in higher precision before quantizing.",
        ],
    },
    {
        "id": "turboquant",
        "title": "TurboQuant: Online Vector Quantization with Near-optimal Distortion Rate",
        "url": "https://arxiv.org/abs/2504.19874",
        "type": "paper",
        "insights": [
            "TurboQuant targets online vector quantization, including KV-cache quantization.",
            "The paper optimizes both mean-squared error and inner-product distortion.",
            "The reported KV-cache setting highlights very low bit budgets, so evals must check attention-sensitive tasks.",
        ],
    },
    {
        "id": "llama_cpp_cache_types",
        "title": "llama.cpp CLI/server cache type flags",
        "url": "https://github.com/ggml-org/llama.cpp/tree/master/tools/server",
        "type": "official-docs",
        "insights": [
            "llama.cpp exposes separate --cache-type-k and --cache-type-v flags.",
            "The local build documents f32, f16, bf16, q8_0, q4_0, q4_1, iq4_nl, q5_0, q5_1.",
            "The /completion endpoint returns timings and token counts that can be used for eval summaries.",
        ],
    },
]

RESEARCH_PACKET = "\n".join(
    [
        "KV-CACHE QUANTIZATION RESEARCH PACKET",
        *[
            f"- [{source['id']}] {source['title']}: " + " ".join(source["insights"])
            for source in SOURCES
        ],
        "",
        "LOCAL RUNTIME SURFACE",
        "- llama.cpp server supports separate --cache-type-k and --cache-type-v flags.",
        "- Candidate cache types in this build: f32, f16, bf16, q8_0, q5_0, q5_1, q4_0, q4_1, iq4_nl.",
        "- Existing Gemma calibration uses flash attention and a balanced q8_0/q5_1 KV setting.",
        "- A useful first matrix compares f16/f16 baseline, q8_0/q8_0, q8_0/q5_1, q5_1/q5_1, q4_0/q4_0, and iq4_nl/iq4_nl.",
    ]
)

DISTRACTOR_PARAGRAPHS = [
    "Repository note: the dashboard renders a static MoE expert map and separate routing traces.",
    "Operational note: generated artifacts should live under data/kv_cache_eval/runs and should not be committed by default.",
    "Measurement note: prompt processing throughput and decode throughput can move in different directions.",
    "Quality note: long-context retrieval failures can look like confident implementation mistakes.",
    "Implementation note: keep cache_prompt disabled when comparing full prompt processing across cache formats.",
    "Agent note: a good answer should state assumptions, propose a sweep, and define pass/fail criteria.",
]


def long_context(repeats: int) -> str:
    blocks = []
    for idx in range(repeats):
        blocks.append(f"Context block {idx:02d}:")
        for paragraph in DISTRACTOR_PARAGRAPHS:
            blocks.append(f"{paragraph} Repeat marker {idx:02d}.")
    return "\n".join(blocks)


def check(check_id: str, kind: str, points: float, **kwargs: object) -> dict[str, object]:
    return {"id": check_id, "kind": kind, "points": points, **kwargs}


def task(
    task_id: str,
    title: str,
    category: str,
    body: str,
    checks: list[dict[str, object]],
    repeats: int,
) -> dict[str, object]:
    prompt = textwrap.dedent(
        f"""
        You are an autonomous research-and-coding agent working in a local llama.cpp + Gemma repo.
        Your job is to read the evidence packet, reason about the engineering tradeoff, and answer the task.

        {RESEARCH_PACKET}

        LONG WORKSPACE CONTEXT
        {long_context(repeats)}

        TASK
        {body}

        RESPONSE FORMAT
        Use concise markdown with these headings:
        - Decision
        - Evidence
        - Implementation
        - Validation
        Preserve exact flag and cache-type spellings when they matter, such as --cache-type-k, --cache-type-v,
        f16, q8_0, q5_1, q4_0, and iq4_nl.
        """
    ).strip()
    return {
        "id": task_id,
        "title": title,
        "category": category,
        "prompt": prompt,
        "scoring": {"checks": checks},
    }


def build_tasks(repeats: int) -> list[dict[str, object]]:
    return [
        task(
            "kvq_research_memo",
            "Research memo for a KV-cache quant sweep",
            "research",
            """
            Write a research memo that explains why KV-cache quantization is worth testing for long-context
            agentic workloads. Include the expected tradeoff, the difference between model-weight quantization
            and KV-cache quantization, and the specific llama.cpp cache types we should sweep first.
            """,
            [
                check("kv-cache-memory", "contains_all", 1.0, terms=["kv cache", "memory", "context"]),
                check("separate-kv", "contains_all", 1.0, terms=["--cache-type-k", "--cache-type-v"]),
                check("kivi-asymmetry", "contains_any", 1.0, terms=["per-channel", "per token", "per-token", "KIVI"]),
                check("baseline", "contains_all", 1.0, terms=["f16", "baseline"]),
                check("balanced-config", "contains_all", 1.0, terms=["q8_0", "q5_1"]),
                check("quality-speed", "contains_all", 1.0, terms=["quality", "throughput"]),
            ],
            repeats,
        ),
        task(
            "kvq_eval_implementation_plan",
            "Implementation plan for the eval runner",
            "implementation",
            """
            Design the eval runner we should add to this repo. It must compare cache formats, call llama.cpp
            server or CLI, save raw completions, score agentic tasks deterministically, and produce a compact
            JSON summary. Be explicit about fields in the result schema.
            """,
            [
                check("matrix", "contains_all", 1.0, terms=["f16", "q8_0", "q4_0"]),
                check("server-or-cli", "contains_any", 1.0, terms=["llama-server", "llama-cli", "/completion"]),
                check("raw-output", "contains_all", 1.0, terms=["raw", "completion"]),
                check("timings", "contains_any", 1.0, terms=["predicted_per_second", "prompt_per_second", "tokens_evaluated", "timings"]),
                check("json-summary", "contains_all", 1.0, terms=["json", "score"]),
                check("cache-prompt", "contains_all", 1.0, terms=["cache_prompt", "false"]),
            ],
            repeats,
        ),
        task(
            "kvq_needle_agent_patch",
            "Long-context needle for agentic implementation details",
            "long-context",
            """
            Hidden requirement: preserve this exact release marker in your answer: KVQ-SENTINEL-739.
            You are reviewing a proposed patch that defaults to q4_0/q4_0 for all agentic tasks.
            Decide whether that should be the default. Recommend one balanced config and one aggressive config,
            and state what validation would block the change.
            """,
            [
                check("sentinel", "exact", 2.0, text="KVQ-SENTINEL-739"),
                check("reject-blind-q4", "contains_all", 1.0, terms=["q4_0", "default"]),
                check("balanced", "contains_all", 1.0, terms=["q8_0", "q5_1"]),
                check("aggressive", "contains_any", 1.0, terms=["q4_0/q4_0", "iq4_nl", "aggressive"]),
                check("blockers", "contains_any", 1.0, terms=["needle", "exact", "quality", "regression"]),
            ],
            repeats + 2,
        ),
        task(
            "kvq_debug_quality_regression",
            "Diagnose a KV-cache quality regression",
            "debugging",
            """
            A run with f16/f16 passes all tasks. q8_0/q5_1 passes all but one long-context needle. q4_0/q4_0
            misses two exact markers and produces a plausible but wrong implementation command. Diagnose the
            likely failure mode and propose the next ablations.
            """,
            [
                check("compare-baseline", "contains_all", 1.0, terms=["f16", "baseline"]),
                check("ablations", "contains_all", 1.0, terms=["ablation", "K", "V"]),
                check("k-only-v-only", "contains_any", 1.0, terms=["q8_0/f16", "f16/q8_0", "K-only", "V-only"]),
                check("long-context", "contains_all", 1.0, terms=["long", "context"]),
                check("do-not-ship", "contains_any", 1.0, terms=["do not", "block", "regression"]),
                check("deterministic", "contains_any", 1.0, terms=["seed", "temperature", "deterministic"]),
            ],
            repeats,
        ),
    ]


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--sources-out", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--repeat-context", type=int, default=10, help="More repeats means longer prompts.")
    args = parser.parse_args()

    tasks = build_tasks(max(0, args.repeat_context))
    write_jsonl(args.out, tasks)
    args.sources_out.parent.mkdir(parents=True, exist_ok=True)
    args.sources_out.write_text(json.dumps({"sources": SOURCES}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out} ({len(tasks)} tasks)")
    print(f"wrote {args.sources_out} ({len(SOURCES)} sources)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
