#!/usr/bin/env python3
"""Run agentic KV-cache quantization evals against llama.cpp server."""

from __future__ import annotations

import argparse
import datetime as dt
import http.client
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKS = ROOT / "data" / "kv_cache_eval" / "tasks.jsonl"
DEFAULT_RUNS = ROOT / "data" / "kv_cache_eval" / "runs"
DEFAULT_MODEL = os.environ.get("GEMMA4_GGUF", "/data/ai-ml/hf-models/gemma4-26ba4b-qat-gguf/gemma-4-26B_q4_0-it.gguf")
DEFAULT_SERVER = os.environ.get("LLAMA_SERVER", str(Path.home() / "projects" / "llama.cpp" / "build" / "bin" / "llama-server"))
DEFAULT_CONFIGS = [
    "f16:f16:f16",
    "q8:q8_0:q8_0",
    "balanced:q8_0:q5_1",
    "q5:q5_1:q5_1",
    "q4:q4_0:q4_0",
    "iq4:iq4_nl:iq4_nl",
]
REASONING_CHOICES = {"on", "off", "auto"}


def load_tasks(
    path: Path,
    limit: int | None,
    limit_per_category: int | None,
    categories: set[str] | None = None,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    category_counts: dict[str, int] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            task = json.loads(line)
            if categories is not None and str(task.get("category", "uncategorized")) not in categories:
                continue
            if limit_per_category is not None:
                category = str(task.get("category", "uncategorized"))
                count = category_counts.get(category, 0)
                if count >= limit_per_category:
                    continue
                category_counts[category] = count + 1
            tasks.append(task)
            if limit is not None and len(tasks) >= limit:
                break
    return tasks


def parse_cache_config(raw: str) -> dict[str, str]:
    parts = raw.split(":")
    if len(parts) == 2:
        k_type, v_type = parts
        name = f"{k_type}_{v_type}"
    elif len(parts) == 3:
        name, k_type, v_type = parts
    else:
        raise argparse.ArgumentTypeError("cache config must be K:V or NAME:K:V")
    return {"name": slug(name), "cache_type_k": k_type, "cache_type_v": v_type}


def parse_reasoning_modes(reasoning: str, sweep: str | None) -> list[str]:
    raw_modes = sweep if sweep is not None else reasoning
    modes = [mode.strip().lower() for mode in raw_modes.split(",") if mode.strip()]
    if not modes:
        raise argparse.ArgumentTypeError("at least one reasoning mode is required")
    unknown = [mode for mode in modes if mode not in REASONING_CHOICES]
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown reasoning mode(s): {', '.join(unknown)}")
    deduped: list[str] = []
    for mode in modes:
        if mode not in deduped:
            deduped.append(mode)
    return deduped


def config_for_reasoning(config: dict[str, str], reasoning: str, multi_reasoning: bool) -> dict[str, str]:
    if multi_reasoning:
        name = f"{config['name']}_reasoning_{reasoning}"
    else:
        name = config["name"]
    return {
        **config,
        "name": name,
        "base_name": config["name"],
        "reasoning": reasoning,
    }


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def score_text(task: dict[str, Any], text: str) -> dict[str, Any]:
    checks = task.get("scoring", {}).get("checks", [])
    normalized = normalize_for_contains(text)
    total = 0.0
    earned = 0.0
    details = []
    for item in checks:
        points = float(item.get("points", 1.0))
        total += points
        kind = item.get("kind")
        passed = False
        if kind == "contains_all":
            terms = [normalize_for_contains(str(term)) for term in item.get("terms", [])]
            passed = all(term in normalized for term in terms)
        elif kind == "contains_any":
            terms = [normalize_for_contains(str(term)) for term in item.get("terms", [])]
            passed = any(term in normalized for term in terms)
        elif kind == "regex":
            passed = re.search(str(item.get("pattern", "")), text, flags=re.IGNORECASE | re.MULTILINE) is not None
        elif kind == "exact":
            passed = str(item.get("text", "")) in text
        elif kind == "not_contains_any":
            terms = [normalize_for_contains(str(term)) for term in item.get("terms", [])]
            passed = not any(term in normalized for term in terms)
        elif kind == "not_contains_all":
            terms = [normalize_for_contains(str(term)) for term in item.get("terms", [])]
            passed = not all(term in normalized for term in terms)
        else:
            raise ValueError(f"unsupported check kind: {kind}")
        if passed:
            earned += points
        details.append(
            {
                "id": item.get("id"),
                "kind": kind,
                "points": points,
                "passed": passed,
            }
        )
    return {
        "score": earned / total if total else 0.0,
        "points_earned": earned,
        "points_total": total,
        "checks": details,
    }


def normalize_for_contains(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9_]+", " ", value.lower())).strip()


def find_free_port(start: int) -> int:
    for port in range(start, start + 200):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"no free port found starting at {start}")


