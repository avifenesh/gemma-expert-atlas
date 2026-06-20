#!/usr/bin/env python3
"""Create a larger personal-agent task bank from Hermes and recurring Codex work."""

from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path
from typing import Any

from make_personal_agent_eval import AVI_PROFILE, REPO_SURFACE, SOURCES, check, write_jsonl


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "personal_agent_bank" / "tasks.jsonl"
DEFAULT_SOURCES = ROOT / "data" / "personal_agent_bank" / "sources.json"

CODEX_SURFACES = [
    {
        "id": "codex_recurring_work",
        "title": "Recurring Codex-style work patterns",
        "insights": [
            "Review tasks should prioritize bugs, regressions, missing tests, and concrete file or command evidence.",
            "Implementation tasks should inspect first, patch narrowly, preserve unrelated dirty work, run tests, and prove runtime behavior when user-visible.",
            "Release or install tasks should verify the installed/runtime surface, not just the repository state.",
            "Local model tasks should prefer actual local wrappers and measured behavior over generic assumptions.",
            "Cleanup tasks should identify what is safe to stop or remove and avoid destructive actions without clear evidence.",
        ],
    }
]

COMMON_CONTEXT = """
The model is being evaluated as Avi's local personal agent. It should do useful work,
recover from failed tools, preserve preferences, and prefer evidence over polished generic advice.
It should be especially strong at local model work, MoE expert surgery, coding, debugging, agent
orchestration, research ranking, quiet monitoring, memory hygiene, and social support.
"""

FAMILY_CHECKS: dict[str, list[dict[str, object]]] = {
    "personal_research": [
        check("avi-fit", "contains_any", 1.0, terms=["Avi", "fit", "local", "personal"]),
        check("reject-noise", "contains_any", 1.0, terms=["reject", "ignore", "not a fit", "generic"]),
        check("next-action", "contains_any", 1.0, terms=["next action", "first step", "run", "measure"]),
        check("no-unrelated-inspect", "not_contains_any", 1.0, terms=["npm run inspect", "inspect_gemma4_moe.py"]),
    ],
    "tool_recovery": [
        check("no-fabrication", "contains_any", 1.0, terms=["do not fabricate", "not assume", "verify", "evidence"]),
        check("alternate-route", "contains_any", 1.0, terms=["fallback", "alternate", "retry", "inspect"]),
        check("tool-or-command", "contains_any", 1.0, terms=["rg", "find", "ls", "web_search", "browser", "command"]),
    ],
    "coding_agent": [
        check("inspect", "contains_any", 1.0, terms=["rg", "read", "inspect", "reproduce"]),
        check("patch", "contains_any", 1.0, terms=["patch", "apply_patch", "edit"]),
        check("validate", "contains_any", 1.0, terms=["test", "build", "run", "verify", "browser"]),
    ],
    "code_review": [
        check("findings-first", "contains_any", 1.0, terms=["bug", "risk", "regression", "missing test"]),
        check("evidence", "contains_any", 1.0, terms=["file", "line", "evidence", "reproduce"]),
        check("severity", "contains_any", 1.0, terms=["severity", "P0", "P1", "P2", "priority"]),
    ],
    "routine_monitoring": [
        check("silent", "contains_any", 1.0, terms=["[SILENT]", "silent", "do not notify"]),
        check("criteria", "contains_any", 1.0, terms=["today", "deadline", "urgent", "needs action"]),
        check("delivery", "contains_any", 1.0, terms=["deliver", "origin", "message", "notify"]),
    ],
    "personalization_memory": [
        check("durable", "contains_any", 1.0, terms=["durable", "memory", "promote", "preference"]),
        check("reject-oneoff", "contains_any", 1.0, terms=["one-off", "do not", "summary", "reject"]),
        check("secrets", "contains_any", 1.0, terms=["secret", "token", "never", "raw"]),
    ],
    "agent_orchestration": [
        check("roles", "contains_any", 1.0, terms=["planner", "implementer", "reviewer", "subagent", "phase"]),
        check("tools", "contains_any", 1.0, terms=["web", "terminal", "file", "browser", "tool"]),
        check("integrate", "contains_any", 1.0, terms=["integrate", "final", "evidence", "handoff"]),
    ],
    "model_ops": [
        check("model", "contains_any", 1.0, terms=["Gemma", "Qwen", "MoE", "expert", "llama.cpp"]),
        check("quant-or-kv", "contains_any", 1.0, terms=["quant", "KV", "cache", "GGUF", "fp16", "bf16"]),
        check("eval", "contains_any", 1.0, terms=["eval", "baseline", "regression", "score", "throughput"]),
    ],
    "expert_surgery": [
        check("expert", "contains_all", 1.0, terms=["expert", "eval"]),
        check("trim-merge", "contains_any", 1.0, terms=["trim", "merge", "prune", "candidate"]),
        check("gate", "contains_any", 1.0, terms=["regression", "baseline", "gate", "quality"]),
    ],
    "social_support": [
        check("warm", "contains_any", 1.0, terms=["warm", "kind", "simple", "human"]),
        check("responsibility", "contains_any", 1.0, terms=["sorry", "own", "responsibility", "defensive"]),
        check("draft", "contains_any", 1.0, terms=["draft", "say", "message", "talk"]),
    ],
    "instruction_following": [
        check("format", "contains_any", 1.0, terms=["exact", "format", "JSON", "only"]),
        check("constraint", "contains_any", 1.0, terms=["do not", "must", "preserve", "limit"]),
        check("complete", "contains_any", 1.0, terms=["done", "complete", "answer", "return"]),
    ],
    "local_system_ops": [
        check("identify", "contains_any", 1.0, terms=["process", "daemon", "service", "GPU", "port"]),
        check("safe", "contains_any", 1.0, terms=["safe", "confirm", "evidence", "non-destructive"]),
        check("command", "contains_any", 1.0, terms=["pgrep", "nvidia-smi", "kill", "systemctl", "command"]),
    ],
    "eval_design": [
        check("baseline", "contains_any", 1.0, terms=["baseline", "control", "compare"]),
        check("metric", "contains_any", 1.0, terms=["score", "latency", "throughput", "pass", "regression"]),
        check("artifact", "contains_any", 1.0, terms=["JSON", "results", "completion", "trace", "artifact"]),
    ],
}


