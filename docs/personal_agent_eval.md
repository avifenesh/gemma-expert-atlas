# Personal-Agent Eval

This suite turns the Hermes and Avi-ops task shape into local model eval tasks.
It is separate from the KV-cache eval, but it uses the same runner so cache type,
reasoning mode, speed, and quality can be compared on the tasks Avi actually
cares about.

## Generate Tasks

```bash
npm run make-personal-agent-eval
```

This writes:

- `data/personal_agent_eval/tasks.jsonl`
- `data/personal_agent_eval/sources.json`

The current suite has eight task families:

- personal research and interest scouting
- tool-failure recovery
- coding-agent debug loops
- quiet routine monitors
- personalization and memory hygiene
- social repair support
- agent orchestration for KV-cache eval work
- tool-call selection

The task sources are local Hermes surfaces:

- `hermes-agent/README.md`
- `hermes-agent/toolset_distributions.py`
- `hermes-agent/cron/blueprint_catalog.py`
- `~/.hermes/avi-ops-policy.json`
- `~/.hermes/avi-debugger-policy.json`

The generated prompts include summaries of those surfaces, not raw secrets or
token-bearing config.

## Run The Eval

Reasoning-on is the default, because that is the normal personal-agent mode:

```bash
npm run eval:personal-agent
```

To compare reasoning-on and reasoning-off on the same cache formats:

```bash
npm run eval:personal-agent:both
```

For a fast smoke:

```bash
python3 scripts/run_kv_cache_eval.py \
  --tasks data/personal_agent_eval/tasks.jsonl \
  --runs-dir data/personal_agent_eval/runs \
  --limit 1 \
  --cache-config balanced:q8_0:q5_1 \
  --reasoning on
```

## Expert Routing

The theme calibration generator now includes matching personal-agent themes:

- `personal_research`
- `tool_recovery`
- `routine_monitoring`
- `personalization_memory`
- `coding_agent`
- `social_support`
- `agentic_kv_cache`

Run the routing calibration when you want expert heatmaps for those task
families:

```bash
npm run calibrate:themes
```

For a smaller first pass:

```bash
THEMES=personal_research,tool_recovery,coding_agent,agentic_kv_cache npm run calibrate:themes
```