def http_json(method: str, host: str, port: int, path: str, payload: dict[str, Any] | None, timeout: int) -> tuple[int, Any]:
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {} if payload is None else {"Content-Type": "application/json"}
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            parsed = raw.decode("utf-8", errors="replace")
        return response.status, parsed
    finally:
        conn.close()


def wait_for_server(host: str, port: int, proc: subprocess.Popen[bytes], timeout_s: int) -> None:
    deadline = time.time() + timeout_s
    last_status: Any = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited early with code {proc.returncode}")
        try:
            status, payload = http_json("GET", host, port, "/health", None, timeout=5)
            last_status = payload
            if status == 200 and isinstance(payload, dict) and payload.get("status") == "ok":
                return
        except OSError as exc:
            last_status = str(exc)
        time.sleep(2)
    raise TimeoutError(f"server did not become healthy within {timeout_s}s; last={last_status}")


def start_server(
    args: argparse.Namespace,
    config: dict[str, str],
    run_dir: Path,
    port: int,
    reasoning: str,
) -> subprocess.Popen[bytes]:
    log_path = run_dir / f"server_{config['name']}.log"
    log_file = log_path.open("wb")
    cmd = [
        args.server_bin,
        "-m",
        args.model,
        "--host",
        args.host,
        "--port",
        str(port),
        "-c",
        str(args.ctx),
        "-b",
        str(args.batch),
        "-ub",
        str(args.ubatch),
        "-np",
        "1",
        "-fa",
        args.flash_attn,
        "-ngl",
        args.ngl,
        "--cache-type-k",
        config["cache_type_k"],
        "--cache-type-v",
        config["cache_type_v"],
        "--no-cache-prompt",
        "--no-webui",
        "--metrics",
        "--reasoning",
        reasoning,
    ]
    if reasoning != "off" and args.reasoning_budget is not None:
        cmd.extend(["--reasoning-budget", str(args.reasoning_budget)])
        if args.reasoning_budget_message:
            cmd.extend(["--reasoning-budget-message", args.reasoning_budget_message])
    cmd.extend(args.server_arg)
    proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    proc._kvq_log_file = log_file  # type: ignore[attr-defined]
    proc._kvq_command = cmd  # type: ignore[attr-defined]
    return proc


def stop_server(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None:
        return
    if proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=20)
    log_file = getattr(proc, "_kvq_log_file", None)
    if log_file is not None:
        log_file.close()


def request_path(args: argparse.Namespace) -> str:
    if args.endpoint == "completion":
        return "/completion"
    if args.endpoint == "chat":
        return "/v1/chat/completions"
    raise ValueError(f"unsupported endpoint: {args.endpoint}")


