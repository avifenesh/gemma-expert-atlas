# Gemma Expert Atlas

Static inspection, routing analysis, and conservative expert-surgery tracking
for Gemma 4 26B A4B MoE checkpoints.

This repo is not a benchmark leaderboard. It is a working atlas for answering a
narrow question: which Gemma MoE experts look safe enough to probe, and which
triage decisions have already been rejected, held, or promoted for more eval?

## Public docs

- [Expert surgery loop](docs/expert_surgery_loop.md): project purpose,
  experiment protocol, eval gates, and artifact map.
- [Expert triage decision ledger](docs/expert_triage_ledger.md): durable record
  of decisions made so far and the format for future entries.
- [Personal-agent eval](docs/personal_agent_eval.md): task map and
  expert-routing workflow for the local personal-agent workload.
- [KV-cache quantization eval](docs/kv_cache_quant_eval.md): separate
  long-context cache-format eval notes.

## Publication note

Raw model outputs, eval run directories, local GGUF copies, and surgery-model
manifests are ignored by default. The curated reports and dashboard JSON are the
public evidence trail. Combined routing bundles are lightweight indexes; full
expert arrays live in the per-trace JSON files and are lazy-loaded by the UI.

Some generated task banks intentionally include Avi-specific personal-agent
profile text because that is the workload being studied. Review or anonymize
those files before publishing if the repo should become a fully generic public
artifact.

The first pass maps the local HF safetensors checkpoint without loading weights. It reads only:

- `config.json`
- `model.safetensors.index.json`
- safetensors file headers

## Generate the manifest

```bash
npm run inspect
```

The output lands at:

```text
public/data/expert_manifest.json
```

## Run the dashboard

```bash
npm run dev
```

The dashboard opens on the static expert map and lazy-loads aggregate or
theme-specific routing traces only when a lens needs the full expert counts.

## Routing traces

Aggregate reasoning traces:

```bash
npm run calibrate:all
```

Theme x reasoning traces:

```bash
npm run calibrate:themes
```

The theme runner creates paired corpora for ML, coding, debugging, website building, io_uring writing, code testing, tool calling, math, factual knowledge, psychology, relationship help, agent orchestration, MoE training, and Hermes-shaped personal-agent work. Each theme is run twice: `reasoning_off` and `reasoning_on`. Temporary imatrix GGUF files are deleted after import; the durable outputs are per-trace JSON files under `public/data/*_traces/` plus slim index bundles under `public/data/`.

## KV-cache quantization eval

Generate the agentic KV-cache eval tasks:

```bash
npm run make-kv-cache-eval
```

Run the llama.cpp cache-format sweep:

```bash
npm run eval:kv-cache
```

The eval compares `--cache-type-k` / `--cache-type-v` pairs on long-context research, implementation, needle, and debugging tasks. See [docs/kv_cache_quant_eval.md](docs/kv_cache_quant_eval.md) for the research notes, default cache matrix, and result schema.

## Personal-agent eval

Generate the Hermes-shaped personal-agent eval tasks:

```bash
npm run make-personal-agent-eval
```

Run the local model on personal research, tool recovery, coding-agent loops, routine monitoring, personalization memory, social support, orchestration, and tool-call selection:

```bash
npm run eval:personal-agent
```

To compare reasoning-on and reasoning-off:

```bash
npm run eval:personal-agent:both
```

See [docs/personal_agent_eval.md](docs/personal_agent_eval.md) for the task map and expert-routing workflow.

## Expert surgery loop

Generate a larger personal-agent task bank from Hermes-style tasks and recurring Codex work:

```bash
npm run make-personal-agent-bank
```

Create matching routing corpora:

```bash
npm run make-personal-agent-corpora
```

Run routing calibration for the personal-agent families:

```bash
npm run calibrate:personal-agent
```

Classify experts as globally dead, cold trim candidates, low-use merge candidates, ordinary, task-hot protected, or always-hot protected:

```bash
npm run analyze:experts
```

Create the trim/merge/add experiment plan:

```bash
npm run plan:surgery
```

Create a same-layer HF checkpoint blend before re-quantizing:

```bash
npm run blend:hf-expert -- --base-expert L08.E054 --donor-expert L08.E018 --donor-weight 0.25
```

This patches the HF/safetensors checkpoint in BF16 chunks as
`0.75 * L08.E054 + 0.25 * L08.E018`. Quantize the blended checkpoint to GGUF,
then run the focused guard before the full personal-agent bank.

The full setup pipeline is:

```bash
npm run pipeline:surgery
```

Use `RUN_CALIBRATION=1 npm run pipeline:surgery` when you want fresh routing traces. See [docs/expert_surgery_loop.md](docs/expert_surgery_loop.md) for the caveats and eval gates.

The running expert-surgery decisions are recorded in
[docs/expert_triage_ledger.md](docs/expert_triage_ledger.md). Update that ledger
when a probe is accepted, rejected, held yellow, or promoted to a broader eval.