SCENARIOS: dict[str, list[tuple[str, str]]] = {
    "personal_research": [
        (
            "Rank these paper/tool leads by Avi-fit and reject the generic ones: "
            "A. MoE router specialization for local agents; B. enterprise prompt dashboards; "
            "C. KV-cache quantization for long-context coding; D. celebrity AI summaries; "
            "E. small benchmark for failed-tool recovery."
        ),
        ("Choose which of five project ideas should become a weekend experiment for local-model agent tooling."),
        ("Turn a noisy web scan into three concrete opportunities around MoE surgery, llama.cpp, and agent evals."),
        ("Decide whether a new browser automation library is worth Avi's time compared with model-routing work."),
        ("Summarize a set of small local tooling ideas and pick one that connects to Avi's current model work."),
        ("Find what is missing before saving an idea about personal agents into long-term memory."),
        ("Given several AI releases, identify which should trigger an experiment and which are just news."),
        ("Create a short opportunity note for a task that combines performance optimization and personal agents."),
    ],
    "tool_recovery": [
        ("Recover when a local model path from memory does not exist and the first search returns no matches."),
        ("Recover when a browser page is blocked and a web search gives unrelated SEO pages."),
        ("Recover when a command exits 127 during an eval run and the user expects the task to keep moving."),
        ("Recover when a Hugging Face download has an incomplete shard and the model loader fails."),
        ("Recover when a tool returns empty output but the task still needs evidence."),
        ("Recover when a calendar or email connector is missing during a monitor setup."),
        ("Recover when a local server starts but the health endpoint never becomes ready."),
        ("Recover when an eval completion is empty in reasoning-on mode under a short token budget."),
    ],
    "coding_agent": [
        ("Fix a React heatmap state bug while preserving unrelated dirty work and prove it with a browser action."),
        ("Implement a CLI flag in a Python eval runner, update docs, and run a dry-run plus a smoke."),
        ("Debug a script that works from the shell but fails from npm because of working directory assumptions."),
        ("Patch a JSON importer that silently drops expert counts and add a small regression check."),
        ("Add a score-only path for an eval runner and verify it with a fixture completion."),
        ("Make a local dev server URL available after changing a dashboard and check console health."),
        ("Fix a timeout in a model server loop and ensure the process is stopped afterward."),
        ("Refactor duplicated task-generation code only if it reduces real complexity and keeps behavior stable."),
    ],
    "code_review": [
        ("Review a patch that changes model-loading flags and look for runtime regressions and missing smoke tests."),
        ("Review a PR that updates a memory pipeline and check for durable-learning and secret-logging risks."),
        ("Review a browser UI change for state bugs, empty screens, and mobile text overflow."),
        ("Review a shell cleanup script for destructive commands and poor process matching."),
        ("Review a KV-cache eval patch for unfair prompt-cache reuse and missing baseline comparisons."),
        ("Review a model-surgery script for metadata corruption, tensor-shape mistakes, and no rollback path."),
        ("Review a scheduling change that might notify the user too often instead of returning [SILENT]."),
        ("Review a tool-calling agent patch that hides failed tools behind a polished final answer."),
    ],
    "routine_monitoring": [
        ("Design a morning briefing that uses calendar, weather, urgent items, and stays useful when sources are missing."),
        ("Design an important-mail monitor that only surfaces messages needing action today."),
        ("Design a weekly review that summarizes done work, open loops, and next week without becoming an agent console."),
        ("Design a news digest that dedupes against prior sends and returns [SILENT] when nothing changed."),
        ("Decide whether a project update should notify Avi, be logged locally, or be ignored."),
        ("Create a quiet monitor for repeated local agent errors with escalation after repeated incidents."),
        ("Create a reminder automation and include schedule, delivery, and failure behavior."),
        ("Debug a noisy automation that sends low-value messages despite an urgency rule."),
    ],
    "personalization_memory": [
        ("Promote a recurring preference about live validation and reject a one-off terminal issue."),
        ("Classify a candidate memory that includes a raw token, a useful behavior preference, and a stale path."),
        ("Summarize a completed release loop without storing repo-specific noise as a permanent preference."),
        ("Decide whether 'be kind in PR comments' should update style memory or remain task-local."),
        ("Handle a stale memory-derived model path by marking it uncertain and collecting current evidence."),
        ("Create memory notes for agent behavior without logging hidden reasoning."),
        ("Reject over-broad memory from one conversation that would overfit the personal agent."),
        ("Choose what to ask Avi before changing durable learning rules."),
    ],
    "agent_orchestration": [
        ("Plan subagents for a KV-cache research and implementation task with source gathering, patching, review, and QA."),
        ("Orchestrate a coding task with planner, implementer, reviewer, and browser verifier roles."),
        ("Decide when a personal agent should spawn a subagent instead of using a tool directly."),
        ("Integrate useful subagent findings into a single final answer without losing evidence."),
        ("Design a multi-agent expert-surgery experiment with routing analysis, tensor inspection, ablation, and eval gates."),
        ("Route a task between web research, terminal work, file edits, and final summarization."),
        ("Plan a handoff from background Hermes monitoring to interactive Codex work."),
        ("Debug an orchestration where all subagents succeeded but the final answer ignored their results."),
    ],
    "model_ops": [
        ("Compare QAT, AWQ, GPTQ, GGUF, NVFP4, and KV-cache quantization for this local Gemma workflow."),
        ("Decide whether to run Gemma MoE half on GPU and half on CPU, naming practical bottlenecks."),
        ("Create an eval matrix for q8_0/q5_1 KV cache versus f16/f16 on long-context agent tasks."),
        ("Explain why active parameters are not enough to predict memory stress for an MoE model."),
        ("Plan how to locally quantize a changed HF checkpoint after every expert-surgery step."),
        ("Debug a llama.cpp server that works with reasoning-off but returns empty visible content with reasoning-on."),
        ("Compare local Gemma MoE against dense Qwen for personal-agent tasks with speed and quality metrics."),
        ("Choose cache, batch, context, and reasoning settings for a short local smoke before a full eval."),
    ],
    "expert_surgery": [
        ("Create a safe first trim plan for experts that are dead across personal-agent routing traces."),
        ("Explain why a half-dead expert should be merged only after routing and weight-similarity evidence."),
        ("Design an experiment with baseline, trim-only, merge-low-use, and add-specialist variants."),
        ("Set gates for accepting a trimmed model: no exact-task failures, no tool recovery regression, and speed improvement."),
        ("Explain how to discover task-hot experts that should be protected even if they are cold globally."),
        ("Plan how to compare two expert-surgery variants and transplant the useful specialized behavior."),
        ("Describe why adding experts requires router adaptation and cannot be validated by copying tensors alone."),
        ("Create a rollback plan if a surgery improves speed but fails social-support or memory-hygiene tasks."),
    ],
    "social_support": [
        ("Draft a repair message after Avi sounded defensive with his partner and wants it to feel human."),
        ("Help decide whether to apologize, explain, or ask a clarifying question after a tense text exchange."),
        ("Write a kind message that owns one concrete thing without overdoing therapy language."),
        ("Coach a calm conversation when Avi worries that bringing up a need will create conflict."),
        ("Help separate facts, feelings, and requests without making the answer clinical."),
        ("Suggest a small thoughtful gesture after a stressful week without turning it into a performance."),
        ("Answer honestly about not having human feelings while still being warm and present."),
        ("Help rewrite a message so it is simpler, less defensive, and easier to hear."),
    ],
    "instruction_following": [
        ("Return exactly a JSON array of tool actions and no prose for a local model inspection task."),
        ("Follow a user's instruction to avoid writeup-only work and create artifacts plus validation."),
        ("Keep an answer short but include the exact file and command evidence the user needs."),
        ("Refuse to invent unavailable information and ask only if the missing fact blocks progress."),
        ("Preserve an exact sentinel string in a long-context answer while solving the task."),
        ("Choose between acting and asking when user intent is terse but the operation is safe."),
        ("Follow a constraint to avoid generic tasks and produce reusable personal-agent tasks only."),
        ("Report command output accurately without exposing internal tool noise."),
    ],
    "local_system_ops": [
        ("Stop a local embedding service until needed again and verify no matching process remains."),
        ("Kill a development daemon by name without killing unrelated processes."),
        ("Check GPU memory before starting a local model server and decide whether to proceed."),
        ("Clean generated eval artifacts while preserving source datasets and unrelated work."),
        ("Inspect which ports are in use before starting a dashboard or llama-server."),
        ("Shut down a long-running local server after a smoke test and prove it stopped."),
        ("Find the largest local model artifacts and propose cleanup without deleting anything yet."),
        ("Diagnose why a local model run is swapping by checking VRAM, mmap, CPU offload, and background services."),
    ],
    "eval_design": [
        ("Design deterministic scoring for personal-agent tasks without a judge model."),
        ("Create an eval split for smoke, daily, full, and surgery-gate runs."),
        ("Define metrics for speed, memory, quality, exact retrieval, and tool recovery."),
        ("Design an ablation that compares reasoning-on and reasoning-off for each task family."),
        ("Create a result schema that stores prompts, completions, scores, timings, cache settings, and model variant."),
        ("Decide when a quality drop is acceptable because a trimmed model is much faster."),
        ("Create a regression gate for expert surgery with family-level minimum scores."),
        ("Explain how routing traces and eval results should be joined before deleting experts."),
    ],
}