def request_payload(task: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    common = {
        "n_predict": args.n_predict,
        "max_tokens": args.n_predict,
        "temperature": args.temperature,
        "top_k": args.top_k,
        "top_p": 1.0,
        "min_p": 0.0,
        "seed": args.seed,
        "cache_prompt": False,
        "timings_per_token": False,
        "stream": False,
        "stop": args.stop,
    }
    if args.endpoint == "completion":
        return {"prompt": task["prompt"], **common}
    return {
        "model": "kv-cache-eval",
        "messages": [{"role": "user", "content": task["prompt"]}],
        **common,
    }


def extract_response(payload: Any) -> tuple[str, dict[str, Any], dict[str, Any]]:
    if not isinstance(payload, dict):
        return str(payload), {}, {}
    if "content" in payload:
        timings = payload.get("timings", {})
        metrics = {
            "tokens_evaluated": payload.get("tokens_evaluated"),
            "tokens_predicted": payload.get("tokens_predicted"),
            "truncated": payload.get("truncated"),
            "stop_type": payload.get("stop_type"),
        }
        return str(payload.get("content", "")), timings if isinstance(timings, dict) else {}, metrics
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0] if isinstance(choices[0], dict) else {}
        message = first.get("message") if isinstance(first, dict) else {}
        if isinstance(message, dict):
            content = str(message.get("content", ""))
            if not content and message.get("reasoning_content"):
                content = str(message.get("reasoning_content", ""))
        else:
            content = str(first.get("text", ""))
        timings = payload.get("timings", {})
        usage = payload.get("usage", {})
        metrics = {
            "tokens_evaluated": usage.get("prompt_tokens") if isinstance(usage, dict) else None,
            "tokens_predicted": usage.get("completion_tokens") if isinstance(usage, dict) else None,
            "truncated": payload.get("truncated"),
            "stop_type": first.get("finish_reason") if isinstance(first, dict) else None,
        }
        return content, timings if isinstance(timings, dict) else {}, metrics
    return json.dumps(payload, sort_keys=True), {}, {}


