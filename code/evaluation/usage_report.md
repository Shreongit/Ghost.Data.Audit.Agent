# Groq LLM usage report

The Groq provider was exercised using `GROQ_API_KEY` only in child-process environments. The key is not stored in repository files, logs, reports, or the archive. An authenticated `GET /models` succeeded; model IDs and listed prices below came from that response.

## Models and rates

| Model ID | Selected role | Listed modalities/features | Input price / 1M tokens | Output price / 1M tokens |
|---|---|---|---:|---:|
| `qwen/qwen3.8-27b` | Fast; PNG vision | text, image; JSON mode | $0.80 | $4.00 |
| `openai/gpt-oss-120b` | Strong; structured investigation | text; structured outputs | $0.15 | $0.60 |

These are the per-token rates returned by the authenticated Groq `/models` endpoint at run time. Pricing was available, so the estimates use those rates. Successful text and structured responses are cached; cache hits do not issue another inference request.

## Smoke checks

| Check | Result | Successful calls | Input / output tokens | Estimated cost |
|---|---|---:|---:|---:|
| Plain text | Passed | 1 | 17 / 2 | $0.00002160 |
| JSON Schema | Passed with `openai/gpt-oss-120b` | 1 | 210 / 58 | $0.00006630 |
| Image on one PNG | Passed with `qwen/qwen3.8-27b`; image input accepted | 1 | 1,866 / 48 | $0.00168480 |
| **Smoke total** | | **3** | **2,093 / 108** | **$0.00177270** |

## Public-sample ablation

| Mode | Status accuracy | Step F1 | Exact sequences | Successful calls | Input / output tokens | Cost |
|---|---:|---:|---:|---:|---:|---:|
| `--no-llm` | 32/32 (100%) | 91.67% | 18/32 | 0 | 0 / 0 | $0.00 |
| Groq live path | 32/32 (100%) | 91.67% | 18/32 | 78 | 72,790 / 27,525 | $0.04075195 |

The live sample matched the deterministic baseline, so it passed the non-regression gate. An initial run let the intent classifier override deterministic authorization for one request and scored 31/32. A general conflict guard now preserves deterministic intent when the model disagrees; the final live sample matches the baseline.

## Final full-dataset run

Command: `python code/main.py --llm --link-agent-max-cases 25`  
Requests: **518**. The first production pass took **70.544 seconds**; the byte-for-byte replay took **29.085 seconds** and reproduced the same SHA-256 output.  
Across both passes: **18 new inference completions**, **223 cache hits**, **5 HTTP 429 retries**; **15,569 input** and **2,019 output tokens**; estimated cost **$0.01508530**.  
Average across the two passes: **33.95 model tokens per request** and **$0.00002912 per request**.

The vision model inspected all **11 PNGs** against cached Tesseract text: **5 agreed, 3 mismatched, and 3 showed OCR omissions**. Images were accepted. The VLM returned no additional verified facts from the screenshots. The fast model rejected strict JSON Schema output, so calls used JSON-mode fallback with local schema validation and repair.

The bounded investigator considered at most 25 ambiguous cases: **9 accepted, 9 rejected, 5 unresolved, and 2 skipped after provider errors** (payload-too-large and bad-request responses). Successful investigator completions across the workflow: **73**. Successful low-confidence classifier completions: **9 intent** and **7 category**. Authorization disagreements retained the deterministic decision.

## Cumulative successful inference ledger

Across smoke checks, sample ablation, full run, and replay: **99 successful inference completions**, **90,452 input tokens**, **29,652 output tokens**, **120,104 total tokens**, and **$0.05760995** estimated cost. Average across 518 evaluation requests: **231.86 tokens** and **$0.00011122 per request**.

| Model | Successful calls | Input tokens | Output tokens | Estimated cost |
|---|---:|---:|---:|---:|
| openai/gpt-oss-120b | 74 | 56,437 | 28,434 | $0.02552595 |
| qwen/qwen3.8-27b | 25 | 34,015 | 1,218 | $0.03208400 |
| **Overall** | **99** | **90,452** | **29,652** | **$0.05760995** |

Response modes: **25 JSON Schema**, **73 JSON-mode fallback**, **1 plain text**. The fallback includes a rejected schema-format request followed by a JSON-mode request; only successful completions appear in the token ledger. Additional HTTP errors and 429 retries return no completion-token usage and are reported separately above. The xAI provider remains available separately.
