# KV-Cache Quantization Agentic Eval

This repo includes a small agentic eval for KV-cache quantization. The goal is not to prove a universal winner. It is to catch the practical failure mode we care about: a cache format that looks fine on throughput or short prompts but quietly breaks long-context research, debugging, or implementation tasks.

## Research Notes

- KV cache memory grows with context length and batch size. For long-context inference, the cache can become a serving bottleneck even when model weights already fit.
- KV-cache quantization is an inference-time cache format choice, separate from model-weight quantization. It changes the stored attention keys and values produced while processing the prompt.
- K and V should be treated separately. KIVI reports different structure for the two caches and uses per-channel quantization for keys and per-token quantization for values.
- Hugging Face Transformers exposes `QuantizedCache` backends for low-bit KV cache experiments. That is a useful conceptual reference, but this repo runs the local llama.cpp surface.
- This llama.cpp build exposes separate `--cache-type-k` and `--cache-type-v` values: `f32`, `f16`, `bf16`, `q8_0`, `q4_0`, `q4_1`, `iq4_nl`, `q5_0`, `q5_1`.
- TurboQuant-style work is a reminder that inner-product distortion matters, not just MSE. Agentic evals should include exact retrieval and implementation details, because small attention errors can become confident wrong commands.

Primary sources:

- [KIVI paper](https://arxiv.org/abs/2402.02750)
- [Hugging Face Transformers KV cache docs](https://huggingface.co/docs/transformers/en/kv_cache)
- [Hugging Face KV cache quantization blog](https://huggingface.co/blog/kv-cache-quantization)
- [TurboQuant paper](https://arxiv.org/abs/2504.19874)
- [llama.cpp server docs](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)

## Generate Tasks

```bash
npm run make-kv-cache-eval
```

This writes:

- `data/kv_cache_eval/tasks.jsonl`
- `data/kv_cache_eval/sources.json`

The default dataset has four long-context agentic tasks:

- research memo
- eval implementation plan
- long-context needle with an exact marker
- quality-regression debugging diagnosis

Each task has deterministic checks. This is intentionally simple: it lets us compare cache formats with the same prompt, seed, and rubric before introducing a judge model.

## Run The Eval

```bash
npm run eval:kv-cache
```

By default the runner starts one `llama-server` per cache config, calls `/v1/chat/completions`, disables prompt-cache reuse for fairness, starts the chat template with `--reasoning on`, and writes a run directory under:

```text
data/kv_cache_eval/runs/YYYYMMDDTHHMMSSZ/
```

Each run includes:

- `results.json` with per-config summary scores and timings
- raw prompt/completion text for each task
- per-task score JSON
- server logs for each cache config

Default sweep:

```text
f16/f16
q8_0/q8_0
q8_0/q5_1
q5_1/q5_1
q4_0/q4_0
iq4_nl/iq4_nl
```

For a faster smoke run:

```bash
python3 scripts/run_kv_cache_eval.py --limit 1 --cache-config f16:f16:f16 --cache-config balanced:q8_0:q5_1
```

For a dry plan without loading the model:

```bash
python3 scripts/run_kv_cache_eval.py --dry-run
```

For a raw completion-mode experiment instead of the chat template:

```bash
python3 scripts/run_kv_cache_eval.py --endpoint completion
```

To measure reasoning-mode interaction with KV-cache quantization:

```bash
python3 scripts/run_kv_cache_eval.py --reasoning-sweep on,off
```

Reasoning-on runs use a bounded llama.cpp reasoning budget by default:

```bash
python3 scripts/run_kv_cache_eval.py --reasoning on --reasoning-budget 256 --n-predict 1024
```

## How To Read Results

Start with `f16/f16` as the quality baseline. A cache config is interesting only if it preserves task score while improving prompt/decode throughput or making a longer context/batch fit.

Blocking failures:

- lower score on the exact-marker task
- missing `--cache-type-k` / `--cache-type-v` implementation details
- plausible but wrong commands
- prompt truncation
- large quality drop versus `f16/f16`

Useful next ablations after a failure:

- K-only quantization, such as `q8_0/f16`
- V-only quantization, such as `f16/q8_0`
- balanced K/V, such as `q8_0/q5_1`
- aggressive K/V, such as `q4_0/q4_0` or `iq4_nl/iq4_nl`