def run_task(host: str, port: int, task: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    status, payload = http_json("POST", host, port, request_path(args), request_payload(task, args), timeout=args.request_timeout)
    elapsed_ms = (time.time() - started) * 1000
    if status != 200:
        return {
            "task_id": task["id"],
            "ok": False,
            "http_status": status,
            "error": payload,
            "elapsed_ms": elapsed_ms,
            "score": 0.0,
        }
    content, timings, metrics = extract_response(payload)
    scored = score_text(task, content)
    return {
        "task_id": task["id"],
        "ok": True,
        "http_status": status,
        "elapsed_ms": elapsed_ms,
        "content": content,
        "score": scored["score"],
        "points_earned": scored["points_earned"],
        "points_total": scored["points_total"],
        "checks": scored["checks"],
        "timings": timings,
        "tokens_evaluated": metrics.get("tokens_evaluated"),
        "tokens_predicted": metrics.get("tokens_predicted"),
        "truncated": metrics.get("truncated"),
        "stop_type": metrics.get("stop_type"),
    }


def summarize_config(config: dict[str, str], task_results: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [float(result.get("score", 0.0)) for result in task_results]
    prompt_tps = [
        float(result.get("timings", {}).get("prompt_per_second"))
        for result in task_results
        if isinstance(result.get("timings"), dict) and result.get("timings", {}).get("prompt_per_second") is not None
    ]
    decode_tps = [
        float(result.get("timings", {}).get("predicted_per_second"))
        for result in task_results
        if isinstance(result.get("timings"), dict) and result.get("timings", {}).get("predicted_per_second") is not None
    ]
    return {
        **config,
        "tasks": len(task_results),
        "ok_tasks": sum(1 for result in task_results if result.get("ok")),
        "mean_score": sum(scores) / len(scores) if scores else 0.0,
        "min_score": min(scores) if scores else 0.0,
        "mean_prompt_tokens_per_second": sum(prompt_tps) / len(prompt_tps) if prompt_tps else None,
        "mean_decode_tokens_per_second": sum(decode_tps) / len(decode_tps) if decode_tps else None,
    }


def write_artifacts(run_dir: Path, config: dict[str, str], task: dict[str, Any], result: dict[str, Any]) -> None:
    config_dir = run_dir / config["name"]
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / f"{task['id']}.prompt.txt").write_text(task["prompt"], encoding="utf-8")
    (config_dir / f"{task['id']}.completion.txt").write_text(str(result.get("content", "")), encoding="utf-8")
    compact = {key: value for key, value in result.items() if key != "content"}
    (config_dir / f"{task['id']}.score.json").write_text(json.dumps(compact, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_artifact_result(run_dir: Path, config: dict[str, str], task: dict[str, Any], reasoning: str) -> dict[str, Any] | None:
    score_path = run_dir / config["name"] / f"{task['id']}.score.json"
    if not score_path.exists():
        return None
    result = json.loads(score_path.read_text(encoding="utf-8"))
    result.setdefault("task_id", task["id"])
    result.setdefault("config", config)
    result.setdefault("reasoning", reasoning)
    return result


def run_score_only(tasks: list[dict[str, Any]], args: argparse.Namespace) -> int:
    text = Path(args.score_only).read_text(encoding="utf-8")
    for task in tasks:
        scored = score_text(task, text)
        print(f"{task['id']}: {scored['score']:.3f} ({scored['points_earned']}/{scored['points_total']})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
    parser.add_argument("--model", default=os.environ.get("MODEL", DEFAULT_MODEL))
    parser.add_argument("--server-bin", default=os.environ.get("LLAMA_SERVER", DEFAULT_SERVER))
    parser.add_argument("--cache-config", action="append", default=[], help="Repeatable: NAME:K:V or K:V")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--category", action="append", default=[], help="Task category to include. Repeatable.")
    parser.add_argument(
        "--limit-per-category",
        type=int,
        default=None,
        help="Balanced smoke mode: keep at most N tasks from each task category before applying --limit.",
    )
    parser.add_argument("--ctx", type=int, default=int(os.environ.get("CTX", "8192")))
    parser.add_argument("--batch", type=int, default=int(os.environ.get("BATCH", "512")))
    parser.add_argument("--ubatch", type=int, default=int(os.environ.get("UBATCH", "128")))
    parser.add_argument("--ngl", default=os.environ.get("NGL", "auto"))
    parser.add_argument("--flash-attn", default=os.environ.get("FLASH_ATTN", "on"), choices=["on", "off", "auto"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--start-port", type=int, default=18180)
    parser.add_argument("--server-timeout", type=int, default=900)
    parser.add_argument("--request-timeout", type=int, default=900)
    parser.add_argument("--n-predict", type=int, default=1024)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-k", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--stop", action="append", default=[])
    parser.add_argument("--endpoint", choices=["chat", "completion"], default="chat")
    parser.add_argument("--reasoning", choices=sorted(REASONING_CHOICES), default=os.environ.get("REASONING", "on"))
    parser.add_argument(
        "--reasoning-sweep",
        help="Comma-separated reasoning modes to run for every cache config, e.g. on,off.",
    )
    parser.add_argument(
        "--reasoning-budget",
        type=int,
        default=int(os.environ.get("REASONING_BUDGET", "256")),
        help="llama.cpp reasoning token budget for reasoning-on/auto runs. Use -1 for unlimited.",
    )
    parser.add_argument(
        "--reasoning-budget-message",
        default=os.environ.get("REASONING_BUDGET_MESSAGE", "End reasoning and answer now."),
        help="Message injected by llama.cpp when the reasoning budget is reached.",
    )
    parser.add_argument("--server-arg", action="append", default=[])
    parser.add_argument("--run-id", help="Use a fixed run directory name instead of creating a timestamped one.")
    parser.add_argument("--resume", action="store_true", help="Reuse existing per-task score artifacts in the run directory.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan and do not start servers.")
    parser.add_argument("--score-only", help="Score a completion text file against all tasks and exit.")
    args = parser.parse_args()

    categories = set(args.category) if args.category else None
    tasks = load_tasks(args.tasks, args.limit, args.limit_per_category, categories)
    if args.score_only:
        return run_score_only(tasks, args)

    reasoning_modes = parse_reasoning_modes(args.reasoning, args.reasoning_sweep)
    configs = [parse_cache_config(raw) for raw in (args.cache_config or DEFAULT_CONFIGS)]
    run_id = args.run_id or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.runs_dir / run_id

    if args.dry_run:
        print(f"tasks: {len(tasks)} from {args.tasks}")
        print(f"model: {args.model}")
        print(f"server: {args.server_bin}")
        print(f"reasoning modes: {', '.join(reasoning_modes)}")
        for config in configs:
            for reasoning in reasoning_modes:
                effective = config_for_reasoning(config, reasoning, len(reasoning_modes) > 1)
                print(
                    f"config {effective['name']}: K={effective['cache_type_k']} "
                    f"V={effective['cache_type_v']} reasoning={reasoning}"
                )
        return 0

    if not Path(args.server_bin).exists() and shutil.which(args.server_bin) is None:
        raise SystemExit(f"server binary not found: {args.server_bin}")
    if not Path(args.model).exists():
        raise SystemExit(f"model not found: {args.model}")

    run_dir.mkdir(parents=True, exist_ok=True)
    all_results: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []

    run_index = 0
    for config in configs:
        for reasoning in reasoning_modes:
            effective_config = config_for_reasoning(config, reasoning, len(reasoning_modes) > 1)
            proc: subprocess.Popen[bytes] | None = None
            task_results_by_id: dict[str, dict[str, Any]] = {}
            pending_tasks: list[dict[str, Any]] = []
            if args.resume:
                for task in tasks:
                    result = read_artifact_result(run_dir, effective_config, task, reasoning)
                    if result is None:
                        pending_tasks.append(task)
                    else:
                        task_results_by_id[task["id"]] = result
                        print(f"{effective_config['name']} {task['id']}: resume score={result.get('score', 0):.3f}")
            else:
                pending_tasks = tasks

            if pending_tasks:
                port = find_free_port(args.start_port + run_index * 10)
                run_index += 1
            else:
                print(f"{effective_config['name']}: resume complete ({len(task_results_by_id)} tasks)")
                summaries.append(summarize_config(effective_config, [task_results_by_id[task["id"]] for task in tasks]))
                all_results.extend(task_results_by_id[task["id"]] for task in tasks)
                continue

            try:
                proc = start_server(args, effective_config, run_dir, port, reasoning)
                wait_for_server(args.host, port, proc, args.server_timeout)
                for task in pending_tasks:
                    result = run_task(args.host, port, task, args)
                    result["config"] = effective_config
                    result["reasoning"] = reasoning
                    write_artifacts(run_dir, effective_config, task, result)
                    task_results_by_id[task["id"]] = result
                    print(f"{effective_config['name']} {task['id']}: score={result.get('score', 0):.3f}")
            finally:
                stop_server(proc)
            task_results = [task_results_by_id[task["id"]] for task in tasks if task["id"] in task_results_by_id]
            all_results.extend(task_results)
            summaries.append(summarize_config(effective_config, task_results))

    output = {
        "schema_version": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model": args.model,
        "server_bin": args.server_bin,
        "tasks": [task["id"] for task in tasks],
        "settings": {
            "ctx": args.ctx,
            "batch": args.batch,
            "ubatch": args.ubatch,
            "ngl": args.ngl,
            "flash_attn": args.flash_attn,
            "n_predict": args.n_predict,
            "temperature": args.temperature,
            "top_k": args.top_k,
            "seed": args.seed,
            "endpoint": args.endpoint,
            "reasoning": args.reasoning,
            "reasoning_modes": reasoning_modes,
            "reasoning_budget": args.reasoning_budget,
            "reasoning_budget_message": args.reasoning_budget_message,
        },
        "summaries": summaries,
        "results": [{key: value for key, value in result.items() if key != "content"} for result in all_results],
    }
    out_path = run_dir / "results.json"
    out_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
