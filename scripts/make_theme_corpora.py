#!/usr/bin/env python3
"""Generate paired theme corpora for reasoning-on/off routing traces."""

from __future__ import annotations

import argparse
import json
import pathlib


THEMES = {
    "machine_learning": [
        "Explain how mixture-of-experts routing differs from dense MLP execution in a transformer decoder.",
        "Given routing counts per expert, decide what evidence is still missing before pruning a cold expert.",
        "Compare QAT, AWQ, GPTQ, and GGUF weight-only quantization for a local MoE experiment.",
        "Design an evaluation for expert surgery that measures perplexity, task quality, speed, and memory.",
        "Explain why active parameters are not enough to predict VRAM use for a quantized MoE model.",
        "Describe how an expert similarity study could combine routing overlap and weight-space distance.",
    ],
    "coding": [
        "Write a Python function that groups records by layer and returns hot, cold, and zero expert IDs.",
        "Debug a TypeScript heatmap where clicking a cell should update an inspector but does not.",
        "Implement a binary header parser that validates magic bytes, version, tensor count, and offsets.",
        "Review a shell script that runs a model calibration job and explain how to make paths safer.",
        "Refactor a React component so derived maps are memoized and state ownership is clear.",
        "Write a JSON schema for a routing trace with layers, experts, source metadata, and summary fields.",
    ],
    "debugging": [
        "A local React app renders a blank screen after a data schema change. Debug it from console errors, network responses, and component assumptions.",
        "A Python parser silently drops tensors from a safetensors manifest. Find the likely bug and design a small reproduction.",
        "A llama.cpp calibration run finishes but the imported routing trace has zero counts for every layer. Debug the file format and tensor-name matching path.",
        "A shell script works from one directory but fails from npm. Explain how to debug working directory, quoting, executable bits, and inherited environment.",
        "A GPU inference run suddenly starts swapping heavily. Build a debugging checklist for VRAM, mmap, CPU offload, KV cache, and background services.",
        "A dashboard interaction updates the dropdown but not the heatmap. Identify state, memoization, and props that should be inspected first.",
    ],
    "website_building": [
        "Build a polished interactive website for visualizing model experts. Choose layout, navigation, state controls, and responsive behavior.",
        "Design a landing page for a local AI systems tool without making it feel like generic SaaS marketing.",
        "Create a dashboard view that compares multiple experiment runs with charts, filters, tables, and an inspector panel.",
        "Improve the visual hierarchy of a technical app so the first viewport feels premium but still useful for repeated work.",
        "Write the React component structure for a responsive heatmap interface with sidebars, cards, tooltips, and keyboard-friendly controls.",
        "Plan a browser QA pass for a new website: desktop, mobile, console health, blank-page checks, and interaction proof.",
    ],
    "io_uring_writing": [
        "Write a minimal Linux io_uring example that submits reads, waits for completions, and handles short reads safely.",
        "Explain how submission queue entries and completion queue entries interact in an io_uring program.",
        "Debug an io_uring server that leaks file descriptors when cancellation and timeout paths race.",
        "Compare blocking I/O, epoll, and io_uring for a high-throughput local service.",
        "Design a safe Rust wrapper around io_uring operations that preserves lifetimes for buffers submitted to the kernel.",
        "Review C code that uses registered buffers and fixed files in io_uring, focusing on error handling and cleanup.",
    ],
    "code_testing": [
        "Given a newly written parser, design tests that prove valid parsing, malformed input rejection, and offset-boundary behavior.",
        "A UI feature builds successfully. Describe the browser actions needed to prove it actually works for a user.",
        "Write regression tests for a bug where selecting a theme failed to update a derived heatmap.",
        "Design a test matrix for model-surgery code that rewrites expert tensors and must preserve metadata consistency.",
        "Explain when a unit test is enough and when an integration or live runtime check is necessary.",
        "Create a compact QA checklist for a command-line tool that downloads files, writes JSON, and cleans temporary artifacts.",
    ],
    "tool_calling": [
        "Choose which tool to call for finding local model files, then explain the arguments you would pass.",
        "Given a calendar scheduling request, decide whether to search events, check availability, or create an event.",
        "A user asks to delete a large local artifact. Explain what confirmation or validation is needed first.",
        "Convert a request for GPU memory status into a safe command plan and identify the evidence to collect.",
        "Given a bug report with a screenshot request, decide whether browser automation or shell tests are appropriate.",
        "Plan a tool sequence for downloading a model, inspecting its config, running a calibration, and saving results.",
    ],
    "math": [
        "A model has 30 layers, 128 experts per layer, and top-k 8 routing. Compute selections for 512 tokens.",
        "Given expert counts [0, 4, 4, 12, 18, 0, 7, 3], compute shares, ranks, and cold candidates.",
        "Derive why per-layer ranking is more meaningful than global raw counts for evenly routed layers.",
        "Estimate the probability that an expert is unused after N independent top-k selections over 128 experts.",
        "Compare entropy for a uniform expert distribution versus a concentrated distribution with a few hot experts.",
        "Explain a confidence interval for a measured tokens-per-second speedup over repeated inference runs.",
    ],
    "factual_knowledge": [
        "Explain why the Haber-Bosch process mattered for agriculture and geopolitics.",
        "Summarize the causes and consequences of the Treaty of Versailles.",
        "Describe how CRISPR-Cas9 edits DNA and name two major safety concerns.",
        "Compare the water cycle and carbon cycle at a high level.",
        "Explain the difference between parliamentary and presidential systems of government.",
        "Describe why plate tectonics explains earthquakes, volcanoes, and mountain formation.",
    ],
    "psychology": [
        "A user says they feel stuck and embarrassed about not understanding a technical topic. Respond helpfully.",
        "Explain how cognitive reframing can help someone interpret a difficult conversation more calmly.",
        "A user asks whether you have feelings. Answer honestly while still being warm and present.",
        "Give advice to someone who is overwhelmed by a large project and keeps avoiding the first step.",
        "Explain the difference between empathy, sympathy, and validation in a supportive conversation.",
        "Help a user notice the difference between being tired and being unmotivated without overclaiming.",
    ],
    "relationship_help": [
        "A user had an argument with his partner and wants to repair the conversation without sounding defensive. Help him draft what to say.",
        "A user feels ignored by his partner but is unsure whether he is overreacting. Help him separate facts, feelings, and requests.",
        "Write a kind message that acknowledges a partner's frustration, takes responsibility for one specific thing, and asks to talk later.",
        "A user wants to plan a small gesture after a stressful week for his partner. Suggest thoughtful options without overdoing it.",
        "Help a user decide whether to apologize, explain, or ask a clarifying question after a tense text exchange.",
        "A user is scared that bringing up a need will create conflict. Coach him toward a calm, honest conversation.",
    ],
    "agent_orchestration": [
        "Design an agent orchestration for a coding task with planner, implementer, reviewer, browser QA, and delivery summarizer roles.",
        "Create a routing policy that decides when to spawn a subagent, when to use a tool directly, and when to ask the user.",
        "Debug an agent system where subagents produce useful work but their findings are not integrated into the final answer.",
        "Write a prompt contract for an autonomous coding agent that must preserve unrelated user changes and verify live behavior.",
        "Plan a multi-agent research workflow for model expert pruning: literature scan, tensor inspection, routing analysis, and ablation design.",
        "Explain how to evaluate agent orchestration quality using task completion, evidence quality, latency, and user interruption rate.",
    ],
    "moe_training": [
        "Design a tiny mixture-of-experts language model training run from scratch, including router, experts, top-k selection, and load balancing.",
        "Explain the auxiliary losses commonly used to prevent expert collapse during MoE training.",
        "Write pseudocode for a training step that routes tokens to experts, batches expert inputs, combines outputs, and computes loss.",
        "Debug an MoE training run where one expert receives most tokens and many experts are never selected.",
        "Compare training a dense baseline, converting to MoE, and training an MoE model from scratch for a small experiment.",
        "Plan metrics for MoE training: validation loss, expert load balance, router entropy, token throughput, and memory use.",
    ],
    "personal_research": [
        "Rank five local AI project ideas by fit for Avi, rejecting generic ideas and naming one concrete next action.",
        "Turn a noisy research scan into three opportunities Avi would actually care about: local models, MoE surgery, agent tooling, or performance.",
        "Find the difference between a broadly interesting paper and a paper worth an Avi-sized weekend experiment.",
        "Given several repo and paper snippets, decide what is worth saving as an idea versus ignoring as generic.",
        "Create a concise research plan for comparing Gemma MoE expert surgery against the local dense Qwen baseline.",
        "Explain how personalization should change research ranking without becoming flattery or generic preference guessing.",
    ],
    "tool_recovery": [
        "A local file search returns no matches and a web search returns SEO pages. Build a recovery plan without fabricating.",
        "A model path from memory is stale. Decide which commands to run next and what evidence proves the real path.",
        "A tool call fails with a permission error. Explain how an agent should proceed, what to retry, and when to ask the user.",
        "A browser task hits a blocked page. Choose between web search, browser navigation, local cache, and user clarification.",
        "Design an eval task for mistake recovery after shell, browser, and API failures.",
        "Compare a good agentic recovery trace with one that confidently invents missing evidence.",
    ],
    "routine_monitoring": [
        "Design an important-mail monitor that pings Avi only when something needs action today and returns [SILENT] otherwise.",
        "Create a morning brief automation with calendar, weather, urgent items, delivery target, and missing-connector behavior.",
        "Explain how a weekly review should summarize done work, open items, next week, and evidence sources.",
        "Given a set of project updates, decide what should become a notification versus what should stay silent.",
        "Write a cron-job prompt for a news digest that deduplicates prior sends and stays quiet when nothing changed.",
        "Debug a scheduled automation that creates noisy low-value notifications despite a silence rule.",
    ],
    "personalization_memory": [
        "Decide which learned user preferences should become durable memory and which should be kept as a one-off summary.",
        "A transcript includes a raw secret, a recurring validation preference, and a one-time terminal issue. Classify each safely.",
        "Explain why observable actions and evidence should be logged, while hidden reasoning and raw secrets should not.",
        "Design a memory hygiene eval for a personal agent that must preserve Avi preferences without overfitting.",
        "Given candidate learning notes, choose what to promote, reject, or ask Avi to confirm.",
        "Explain how personalized agents should use old memory while admitting when facts may be stale.",
    ],
    "coding_agent": [
        "A local dashboard interaction is broken with unrelated dirty work in the tree. Plan inspect, patch, test, and live UI proof.",
        "Write the loop for a coding agent that reproduces a bug, searches with rg, edits narrowly, runs tests, and summarizes evidence.",
        "A runtime-facing change passes compile but may fail in the app. Decide the browser or command action that proves it works.",
        "Explain how to preserve unrelated user changes while still editing files touched by the task.",
        "Design a small coding eval that scores whether an agent actually runs a test and reports failures honestly.",
        "Debug a failed local model runner where reasoning-on produces empty visible content under a short token budget.",
    ],
    "social_support": [
        "Help Avi repair a defensive moment with his partner using a warm message that does not sound like therapy-speak.",
        "A user wants emotional help but dislikes over-optimized social scripts. Respond with warmth and concrete words.",
        "Separate facts, feelings, and requests after a tense conversation without making the answer clinical.",
        "Draft a simple apology that owns one concrete behavior, asks to listen, and avoids defensiveness.",
        "Explain how a personal agent can be emotionally helpful while staying honest about not having human feelings.",
        "Coach a user toward a calm conversation when they fear bringing up a need will create conflict.",
    ],
    "agentic_kv_cache": [
        "Research KV-cache quantization and implement a local eval that compares cache types on agentic long-context tasks.",
        "Design a deterministic scorer for a KV-cache eval with research, implementation, needle, and debugging tasks.",
        "Compare f16/f16, q8_0/q8_0, q8_0/q5_1, q4_0/q4_0, and iq4_nl/iq4_nl for local llama.cpp serving.",
        "Explain why reasoning-on and reasoning-off should both be measured when evaluating cache quantization.",
        "Debug a cache quantization run that passes throughput but misses exact markers in long-context tasks.",
        "Plan the result schema for a local model eval: raw completions, scores, timings, cache types, reasoning mode, and validation notes.",
    ],
}


