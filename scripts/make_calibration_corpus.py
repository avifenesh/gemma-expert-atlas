#!/usr/bin/env python3
"""Generate a mixed-domain calibration corpus for routing traces."""

from __future__ import annotations

import argparse
import pathlib


BLOCKS = {
    "systems": [
        "Explain how a local model runtime decides which tensors stay on GPU, which tensors stay on CPU, and why total parameter count matters more than active parameter count for a mixture-of-experts model.",
        "Describe a profiling session where a quantized model loads successfully but decode speed is limited by CPU offload. Include memory pressure, KV cache type, batch size, and tensor transfer costs.",
        "Write a plan for checkpoint surgery: inspect tensor topology, collect routing data, select low-risk experts, rewrite packed tensors, update metadata, quantize, and validate quality.",
        "Compare a static safetensors header map with a dynamic routing trace. The static map tells where weights live. The routing trace tells which experts tokens actually use.",
    ],
    "code": [
        "Write a Python function that groups expert records by layer, computes min, max, mean, and zero counts, and returns a JSON-serializable dictionary.",
        "Review this TypeScript component: it renders an SVG heatmap with 3840 cells. What should be memoized, what state should live at the top level, and how should accessibility labels be handled?",
        "Implement a safe parser for a binary file format. It should validate magic bytes, version, tensor count, metadata entries, tensor descriptors, alignment, and expected byte ranges.",
        "Debug a shell script that launches a model calibration pass. It should fail on unset variables, preserve quoted paths, and allow CTX, CHUNKS, MODEL, and PROMPTS to be overridden.",
    ],
    "math": [
        "A model has 30 layers and 128 experts per layer. Each token selects 8 experts. For 4096 calibration tokens, compute selections per layer, average selections per expert, and a threshold for the coldest 10 percent.",
        "Given expert counts [12, 4, 0, 19, 8, 8, 0, 5], compute total count, usage share for each expert, entropy, and identify cold experts without assuming they are safe to prune.",
        "Explain why rank within a layer is more meaningful than raw count across layers when every layer receives the same number of routed token selections.",
        "Derive the expected number of nonzero experts when routing uniformly at random over 128 experts with top-k 8 for N tokens. Contrast that with specialized routing.",
    ],
    "data": [
        "SQL: select layer, expert, count(*) as routed_tokens from routing_events group by layer, expert order by layer, routed_tokens desc;",
        "JSON: {\"model\":\"Gemma 4 26B A4B\",\"layers\":30,\"experts\":128,\"top_k\":8,\"trace\":\"routing\",\"metrics\":[\"count\",\"share\",\"rank\",\"zero_slots\"]}",
        "CSV columns: layer,expert,count,share,rank,source_tensor,domain. Explain how this table can join with a static manifest table keyed by layer and expert.",
        "Schema design: store one aggregate routing trace and several per-domain traces. Keep source corpus, chunk size, number of tokens, and model quantization in metadata.",
    ],
    "general": [
        "Summarize the risks of pruning a rarely used expert. It may encode rare-domain behavior, compensate for another expert, or become important under prompts not present in calibration.",
        "Explain model quantization to a new engineer. Distinguish QAT from post-training quantization, weight-only quantization from activation quantization, and GGUF formats from algorithms.",
        "Write a short story about an engineer who discovers that a beautiful heatmap is less important than the evidence behind it. The evidence comes from tokens, routers, and careful evaluation.",
        "Give a practical checklist for deciding whether to merge two experts: similar activation patterns, similar weights, low quality loss in ablations, and recoverable performance after tuning.",
    ],
    "instructions": [
        "You are given a routing trace. Identify the hottest expert per layer, the coldest nonzero expert per layer, and the experts with zero count. Return cautious recommendations only.",
        "Create a benchmark plan for a pruned MoE model. Include baseline perplexity, task accuracy, tokens per second, VRAM usage, context length, and qualitative generation checks.",
        "Explain why one calibration chunk is not enough. Mention prompt diversity, rare domains, stochastic routing patterns, and the difference between smoke tests and evidence.",
        "Propose three next experiments after the first aggregate routing map: per-domain traces, expert masking ablations, and similarity clustering over expert weights.",
    ],
}


def direct_answer(domain: str, prompt: str) -> str:
    return (
        f"Direct answer for {domain}: identify the key facts, give the result, and stop. "
        "Do not include hidden reasoning or a step-by-step derivation. Mention the final decision and one concise reason."
    )


def thought_answer(domain: str, prompt: str) -> str:
    return (
        "<|channel>thought\n"
        f"We need solve a {domain} task. First identify the objects involved, then connect them to expert routing. "
        "Check whether counts, shares, ranks, and calibration coverage are enough evidence. "
        "Avoid making a pruning decision from one observation. Compare the current task to static topology and dynamic routing.\n"
        "<channel|>\n"
        f"Final answer for {domain}: use the reasoning trace to justify a cautious recommendation, then name the measurable next step."
    )


def chat_turn(system_text: str, user_text: str, assistant_text: str, *, thinking: bool) -> str:
    think = "<|think|>\n" if thinking else ""
    return (
        f"<|turn>system\n{think}{system_text}<turn|>\n"
        f"<|turn>user\n{user_text}<turn|>\n"
        f"<|turn>model\n{assistant_text}<turn|>\n"
    )


def build_corpus(repeats: int, mode: str) -> str:
    sections: list[str] = []
    for repeat in range(repeats):
        for domain, prompts in BLOCKS.items():
            sections.append(f"\n\n## Domain: {domain} / pass {repeat + 1}\n")
            for idx, prompt in enumerate(prompts, start=1):
                if mode == "mixed":
                    sections.append(f"\n### Prompt {idx}\n{prompt}\n")
                    sections.append(
                        "Answer with concrete details, avoid vague claims, and connect the reasoning back to mixture-of-experts routing, calibration evidence, and local inference constraints.\n"
                    )
                elif mode == "reasoning_off":
                    sections.append(
                        chat_turn(
                            "Reasoning mode disabled. Answer directly and concisely.",
                            prompt,
                            direct_answer(domain, prompt),
                            thinking=False,
                        )
                    )
                elif mode == "reasoning_on":
                    sections.append(
                        chat_turn(
                            "Reasoning mode enabled. Think before answering, then provide the final answer.",
                            prompt,
                            thought_answer(domain, prompt),
                            thinking=True,
                        )
                    )
                else:
                    raise ValueError(f"unknown mode {mode}")
    return "".join(sections).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("data/calibration_mixed.txt"))
    parser.add_argument("--repeats", type=int, default=8)
    parser.add_argument("--mode", choices=["mixed", "reasoning_on", "reasoning_off"], default="mixed")
    args = parser.parse_args()

    corpus = build_corpus(args.repeats, args.mode)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(corpus)
    print(f"wrote {args.out}")
    print(f"bytes {len(corpus.encode('utf-8'))}")
    print(f"sections {len(BLOCKS) * args.repeats}")


if __name__ == "__main__":
    main()