def source_packet() -> str:
    sources = SOURCES + CODEX_SURFACES
    return "\n".join(
        f"- [{source['id']}] {source['title']}: " + " ".join(source["insights"])
        for source in sources
    )


def make_prompt(category: str, body: str, repeats: int) -> str:
    context_blocks = []
    for idx in range(repeats):
        context_blocks.append(
            f"Context pass {idx:02d}: personal-agent work should stay evidence-grounded, "
            "avoid generic output, recover from failed tools, preserve user preferences, "
            "and validate runtime-facing changes."
        )
    return textwrap.dedent(
        f"""
        You are evaluating a local personal-agent model for Avi.

        AVI PROFILE
        {AVI_PROFILE.strip()}

        LOCAL REPO SURFACE
        {REPO_SURFACE.strip()}

        SOURCE PACKET
        {source_packet()}

        COMMON CONTEXT
        {COMMON_CONTEXT.strip()}

        LONG CONTEXT
        {chr(10).join(context_blocks)}

        TASK FAMILY
        {category}

        TASK
        {body}

        RESPONSE FORMAT
        Use concise markdown with these headings:
        - Decision
        - Plan
        - Evidence
        - Validation
        Name exact commands or tools when useful. Do not invent script names, paths, sources, or completed actions.
        """
    ).strip()


def build_tasks(repeats: int) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for category, scenarios in SCENARIOS.items():
        family_checks = FAMILY_CHECKS[category]
        for index, body in enumerate(scenarios, start=1):
            task_id = f"{category}_{index:03d}"
            tasks.append(
                {
                    "id": task_id,
                    "title": body,
                    "category": category,
                    "prompt": make_prompt(category, body, repeats),
                    "scoring": {"checks": family_checks},
                }
            )
    return tasks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--sources-out", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--repeat-context", type=int, default=3)
    args = parser.parse_args()

    tasks = build_tasks(max(0, args.repeat_context))
    write_jsonl(args.out, tasks)
    args.sources_out.parent.mkdir(parents=True, exist_ok=True)
    args.sources_out.write_text(
        json.dumps({"sources": SOURCES + CODEX_SURFACES, "families": sorted(SCENARIOS)}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.out} ({len(tasks)} tasks)")
    print(f"wrote {args.sources_out} ({len(SOURCES) + len(CODEX_SURFACES)} sources)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