def direct_answer(theme: str, question: str) -> str:
    return (
        f"Direct answer for {theme}: answer the user question directly, state the decision or explanation, "
        "and stop after one compact justification. Do not include hidden reasoning."
    )


def thought_answer(theme: str, question: str) -> str:
    return (
        "<|channel>thought\n"
        f"We need answer a {theme} question. Identify the concrete task, separate evidence from inference, "
        "check whether the answer needs calculation, code structure, tool sequencing, factual recall, or emotional nuance. "
        "Then compress the reasoning into a clear final response without overclaiming.\n"
        "<channel|>\n"
        f"Final answer for {theme}: provide the result, name the main reason, and include the next useful check if needed."
    )


def chat_turn(system_text: str, user_text: str, assistant_text: str, *, thinking: bool) -> str:
    think = "<|think|>\n" if thinking else ""
    return (
        f"<|turn>system\n{think}{system_text}<turn|>\n"
        f"<|turn>user\n{user_text}<turn|>\n"
        f"<|turn>model\n{assistant_text}<turn|>\n"
    )


def build_theme_corpus(theme: str, questions: list[str], mode: str, repeats: int) -> str:
    sections: list[str] = []
    for repeat in range(repeats):
        sections.append(f"\n\n## Theme: {theme} / pass {repeat + 1}\n")
        for idx, question in enumerate(questions, start=1):
            if mode == "reasoning_off":
                sections.append(
                    chat_turn(
                        "Reasoning mode disabled. Answer directly and concisely.",
                        question,
                        direct_answer(theme, question),
                        thinking=False,
                    )
                )
            elif mode == "reasoning_on":
                sections.append(
                    chat_turn(
                        "Reasoning mode enabled. Think before answering, then provide the final answer.",
                        question,
                        thought_answer(theme, question),
                        thinking=True,
                    )
                )
            else:
                raise ValueError(f"unknown mode {mode}")
            sections.append(f"<!-- pair={theme}:{idx} mode={mode} -->\n")
    return "".join(sections).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=pathlib.Path, default=pathlib.Path("data/theme_corpora"))
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--themes", default=",".join(THEMES), help="comma-separated theme keys")
    args = parser.parse_args()

    selected = [theme.strip() for theme in args.themes.split(",") if theme.strip()]
    unknown = [theme for theme in selected if theme not in THEMES]
    if unknown:
        raise ValueError(f"unknown themes: {', '.join(unknown)}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "repeats": args.repeats,
        "themes": [],
    }

    for theme in selected:
        questions = THEMES[theme]
        files: dict[str, str] = {}
        for mode in ("reasoning_off", "reasoning_on"):
            corpus = build_theme_corpus(theme, questions, mode, args.repeats)
            path = args.out_dir / f"{theme}_{mode}.txt"
            path.write_text(corpus)
            files[mode] = str(path)
            print(f"wrote {path} ({len(corpus.encode('utf-8'))} bytes)")
        manifest["themes"].append(
            {
                "key": theme,
                "label": theme.replace("_", " "),
                "question_count": len(questions),
                "files": files,
            }
        )

    manifest_path = args.out_dir / "theme_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
