#!/usr/bin/env python3
"""Create a Hermes-shaped personal-agent eval dataset."""

from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "personal_agent_eval" / "tasks.jsonl"
DEFAULT_SOURCES = ROOT / "data" / "personal_agent_eval" / "sources.json"

SOURCES = [
    {
        "id": "hermes_readme",
        "title": "Hermes README surfaces",
        "path": "~/projects/hermes-agent/README.md",
        "insights": [
            "Hermes is a personal agent with a learning loop, memory, skills, session search, and a model of the user across sessions.",
            "It supports scheduled automations, terminal and tool execution, messaging delivery, and subagents.",
            "It is provider-agnostic and can run from local or remote environments.",
        ],
    },
    {
        "id": "hermes_toolsets",
        "title": "Hermes toolset distributions",
        "path": "~/projects/hermes-agent/toolset_distributions.py",
        "insights": [
            "Research tasks are web and browser heavy with some vision and reasoning.",
            "Development tasks are terminal/file heavy with reasoning and occasional web lookup.",
            "Mixed tasks combine browser, terminal, file, web, and occasional vision.",
        ],
    },
    {
        "id": "hermes_automation_catalog",
        "title": "Hermes automation catalogs",
        "path": "~/projects/hermes-agent/cron/blueprint_catalog.py",
        "insights": [
            "Built-in automations include morning briefings, important-mail monitors, weekly reviews, workday starts, reminders, evening wind-downs, and news digests.",
            "Important monitors should return [SILENT] when nothing clears the bar.",
            "Automations need schedule, prompt, delivery, and connected-source behavior.",
        ],
    },
    {
        "id": "avi_ops_policy",
        "title": "Avi ops policy summary",
        "path": "~/.hermes/avi-ops-policy.json",
        "insights": [
            "Avi-facing pages should read like choices for Avi, not assignments from an agent.",
            "Act first when the action is read-only, local-file-only, Notion-only, or otherwise low-risk and well-evidenced.",
            "Escalate or propose when user judgment, external writes, durable learning, GPU use, or low confidence is involved.",
            "Trace observable actions, evidence, decisions, confidence, and next actions; do not log hidden reasoning or raw secrets.",
        ],
    },
    {
        "id": "avi_debugger_policy",
        "title": "Avi debugger policy summary",
        "path": "~/.hermes/avi-debugger-policy.json",
        "insights": [
            "Debugger tasks include incident intake, root-cause analysis, log/session bisection, memory audit, and report drafting.",
            "Escalate repeated incidents or cases spanning model behavior, memory, prompt, and code.",
            "Collect evidence with known-good/known-bad boundaries and confidence rather than guessing.",
        ],
    },
]

AVI_PROFILE = """
Avi uses local models mostly as personal coding and agentic assistants.
The important jobs are: research things that are actually interesting to Avi, find small opportunities,
write and test code, debug local systems, orchestrate agents, help with social conversations, and preserve
personal preferences across sessions.

Current modeling goal: make Gemma 4 26B A4B MoE a better personal agent than the local dense Qwen 27B setup,
with less memory pressure and better tool use, instruction following, coding, recovery from mistakes,
personalization, and social nuance.

Operational preferences:
- Use reasoning-on behavior as first-class because that is the normal working mode.
- Do real validation when code or runtime behavior changes.
- Preserve unrelated dirty work.
- Prefer direct action with evidence over generic advice.
- Avoid writing external systems, durable memory, or GPU-heavy jobs without clear permission.
- Do not expose secrets or hidden reasoning in traces.
"""

REPO_SURFACE = """
Known commands and scripts in this repo:
- npm run inspect
- npm run make-theme-corpora
- npm run calibrate:themes
- npm run make-kv-cache-eval
- npm run eval:kv-cache
- npm run make-personal-agent-eval
- npm run eval:personal-agent
- scripts/inspect_gemma4_moe.py
- scripts/make_theme_corpora.py
- scripts/run_theme_calibrations.sh
- scripts/run_kv_cache_eval.py
- scripts/import_imatrix_counts.py

Do not invent script names. If the exact command is not known from this surface,
say what evidence to inspect next instead of fabricating a command.
"""

DISTRACTORS = [
    "A polished answer is useful only if it still contains concrete commands, files, or verification evidence.",
    "Personalization is not flattery. It means choosing what matters to Avi and discarding generic noise.",
    "A monitor should be quiet when there is nothing important to say.",
    "A tool failure is not the end of the task; it is evidence that should change the next action.",
    "For expert surgery, quality drops matter more than theoretical memory savings.",
    "For agentic local models, instruction following and recovery are as important as raw knowledge.",
]


def long_context(repeats: int) -> str:
    blocks: list[str] = []
    for idx in range(repeats):
        blocks.append(f"Context repetition {idx:02d}:")
        for line in DISTRACTORS:
            blocks.append(f"- {line} Marker {idx:02d}.")
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
    source_packet = "\n".join(
        f"- [{source['id']}] {source['title']}: " + " ".join(source["insights"])
        for source in SOURCES
    )
    prompt = textwrap.dedent(
        f"""
        You are evaluating a local personal-agent model for Avi.
        Use the profile and Hermes evidence below. Answer the task directly and operationally.

        AVI PROFILE
        {AVI_PROFILE.strip()}

        LOCAL REPO SURFACE
        {REPO_SURFACE.strip()}

        HERMES EVIDENCE PACKET
        {source_packet}

        LONG CONTEXT
        {long_context(repeats)}

        TASK
        {body}

        RESPONSE FORMAT
        Use concise markdown with these headings:
        - Decision
        - Plan
        - Evidence
        - Validation
        When tool use is relevant, name the exact tool or command you would use from the repo surface above.
        When nothing should be sent to the user, include the literal token [SILENT].
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
            "personal_interest_scout",
            "Find small opportunities Avi would actually care about",
            "personal_research",
            """
            You found these possible ideas while scanning:
            1. A generic productivity app with calendar colors.
            2. A local MoE expert-surgery workflow for trimming, merging, and re-quantizing Gemma experts.
            3. A new llama.cpp KV-cache quantization comparison for long-context coding agents.
            4. A celebrity news summarizer.
            5. A tiny benchmark for local agent tool-call recovery after failed shell/browser steps.

            Pick the best three for Avi, reject the generic ones, and give the next concrete action for the top pick.
            """,
            [
                check("moe-picked", "contains_all", 1.0, terms=["MoE", "expert"]),
                check("kv-cache-picked", "contains_all", 1.0, terms=["KV", "cache"]),
                check("tool-recovery-picked", "contains_all", 1.0, terms=["tool", "recovery"]),
                check("reject-generic", "contains_any", 1.0, terms=["generic", "reject", "not a fit"]),
                check(
                    "known-command",
                    "contains_any",
                    1.0,
                    terms=[
                        "make-theme-corpora",
                        "calibrate:themes",
                        "run_theme_calibrations.sh",
                        "inspect_gemma4_moe.py",
                        "run_kv_cache_eval.py",
                    ],
                ),
                check("avi-fit", "contains_any", 1.0, terms=["Avi", "personal", "local"]),
            ],
            repeats,
        ),
        task(
            "tool_failure_recovery",
            "Recover after failed tools without fabricating",
            "tool_recovery",
            """
            A research/coding agent tried to inspect a local model and got:
            - `rg gemma4 /data/ai-ml`: no matches
            - `ls /data/ai-ml/hf-models/gemma4-26ba4b-base`: no such file
            - web search for a specific repo returned unrelated SEO pages

            Write the recovery plan. It should continue making progress, avoid fabrication, and say exactly what evidence
            to collect next.
            """,
            [
                check("do-not-fabricate", "contains_any", 1.0, terms=["do not fabricate", "don't fabricate", "not assume"]),
                check("local-search", "contains_any", 1.0, terms=["find", "rg --files", "ls"]),
                check("alternate-paths", "contains_any", 1.0, terms=["HF_HOME", "/data/ai-ml", "huggingface", "cache"]),
                check("web-fallback", "contains_any", 1.0, terms=["official", "source", "repo", "Hugging Face"]),
                check("evidence", "contains_all", 1.0, terms=["evidence", "path"]),
                check("ask-if-blocked", "contains_any", 1.0, terms=["ask", "blocked", "permission"]),
            ],
            repeats,
        ),
        task(
            "coding_agent_debug_loop",
            "Debug, patch, test, and prove a code change",
            "coding_agent",
            """
            A local dashboard loads but the expert heatmap does not update after selecting a different theme.
            There is unrelated dirty work in the tree. Produce the agent loop you want from the model, including how it
            should inspect files, patch safely, test, and prove the UI behavior really changed.
            """,
            [
                check("preserve-dirty", "contains_all", 1.0, terms=["unrelated", "dirty"]),
                check("search-files", "contains_any", 1.0, terms=["rg", "inspect", "read"]),
                check("targeted-patch", "contains_any", 1.0, terms=["patch", "apply_patch", "targeted"]),
                check("tests", "contains_any", 1.0, terms=["test", "build", "npm run"]),
                check("browser-proof", "contains_any", 1.0, terms=["browser", "screenshot", "click", "live"]),
                check("state-bug", "contains_any", 1.0, terms=["state", "memo", "props", "derived"]),
            ],
            repeats,
        ),
        task(
            "automation_monitor_design",
            "Design a quiet useful Hermes monitor",
            "routine_monitoring",
            """
            Design a Hermes automation that checks for important messages and project updates every 30 minutes.
            It should notify Avi only when something needs action today, otherwise stay quiet. Include schedule, delivery,
            source behavior, and failure behavior when no connector is configured.
            """,
            [
                check("schedule", "contains_any", 1.0, terms=["every 30m", "*/30", "30 minutes"]),
                check("silent", "exact", 1.0, text="[SILENT]"),
                check("delivery", "contains_any", 1.0, terms=["origin", "deliver", "delivery"]),
                check("sources", "contains_any", 1.0, terms=["mail", "inbox", "calendar", "project"]),
                check("urgent-only", "contains_any", 1.0, terms=["today", "deadline", "urgent", "needs action"]),
                check("missing-connector", "contains_any", 1.0, terms=["connect", "configured", "connector"]),
            ],
            repeats,
        ),
        task(
            "memory_learning_hygiene",
            "Decide what becomes durable memory",
            "personalization_memory",
            """
            A background learning run found these candidates:
            - Avi likes live validation after runtime changes.
            - A one-off terminal window was empty after a GPU cleanup.
            - A secret token appeared in a log snippet.
            - Avi wants ideas ranked by fit and concrete next action, not generic lists.
            - An npm publish failed once due to an account token problem.

            Decide what should become durable memory, what should be summarized only, and what must never be logged.
            """,
            [
                check("live-validation-memory", "contains_all", 1.0, terms=["live", "validation"]),
                check("ideas-memory", "contains_all", 1.0, terms=["ideas", "next action"]),
                check("secret-never", "contains_all", 1.0, terms=["secret", "never"]),
                check("one-off", "contains_any", 1.0, terms=["one-off", "summary", "do not"]),
                check("durable-learning", "contains_any", 1.0, terms=["durable", "memory", "learning"]),
                check("observable-trace", "contains_any", 1.0, terms=["observable", "evidence", "trace"]),
            ],
            repeats,
        ),
        task(
            "social_repair_message",
            "Help with a girlfriend conversation without becoming robotic",
            "social_support",
            """
            Avi says: "I think I was too defensive with my girlfriend. I want to repair it but not make it sound like
            I am optimizing her or doing therapy-speak." Write the response the personal agent should give.
            """,
            [
                check("acknowledge", "contains_any", 1.0, terms=["defensive", "understand", "acknowledge"]),
                check("responsibility", "contains_any", 1.0, terms=["responsibility", "own", "sorry", "apologize"]),
                check("draft", "contains_any", 1.0, terms=["say", "message", "draft"]),
                check("not-therapy", "contains_any", 1.0, terms=["not", "therapy", "robotic", "overdo"]),
                check("ask-talk", "contains_any", 1.0, terms=["talk", "listen", "hear"]),
                check("warm", "contains_any", 1.0, terms=["warm", "kind", "simple", "human"]),
            ],
            repeats,
        ),
        task(
            "agent_orchestration_handoff",
            "Plan a multi-agent KV-cache eval implementation",
            "agent_orchestration",
            """
            Avi asks: "perform research about KV cache and implement eval for KV cache quant method."
            Design the orchestration for a personal agent: which subagents or phases to use, when to use web, terminal,
            file reads, browser QA, and how to finish with evidence instead of a writeup-only answer.
            """,
            [
                check("research", "contains_any", 1.0, terms=["research", "web", "source"]),
                check("implementation", "contains_any", 1.0, terms=["implement", "patch", "file"]),
                check("terminal", "contains_any", 1.0, terms=["terminal", "command", "test"]),
                check("browser-qa", "contains_any", 1.0, terms=["browser", "QA", "screenshot", "UI"]),
                check("evidence", "contains_all", 1.0, terms=["evidence", "validation"]),
                check("no-writeup-only", "contains_any", 1.0, terms=["not just", "writeup", "artifact"]),
            ],
            repeats,
        ),
        task(
            "tool_call_selection",
            "Choose tools for a personal research-and-code task",
            "tool_calling",
            """
            Available tools: web_search, browser_open, rg, read_file, exec_command, apply_patch, npm_test.
            The user asks: "Find whether my local Gemma model has a better quant available, then update the eval runner if
            the current mode cannot handle reasoning-on."

            Output the first six tool actions as a JSON array. Each item needs tool, args, and why.
            """,
            [
                check("json-array", "regex", 1.0, pattern=r"\[[\s\S]*\]"),
                check("web-search", "contains_any", 1.0, terms=["web_search", "Hugging Face", "official"]),
                check("local-search", "contains_any", 1.0, terms=["rg", "find", "ls"]),
                check("read-file", "contains_any", 1.0, terms=["read_file", "sed", "cat"]),
                check("patch", "contains_any", 1.0, terms=["apply_patch", "patch"]),
                check("test", "contains_any", 1.0, terms=["npm_test", "py_compile", "dry-run"]),
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
    parser.add_argument("--repeat-context", type=int, default=4, help="More repeats means longer prompts.")
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
